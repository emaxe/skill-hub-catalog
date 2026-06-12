# GitHub Copilot Adapter

## Runtime Detection

This adapter activates when any of the following are detected:
- `VSCODE_CWD` environment variable is set (running inside VS Code)
- `.vscode/` directory exists and Copilot extension is active
- `GITHUB_COPILOT_TOKEN` or `COPILOT_TOKEN` environment variable is set
- Explicit user confirmation that the current environment is Copilot Agent mode

> **Detection confidence:** Medium — `VSCODE_CWD` is a strong signal but not definitive. May require user confirmation.

## Execution Strategy: `mcp-server` or `agent-mode`

GitHub Copilot in VS Code operates in **Agent Mode** (`@agent`), which can call tools via MCP (Model Context Protocol) servers and execute bash commands. However, Copilot does **not** support spawning independent sub-agents natively. The recommended strategy is either:

1. **MCP Server (preferred for advanced use):** Create a `bro-orchestrator` MCP server that Copilot calls as a tool. The server manages the `bro` task state and can dispatch work to external processes (e.g., `claude` CLI, `codex` CLI, or local LLM APIs).
2. **Agent Mode with manual role switching:** Use Copilot's `@agent` chat with explicit system prompt changes to simulate roles.

---

## Launch Methods (in order of preference)

### Method 1: MCP Server (recommended for production)

Register `bro-orchestrator` as an MCP server in VS Code settings. This provides the most robust `bro` experience in Copilot.

#### MCP Server Setup

1. **Install dependencies** (from the `bro-mcp-server` directory):
   ```bash
   cd /path/to/bro-mcp-server
   npm install
   ```
   This installs the `@modelcontextprotocol/sdk` package and any other dependencies declared in `package.json`.

2. **Verify the server is healthy** before registering it in VS Code:
   ```bash
   npm run healthcheck
   # or directly:
   node index.js --healthcheck
   ```
   A successful healthcheck prints a short JSON status object and exits with code `0`. If it fails, check Node.js version (≥ 18) and that `npm install` completed without errors.

**VS Code configuration (`settings.json`):**

```json
{
  "mcpServers": {
    "bro-orchestrator": {
      "command": "node",
      "args": [
        "/path/to/bro-mcp-server/index.js",
        "--project-root", "${workspaceFolder}"
      ],
      "env": {
        "BRO_TASK_DIR": "${workspaceFolder}/.bro/tasks"
      }
    }
  }
}
```

**MCP Server responsibilities:**

1. **State management:** Maintain a JSON task tracker in `.bro/tasks/{task-id}.json`.
2. **Role dispatch:** Expose an MCP tool `bro_dispatch` with parameters:
   - `role`: analyst | architect | critic | developer | reviewer | code-reviewer | tester
   - `task`: string (original request)
   - `context`: string (previous results)
   - `constraints`: string (optional)
   - `skills`: string[] (skill names to inline)

3. **Execution backends:** The server can choose how to execute the role:
   - **Local LLM API:** Call OpenAI, Anthropic, Moonshot, or local model API with the role prompt.
   - **External CLI:** Spawn `claude`, `codex`, or `kimi` CLI subprocess.
   - **Copilot itself:** Return the prepared prompt back to Copilot with instructions to "execute this role" (less reliable, but zero external dependencies).

4. **Result aggregation:** Collect results from the execution backend and return them to Copilot.

**Copilot interaction flow:**

```
User: "Implement a new authentication system"

Copilot (@agent):
> I'll use the bro-orchestrator to manage this task.

[Calls bro_dispatch with role="analyst", task="Implement authentication..."]

MCP Server:
> Analyst result: [analysis summary]
> Next recommended role: architect

Copilot:
> Analysis complete. Key findings: [summary].
> Proceeding to architecture planning...

[Calls bro_dispatch with role="architect", context="Analyst result: ..."]
```

**Advantages:**
- Copilot remains the UI — no context switching for the user.
- Task state persists across chat sessions (stored in files).
- Can leverage the best backend for each role (e.g., Claude for architect, Codex for developer).

**Disadvantages:**
- Requires setting up and running an MCP server (Node.js or Python).
- More complex initial configuration.
- MCP server is a single point of failure.

### Method 2: Copilot Agent Mode with Manual Role Switching (fallback, simpler)

If the MCP server is not set up, simulate `bro` within Copilot's Agent Mode by explicitly switching roles in the chat.

**How it works:**

1. **Orchestrator prompt in Copilot chat:**

```
You are the bro Orchestrator. You will manage a multi-agent workflow for this task. 
Do not write code yet. First, follow the analyst instructions below.

--- ANALYST INSTRUCTIONS START ---
[analyst.md contents, summarized]
--- ANALYST INSTRUCTIONS END ---

TASK: [original request]

Act as the Analyst now. Return your analysis.
```

2. **After Copilot returns analysis:**

```
Analysis received. Now switch to Architect role.

--- ARCHITECT INSTRUCTIONS START ---
[architect.md contents, summarized]
--- ARCHITECT INSTRUCTIONS END ---

CONTEXT: [analysis result]
TASK: Design the architecture based on the analysis above.
```

3. **Continue for each role:** critic (if complex) → developer → code-reviewer → tester.

**Key rules for this method:**
- **One role per message turn:** Do not ask Copilot to be multiple roles at once.
- **Explicit switching:** Always say "Now switch to [Role] role" and provide the role instructions.
- **Context forwarding:** Include the original request + all previous synthesized results in every message.
- **No task tracker file:** Since this is purely conversational, the user (or Copilot) must maintain the thread. If the thread is lost, the workflow restarts.

**Advantages:**
- Zero setup. Works in any Copilot Agent Mode chat.
- User sees the full reasoning process in the chat UI.

**Disadvantages:**
- Entirely manual. The user (or Copilot) must remember to switch roles.
- No true isolation (all "roles" are the same Copilot instance).
- Chat history limits may truncate old context.
- Cannot run roles in parallel.
- No automated task tracking.

### Method 3: Copilot + External Orchestrator Script (hybrid)

Use a small Node.js/Python script that runs alongside VS Code. The script:

1. Reads `bro` role files.
2. Calls Copilot's API (if available) or uses the VS Code CLI to inject prompts.
3. Manages the task tracker file.

This is more complex than the MCP server and generally not recommended unless the MCP server cannot be used.

---

## Task Tracker

Copilot has **no native** task tracker. The file-based tracker is mandatory.

**Path:** `.bro/tasks/{task-id}/tracker.json` (or `.claude/bro-task-{task-id}.md` for cross-client compatibility).

**For MCP server:** The server owns the tracker file and exposes `bro_get_status` and `bro_update_task` tools.

**For manual mode:** The user or Copilot chat must manually summarize progress. No automated persistence.

**Recommended tracker format for Copilot:**
```json
{
  "task_id": "auth-system-2024",
  "status": "in_progress",
  "current_role": "developer",
  "completed_roles": ["analyst", "architect"],
  "results": {
    "analyst": "...",
    "architect": "..."
  },
  "blockers": [],
  "next_steps": ["developer implementation"]
}
```

---

## Skill Assignment (Copilot-specific)

Copilot does not have a `Skill` tool. Skills are inlined into the role prompts at dispatch time.

**For MCP server:** The server reads `.claude/skills/` and appends skill contents to the role prompt before sending to the execution backend.

**For manual mode:** The user must manually include skill instructions in the chat prompt. Provide a condensed summary rather than full skill files (Copilot chat has limited context compared to Claude Code).

**External registry fallback (`skills.sh`):** If the MCP server (`bro-mcp-server`) reports `[Skill not found locally]`, or if a skill is missing during manual dispatch, the Orchestrator (running in VS Code) should first attempt the `skills-hub-integrator` workflow (read `skills-hub-integrator.md` from this skill directory): run `npx skills find <skill>`, select the best match (official repos first, then highest install count), install with `npx skills add <owner/repo> --agent copilot -y` (or omit `--agent` if unsupported), then retry reading the skill file from `.claude/skills/`. If the MCP server supports it, extend `resolveSkillFromSkillsHub` (see `bro-mcp-server/index.js`) to call this workflow automatically. If installation fails or is unavailable, proceed with the condensed skill prompt below and notify the user.

**Condensed skill prompts for Copilot:**

| Skill | 1-line instruction for Copilot |
|---|---|
| `superpowers:brainstorming` | "Brainstorm 3+ approaches, list pros/cons, recommend one." |
| `superpowers:writing-plans` | "Write a detailed step-by-step plan before any code." |
| `superpowers:test-driven-development` | "Write tests first, confirm they fail, then implement." |
| `superpowers:systematic-debugging` | "Debug systematically: reproduce → isolate → fix → verify." |
| `superpowers:verification-before-completion` | "Verify all requirements and run tests before finishing." |
| `critical-thinking-logical-reasoning` | "Apply critical thinking: identify claims, examine evidence, spot fallacies, surface hidden assumptions, check consistency, propose alternatives." |
| `deep-research` | "Research alternatives, compare technologies, verify external claims with evidence." |

---

## Context Forwarding (Copilot-specific optimizations)

- **Chat context limits:** Copilot chat windows have limited context (~4K–8K tokens). The Orchestrator MUST aggressively summarize previous results (1–2 paragraphs max per role).
- **File references:** Use `@file` syntax in Copilot chat to reference specific files. Include absolute paths in the prompt for clarity.
- **Terminal integration:** Copilot Agent Mode can run terminal commands. For `tester`, explicitly ask Copilot to run tests in the terminal and report results.
- **No absolute paths in chat UI:** When showing results to the user, convert absolute paths to workspace-relative paths for readability.

---

## Copilot-native Features (optional enhancements)

| Feature | When to use in `bro` |
|---|---|
| `@workspace` / `@file` | `analyst` and `architect` — reference specific files in the codebase. |
| Terminal tool execution | `tester` — run `npm test`, `pytest`, etc. |
| Code edits (inline) | `developer` — Copilot can suggest edits directly in the editor. |
| Git integration | `code-reviewer` — ask Copilot to review the latest diff. |
| Web search (if enabled) | `analyst` — research external APIs, libraries. |

---

### Failure Handling

If the MCP server (`bro-mcp-server`) is not running or returns an error:
1. Log the failure in the task tracker under `failures`.
2. Restart the MCP server process (Node.js) and retry once.
3. If the MCP server cannot be restarted, fall back to **Method 2** (manual Copilot Agent Mode role switching) and notify the user: *"MCP server unavailable. Switching to manual Agent Mode fallback."*
4. If `skills.sh` is unavailable, use the **Condensed skill prompts** table (see above) and inline the skill instructions directly into the Copilot chat prompt.
5. If Copilot Agent Mode itself is unavailable (e.g., VS Code not in agent mode), abort the pipeline and notify the user to switch to a supported client (Claude, Codex, Kimi, or Generic).

## Adapter Status: `experimental`

MCP server strategy is the most promising but requires external setup. Manual role switching works immediately but is labor-intensive. Recommended for users who primarily use VS Code and Copilot as their main IDE.
