# Claude Code Adapter

## Runtime Detection

This adapter activates when the `Agent` tool is available in the environment and the `.claude/` directory structure is present.

> **Detection confidence:** High — these are unique to Claude Code.

## Execution Strategy: `native-subagent`

Claude Code provides first-class support for sub-agents via the `Agent` tool, `Workflow` orchestration, `TeamCreate` for long-lived teams, and native `TaskCreate`/`TaskList` for tracking. This is the richest execution environment.

---

## Launch Methods (in order of preference)

### Method 1: `Agent` Tool (default, most common)

Use the native `Agent` tool for each role dispatch. The Orchestrator MUST:

1. Read the role file (e.g., `analyst.md`).
2. Prepend its contents to the agent prompt.
3. Select `subagent_type` based on role:

| Role | Recommended `subagent_type` | Rationale |
|---|---|---|
| `analyst` | `general-purpose` | Broad exploration and research |
| `architect` | `plan` | Architecture planning with design constraints |
| `critic` | `plan` | Adversarial plan review; read-only critique |
| `developer` | `claude` (default) | Full tool access for implementation |
| `reviewer` | `plan` | Read-only plan review |
| `code-reviewer` | `code-reviewer` | Dedicated code review mode |
| `tester` | `claude` (default) | Needs bash/tests/write tools |

4. **Always** set `team_name` to the current task ID if using `TeamCreate`.
5. **Always** include explicit skill assignment instructions in the prompt.

**Example prompt structure for `Agent`:**

```
You are the {ROLE}. Follow the instructions below:

--- ROLE INSTRUCTIONS START ---
[{role}.md contents]
--- ROLE INSTRUCTIONS END ---

TASK:
[original user request]

CONTEXT:
[all previous results]

CONSTRAINTS:
[performance, security, style]

You MUST invoke the following skills before doing any work: [skill names].
```

**Parallel execution:** Use `parallel()` for independent roles (e.g., `analyst` + `architect` when neither depends on the other, or `code-reviewer` + `tester` after development).

### Method 2: `Workflow` (for repeatable, complex pipelines)

When the task matches a known pattern (e.g., "implement a new feature from scratch", "refactor a module", "security audit"), use `Workflow` with a predefined script. This provides:
- Deterministic execution
- Automatic caching of completed stages
- Better retry / resume behavior

**When to use:**
- The task is expected to take >5 sequential agent launches.
- The pipeline is well-understood (e.g., standard feature flow: Analyst → Architect → Reviewer → Developer → Code Reviewer → Tester).
- You want automatic resumability if interrupted.

**When NOT to use:**
- Simple bug fixes (< 3 files, 1–2 agent launches).
- Tasks requiring frequent Orchestrator decisions mid-flow.

### Method 3: `TeamCreate` + `TaskList` (for large projects)

For tasks that will span many turns or days, create a persistent team:

1. `TeamCreate(team_name="bro-{project}-{task-id}")`
2. Use `TaskCreate` for each sub-task (e.g., "Analyze API requirements", "Design database schema").
3. Assign tasks to agents via `TaskUpdate(owner="{role}")`.
4. Team members automatically see the shared task list.

**Benefits:**
- Task list survives across interruptions.
- Agents can claim available tasks autonomously.
- No manual context re-forwarding needed.

**Trade-offs:**
- Higher initial setup overhead.
- Less granular Orchestrator control over each transition.

---

## Task Tracker

**Primary:** Use `TaskCreate` / `TaskList` / `TaskUpdate` (native tools). This is the most robust option in Claude Code.

**Fallback:** If the task is simple (expected < 3 agent launches) or native tools are unavailable, use the file-based tracker: `.claude/bro-task-{id}.md`.

**Synchronization rule:** When using native `TaskCreate`, mirror critical milestones in the file-based tracker as well (append-only log) for cross-client compatibility and human inspection.

---

## Skill Assignment (Claude-specific)

Before dispatching any sub-agent, scan `.claude/skills/` and `.agents/skills/`. Prioritize:

- `superpowers:brainstorming` for `analyst`
- `superpowers:writing-plans` for `architect` and `reviewer`
- `superpowers:test-driven-development` for `developer` and `tester`
- `superpowers:systematic-debugging` for `developer` (bug fixes)
- `superpowers:verification-before-completion` for `tester` and `code-reviewer`
- `superpowers:subagent-driven-development` for `developer` (complex tasks)
- `critical-thinking-logical-reasoning` for `critic` (adversarial critique)
- `deep-research` for `critic` (technology comparison, alternative analysis)

Include in the agent prompt: `"You MUST invoke the following skills before doing any work: [list]."`

**Fallback — External registry (`skills.sh`):** If a required `superpowers:*` or other skill is missing locally, the Orchestrator MAY invoke the `skills-hub-integrator` workflow (read `skills-hub-integrator.md` from this skill directory): run `npx skills find <skill>`, select the best match (official repos first, then highest install count), install with `npx skills add <owner/repo> --agent claude-code -y`, then re-scan `.claude/skills/`. If installation succeeds, include the skill name in the agent prompt and notify the user: *"Skill `<name>` was installed from skills.sh (`<owner/repo>`) and is now active for this task."*

---

## Context Forwarding (Claude-specific optimizations)

- **Token budget:** Claude Code has generous context limits. Include the full original request and all synthesized prior results — do not truncate.
- **File references:** Use absolute paths with `file_path:line_number` format. Claude sub-agents can click these.
- **Skill instructions:** Mention skill names, not file paths. The sub-agent will load them via `Skill` tool.

---

## Claude-only Features (optional enhancements)

| Feature | When to use |
|---|---|
| `SendMessage` between agents | **Not recommended** by default. `bro` isolates sub-agents for a reason. Only use if you explicitly want peer-to-peer collaboration (e.g., two developers coordinating). |
| `CronCreate` | For recurring checks (e.g., "run tests every hour", "monitor CI status"). Rarely needed in `bro`. |
| `Monitor` | For watching long-running processes (e.g., test suite, build). Use in `tester` role if tests are slow. |
| `npx skills` (skills.sh CLI) | Use in `skills-hub-integrator` workflow for external skill discovery and installation when local skills are missing. Run `npx skills find <skill>` and `npx skills add <owner/repo> --agent claude-code -y`. |
| `WebSearch` / `WebFetch` | Use in `analyst` for external research, API documentation, or dependency security checks. |
| `AskUserQuestion` | Use in `analyst` or `architect` for clarifying ambiguous requirements before committing to a plan. |

---

### Failure Handling

If the `Agent` tool is unavailable or throws an exception (e.g., `ToolUseError`, `AgentNotFound`):
1. Log the failure in the task tracker under `failures`.
2. Retry once after 5 seconds.
3. If still failing, fall back to the **Generic adapter** (`external-process` strategy): run the `generic-orchestrator-template.py` script or invoke the role via CLI in a separate process.
4. Notify the user: *"Claude `Agent` tool unavailable. Switched to Generic adapter fallback."*

If `TaskCreate` / `TaskList` native tools fail, use the file-based task tracker (`.claude/bro-task-{task-id}.md`) exclusively and do not attempt native tools again for this task.

If a skill referenced in the prompt is not found locally, follow the **Skill Discovery & Assignment** process in `orchestrator.md`. If the external registry (`skills.sh`) is also unavailable, inline a condensed version of the skill directive or proceed without it and log the missing skill.

## Adapter Status: `production-ready`

This is the reference implementation. All other adapters are designed to approximate the capabilities of this one within their client constraints.
