# Task Tracker

This template is managed exclusively by the **Orchestrator**. No other agent should read or write this file.

---

## Task: {TASK_ID}

- **Status**: `pending` | `in_progress` | `review` | `completed` | `blocked` | `cancelled`
- **Priority**: `low` | `medium` | `high` | `critical`
- **Created**: {YYYY-MM-DD HH:MM}
- **Updated**: {YYYY-MM-DD HH:MM}
- **Assigned to**: {agent_role} (or `orchestrator` for coordination)

### Description

{Original user request. Full text or summary.}

### Subtasks

- [ ] {Subtask 1} — assigned to: {role}, status: {status}
- [ ] {Subtask 2} — assigned to: {role}, status: {status}
- [ ] {Subtask N}

### Dependencies

- {TASK_ID} blocks this task: Yes / No
- This task blocks: {TASK_ID list}
- External dependencies: {list if any}

### Stage History

#### Stage: Analysis
- **Agent**: Analyst
- **Status**: `not_started` | `in_progress` | `completed` | `skipped` | `completed_with_uncertainty`
- **Thought Loop Count**: {0..2}
- **Result**: {Summary or link to spec}
- **Artifacts**: {Spec file path, if saved}

#### Stage: Architecture
- **Agent**: Architect
- **Status**: `not_started` | `in_progress` | `completed` | `skipped` | `completed_with_uncertainty`
- **Thought Loop Count**: {0..2}
- **Result**: {Summary or link to plan}
- **Artifacts**: {Architecture plan file path, if saved}

#### Stage: Critique (Spec or Plan)
- **Agent**: Critic
- **Status**: `not_started` | `in_progress` | `completed` | `skipped` | `completed_with_uncertainty`
- **Thought Loop Count**: {0..2}
- **Posture**: `SUPPORTIVE` | `CHALLENGING` | `STRONGLY_OPPOSED`
- **Rework Count**: {0..2}
- **Result**: {Summary or link to critique report}
- **Orchestrator Decision**: {Acted / Partially acted / Ignored / Skipped}
- **Key Issues**: {Critical / Major / Minor count}
- **Alternatives Proposed**: {Yes / No}

#### Stage: Review (Plan)
- **Agent**: Reviewer
- **Status**: `not_started` | `in_progress` | `completed` | `skipped` | `completed_with_uncertainty`
- **Thought Loop Count**: {0..2}
- **Verdict**: `APPROVE` | `NEEDS_WORK` | `REJECT`
- **Rework Count**: {0..2}
- **Result**: {Summary or link to review report}
- **Orchestrator Decision**: {Approved / Returned to Analyst / Returned to Architect / Skipped}

#### Stage: Development
- **Agent**: Developer
- **Status**: `not_started` | `in_progress` | `completed` | `skipped` | `completed_with_uncertainty`
- **Thought Loop Count**: {0..2}
- **Result**: {Summary of changes}
- **Artifacts**: {List of changed files}

#### Stage: Code Review
- **Agent**: Code Reviewer
- **Status**: `not_started` | `in_progress` | `completed` | `skipped` | `completed_with_uncertainty`
- **Thought Loop Count**: {0..2}
- **Verdict**: `APPROVE` | `NEEDS_WORK` | `REJECT`
- **Rework Count**: {0..2}
- **Result**: {Summary or link to review report}
- **Orchestrator Decision**: {Approved / Returned to Developer / Skipped}

#### Stage: Testing
- **Agent**: Tester
- **Status**: `not_started` | `in_progress` | `completed` | `skipped` | `completed_with_uncertainty`
- **Thought Loop Count**: {0..2}
- **Verdict**: `PASS` | `NEEDS_WORK` | `FAIL`
- **Rework Count**: {0..2}
- **Result**: {Summary or link to test report}
- **Orchestrator Decision**: {Approved / Returned to Developer / Returned to Analyst / Skipped}

### Stuck Detection

- **Thought Loop Flag**: `true` | `false`
- **Stuck On**: {hypothesis, question, or section where the agent looped}
- **Hard Commit Triggered**: `true` | `false`
- **Resolution**: `proceeded_with_commit` | `skipped_with_warning` | `escalated_to_user`
- **Orchestrator Note**: {how the loop was detected and what action was taken}

### Results

#### Final Artifacts
- {File path} — {description}
- {File path} — {description}

#### Key Decisions
- {Decision 1 and rationale}
- {Decision 2 and rationale}

#### Open Issues / Tech Debt
- {Issue 1 — priority, proposed solution}
- {Issue 2}

### Token Usage

- **token_usage total budget**: `{token_budget}` (default: 100000; override via `BRO_TOKEN_BUDGET`)
- **token_usage total spent**: `{total_tokens_spent}`
- **token_usage by role**:
  - `{role}` — prompt: `{prompt_tokens}`, completion: `{completion_tokens}`, total: `{total_tokens}`
- **token_usage status**: `within_budget` | `warning_80%` | `exceeded` | `hard_stop`

### Failures Log

- `{timestamp}` — `{stage}` — `{failure_type}` — `{action_taken}` — `{resolution}`

### Orchestrator Notes

{Internal notes for the orchestrator: context, next steps, blockers, reminders.}

---

## Task: {NEXT_TASK_ID}

{...repeat structure above...}
