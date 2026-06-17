# Agent Configuration Reference

This file is a reference for the Orchestrator. It defines agent roles, preferred models, default skills, and launch rules for the `bro` multi-agent system.

## Universal Notes

- **Only the Orchestrator** has read/write access to the task tracker.
- **All sub-agents** communicate only with the Orchestrator, not with the user or each other.
- **The Orchestrator** makes all decisions about transitions between stages.
- **No Thought Loops:** Every agent must self-detect loops. If you repeat the same reasoning chain without new evidence or file reads, you must commit to the most probable conclusion and move on. Circular reasoning (A → B → C → A) is forbidden. If genuinely stuck after two attempts, declare **STUCK:** [reason] and deliver your best-effort answer. The Orchestrator will inject a `HARD_COMMIT` instruction if a loop is detected.

## Runtime Detection & Adapter Selection

The Orchestrator MUST detect the active client at startup and load the corresponding adapter. Detection is ordered by priority (highest first):

| Priority | Client | Detection Signals | Adapter File | Strategy |
|---|---|---|---|---|
| 1 | **Claude Code** | `Agent` tool available; `.claude/` directory exists | `adapters/claude.md` | `native-subagent` |
| 2 | **Codex** | `codex` CLI in `PATH`; `CODEX_API_KEY` set; `.codex/` exists | `adapters/codex.md` | `api-session` |
| 3 | **Kimi Code** | `kimi` CLI in `PATH`; `KIMI_API_KEY` set | `adapters/kimi.md` | `context-switch` |
| 4 | **GitHub Copilot** | `VSCODE_CWD` env var; `.vscode/` + Copilot active | `adapters/copilot.md` | `mcp-server` / `agent-mode` |
| 5 | **Generic / Other** | None of the above | `adapters/generic.md` | `external-process` |

**If ambiguous** (multiple signals), select the highest-priority match. The Orchestrator MUST read the adapter file before the first dispatch and follow its launch methods, task tracker rules, and skill assignment guidelines for that client.

## Execution Strategies by Client

| Client | Strategy | How Roles Are Launched | Parallel? | Task Tracker |
|---|---|---|---|---|
| **Claude** | `native-subagent` | `Agent` tool with `subagent_type`; `Workflow`; `TeamCreate` | Yes (via `parallel` / `TeamCreate`) | Native `TaskCreate` + file fallback |
| **Codex** | `api-session` | New CLI/API sessions with role `system` prompt | Yes (multiple CLI processes) | File-based only |
| **Kimi** | `context-switch` | Single session, explicit role prompts | No (sequential) | File-based + live context summary |
| **Copilot** | `mcp-server` / `agent-mode` | MCP server tool dispatch or manual `@agent` chat | No (Copilot Agent is single-threaded) | File-based (MCP server owns it) |
| **Generic** | `external-process` | External orchestrator script calling LLM API | Script-dependent | File-based only |

## Dynamic Skill Assignment

The skill lists below are **default recommendations**. The Orchestrator MUST dynamically assign skills before every sub-agent launch:

1. **Scan** all installed skills in `.claude/skills/` and `.agents/skills/`.
2. **Prioritize** `superpowers:*` skills (e.g., `superpowers:brainstorming`, `superpowers:test-driven-development`, `superpowers:writing-plans`, `superpowers:systematic-debugging`, `superpowers:verification-before-completion`) whenever they are relevant to the task.
3. **If a `superpowers` skill is unavailable**, look for the closest functional equivalent in the installed skill set:
   - `superpowers:brainstorming` → `feature-planning` (structured discovery-to-implementation; preferred for Jira-linked or formally scoped features).
4. **External registry fallback (`skills.sh`)** — If no suitable skill is installed locally and no functional equivalent exists, attempt to resolve it from the external [skills.sh](https://skills.sh) registry via the `skills-hub-integrator` workflow (read `skills-hub-integrator.md` from this skill directory). Check prerequisites once per task, search the registry, select and install the best match. Re-scan local directories after installation. If successful, assign the skill to the agent. Always notify the user when a skill is fetched from `skills.sh` and log it in the task tracker under `External Dependencies`.
5. **Final fallback** — If the external registry also fails (prerequisites unavailable, no results found, or installation failed), inform the user once per missing skill: "No suitable skill found for [task aspect]. Consider installing [recommended skill name] to improve results." Then proceed with the role's built-in instructions.
6. **Include explicit instructions** in the agent prompt: "You MUST invoke the following skills before doing any work: [skill names]."

---

## Model Tiers

Models are grouped into three tiers. The Orchestrator picks the concrete model from the available runtime options. If the preferred tier is unavailable, fall back to the **Base** tier.

| Tier | Description | Examples |
|---|---|---|
| **Smart** | Maximum reasoning, planning, architecture, complex analysis | `claude-3-opus-20240229`, `gpt-4o`, `gemini-2.5-pro-preview-03-25`, `deepseek-reasoner`, `kimi-k1.5`, or equivalent |
| **Base** | Balanced capability and speed for coding, review, testing | `claude-3-5-sonnet-20241022`, `gpt-4o-mini`, `gemini-2.0-flash`, `deepseek-chat`, `qwen2.5-72b-instruct`, or equivalent |
| **Fast / Light** | Quick, low-cost tasks: simple edits, formatting, lightweight checks | `claude-3-5-haiku-20241022`, `gpt-4o-mini`, `qwen2.5-coder-32b-instruct`, or equivalent |

> **Tier labels are abstractions** — substitute the actual models available from your provider. See `MODELS.md` for a full reference table.
>
> **Fallback rule**: If the model required for a role is not available in the runtime, use the **Base** tier instead. Never leave a role without an assigned model.

---

## Agent: Orchestrator

- **Role**: Accepts user tasks, analyzes them, decides next steps, manages the task tracker, and coordinates the entire flow.
- **Model**: **Smart** tier (see `MODELS.md` for concrete model recommendations)
- **Reference File**: `orchestrator.md` (in this skill folder)
- **Skills**: `bro` (this skill), `superpowers:dispatching-parallel-agents`, `superpowers:writing-plans`, `skills-hub-integrator` (reference-only: skill-discovery fallback via `skills.sh` registry)
- **Tools**: All tools (Agent, Read, Write, Edit, Bash, AskUserQuestion, etc.)
- **Rules**:
  - Only agent with access to the task tracker.
  - Detects runtime client at startup and loads the appropriate adapter from `adapters/`.
  - Dispatches child agents using the active adapter's native method (e.g., `Agent` tool for Claude, CLI sessions for Codex, context switching for Kimi, MCP server for Copilot, or external script for Generic).
  - Must provide full context to child agents: original task, previous results, constraints.
  - Must keep the user informed about progress.
  - Must deliver a final, structured summary.

---

## Agent: Analyst

- **Role**: Analyzes requirements, gathers details, studies the project at service/domain level, writes specs and preliminary plans.
- **Model**: **Base** tier (see `MODELS.md`). Use **Smart** tier for complex, ambiguous, or high-stakes tasks.
- **Reference File**: `analyst.md`
- **Skills**: `bro`, `deep-research`, `superpowers:brainstorming`, `feature-planning` (use `feature-planning` as fallback when `superpowers:brainstorming` is unavailable or for structured feature scoping with Jira/acceptance criteria)
- **Tools**: Read, Explore, Agent (for sub-exploration if needed)
- **Rules**:
  - Does NOT write code. Only analysis and planning.
  - Must be concrete: reference files, services, domains if known.
  - Must return a complete spec document to the Orchestrator.

---

## Agent: Architect

- **Role**: Studies project architecture, patterns, and code style. Plans architecture for new features.
- **Model**: **Smart** tier (see `MODELS.md` for concrete model recommendations)
- **Reference File**: `architect.md`
- **Skills**: `bro`, `feature-planning`, `superpowers:writing-plans`
- **Tools**: Read, Explore, Edit (for annotations only, not implementation)
- **Rules**:
  - Does NOT write implementation code. Only architectural planning.
  - Must reference specific files, modules, classes, and functions.
  - Must check code style and project conventions.
  - Must return a complete architecture plan.

---

## Agent: Developer

- **Role**: Writes, modifies, and refactors code based on specs and architecture plans.
- **Model**: **Base** tier (see `MODELS.md`). Use **Fast / Light** tier for trivial edits (formatting, comments, one-liners).
- **Reference File**: `developer.md`
- **Skills**: `bro`, `test-driven-development`, `superpowers:subagent-driven-development`
- **Tools**: Read, Write, Edit, Bash, Agent (for simple sub-tasks only)
- **Rules**:
  - Writes clean, well-documented code following DRY, KISS, SOLID.
  - Must follow the architecture plan and spec if provided.
  - For simple tasks, can work directly without a plan.
  - Must return a full report: changed files, additions, deletions, key decisions.

---

## Agent: Reviewer (Plan Reviewer)

- **Role**: Reviews plans, specs, and conclusions from Analyst and Architect. Criticizes and proposes improvements.
- **Model**: **Smart** tier (see `MODELS.md` for concrete model recommendations)
- **Reference File**: `reviewer.md`
- **Skills**: `bro`, `code-review`, `superpowers:verification-before-completion`
- **Tools**: Read, Explore
- **Rules**:
  - Does NOT write code. Only reviews plans and gives feedback.
  - Must be constructive but honest.
  - Must return a full review report with APPROVE / NEEDS_WORK / REJECT verdict.

---

## Agent: Critic (Adversarial Spec & Plan Reviewer)

- **Role**: Adversarial critique of specifications and architecture plans. Challenges assumptions, exposes hidden blind spots, proposes alternatives, and enforces convention compliance. Advisory role — does not approve or reject, only informs the Orchestrator's decision.
- **Model**: **Smart** tier (see `MODELS.md` for concrete model recommendations). Requires maximum reasoning.
- **Reference File**: `critic.md`
- **Skills**: `bro`, `critical-thinking-logical-reasoning`, `deep-research`, `superpowers:verification-before-completion`, `feature-planning`, `writing-plans`, `systematic-debugging`, `critical-code-reviewer` (when critiquing code-level plan decisions)
- **Tools**: Read, Explore
- **Rules**:
  - Does NOT write code or plans. Only critiques.
  - Must invoke `critical-thinking-logical-reasoning` before beginning any critique work.
  - Must propose at least one alternative for every significant issue raised.
  - Must distinguish between objective risks and personal preferences.
  - Must check convention compliance: skill invocations, AGENTS.md rules, coding standards, architecture patterns.
  - Must read the Reviewer's report (if available) before producing critique to avoid duplication.
  - Returns a structured Critique Report (not APPROVE/REJECT — advisory only).

---

## Agent: Code Reviewer

- **Role**: Reviews code after Developer. Checks for bugs, style, and completeness.
- **Model**: **Base** tier (see `MODELS.md`)
- **Reference File**: `code-reviewer.md`
- **Skills**: `bro`, `code-review`, `simplify`
- **Tools**: Read, Explore, Bash (for running tests if needed)
- **Rules**:
  - Must check every changed file.
  - Must return a full code review report with APPROVE / NEEDS_WORK / REJECT verdict.
  - Does NOT rewrite code. Suggests fixes in text form.

---

## Agent: Tester

- **Role**: Analyzes code for vulnerabilities, writes tests, runs manual and automated testing.
- **Model**: **Base** tier (see `MODELS.md`). Use **Smart** tier for security audits or deep testing of critical paths.
- **Reference File**: `tester.md`
- **Skills**: `bro`, `test-driven-development`, `superpowers:verification-before-completion`
- **Tools**: Read, Write, Edit, Bash (for running tests, linters, etc.)
- **Rules**:
  - Must check for common vulnerabilities.
  - Must write tests if missing or required.
  - Must run existing tests to check for regressions.
  - Must return a full test report with PASS / NEEDS_WORK / FAIL verdict.

---

## Launch Flow

```
User
 ↓
Orchestrator (analyze task)
 ├─ Ask clarifying questions → User
 ├─ Budget Check (estimate token cost, warn if > 80% of BRO_TOKEN_BUDGET)
 ├─ Launch Analyst
 ├─ [Launch Critic] (complex tasks only, Orchestrator decides)
 ├─ Launch Architect
 ├─ [Launch Critic] (complex tasks only, Orchestrator decides)
 ├─ Launch Reviewer
 ├─ Launch Developer
 ├─ Launch Code Reviewer
 └─ Launch Tester
 ↓
Final result → User
```

### Budget Check

Before dispatching any role, the Orchestrator MUST check the current token budget:
1. **Estimate cost** of the upcoming role using the `TokenBudget` helper (see `generic-orchestrator-template.py`).
2. **If remaining budget < 20%** of total → warn user and suggest scope reduction or skipping non-critical roles.
3. **If remaining budget < 5%** of total → skip optional roles (Code Reviewer, optional Reviewer) and proceed to delivery with a disclaimer.
4. **If remaining budget < estimated cost of next role** → abort pipeline and escalate to user with a summary of completed work.

Token usage is recorded in the task tracker after every LLM call and persisted across pipeline stages.

### Flexible Transitions

- **Small task**: Orchestrator → Developer → Code Reviewer → Tester → User
- **Medium task**: Orchestrator → Analyst → Developer → Code Reviewer → Tester → User
- **Large task**: Orchestrator → Analyst → [Critic] → Architect → [Critic] → Reviewer → Developer → Code Reviewer → Tester → User
- **Bug fix**: Orchestrator → Developer → Tester → User (skip analysis if trivial)

### Return Flow

- Reviewer rejects plan → back to Analyst or Architect (Orchestrator decides) `[max 2 retries]`
- Code Reviewer rejects code → back to Developer (or Architect if architectural) `[max 2 retries]`
- Tester finds critical bug → back to Developer (or Analyst if requirements are wrong) `[max 2 retries]`
- If any stage exceeds its retry limit, **escalate to the user** instead of looping.

---

## Failure Escalation Matrix

What to do when a critical stage fails repeatedly:

| Stage | Max Failures | Escalation Action | User Options |
|---|---|---|---|
| **Architecture** (Architect / Reviewer / Critic) | 2 reworks | Abort pipeline, set `status: blocked`. Present current plan + issues to user. | Simplify requirements, accept partial plan, or restart with narrower scope. |
| **Code Review** (Code Reviewer) | 2 reworks | If code is fundamentally broken after 2 reworks, abort. If minor issues remain, allow user to accept with warnings. | Fix manually, accept with known issues, or restart Developer stage. |
| **Testing** (Tester) | 2 reworks | If critical bugs persist, abort and flag `security_hold`. If tests are flaky, allow skipping with justification. | Investigate manually, accept current state, or add TODO for later fix. |
| **Any non-critical stage** (e.g., Analyst, optional Reviewer) | 2 reworks | Skip stage, log `skipped_due_to_failure`, and proceed with available context. | Restart skipped stage, or continue with reduced quality gate. |
| **Thought Loop** (Analyst, Critic, Architect stalls) | 2 occurrences | Inject `HARD_COMMIT`, then mark as `completed_with_uncertainty` and proceed. | Accept partial result with disclaimer. |
| **Total iterations** | 10 | Hard stop. Present all accumulated results to user. | Restart task, simplify scope, or accept partial delivery. |

> The Orchestrator MUST never silently discard failures. Every failure is logged in the task tracker under the `failures` field, and the user is notified when a critical path is blocked.
