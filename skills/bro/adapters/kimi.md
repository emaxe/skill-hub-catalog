# Kimi Code Adapter

## Runtime Detection

This adapter activates when any of the following are detected:
- `kimi` CLI is available in `PATH`
- `KIMI_API_KEY` environment variable is set
- `kimi_code` or `moonshot` API context is present

**Explicit detection commands:**
```bash
which kimi          # verifies CLI is on PATH
kimi --version      # prints version (e.g., "kimi version 1.2.3")
```

If `which kimi` returns a path and `kimi --version` prints a version string, the CLI is ready. If only `KIMI_API_KEY` is set but the CLI is missing, the Orchestrator should fall back to the **Kimi API** (Method 3) or the **Generic adapter**.

> **Detection confidence:** Medium-High — `KIMI_API_KEY` is the strongest signal.

## Execution Strategy: `context-switch`

Kimi (Moonshot AI) is renowned for its extremely long context window (up to 200K+ tokens). This makes it uniquely suited for a **single-session, context-switching** strategy where all roles are executed within one continuous conversation. The Orchestrator switches the agent's role identity by updating the system prompt.

Alternatively, separate sessions can be spawned via CLI for stricter isolation.

---

## Launch Methods (in order of preference)

### Method 1: Context Switching within Single Session (default, recommended)

This is the most efficient strategy for Kimi due to its long-context capabilities. The Orchestrator manages the entire pipeline in one session.

**How it works:**

1. **Orchestrator initialization:** The Orchestrator loads all role files (`analyst.md`, `architect.md`, `developer.md`, etc.) into the context at the start. This is a one-time cost.

2. **Role dispatch:** When a role is needed, the Orchestrator sends a message that explicitly switches the agent's identity:

```
[SYSTEM CONTEXT UPDATE]
You are now assuming the role of {ROLE_NAME}. 
All previous instructions are suspended. 
Follow ONLY the instructions below for this role.

--- ROLE INSTRUCTIONS START ---
[{role}.md contents]
--- ROLE INSTRUCTIONS END ---

TASK:
[original user request, summarized]

CONTEXT FROM PREVIOUS ROLES:
[synthesized results from all prior stages]

CONSTRAINTS:
[performance, security, style]

You MUST apply the following skill principles before doing any work:
[skill instructions, inlined]

Return your complete result to the Orchestrator. Do not ask for user input unless absolutely necessary.
```

3. **Result capture:** The Kimi agent returns its analysis/plan/code.

4. **Return to Orchestrator:** The Orchestrator sends:

```
[SYSTEM CONTEXT UPDATE]
Role {ROLE_NAME} complete. Return to Orchestrator mode.

Summarized result: [2-3 paragraph synthesis]

Decision: Proceed to [next role] / Rework required / Deliver to user.
```

**Role switching best practices:**
- **Clear delimiters:** Use `[SYSTEM CONTEXT UPDATE]` and `--- ROLE INSTRUCTIONS START/END ---` to minimize role bleed.
- **Summarize aggressively:** After each role completes, the Orchestrator MUST synthesize its output into a concise summary (300–800 words) before storing it in the running context. This prevents context bloat.
- **One role at a time:** Do not interleave roles. Complete one fully before switching to the next.
- **Avoid mid-role switching:** Once a role is started, let it finish. Only switch back to Orchestrator when the role signals completion or asks for a decision.

**Advantages:**
- No overhead of spawning new sessions.
- Full history visible to all roles (no context loss between handoffs).
- Perfect for long-context Kimi models.

**Disadvantages:**
- Risk of role identity bleed (earlier role instructions influencing later ones).
- If the session is interrupted, the entire task state is in the conversation history (harder to resume than file-based tracking).
- Cannot truly run roles in parallel (everything is sequential in one session).

### Method 2: Separate CLI Sessions (for isolation)

For users who prefer strict role isolation, spawn separate `kimi` CLI sessions per role.

**Concrete example for a Developer role:**

```bash
ROLE=developer
TASK="Implement a user login endpoint using JWT tokens"
CONTEXT=$(cat analyst_result.md architect_result.md)
CONSTRAINTS="Use existing auth middleware. Follow PEP 8. No external dependencies."

kimi chat \
  --system "$(cat ${ROLE}.md)" \
  --prompt "TASK: ${TASK}

CONTEXT:
${CONTEXT}

CONSTRAINTS:
${CONSTRAINTS}" \
  --output ${ROLE}_result.md
```

**Command template:**

```bash
kimi chat \
  --system "$(cat {role}.md)" \
  --prompt "TASK: {original_request}

CONTEXT:
{previous_results}

CONSTRAINTS:
{constraints}" \
  --output {role}_result.md
```

**Parallel execution:** Limited. Kimi CLI may not support background spawning as cleanly as Codex. Prefer sequential execution unless multiple CLI instances are confirmed to work independently.

### Method 3: Kimi API (programmatic)

```python
from kimi import KimiClient

client = KimiClient(api_key=os.environ["KIMI_API_KEY"])

messages = [
    {"role": "system", "content": open("architect.md").read()},
    {"role": "user", "content": f"TASK: {task}\nCONTEXT: {context}"}
]

response = client.chat.completions.create(
    model="kimi-latest",
    messages=messages,
    tools=[...],  # if tool use is available
)
```

This is useful for integrating Kimi into the generic orchestrator script or a CI pipeline.

---

## Task Tracker

Kimi does not have native `TaskCreate` / `TaskList` tools. The task tracker **must** be file-based.

**Path:** `.claude/bro-task-{task-id}.md` (cross-client compatible) or `.kimi/bro-tasks/{task-id}/tracker.md`.

**For the single-session strategy:**
- The Orchestrator maintains a **live summary** of the task tracker in the conversation context (e.g., a "Task Tracker" section in every message).
- Additionally, the Orchestrator MUST write the tracker to a file after every completed role as a backup.
- If the session is interrupted, the file-based tracker is the source of truth for resuming.

**Resumption strategy:**
```
[SYSTEM CONTEXT UPDATE]
Resuming task {task-id}. Current state from tracker:
--- TRACKER START ---
[file contents]
--- TRACKER END ---

Next role to execute: {role_name}
```

---

## Skill Assignment (Kimi-specific)

Kimi does not have a `Skill` tool. Skills are inlined into the role instructions at the moment of context switching.

**Procedure:**
1. Before starting the task, the Orchestrator reads all relevant skill files from `.claude/skills/`.
2. When switching to a role, the Orchestrator appends the relevant skill instructions directly into the role prompt.

**Example:**
```
--- ROLE INSTRUCTIONS START ---
[developer.md contents]
--- ROLE INSTRUCTIONS END ---

ADDITIONAL SKILL INSTRUCTIONS:
--- TDD START ---
[contents of superpowers/test-driven-development/SKILL.md]
--- TDD END ---
```

**External registry fallback (`skills.sh`):** If a skill file is not found locally for inlining, the Orchestrator should attempt the `skills-hub-integrator` workflow (read `skills-hub-integrator.md` from this skill directory): run `npx skills find <skill>`, select the best match (official repos first, then highest install count), install with `npx skills add <owner/repo> -y`, then retry reading the file from `.claude/skills/`. If still missing after installation, append a note in the prompt: `[Skill <name> unavailable — attempted fetch from skills.sh but failed]` and notify the user.

**Key skill mappings:**

| `bro` skill | Kimi inline equivalent |
|---|---|
| `superpowers:brainstorming` | Append brainstorming instructions to `analyst` prompt. |
| `superpowers:writing-plans` | Append planning instructions to `architect` prompt. |
| `superpowers:test-driven-development` | Append TDD rules to `developer` and `tester` prompts. |
| `superpowers:systematic-debugging` | Append debugging protocol to `developer` prompt. |
| `superpowers:verification-before-completion` | Append verification checklist to `tester` and `code-reviewer` prompts. |
| `critical-thinking-logical-reasoning` | Append critical thinking methodology to `critic` prompt. |
| `deep-research` | Append research protocol to `critic` prompt for technology comparison. |

---

## Context Forwarding (Kimi-specific optimizations)

- **Long context is your ally:** Kimi handles 200K+ tokens well. Include full original request and detailed prior summaries. No need to truncate as aggressively as with Codex.
- **Summarize old roles:** Keep the full context of the last 1–2 roles, but compress older roles to bullet points. This prevents the conversation from becoming unwieldy.
- **Use structured formats:** Kimi responds well to structured prompts (markdown tables, JSON, numbered lists). Use these for context forwarding.

---

## Kimi-native Features (optional enhancements)

| Feature | When to use in `bro` |
|---|---|
| Long context window | Keep entire codebase context in `analyst` session. Summarize less. |
| Web search (if available) | `analyst` role for external research, API docs, dependency checks. |
| Code execution (if available) | `tester` role for running tests and scripts. |
| File upload (if available) | `analyst` and `architect` for reading large design documents. |

---

## Known Limitations

- **No native sub-agent tool:** Unlike Claude Code, Kimi does not provide a `TaskCreate` or `Agent` tool. Role isolation is simulated via context switching or separate CLI sessions. There is no true process-level sandbox.
- **Session interruption risk:** If the single-session context-switching strategy (Method 1) is interrupted, the entire conversation history is lost. The Orchestrator must persist the task tracker to a file after every completed role to enable resumption.
- **Limited parallel execution:** The `kimi chat` CLI does not support background/parallel execution natively. Parallel dispatch requires multiple independent terminal sessions or an external wrapper script.
- **Tool availability variance:** Web search, code execution, and file upload may not be available depending on the Kimi model version and API tier. The Orchestrator should verify tool availability before dispatching roles that depend on them (e.g., `tester` needing code execution).
- **Context window limits:** While Kimi supports 200K+ tokens, very large projects (e.g., 500+ files) can still exceed the context window. The Orchestrator should use `grep`/`glob` pre-filtering and aggressive summarization for large codebases.

---

### Failure Handling

If the `kimi` CLI is unavailable or the API returns an error (e.g., `KIMI_API_KEY` invalid, connection timeout):
1. Log the failure in the task tracker under `failures`.
2. Retry once after 5 seconds.
3. If still failing, fall back to the **Generic adapter** (external Python script using the Kimi/OpenAI-compatible API endpoint).
4. If a skill is missing locally and `skills.sh` is unreachable, inline the condensed skill prompt (see Key skill mappings table) and log the missing skill.
5. If the session is interrupted and context is lost, resume from the file-based task tracker (`.claude/bro-task-{task-id}.md`).

## Adapter Status: `beta`

Single-session context switching is the primary and recommended strategy. Works best with Kimi's long-context models. File-based task tracker required. No native parallel execution within one session.
