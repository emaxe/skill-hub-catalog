# Codex Adapter

## Runtime Detection

This adapter activates when any of the following are detected:
- `codex` CLI is available in `PATH`
- `CODEX_API_KEY` environment variable is set
- `.codex/` directory exists in the project root

> **Detection confidence:** High — Codex CLI and env vars are unique identifiers.

## Execution Strategy: `api-session`

Codex provides a powerful agent mode via CLI and API. It supports parallel tool calls (via `responses` API with multiple tools), built-in code interpreter, and file search. However, it does **not** have a native `Agent` tool like Claude Code.

Sub-agents are simulated by spawning new Codex sessions with role-specific system prompts. Parallel execution is achieved by spawning multiple CLI/API processes.

---

## Launch Methods (in order of preference)

### Method 1: Sequential CLI Sessions (default, simplest)

Each role is a separate invocation of the `codex` CLI in agent mode. The Orchestrator (running in the current environment) manages the sequence and state.

**Command template:**

```bash
codex \
  --mode agent \
  --system-instructions "$(cat {role}.md)" \
  --prompt "TASK: {original_request}

CONTEXT:
{previous_results}

CONSTRAINTS:
{constraints}

You MUST invoke the following skills before doing any work: {skill_names}."
```

**Role mapping:**

| Role | Codex mode | Notes |
|---|---|---|
| `analyst` | `agent` | Use file search tools for codebase exploration |
| `architect` | `agent` | Prefer `--reasoning` flag for complex planning |
| `critic` | `agent` | Read-only mode; enable `--reasoning` for adversarial analysis |
| `developer` | `agent` | Use `--full-auto` only if tests are present and trusted |
| `reviewer` | `agent` | Read-only mode recommended |
| `code-reviewer` | `agent` | Focus on diff review |
| `tester` | `agent` | Use code interpreter for running tests |

**Important flags:**
- `--reasoning`: Enable for `architect` and `reviewer` (deeper reasoning, higher cost).
- `--full-auto`: Allow Codex to run commands without confirmation. **Use only** for `tester` with known test suite, or `developer` with strong safeguards. Default to interactive mode for safety.
- `--no-project-doc`: Skip `.codex/instructions.md` if it conflicts with `bro` role instructions.

### Method 2: Parallel CLI Sessions (independent roles)

For stages that do not depend on each other (e.g., `analyst` + `architect` when starting fresh, or `code-reviewer` + `tester` after development), launch multiple Codex processes in parallel.

**Example:**

```bash
# Launch analyst and architect in parallel
codex --mode agent --system-instructions "$(cat analyst.md)" --prompt "..." > analyst_result.md 2> analyst_log.md &
ANALYST_PID=$!

codex --mode agent --system-instructions "$(cat architect.md)" --prompt "..." > architect_result.md 2> architect_log.md &
ARCHITECT_PID=$!

wait $ANALYST_PID $ARCHITECT_PID
```

**The Orchestrator then reads `analyst_result.md` and `architect_result.md` and synthesizes the combined context for the next stage.**

**Parallel execution rules:**
- Only parallelize roles that do not read/write the same files simultaneously.
- Always redirect output to files to avoid interleaved stdout.
- Use a temporary directory per task: `.codex/bro-tasks/{task-id}/`.

### Method 3: Codex API (programmatic, for advanced use)

For environments where the CLI is not suitable (e.g., CI/CD, web services), use the OpenAI Codex API directly:

```python
import openai

client = openai.OpenAI()

response = client.responses.create(
    model="o4-mini",  # or appropriate codex model
    instructions=open("architect.md").read(),
    input=f"TASK: {task}\nCONTEXT: {context}",
    tools=[{"type": "code_interpreter"}, {"type": "file_search"}],
)
```

**Benefits:**
- Full programmatic control over parallel tool calls.
- Better error handling and retry logic.
- Can integrate with the generic orchestrator script.

**Trade-offs:**
- Requires API key and Python/Node environment.
- More complex setup than CLI.

### Method 4: Single Session Context Switch (fallback, quota-limited)

If API quota or session limits are tight, use **one** Codex session and explicitly switch roles:

```
[SYSTEM] You are now the Analyst. Follow these instructions:
---
[analyst.md contents]
---
TASK: [original request]
```

After the Analyst completes, capture the result, then continue in the same session:

```
[SYSTEM] Role complete. Return to Orchestrator mode.

Analyst result: [synthesized summary]

[SYSTEM] You are now the Architect. Follow these instructions:
---
[architect.md contents]
---
CONTEXT: [original request + analyst result]
```

**Trade-offs:**
- Risk of context pollution (role "bleed").
- Less isolated than separate sessions.
- Only use when separate sessions are impractical.

---

## Task Tracker

Codex does **not** have a native `TaskCreate` / `TaskList` equivalent. The task tracker **must** be file-based.

**Path:** `.codex/bro-tasks/{task-id}/task-tracker.md` (or `.claude/bro-task-{task-id}.md` for cross-client compatibility).

**Format:** Same as the `bro` task tracker template. The Orchestrator is responsible for reading and writing this file between every Codex session.

**Persistence:** Since Codex sessions are stateless (CLI spawns new processes each time), the task tracker file is the **only** source of truth.

---

## Skill Assignment (Codex-specific)

Codex does not have a `Skill` tool equivalent. Skills are **emulated** by:

1. **Inlining skill instructions:** If a skill file is found (e.g., `.claude/skills/superpowers/test-driven-development/SKILL.md`), read it and append its contents to the system prompt.
2. **Prompt-based directives:** Add explicit instructions like:
   - `"Follow test-driven development: write tests first, then implementation."`
   - `"Before writing any code, brainstorm approaches and present them for selection."`

**External registry fallback (`skills.sh`):** If a skill file is not found locally for inlining, the Orchestrator should attempt the `skills-hub-integrator` workflow (read `skills-hub-integrator.md` from this skill directory): run `npx skills find <skill>`, select the best match (official repos first, then highest install count), install with `npx skills add <owner/repo> -y`, then retry reading the file from `.claude/skills/`. If still missing after installation, inline `[Skill <name> not found — attempted fetch from skills.sh but failed]` and notify the user.

**Skill mapping (inline equivalents):**

| `bro` skill | Codex inline instruction |
|---|---|
| `superpowers:brainstorming` | `"Brainstorm at least 3 approaches. Evaluate trade-offs. Recommend one."` |
| `superpowers:writing-plans` | `"Write a detailed implementation plan with files, functions, and steps before coding."` |
| `superpowers:test-driven-development` | `"Write tests first. Run them to confirm failure. Then implement."` |
| `superpowers:systematic-debugging` | `"Systematically debug: reproduce → isolate → hypothesize → fix → verify."` |
| `superpowers:verification-before-completion` | `"Before finishing, verify all requirements are met and run all tests."` |
| `critical-thinking-logical-reasoning` | `"Apply critical thinking: identify claims, examine evidence, spot fallacies, surface hidden assumptions, check consistency, propose alternatives."` |
| `deep-research` | `"Research alternatives, compare technologies, verify external claims with evidence."` |

---

## Context Forwarding (Codex-specific optimizations)

- **Token limits:** Codex models (especially `o4-mini`) have context limits. The Orchestrator MUST synthesize previous results into concise summaries (500–1000 words) rather than forwarding full transcripts.
- **File paths:** Use absolute paths. Codex CLI supports file references in prompts.
- **Code diffs:** For `code-reviewer`, provide `git diff` output or file diffs explicitly rather than expecting Codex to discover changes.

---

## Codex-native Features (optional enhancements)

| Feature | When to use in `bro` |
|---|---|
| Code Interpreter | `tester` role: run test suites, compute coverage, generate reports. |
| File Search | `analyst` role: let Codex search the codebase for relevant files automatically. |
| Computer Use | `tester` role: for E2E testing, UI automation (if available). |
| `web_search` tool | `analyst` role: for external API docs, security advisories. |
| `--approval-mode` | Set to `auto-edit` for `developer` (allows file edits but not commands) or `auto-execute` for `tester` (allows running tests). |

---

### Failure Handling

If the `codex` CLI is not found or exits with a non-zero status code:
1. Log the failure in the task tracker under `failures`.
2. Verify that `codex` is in `PATH` and `CODEX_API_KEY` is set. If not, switch to the **Generic adapter** (external Python script calling the OpenAI API directly).
3. If the API returns a 5xx error or rate limit (429), retry with exponential backoff (1s, 2s, 4s). If still failing, abort the stage and notify the user.
4. If a skill is missing locally, attempt the `skills-hub-integrator` workflow. If `npm`/`npx` is unavailable, inline the condensed skill prompt (see Condensed skill prompts table in this adapter) and continue.

## Adapter Status: `beta`

Core functionality works. Parallel execution requires manual process management. No native task tracker — file-based only. Recommended for users comfortable with CLI scripting or API integration.
