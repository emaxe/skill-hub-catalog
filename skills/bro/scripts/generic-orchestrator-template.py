#!/usr/bin/env python3
"""
Bro Generic Orchestrator — Template
====================================
A minimal, extensible Python script that implements the `bro` multi-agent
dispatch loop for generic / non-standard LLM environments (Qwen, DeepSeek,
GLM, local models via Ollama, etc.).

Usage:
    python generic-orchestrator.py \
        --task "Implement authentication system" \
        --pipeline analyst,architect,developer,tester \
        --model qwen2.5:14b \
        --base-url http://localhost:11434/v1 \
        --api-key dummy

Environment:
    BRO_SKILL_DIR    Path to the `bro` skill directory (default: .claude/skills/bro)
    LLM_API_KEY      API key (can be overridden by --api-key)
    LLM_BASE_URL     Base URL for OpenAI-compatible API
    LLM_MODEL        Model name

Requirements:
    pip install openai
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Skills Hub Integrator — External registry fallback (skills.sh)
# ---------------------------------------------------------------------------

_skills_hub_prerequisites_cache: dict[str, Any] | None = None


def check_skills_hub_prerequisites() -> dict[str, Any]:
    """Check prerequisites for skills.sh CLI. Caches result per process."""
    global _skills_hub_prerequisites_cache
    if _skills_hub_prerequisites_cache is not None:
        return _skills_hub_prerequisites_cache

    steps = [
        ("node", ["node", "--version"]),
        ("npm", ["npm", "--version"]),
        ("npx", ["npx", "--version"]),
        ("skills CLI", ["npx", "skills", "--version"]),
    ]
    for name, cmd in steps:
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=True)
        except Exception as exc:
            _skills_hub_prerequisites_cache = {"ok": False, "reason": f"{name} unavailable ({' '.join(cmd)} failed: {exc})"}
            return _skills_hub_prerequisites_cache
    _skills_hub_prerequisites_cache = {"ok": True}
    return _skills_hub_prerequisites_cache


def resolve_skill_from_skills_hub(skill_name: str) -> dict[str, Any]:
    """Attempt to resolve a skill from skills.sh (external registry).

    Steps: prerequisites -> find -> select -> install -> verify.
    Returns dict with keys: success (bool), skill_path (Path|None), owner_repo (str|None), reason (str|None).
    """
    pre = check_skills_hub_prerequisites()
    if not pre["ok"]:
        return {"success": False, "reason": f"skills.sh prerequisites failed: {pre['reason']}"}

    # 1. Search
    try:
        find_output = subprocess.run(
            ["npx", "skills", "find", skill_name],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout
    except Exception as exc:
        return {"success": False, "reason": f"npx skills find failed: {exc}"}

    if not find_output or not find_output.strip():
        return {"success": False, "reason": f'No results on skills.sh for "{skill_name}"'}

    # 2. Select best match — parse first line that looks like "owner/repo@skill"
    import re
    lines = [l for l in find_output.split("\n") if l.strip()]
    selected = None
    official_repos = ["anthropics/skills", "vercel-labs/agent-skills", "obra/superpowers", "microsoft/azure-skills"]
    for line in lines:
        match = re.match(r"([\w-]+/[\w-]+)(?:@([\w-]+))?", line.strip())
        if match:
            owner_repo = match.group(1)
            skill = match.group(2) or skill_name
            is_official = any(owner_repo.startswith(r) for r in official_repos)
            if not selected or is_official:
                selected = {"owner_repo": owner_repo, "skill": skill}
                if is_official:
                    break
    if not selected:
        return {"success": False, "reason": f'Could not parse any valid owner/repo from skills.sh search results for "{skill_name}"'}

    # 3. Install
    install_cmd = ["npx", "skills", "add", selected["owner_repo"], "-y"]
    try:
        subprocess.run(install_cmd, capture_output=True, text=True, timeout=60, check=True)
    except Exception as exc:
        return {"success": False, "reason": f"Installation failed ({' '.join(install_cmd)}): {exc}", "attempted": selected["owner_repo"]}

    # 4. Verify — check standard skill directories
    search_paths = []
    for base in _get_skill_search_paths():
        search_paths.extend([
            base / skill_name / "SKILL.md",
            base / f"{skill_name}.md",
        ])
    for _ in range(2):
        for p in search_paths:
            if p.exists():
                return {"success": True, "skill_path": p, "owner_repo": selected["owner_repo"]}
        # Wait briefly for async filesystem sync on first attempt
        time.sleep(1)
    return {"success": False, "reason": f"Installed {selected['owner_repo']} but skill file not found in expected paths.", "attempted": selected["owner_repo"]}



# Lazily import openai so the module can be imported for testing without it.
_openai = None


def _get_openai():
    global _openai
    if _openai is None:
        try:
            import openai as _oa
            _openai = _oa
        except ImportError as exc:
            raise ImportError(
                "`openai` package is not installed. Install it with: pip install openai"
            ) from exc
    return _openai


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BRO_SKILL_DIR = Path(os.environ.get("BRO_SKILL_DIR", ".claude/skills/bro"))
TASK_DIR = Path(".bro/tasks")

# Standard skill search paths (resolved relative to BRO_SKILL_DIR)
_DEFAULT_SKILL_SEARCH_PATHS = [
    BRO_SKILL_DIR.parent,                       # e.g. .claude/skills/
    BRO_SKILL_DIR.parent.parent / ".agents" / "skills",  # e.g. .agents/skills/
]


def _get_skill_search_paths() -> list[Path]:
    """Return ordered list of directories to search for skills.

    Priority:
    1. SKILLS_SEARCH_PATHS env variable (CSV of absolute or relative paths)
    2. Standard paths derived from BRO_SKILL_DIR
    """
    env_paths = os.environ.get("SKILLS_SEARCH_PATHS", "")
    if env_paths.strip():
        return [Path(p.strip()) for p in env_paths.split(",") if p.strip()]
    return _DEFAULT_SKILL_SEARCH_PATHS


def load_role(role_name: str) -> str:
    """Read a role instruction file from the bro skill directory."""
    path = BRO_SKILL_DIR / f"{role_name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Role file not found: {path}")
    return path.read_text(encoding="utf-8")


def load_skill(skill_name: str) -> str | None:
    """Read a skill file if available (for inlining).

    Searches in directories listed by _get_skill_search_paths().
    Looks for: {skill_name}/SKILL.md and {skill_name}.md in each directory.
    """
    for base in _get_skill_search_paths():
        candidates = [
            base / skill_name / "SKILL.md",
            base / f"{skill_name}.md",
        ]
        for p in candidates:
            if p.exists():
                return p.read_text(encoding="utf-8")
    return None


# ---------------------------------------------------------------------------
# Quick Scope Scan — Heuristic for pipeline selection
# ---------------------------------------------------------------------------

def quick_scope_scan(task: str) -> dict[str, Any]:
    """Return a heuristic scope estimate based on the task description.

    This is a lightweight stub. In production, extend it with:
    - glob/grep over the codebase using keywords extracted from the task
    - static analysis (AST) to count affected modules
    - LLM-based summarization of the task into keywords

    Returns a dict with keys:
        - estimated_scope: "small" | "medium" | "large"
        - affected_files: list[str] (placeholder; real impl would return actual paths)
        - keywords: list[str] (extracted keywords from the task)
        - heuristic: str (explanation of the decision)
    """
    task_lower = task.lower()

    # Keyword-based heuristics
    small_signals = ["fix bug", "fix typo", "refactor", "update test", "add log", "rename ", "lint", "format"]
    large_signals = [
        "new module", "new service", "architecture", "redesign", "restructure",
        "microservice", "database migration", "api v", "breaking change",
    ]

    small_hits = sum(1 for s in small_signals if s in task_lower)
    large_hits = sum(1 for s in large_signals if s in task_lower)

    # Simple keyword extraction (split by non-word, take 3-12 char tokens)
    import re
    tokens = re.findall(r"[a-zA-Z_]{3,}", task)
    keywords = sorted(set(t.lower() for t in tokens if t.lower() not in {
        "the", "and", "for", "with", "from", "that", "this", "you", "are",
        "must", "should", "will", "can", "add", "new", "fix", "bug", "use",
    }))[:10]

    if large_hits > 0:
        scope = "large"
        heuristic = f"Large-signal keywords matched ({large_hits}): {large_signals[:large_hits]}"
    elif small_hits > 0:
        scope = "small"
        heuristic = f"Small-signal keywords matched ({small_hits}): {small_signals[:small_hits]}"
    else:
        # Default to medium if ambiguous
        scope = "medium"
        heuristic = "No strong scope signals; defaulting to medium."

    return {
        "estimated_scope": scope,
        "affected_files": [],  # TODO: populate with actual glob/grep results
        "keywords": keywords,
        "heuristic": heuristic,
    }


# ---------------------------------------------------------------------------
# Token Budget
# ---------------------------------------------------------------------------

class TokenBudget:
    """Track token usage across pipeline stages and enforce budget limits."""

    def __init__(self, total_limit: int | None = None, warn_threshold: float = 0.8):
        self.total_limit = total_limit or int(os.environ.get("BRO_TOKEN_BUDGET", 100000))
        self.warn_threshold = warn_threshold
        self.spent = 0
        self._by_role: dict[str, dict] = {}

    def record_usage(self, tokens: int, role: str | None = None, prompt_tokens: int = 0, completion_tokens: int = 0):
        """Record token usage. If role is given, also record per-role breakdown."""
        self.spent += tokens
        if role:
            self._by_role.setdefault(role, {"prompt": 0, "completion": 0, "total": 0})
            self._by_role[role]["prompt"] += prompt_tokens or 0
            self._by_role[role]["completion"] += completion_tokens or 0
            self._by_role[role]["total"] += tokens

    def remaining(self) -> int:
        return max(0, self.total_limit - self.spent)

    def is_within_budget(self) -> bool:
        return self.spent <= self.total_limit

    def is_over_threshold(self) -> bool:
        return self.spent >= self.total_limit * self.warn_threshold

    def estimate_prompt_tokens(self, text: str) -> int:
        """Rough heuristic: ~1 token per 4 characters (English)."""
        return max(1, len(text) // 4)

    def to_dict(self) -> dict:
        return {
            "total_budget": self.total_limit,
            "total_spent": self.spent,
            "by_role": self._by_role,
            "status": "hard_stop" if not self.is_within_budget() else ("warning_80%" if self.is_over_threshold() else "within_budget"),
        }


# ---------------------------------------------------------------------------
# Task Tracker
# ---------------------------------------------------------------------------

class TaskTracker:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.task_dir = TASK_DIR / task_id
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.tracker_path = self.task_dir / "tracker.json"
        self._data = self._load()
        self._save()

    def _load(self) -> dict:
        if self.tracker_path.exists():
            return json.loads(self.tracker_path.read_text(encoding="utf-8"))
        return {
            "task_id": self.task_id,
            "status": "pending",
            "pipeline": [],
            "current_role": None,
            "completed_roles": [],
            "results": {},
            "verdicts": {},
            "blockers": [],
            "iterations": 0,
            "token_usage": TokenBudget().to_dict(),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def _save(self):
        self._data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.tracker_path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def start_role(self, role: str):
        self._data["status"] = "in_progress"
        self._data["current_role"] = role
        self._data["iterations"] += 1
        self._save()

    def record_rework(self, role: str):
        """Increment the rework count for a given role/stage."""
        self._data.setdefault("rework_count", {})
        self._data["rework_count"][role] = self._data["rework_count"].get(role, 0) + 1
        self._save()

    def finish_role(self, role: str, result: str, verdict: str = "PENDING", token_usage: dict | None = None):
        self._data["completed_roles"].append(role)
        self._data["results"][role] = result
        self._data["verdicts"][role] = verdict
        self._data["current_role"] = None
        if token_usage:
            self._data["token_usage"] = token_usage
        self._save()

    def set_blockers(self, blockers: list[str]):
        self._data["blockers"] = blockers
        self._save()

    def set_status(self, status: str):
        self._data["status"] = status
        self._save()

    @property
    def data(self) -> dict:
        return self._data


# ---------------------------------------------------------------------------
# LLM Dispatch
# ---------------------------------------------------------------------------

class LLMClient:
    def __init__(self, model: str, api_key: str, base_url: str | None = None):
        self.model = model
        openai = _get_openai()
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = openai.OpenAI(**kwargs)

    def chat(self, system: str, user: str, max_tokens: int = 8000, timeout: int = 300) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class BroOrchestrator:
    def __init__(self, llm: LLMClient, tracker: TaskTracker, task: str, skills: list[str] | None = None):
        self.llm = llm
        self.tracker = tracker
        self.task = task
        self.skills = skills or []
        self.results: dict[str, str] = {}

    def _build_system_prompt(self, role: str) -> str:
        role_text = load_role(role)
        skill_blocks = []
        for s in self.skills:
            skill_text = load_skill(s)
            if skill_text:
                skill_blocks.append(f"--- SKILL: {s} ---\n{skill_text}\n--- END SKILL ---")
            else:
                # Attempt external registry fallback via skills.sh
                external = resolve_skill_from_skills_hub(s)
                if external.get("success") and external.get("skill_path"):
                    skill_path = external["skill_path"]
                    skill_text = skill_path.read_text(encoding="utf-8")
                    skill_blocks.append(
                        f"--- SKILL: {s} (fetched from skills.sh: {external['owner_repo']}) ---\n"
                        f"{skill_text}\n--- END SKILL ---"
                    )
                    # Log in tracker
                    self.tracker._data.setdefault("external_dependencies", []).append(
                        {
                            "source": "skills.sh",
                            "skill": s,
                            "owner_repo": external["owner_repo"],
                            "status": "SUCCESS",
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        }
                    )
                else:
                    reason_suffix = external.get("reason", "")
                    if reason_suffix:
                        reason_suffix = f": {reason_suffix}"
                    skill_blocks.append(
                        f"--- SKILL: {s} ---\n[Skill not found locally or on skills.sh{reason_suffix}]\n--- END SKILL ---"
                    )
                    self.tracker._data.setdefault("external_dependencies", []).append(
                        {
                            "source": "skills.sh",
                            "skill": s,
                            "status": "FAILED",
                            "reason": external.get("reason", "unknown"),
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        }
                    )
        system = role_text
        if skill_blocks:
            system += "\n\n## Inlined Skill Directives\n\n" + "\n\n".join(skill_blocks)
        return system

    def _build_user_prompt(self, role: str, previous_results: dict[str, str]) -> str:
        context_parts = []
        for prev_role, result in previous_results.items():
            summary = result[:4000] if len(result) > 4000 else result
            context_parts.append(f"### {prev_role.upper()} RESULT:\n{summary}\n")
        context = "\n".join(context_parts) if context_parts else "No previous context."
        return (
            f"TASK: {self.task}\n\n"
            f"CONTEXT FROM PREVIOUS ROLES:\n{context}\n\n"
            f"Your role is {role}. Execute according to your role instructions. "
            f"Return a structured report."
        )

    def dispatch_role(self, role: str) -> str:
        self.tracker.start_role(role)
        print(f"\n>>> Dispatching role: {role}")
        system = self._build_system_prompt(role)
        user = self._build_user_prompt(role, self.results)
        result = self.llm.chat(system, user)

        # Handle ERROR responses: retry once, then skip or abort
        if result.startswith("ERROR:"):
            print(f"!!! {role} returned ERROR. Retrying once with backoff...")
            time.sleep(5)
            result = self.llm.chat(system, user)
            if result.startswith("ERROR:"):
                self.tracker._data.setdefault("failures", []).append({
                    "role": role,
                    "error": result,
                    "action": "retry_exhausted",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })
                # For non-critical roles, skip; for critical roles, raise
                if role in ("architect", "reviewer"):
                    raise RuntimeError(f"Critical role {role} failed after retry: {result}")
                print(f"!!! {role} failed after retry. Skipping.")
                result = f"[SKIPPED due to error after retry: {result}]"

        self.results[role] = result
        self.tracker.finish_role(role, result)
        print(f"<<< {role} completed. Output length: {len(result)} chars")
        return result

    MAX_ITERATIONS = 10

    def run_pipeline(self, pipeline: list[str]) -> dict[str, str]:
        self.tracker._data["pipeline"] = pipeline
        self.tracker.set_status("in_progress")
        for role in pipeline:
            if self.tracker.data.get("iterations", 0) >= self.MAX_ITERATIONS:
                raise RuntimeError(
                    f"Pipeline aborted: exceeded MAX_ITERATIONS ({self.MAX_ITERATIONS}). "
                    "Escalate to the user to simplify the task or accept the current result."
                )
            self.dispatch_role(role)
        self.tracker.set_status("completed")
        return self.results


def main():
    parser = argparse.ArgumentParser(description="Bro Generic Orchestrator")
    parser.add_argument("--task", required=True, help="User task description")
    parser.add_argument(
        "--pipeline",
        default="analyst,developer,tester",
        help="Comma-separated list of roles (default: analyst,developer,tester)",
    )
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL", "gpt-4o"), help="LLM model name")
    parser.add_argument("--api-key", default=os.environ.get("LLM_API_KEY"), help="API key")
    parser.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL"), help="OpenAI-compatible base URL")
    parser.add_argument("--task-id", default=None, help="Task ID (default: auto-generated)")
    parser.add_argument("--skills", default="", help="Comma-separated skill names to inline")
    args = parser.parse_args()

    if not args.api_key:
        print("ERROR: --api-key or LLM_API_KEY required")
        sys.exit(1)

    pipeline = [r.strip() for r in args.pipeline.split(",")]
    skills = [s.strip() for s in args.skills.split(",") if s.strip()]
    task_id = args.task_id or f"task-{int(time.time())}"

    tracker = TaskTracker(task_id)
    llm = LLMClient(model=args.model, api_key=args.api_key, base_url=args.base_url)
    orchestrator = BroOrchestrator(llm, tracker, args.task, skills=skills)

    print(f"=== Bro Generic Orchestrator ===")
    print(f"Task ID : {task_id}")
    print(f"Model   : {args.model}")
    print(f"Pipeline: {pipeline}")
    print(f"Skills  : {skills}")
    print(f"Tracker : {tracker.tracker_path}")
    print("=" * 40)

    results = orchestrator.run_pipeline(pipeline)

    print("\n=== ALL ROLES COMPLETE ===")
    for role, result in results.items():
        out_path = tracker.task_dir / f"{role}_result.md"
        out_path.write_text(result, encoding="utf-8")
        print(f"  {role}: {out_path}")
    print(f"\nTracker: {tracker.tracker_path}")


if __name__ == "__main__":
    try:
        import openai  # noqa: F401
    except ImportError:
        print("ERROR: `openai` package not installed. Run: pip install openai")
        sys.exit(1)
    main()
