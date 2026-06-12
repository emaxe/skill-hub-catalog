---
name: bro
version: 1.0.0
description: Multi-agent coding system. Orchestrator manages task execution flow by dispatching specialized agent roles (analyst, architect, critic, developer, reviewer, code-reviewer, tester). All role instructions and task tracker templates live inside this skill folder.
metadata:
  type: project
---

# bro — Multi-Agent Coding System

## Overview

`bro` is a coordinated multi-agent system for software engineering tasks. When activated, the orchestrator (the agent running this skill) receives the user's task, analyzes it, and dispatches specialized sub-agents by reading role instruction files from this skill's directory.

## Directory Layout (This Skill)

| File | Purpose |
|---|---|
| `SKILL.md` | This file — orchestrator instructions and dispatch rules |
| `orchestrator.md` | Reference role definition for the Orchestrator |
| `analyst.md` | Role prompt for the Analyst sub-agent |
| `architect.md` | Role prompt for the Architect sub-agent |
| `developer.md` | Role prompt for the Developer sub-agent |
| `reviewer.md` | Role prompt for the Reviewer (plan/spec reviewer) sub-agent |
| `critic.md` | Role prompt for the Critic (adversarial spec & plan reviewer) sub-agent |
| `code-reviewer.md` | Role prompt for the Code Reviewer sub-agent |
| `tester.md` | Role prompt for the Tester sub-agent |
| `task-tracker.md` | Task tracker template (copy and fill per task) |
| `examples/` | Sample task pipelines (`simple-bug-fix`, `new-feature`) |
| `AGENTS.md` | Agent configuration reference (models, skills, rules, client adapters) |
| `adapters/` | Client-specific adapter instructions (Claude, Codex, Kimi, Copilot, Generic) |

## Multi-Client Runtime Support

`bro` is designed to work across multiple AI coding assistants. The Orchestrator MUST detect the active runtime at startup and follow the corresponding adapter.

### Runtime Detection Priority

At startup, the Orchestrator checks the environment in this order:

| Priority | Client | Detection Method | Adapter File |
|---|---|---|---|
| 1 | **Claude Code** | `Agent` tool is available; `.claude/` directory exists | `adapters/claude.md` |
| 2 | **Codex** | `codex` CLI available in `PATH`; `CODEX_API_KEY` set | `adapters/codex.md` |
| 3 | **Kimi Code** | `kimi` CLI available in `PATH`; `KIMI_API_KEY` set | `adapters/kimi.md` |
| 4 | **GitHub Copilot** | `VSCODE_CWD` env var set; Copilot Agent Mode active | `adapters/copilot.md` |
| 5 | **Generic / Other** | None of the above detected | `adapters/generic.md` |

> If detection is ambiguous (e.g., multiple signals present), the Orchestrator MUST load the highest-priority adapter. It may briefly mention which signals were detected and why that adapter was chosen.

### Adapter Execution Strategies

Each adapter defines an **execution strategy** — the native mechanism for launching sub-agents on that client:

| Client | Strategy | Native Mechanism |
|---|---|---|
| **Claude** | `native-subagent` | `Agent` tool, `Workflow`, `TeamCreate`, `TaskCreate` |
| **Codex** | `api-session` | New CLI/API sessions with role-specific system prompts |
| **Kimi** | `context-switch` | Single-session role switching via long-context prompts |
| **Copilot** | `mcp-server` or `agent-mode` | MCP server tool or manual `@agent` role switching |
| **Generic** | `external-process` | External orchestrator script calling the LLM API |

### How to Use an Adapter

1. **Detect the runtime** (see table above).
2. **Read the adapter file** from `adapters/{client}.md` in this skill directory.
3. **Follow the adapter's launch methods** for dispatching sub-agents instead of the generic `Agent` tool instructions below.
4. **Maintain universal invariants** regardless of client:
   - Only the Orchestrator touches the task tracker.
   - Sub-agents never communicate directly with each other.
   - Always forward full context (original request + all prior results).
   - Keep the user informed of high-level progress.

### Adapter Fallback

If the detected adapter fails (e.g., Claude `Agent` tool throws errors, Codex CLI not found), the Orchestrator:
1. Logs the failure.
2. Falls back to the next-lower-priority adapter (e.g., Claude → Generic).
3. Informs the user: `"Detected {client} but native tools unavailable. Falling back to {fallback} strategy."`

## Skills Integration

The `bro` system leverages the `superpowers` skill ecosystem to enforce quality gates and best practices. Each role has **recommended skills** that should be invoked before work begins (see the `Recommended Skills` section in each role file). The Orchestrator is responsible for assigning these skills to sub-agents when dispatching tasks.

### Core Skills Assignment Matrix

| Role | Primary Skills | Quality Gate |
|---|---|---|
| **Analyst** | `brainstorming`, `deep-research` | Spec validated via brainstorming or research |
| **Architect** | `writing-plans` | Plan saved to `docs/superpowers/plans/` |
| **Developer** | `test-driven-development`, `subagent-driven-development` | No production code without failing test first |
| **Reviewer** | `verification-before-completion` | Evidence-based plan approval |
| **Critic** | `critical-thinking-logical-reasoning`, `deep-research`, `verification-before-completion` | Adversarial critique of specs and plans |
| **Code Reviewer** | `requesting-code-review`, `receiving-code-review` | Structured review process |
| **Tester** | `systematic-debugging`, `verification-before-completion` | Bugs investigated systematically before fixes |

### Skill Invocation Rules

1. **Before dispatch**: The Orchestrator MUST check which skills are recommended for the target role and include explicit instructions in the sub-agent prompt: `You MUST invoke the following skills before doing any work: [skill names].`
2. **TDD enforcement**: Developer MUST invoke `test-driven-development` before writing any implementation code. The Iron Law applies: NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.
3. **Verification gate**: Before claiming work is complete, Developer MUST invoke `verification-before-completion` and provide evidence (test output, build logs, etc.).
4. **Brainstorming gate**: For creative tasks, Analyst MUST invoke `brainstorming` (or `feature-planning` as fallback) before producing specs.
5. **Fallback**: If a recommended skill is not available locally, use the **Skill Discovery & Assignment** process in `orchestrator.md` (scan local skills, check functional equivalents, resolve via `skills.sh` if needed).

## Role Dispatch Rules

### Role Selection

| Scenario | Roles to dispatch (typical) |
|---|---|
| Simple bug fix (quick-scope-scan suggests < 5 affected files) | Developer → Code Reviewer (optional) → Tester |
| Medium feature (new module, API) | Analyst → Developer → Code Reviewer → Tester |
| Large feature (architecture changes) | Analyst → [Critic] → Architect → [Critic] → Reviewer → Developer → Code Reviewer → Tester |
| Refactoring | Architect → [Critic] → Developer → Code Reviewer → Tester |
| Security / performance issue | Analyst → [Critic] → Architect → [Critic] → Reviewer → Developer → Tester |
| Code review only | Code Reviewer |
| Testing only | Tester |

These are defaults. You may skip or reorder stages based on task specifics.

### How to Launch a Sub-Agent (Claude Code — default)

**When running under the Claude Code adapter (`native-subagent` strategy):**

When you launch an `Agent` tool:
1. **Read the role file** from this skill directory (e.g., read `.claude/skills/bro/analyst.md`).
2. **Prepend the role file contents** to your prompt for the agent.
3. **Add the task context** after the role instructions:
   - Original user request
   - Results from previous roles (if any)
   - Specific files or areas to focus on
   - Constraints and requirements

**For other clients (Codex, Kimi, Copilot, Generic):**

Follow the launch methods defined in the active adapter file (`adapters/{client}.md`). The adapter provides the correct mechanism for dispatching sub-agents (CLI sessions, API calls, context switches, MCP server calls, etc.).

**Always** read the adapter file before the first dispatch if the runtime is not Claude Code.

### Example Prompt for Sub-Agent (Claude Code)

```
You are the Analyst. Follow the instructions below:

--- ROLE INSTRUCTIONS START ---
[full contents of analyst.md]
--- ROLE INSTRUCTIONS END ---

TASK:
[original user request]

CONTEXT:
[previous results from other roles if any]

CONSTRAINTS:
- [e.g., performance requirement]
- [e.g., security requirement]

SKILLS:
You MUST invoke the following skills before doing any work: [skill names from the role's Recommended Skills section].
```

### Skill Dispatch Instructions

When dispatching a sub-agent, add the skill dispatch instruction at the end of the prompt (after CONSTRAINTS):

```
SKILLS:
You MUST invoke the following skills before doing any work: [skill names].
```

List the skills from the role's `Recommended Skills` section that are relevant to the current task. For example, for a Developer working on a new feature: `You MUST invoke the following skills before doing any work: test-driven-development.` For a Code Reviewer: `You MUST invoke the following skills before doing any work: requesting-code-review.`

## Workflow Phases

### Phase 1: Analysis (Analyst)

**Trigger:** The user's request is ambiguous, complex, or involves multiple domains.

**What to do:**
1. Read `analyst.md` from this skill directory.
2. Dispatch the Analyst agent with the user's request + project context.
3. Receive a structured specification document.

**Decision:** If the spec is clear and actionable, proceed to Phase 2. If not, return the spec to the Analyst for refinement. *If rework exceeds the limit (max 2 per stage / 10 total), abort and escalate to the user.*

### Phase 1.5: Critique (Critic) — Optional

**Trigger:** The Orchestrator judges the task to be complex, ambiguous, high-stakes, or cross-cutting. The Critic is NOT invoked for simple or medium tasks unless the Orchestrator detects high risk.

**What to do:**
1. Read `critic.md` from this skill directory.
2. Dispatch the Critic agent with the Analyst's spec + project context.
3. Receive a structured critique report (Critical / Major / Minor issues, hidden assumptions, alternatives).

**Decision:** If the critique reveals critical blockers, return the spec to the Analyst (or escalate to the user). If the critique is supportive or minor, proceed to Phase 2. The Orchestrator decides whether to act on each critique item. *If rework exceeds the limit, abort and escalate.*

> **Critic vs Reviewer:** The Critic is adversarial and advisory; the Reviewer is a gatekeeper with an APPROVE/NEEDS_WORK/REJECT verdict. The Critic may run before the Reviewer (Phase 1.5 / 2.5) or in parallel with the Reviewer on very large tasks. The Orchestrator decides based on token budget and complexity.

### Phase 2: Architecture (Architect) — Optional

**Trigger:** The task involves architecture changes, new large modules, or affects multiple services.

**What to do:**
1. Read `architect.md` from this skill directory.
2. Dispatch the Architect agent with the Analyst's spec + project context.
3. Receive a structured architecture plan.

**Decision:** If the plan is sound, proceed to Phase 2.5 or Phase 3. If not, return to the Architect or Analyst for rework. *If rework exceeds the limit (max 2 per stage / 10 total), abort and escalate to the user.*

### Phase 2.5: Critique (Critic) — Optional

**Trigger:** An architecture plan was produced in Phase 2, and the Orchestrator judges the task to be complex, high-stakes, or involving significant architectural risk.

**What to do:**
1. Read `critic.md` from this skill directory.
2. Dispatch the Critic agent with the Analyst's spec + Architect's plan + project context.
3. Receive a structured critique report focusing on architectural risks, hidden assumptions, and alternative approaches.

**Decision:** If the critique reveals critical blockers, return the plan to the Architect (or Analyst). If the critique is supportive or minor, proceed to Phase 3 (Reviewer). The Orchestrator decides whether to act on each critique item. *If rework exceeds the limit, abort and escalate.*

> **Running Critic + Reviewer in parallel:** On very large tasks with sufficient token budget, the Orchestrator MAY dispatch Critic and Reviewer in parallel after Phase 2. The Critic focuses on assumptions, alternatives, and convention gaps; the Reviewer focuses on completeness, correctness, and approval. The Orchestrator synthesizes both reports before deciding on rework or proceed.

### Phase 3: Review (Reviewer) — Optional

**Trigger:** An architecture plan was produced in Phase 2.

**What to do:**
1. Read `reviewer.md` from this skill directory.
2. Dispatch the Reviewer agent with the Analyst's spec + Architect's plan.
3. Receive a review report with critical/major/minor issues.

**Decision:** If approved, proceed to Phase 4. If rejected, return the plan to the Architect or Analyst for rework. *If rework exceeds the limit (max 2 per stage / 10 total), abort and escalate to the user.*

### Phase 4: Development (Developer)

**What to do:**
1. Read `developer.md` from this skill directory.
2. Dispatch the Developer agent with the spec, plan (if any), and task context.
3. Receive the implementation (changed files, new code, etc.).

### Phase 5: Code Review (Code Reviewer) — Optional

**Trigger:** Code changes are significant, or the task requires it.

**What to do:**
1. Read `code-reviewer.md` from this skill directory.
2. Dispatch the Code Reviewer agent with the changed files and the original task.
3. Receive a code review report.

**Decision:** If approved, proceed to Phase 6. If rejected, return the review to the Developer for fixes. *If rework exceeds the limit (max 2 per stage / 10 total), abort and escalate to the user.*

### Phase 6: Testing (Tester)

**What to do:**
1. Read `tester.md` from this skill directory.
2. Dispatch the Tester agent with the changed files and the task context.
3. Receive a test report (test results, security analysis, edge cases).

**Decision:** If PASS, deliver to the user. If FAIL, return the findings to the Developer for fixes. *If rework exceeds the limit (max 2 per stage / 10 total), abort and escalate to the user.*

### Phase 7: Delivery

**What to do:**
1. Synthesize all results into a clear, user-friendly response.
2. Include:
   - What was done.
   - Key decisions made.
   - Files changed / created.
   - Known issues or limitations (if any).
   - Any recommendations for next steps.

## Task Tracking

The Orchestrator maintains a task tracker for each active task. The tracker uses a **file-based task tracker** for cross-client compatibility (works on Claude, Codex, Kimi, Copilot, and Generic runtimes). See `task-tracker.md` in this skill directory for the template.

## Rules

- **Do NOT** dispatch agents unnecessarily. If you can do it yourself, do it.
- **Always** read the relevant role file before dispatching a sub-agent. Do not rely on memory.
- **Forward full context** to every sub-agent: original request + all previous results.
- **Track progress** in the task tracker. Update it after each phase.
- **Keep the user informed** of high-level progress ("Launching Analyst...", "Analysis complete. Starting architecture phase...", etc.).
- **Make decisions** — don't ask the user for every transition. Use your judgment. Only ask when truly ambiguous.
- **When in doubt**, err on the side of quality: run an extra review or test phase rather than rushing to delivery.
- **Skill dispatch**: Always check the role's Recommended Skills section and dispatch the relevant skills before work begins. This is a quality gate, not optional.
- **Error recovery**: If a sub-agent does not respond in the expected format (missing markdown headers, no APPROVE/REJECT/PASS/FAIL verdict, or empty output), do not attempt to guess what it meant. Request a reformatted response once, or reduce the scope of the task. If it still fails, log the failure and escalate to the user.
- **Token budget**: Enforce the token budget defined in `orchestrator.md`. Track `token_usage` in the task tracker after every role dispatch. Warn the user at 80 % budget consumption and abort at 100 % unless the user explicitly approves an override. Prefer Base-tier models for Developer and Tester to reduce costs on large tasks.
