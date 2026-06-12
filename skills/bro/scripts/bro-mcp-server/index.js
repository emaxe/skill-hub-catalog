#!/usr/bin/env node
/**
 * Bro MCP Server — Copilot Adapter
 * ==================================
 * A lightweight Model Context Protocol (MCP) server that acts as the
 * orchestration backend for `bro` when running inside GitHub Copilot
 * (VS Code Agent Mode).
 *
 * What it does:
 *   - Maintains a JSON-based task tracker (per-task state).
 *   - Exposes `bro_dispatch` for launching a `bro` role.
 *   - Can delegate to local LLM APIs, external CLI tools, or return a
 *     prepared prompt back to Copilot for execution.
 *
 * Setup (VS Code settings.json):
 *   {
 *     "mcpServers": {
 *       "bro-orchestrator": {
 *         "command": "node",
 *         "args": [
 *           "/path/to/.claude/skills/bro/scripts/bro-mcp-server/index.js",
 *           "--project-root", "${workspaceFolder}"
 *         ],
 *         "env": {
 *           "BRO_TASK_DIR": "${workspaceFolder}/.bro/tasks",
 *           "BRO_SKILL_DIR": "${workspaceFolder}/.claude/skills/bro"
 *         }
 *       }
 *     }
 *   }
 *
 * Requirements:
 *   node >= 18
 *   npm install @modelcontextprotocol/sdk
 */

const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} = require("@modelcontextprotocol/sdk/types.js");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const PROJECT_ROOT = process.argv.includes("--project-root")
  ? process.argv[process.argv.indexOf("--project-root") + 1]
  : process.cwd();

const TASK_DIR = process.env.BRO_TASK_DIR || path.join(PROJECT_ROOT, ".bro", "tasks");
const SKILL_DIR = process.env.BRO_SKILL_DIR || path.join(PROJECT_ROOT, ".claude", "skills", "bro");

function ensureDir(p) {
  if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true });
}

ensureDir(TASK_DIR);

// ---------------------------------------------------------------------------
// Task Tracker helpers
// ---------------------------------------------------------------------------

function taskPath(taskId) {
  return path.join(TASK_DIR, `${taskId}.json`);
}

function loadTask(taskId) {
  const p = taskPath(taskId);
  if (fs.existsSync(p)) return JSON.parse(fs.readFileSync(p, "utf-8"));
  return null;
}

function saveTask(taskId, data) {
  fs.writeFileSync(taskPath(taskId), JSON.stringify(data, null, 2), "utf-8");
}

function initTask(taskId, taskDescription, pipeline) {
  const data = {
    task_id: taskId,
    description: taskDescription,
    status: "pending",
    pipeline,
    current_role: null,
    completed_roles: [],
    results: {},
    verdicts: {},
    blockers: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  saveTask(taskId, data);
  return data;
}

function readRole(roleName) {
  const p = path.join(SKILL_DIR, `${roleName}.md`);
  if (!fs.existsSync(p)) throw new Error(`Role file not found: ${p}`);
  return fs.readFileSync(p, "utf-8");
}

// ---------------------------------------------------------------------------
// Skills Hub Integrator — External registry fallback (skills.sh)
// ---------------------------------------------------------------------------

// Cached prerequisites check result (per-process)
let skillsHubPrerequisitesCache = null;

/**
 * Check prerequisites for skills.sh CLI.
 * Caches the result so we only run once per process.
 * Returns { ok: boolean, reason?: string }.
 */
function checkSkillsHubPrerequisites() {
  if (skillsHubPrerequisitesCache !== null) return skillsHubPrerequisitesCache;
  const steps = [
    { name: "node", cmd: "node --version" },
    { name: "npm", cmd: "npm --version" },
    { name: "npx", cmd: "npx --version" },
    { name: "skills CLI", cmd: "npx skills --version" },
  ];
  for (const step of steps) {
    try {
      execSync(step.cmd, { stdio: "pipe", timeout: 15000 });
    } catch (err) {
      skillsHubPrerequisitesCache = { ok: false, reason: `${step.name} unavailable (${step.cmd} failed: ${err.message})` };
      return skillsHubPrerequisitesCache;
    }
  }
  skillsHubPrerequisitesCache = { ok: true };
  return skillsHubPrerequisitesCache;
}

/**
 * Attempt to resolve a skill from skills.sh (external registry).
 * Steps: prerequisites -> find -> select -> install -> verify.
 * Returns { success: boolean, skillPath?: string, ownerRepo?: string, reason?: string }.
 */
function resolveSkillFromSkillsHub(skillName, taskId) {
  const pre = checkSkillsHubPrerequisites();
  if (!pre.ok) {
    return { success: false, reason: `skills.sh prerequisites failed: ${pre.reason}` };
  }

  // 1. Search
  let findOutput;
  try {
    findOutput = execSync(`npx skills find ${skillName}`, {
      encoding: "utf-8",
      stdio: "pipe",
      timeout: 30000,
    });
  } catch (err) {
    return { success: false, reason: `npx skills find failed: ${err.message}` };
  }

  if (!findOutput || findOutput.trim().length === 0) {
    return { success: false, reason: `No results on skills.sh for "${skillName}"` };
  }

  // 2. Select best match — parse first line that looks like "owner/repo@skill"
  const lines = findOutput.split("\n").filter((l) => l.trim());
  let selected = null;
  const officialRepos = ["anthropics/skills", "vercel-labs/agent-skills", "obra/superpowers", "microsoft/azure-skills"];
  for (const line of lines) {
    const match = line.match(/^([\w-]+\/[\w-]+)(?:@([\w-]+))?/);
    if (match) {
      const ownerRepo = match[1];
      const skill = match[2] || skillName;
      const isOfficial = officialRepos.some((r) => ownerRepo.startsWith(r));
      if (!selected || isOfficial) {
        selected = { ownerRepo, skill };
        if (isOfficial) break; // Prefer first official match
      }
    }
  }
  if (!selected) {
    return { success: false, reason: `Could not parse any valid owner/repo from skills.sh search results for "${skillName}"` };
  }

  // 3. Install
  const installCmd = `npx skills add ${selected.ownerRepo} -y`;
  try {
    execSync(installCmd, {
      encoding: "utf-8",
      stdio: "pipe",
      timeout: 60000,
    });
  } catch (err) {
    return { success: false, reason: `Installation failed (${installCmd}): ${err.message}`, attempted: selected.ownerRepo };
  }

  // 4. Verify — check common skill directories
  const searchPaths = [
    path.join(SKILL_DIR, "..", "..", "skills", skillName, "SKILL.md"),
    path.join(SKILL_DIR, "..", `${skillName}.md`),
    path.join(SKILL_DIR, "..", "..", ".agents", "skills", skillName, "SKILL.md"),
  ];
  for (let attempt = 0; attempt < 2; attempt++) {
    for (const p of searchPaths) {
      if (fs.existsSync(p)) {
        return { success: true, skillPath: p, ownerRepo: selected.ownerRepo };
      }
    }
    if (attempt === 0) {
      // Wait briefly for async filesystem sync
      try {
        execSync("sleep 1", { stdio: "pipe", timeout: 5000 });
      } catch (_) {}
    }
  }
  return { success: false, reason: `Installed ${selected.ownerRepo} but skill file not found in expected paths.`, attempted: selected.ownerRepo };
}

// ---------------------------------------------------------------------------
// MCP Server
// ---------------------------------------------------------------------------

const server = new Server(
  { name: "bro-orchestrator", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "bro_dispatch",
        description:
          "Dispatch a bro role (analyst, architect, developer, reviewer, code-reviewer, tester) for a given task. Returns the prepared system prompt and context. The caller (Copilot) should execute the role and then call bro_report_result.",
        inputSchema: {
          type: "object",
          properties: {
            task_id: { type: "string", description: "Unique task identifier" },
            task: { type: "string", description: "Original user task description" },
            role: {
              type: "string",
              enum: ["analyst", "architect", "developer", "reviewer", "code-reviewer", "tester"],
              description: "Role to dispatch",
            },
            pipeline: {
              type: "array",
              items: { type: "string" },
              description: "Full planned pipeline (optional, for initialization)",
            },
            previous_results: {
              type: "object",
              description: "Mapping from previous role names to their results",
            },
            constraints: { type: "string", description: "Optional constraints" },
            skills: {
              type: "array",
              items: { type: "string" },
              description: "Skill names to inline (optional)",
            },
          },
          required: ["task_id", "task", "role"],
        },
      },
      {
        name: "bro_report_result",
        description:
          "Report the result of a dispatched bro role back to the orchestrator. Updates the task tracker.",
        inputSchema: {
          type: "object",
          properties: {
            task_id: { type: "string" },
            role: { type: "string" },
            result: { type: "string", description: "Full result text from the role" },
            verdict: {
              type: "string",
              enum: ["APPROVE", "NEEDS_WORK", "REJECT", "PASS", "FAIL", "PENDING"],
              description: "Verdict from the role (if applicable)",
            },
          },
          required: ["task_id", "role", "result"],
        },
      },
      {
        name: "bro_get_status",
        description: "Get the current status and history of a bro task.",
        inputSchema: {
          type: "object",
          properties: {
            task_id: { type: "string" },
          },
          required: ["task_id"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  // ---------------------------------------------------------------
  // bro_dispatch
  // ---------------------------------------------------------------
  if (name === "bro_dispatch") {
    const { task_id, task, role, pipeline, previous_results, constraints, skills } = args;

    let tracker = loadTask(task_id);
    if (!tracker) {
      tracker = initTask(task_id, task, pipeline || []);
    }

    tracker.current_role = role;
    tracker.status = "in_progress";
    tracker.updated_at = new Date().toISOString();
    saveTask(task_id, tracker);

    let systemPrompt;
    try {
      systemPrompt = readRole(role);
    } catch (e) {
      return {
        content: [
          { type: "text", text: `ERROR: ${e.message}` },
        ],
        isError: true,
      };
    }

    // Inline skills if requested (best-effort)
    const skillDir = SKILL_DIR;
    if (skills && skills.length) {
      const skillBlocks = [];
      for (const skillName of skills) {
        const candidates = [
          path.join(skillDir, "..", "..", "skills", skillName, "SKILL.md"),
          path.join(skillDir, "..", `${skillName}.md`),
        ];
        let found = false;
        for (const cand of candidates) {
          if (fs.existsSync(cand)) {
            skillBlocks.push(`--- SKILL: ${skillName} ---\n${fs.readFileSync(cand, "utf-8")}\n--- END SKILL ---`);
            found = true;
            break;
          }
        }
        if (!found) {
          // Attempt external registry fallback via skills.sh
          const external = resolveSkillFromSkillsHub(skillName, task_id);
          if (external.success && external.skillPath) {
            skillBlocks.push(
              `--- SKILL: ${skillName} (fetched from skills.sh: ${external.ownerRepo}) ---\n${fs.readFileSync(external.skillPath, "utf-8")}\n--- END SKILL ---`
            );
            // Log in tracker
            tracker.external_dependencies = tracker.external_dependencies || [];
            tracker.external_dependencies.push({
              source: "skills.sh",
              skill: skillName,
              owner_repo: external.ownerRepo,
              status: "SUCCESS",
              timestamp: new Date().toISOString(),
            });
          } else {
            skillBlocks.push(`--- SKILL: ${skillName} ---\n[Skill not found locally or on skills.sh${external.reason ? ": " + external.reason : ""}]\n--- END SKILL ---`);
            tracker.external_dependencies = tracker.external_dependencies || [];
            tracker.external_dependencies.push({
              source: "skills.sh",
              skill: skillName,
              status: "FAILED",
              reason: external.reason || "unknown",
              timestamp: new Date().toISOString(),
            });
          }
        }
      }
      if (skillBlocks.length) {
        systemPrompt += "\n\n## Inlined Skill Directives\n\n" + skillBlocks.join("\n\n");
      }
    }

    // Build context from previous results
    const contextParts = [];
    if (previous_results) {
      for (const [prevRole, result] of Object.entries(previous_results)) {
        const summary =
          typeof result === "string" && result.length > 4000
            ? result.slice(0, 4000) + "\n... [truncated]"
            : result;
        contextParts.push(`### ${prevRole.toUpperCase()} RESULT:\n${summary}\n`);
      }
    }

    const context = contextParts.length ? contextParts.join("\n") : "No previous context.";

    const userPrompt = `TASK: ${task}\n\nCONTEXT FROM PREVIOUS ROLES:\n${context}\n\n${constraints ? `CONSTRAINTS: ${constraints}\n\n` : ""}Your role is ${role}. Execute according to your role instructions. Return a structured report.`;

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              task_id,
              role,
              system_prompt: systemPrompt,
              user_prompt: userPrompt,
              tracker_status: tracker.status,
              completed_roles: tracker.completed_roles,
              instruction: "Execute this role using the provided system and user prompts. When done, call bro_report_result with the full output.",
            },
            null,
            2
          ),
        },
      ],
    };
  }

  // ---------------------------------------------------------------
  // bro_report_result
  // ---------------------------------------------------------------
  if (name === "bro_report_result") {
    const { task_id, role, result, verdict } = args;
    let tracker = loadTask(task_id);
    if (!tracker) {
      return {
        content: [{ type: "text", text: `ERROR: Task ${task_id} not found.` }],
        isError: true,
      };
    }
    tracker.completed_roles.push(role);
    tracker.results[role] = result;
    if (verdict) tracker.verdicts[role] = verdict;
    tracker.current_role = null;
    tracker.updated_at = new Date().toISOString();
    saveTask(task_id, tracker);

    return {
      content: [
        {
          type: "text",
          text: `Result recorded for role "${role}" in task "${task_id}".\n\nCompleted roles: ${tracker.completed_roles.join(", ")}\nTracker: ${taskPath(task_id)}`,
        },
      ],
    };
  }

  // ---------------------------------------------------------------
  // bro_get_status
  // ---------------------------------------------------------------
  if (name === "bro_get_status") {
    const { task_id } = args;
    const tracker = loadTask(task_id);
    if (!tracker) {
      return {
        content: [{ type: "text", text: `ERROR: Task ${task_id} not found.` }],
        isError: true,
      };
    }
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(tracker, null, 2),
        },
      ],
    };
  }

  return {
    content: [{ type: "text", text: `Unknown tool: ${name}` }],
    isError: true,
  };
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Bro MCP Server running on stdio");
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
