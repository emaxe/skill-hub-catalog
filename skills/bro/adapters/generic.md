# Generic Adapter (Fallback)

## Runtime Detection

This adapter activates when **no specific client** is detected (Claude, Codex, Kimi, Copilot). It serves as the universal fallback for:
- Qwen (Alibaba)
- DeepSeek
- GLM (Zhipu AI)
- Local LLMs (Ollama, LM Studio, vLLM, etc.)
- Custom API endpoints
- Any other tool-use-capable LLM environment

> **Detection confidence:** Low — this is the default catch-all. The user may be running a custom setup.

## Execution Strategy: `external-process`

Generic environments typically provide one or more of the following:
- An API endpoint (OpenAI-compatible, or custom)
- A CLI tool
- A Python/Node.js SDK
- Basic function/tool calling support

The recommended strategy is an **external orchestrator script** (Python or Node.js) that implements the `bro` protocol by calling the LLM API with role-specific system prompts. This script replaces the native Orchestrator agent and manages the entire pipeline.

---

## Launch Methods (in order of preference)

### Method 1: External Orchestrator Script (recommended)

Implement a small Python or Node.js script (`bro-generic-orchestrator`) that:

1. **Reads configuration:**
   - `.bro/config.json` or env vars (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`)
   - Detects the API type (OpenAI-compatible, Ollama, custom)

2. **Reads role files:** From `bro/` skill directory (`analyst.md`, `architect.md`, etc.)

3. **Executes the pipeline:**
   ```
   For each role in the selected pipeline:
     a. Read task tracker state
     b. Build system prompt = role.md + inlined skills + task context
     c. Call LLM API with tool definitions (read, edit, bash if supported)
     d. Parse response (may require tool call loop)
     e. Update task tracker
     f. Decide next role or return for rework
   ```

4. **Manages the task tracker:** File-based JSON or Markdown.

**Example minimal Python orchestrator:**

```python
import os, json, openai
from pathlib import Path

class BroGenericOrchestrator:
    def __init__(self, model, api_key, base_url=None):
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.task_tracker = {}

    def load_role(self, role_name):
        return Path(f"bro/{role_name}.md").read_text()

    def dispatch(self, role, task, context):
        system = self.load_role(role)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"TASK: {task}\n\nCONTEXT:\n{context}"}
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[...]  # if tool use is supported
        )
        return response.choices[0].message.content

    def run(self, task, pipeline):
        results = {}
        for role in pipeline:
            result = self.dispatch(role, task, results)
            results[role] = result
            self.save_tracker(role, result)
        return results
```

**Deployment options:**
- **Local:** Run as a Python script in the project directory.
- **CI/CD:** Integrate into GitHub Actions / GitLab CI for automated code reviews or testing.
- **Web service:** Run as a FastAPI/Flask endpoint for team-wide `bro` access.

### Method 2: CLI Tool per Role (manual)

If a CLI tool is available for the LLM (e.g., `ollama run`, `qwen-cli`, `deepseek-chat`), use it sequentially:

```bash
# Analyst
ollama run qwen2.5 "$(cat analyst.md)

TASK: $TASK
CONTEXT: $CONTEXT" > analyst_result.md

# Architect
ollama run qwen2.5 "$(cat architect.md)

TASK: $TASK
CONTEXT: $(cat analyst_result.md)" > architect_result.md
```

**Script wrapper:**
Write a shell script (`bro-run.sh`) that automates the above for any LLM CLI.

**Limitations:**
- No tool calling (unless CLI supports it).
- No parallel execution (unless shell background jobs are used).
- Manual error handling.
- No built-in retry logic.

### Method 3: Single-Session Context Switch (if API supports long context)

Similar to the Kimi adapter. If the generic LLM has a large context window (>64K tokens), use a single API session and explicitly switch roles in the prompt.

```
[SYSTEM] You are the Analyst. Follow these instructions...
[USER] TASK: ...
[ASSISTANT] [analysis result]
[SYSTEM] You are now the Architect. Follow these instructions...
[USER] CONTEXT: [analysis] TASK: Design...
```

**Trade-offs:**
- Same as Kimi Method 4: risk of role bleed, context pollution.
- Only suitable for high-capacity models.

---

## Task Tracker

File-based only. No native equivalents in generic environments.

**Path:** `.bro/tasks/{task-id}/tracker.json`

**Format:** JSON is recommended for programmatic access by the orchestrator script.

```json
{
  "task_id": "string",
  "status": "pending | in_progress | completed | failed",
  "pipeline": ["analyst", "architect", "developer", "code-reviewer", "tester"],
  "current_role": "string | null",
  "completed_roles": ["string"],
  "results": {
    "analyst": "string",
    "architect": "string",
    "developer": "string",
    "code-reviewer": "string",
    "tester": "string"
  },
  "verdicts": {
    "reviewer": "APPROVE | NEEDS_WORK | REJECT",
    "code-reviewer": "APPROVE | NEEDS_WORK | REJECT",
    "tester": "PASS | NEEDS_WORK | FAIL"
  },
  "blockers": ["string"],
  "iterations": 0,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

The orchestrator script is responsible for reading and writing this file between every role dispatch.

---

## Skill Assignment (Generic-specific)

No `Skill` tool. Skills are inlined into system prompts or orchestrator script configuration.

**Best practice:**
1. At orchestrator startup, scan `.claude/skills/` and `bro/` directories.
2. Build a skill registry: `{"skill-name": "file-contents"}`.
3. When dispatching a role, append relevant skill contents to the system prompt.

**Example skill inclusion in system prompt:**
```
[ROLE INSTRUCTIONS]
...

[ADDITIONAL SKILL DIRECTIVES]
- Test-Driven Development: Write tests before implementation. Run tests. Confirm failure. Implement. Confirm pass.
- Systematic Debugging: Reproduce the bug. Isolate the cause. Form a hypothesis. Apply fix. Verify resolution.
```

**External registry fallback (`skills.sh`):** If a skill is missing locally, the Orchestrator should attempt the `skills-hub-integrator` workflow (read `skills-hub-integrator.md` from this skill directory): run `npx skills find <skill>`, select the best match (official repos first, then highest install count), install with `npx skills add <owner/repo> -y`, then re-read the file from `.claude/skills/`. If installation succeeds, include the full skill content in the system prompt. If it fails or `skills.sh` is unavailable, include a short note in the system prompt: `[Skill <name> unavailable locally and on skills.sh]` and notify the user.

**For LLMs with limited context:** Provide only the most critical skill directives (1–2 sentences each) rather than full skill files.

---

## Context Forwarding (Generic-specific optimizations)

- **Assume limited context:** Unless the model is known to have >64K context, aggressively summarize (200–500 words per prior role).
- **Structured output:** Request JSON or markdown from the LLM for easier parsing by the orchestrator script.
- **Tool use:** If the LLM supports function calling, define tools for `read_file`, `write_file`, `run_bash`, `list_directory`. This gives the sub-agent autonomy similar to Claude Code.
- **No tool use:** If the LLM does not support tools, the orchestrator must manually handle file operations (e.g., the LLM returns a code block, the script writes it to the file).

---

## Generic-native Features (optional enhancements)

| Feature | When to use |
|---|---|
| Local model (Ollama) | Offline development, privacy-sensitive code. Slower but fully local. |
| Custom fine-tuned model | If you have a model fine-tuned for specific roles (e.g., a "code reviewer" model). |
| API chaining | Use different models for different roles (e.g., cheap model for analyst, strong model for developer). |
| Quantized models | For limited hardware. May reduce role execution quality. |

---

### Failure Handling

If the LLM API returns an error (5xx, 429, timeout, or connection failure):
1. Log the failure in the task tracker under `failures`.
2. Retry with exponential backoff (1s, 2s, 4s) up to 3 times.
3. If still failing, check `LLM_BASE_URL` and `LLM_API_KEY`. If the endpoint is permanently down, switch to a local model (Ollama) if available, or abort and notify the user.
4. If a skill is missing locally and `skills.sh` is unreachable, inline a condensed version of the skill directive (1–2 sentences) and log the missing skill.
5. If the orchestrator script crashes (unhandled exception), write the current task tracker to disk before exiting, and notify the user with the traceback.

## Adapter Status: `experimental`

This is the fallback adapter. It requires the most setup (external orchestrator script). Recommended for advanced users, CI/CD pipelines, or teams using non-standard LLM infrastructure. For most users, Claude, Codex, or Kimi adapters are preferable.

---

## Quick-Start Script Template

A minimal Python script template is available at `bro/scripts/generic-orchestrator-template.py` (to be created). Copy it, set your API key, and run:

```bash
python bro-generic.py --task "Implement auth system" --pipeline analyst,architect,critic,developer,tester
```

This template implements the full `bro` dispatch loop with file-based task tracking and basic error handling.
