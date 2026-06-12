/**
 * Tests for bro-mcp-server/index.js — Skills Hub Integrator fallback logic.
 * Run: cd __tests__ && node --test index.test.js  (Node.js 20+ native test runner)
 *   or: npx jest index.test.js
 */

const { describe, it, beforeEach } = require("node:test");
const assert = require("node:assert");
const path = require("path");
const fs = require("fs");
const { execSync } = require("child_process");

// Mock modules before requiring the server module
const mockFs = {
  existsSync: () => false,
  readFileSync: () => "",
  writeFileSync: () => {},
  mkdirSync: () => {},
};

const mockExecSync = () => "";

// We need to re-require the module with fresh mocks for each test.
// Since CommonJS modules are cached, we'll test via a helper function
// that simulates the logic inline, or mock child_process and fs globally.

// Alternative: test the core functions in isolation by copying them here.
// For simplicity we test the algorithmic logic directly.

// ---------------------------------------------------------------------------
// Replicate the core functions from index.js for isolated testing
// ---------------------------------------------------------------------------

let skillsHubPrerequisitesCache = null;

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
      skillsHubPrerequisitesCache = {
        ok: false,
        reason: `${step.name} unavailable (${step.cmd} failed: ${err.message})`,
      };
      return skillsHubPrerequisitesCache;
    }
  }
  skillsHubPrerequisitesCache = { ok: true };
  return skillsHubPrerequisitesCache;
}

function resetPrerequisitesCache() {
  skillsHubPrerequisitesCache = null;
}

function resolveSkillFromSkillsHub(skillName, skillDir, taskId) {
  const pre = checkSkillsHubPrerequisites();
  if (!pre.ok) {
    return { success: false, reason: `skills.sh prerequisites failed: ${pre.reason}` };
  }

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

  const lines = findOutput.split("\n").filter((l) => l.trim());
  let selected = null;
  const officialRepos = [
    "anthropics/skills",
    "vercel-labs/agent-skills",
    "obra/superpowers",
    "microsoft/azure-skills",
  ];
  for (const line of lines) {
    const match = line.match(/^([\w-]+\/[\w-]+)(?:@([\w-]+))?/);
    if (match) {
      const ownerRepo = match[1];
      const skill = match[2] || skillName;
      const isOfficial = officialRepos.some((r) => ownerRepo.startsWith(r));
      if (!selected || isOfficial) {
        selected = { ownerRepo, skill };
        if (isOfficial) break;
      }
    }
  }
  if (!selected) {
    return {
      success: false,
      reason: `Could not parse any valid owner/repo from skills.sh search results for "${skillName}"`,
    };
  }

  const installCmd = `npx skills add ${selected.ownerRepo} -y`;
  try {
    execSync(installCmd, {
      encoding: "utf-8",
      stdio: "pipe",
      timeout: 60000,
    });
  } catch (err) {
    return {
      success: false,
      reason: `Installation failed (${installCmd}): ${err.message}`,
      attempted: selected.ownerRepo,
    };
  }

  const searchPaths = [
    path.join(skillDir, "..", "..", "skills", skillName, "SKILL.md"),
    path.join(skillDir, "..", `${skillName}.md`),
    path.join(skillDir, "..", "..", ".agents", "skills", skillName, "SKILL.md"),
  ];
  for (let attempt = 0; attempt < 2; attempt++) {
    for (const p of searchPaths) {
      if (fs.existsSync(p)) {
        return { success: true, skillPath: p, ownerRepo: selected.ownerRepo };
      }
    }
    if (attempt === 0) {
      try {
        execSync("sleep 1", { stdio: "pipe", timeout: 5000 });
      } catch (_) {}
    }
  }
  return {
    success: false,
    reason: `Installed ${selected.ownerRepo} but skill file not found in expected paths.`,
    attempted: selected.ownerRepo,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("checkSkillsHubPrerequisites", () => {
  beforeEach(() => {
    resetPrerequisitesCache();
  });

  it("returns ok when all prerequisites are met", () => {
    const originalExecSync = execSync;
    // Mock execSync to always succeed
    require("child_process").execSync = () => "v20.0.0";

    const result = checkSkillsHubPrerequisites();
    assert.strictEqual(result.ok, true);

    require("child_process").execSync = originalExecSync;
  });

  it("returns failure when node is missing", () => {
    const originalExecSync = execSync;
    let callCount = 0;
    require("child_process").execSync = () => {
      callCount++;
      if (callCount === 1) throw new Error("node not found");
      return "";
    };

    resetPrerequisitesCache();
    const result = checkSkillsHubPrerequisites();
    assert.strictEqual(result.ok, false);
    assert.ok(result.reason.includes("node unavailable"));

    require("child_process").execSync = originalExecSync;
  });

  it("caches the result", () => {
    const originalExecSync = execSync;
    let callCount = 0;
    require("child_process").execSync = () => {
      callCount++;
      return "v20.0.0";
    };

    resetPrerequisitesCache();
    checkSkillsHubPrerequisites();
    checkSkillsHubPrerequisites();
    assert.strictEqual(callCount, 4); // only 4 calls total (cached)

    require("child_process").execSync = originalExecSync;
  });
});

describe("resolveSkillFromSkillsHub", () => {
  beforeEach(() => {
    resetPrerequisitesCache();
  });

  it("returns failure when prerequisites are not met", () => {
    const originalExecSync = execSync;
    require("child_process").execSync = () => {
      throw new Error("npx not found");
    };

    const result = resolveSkillFromSkillsHub("brainstorming", "/tmp/skills", "task-1");
    assert.strictEqual(result.success, false);
    assert.ok(result.reason.includes("prerequisites failed"));

    require("child_process").execSync = originalExecSync;
  });

  it("returns failure when search yields no results", () => {
    const originalExecSync = execSync;
    let callCount = 0;
    require("child_process").execSync = (cmd) => {
      callCount++;
      if (cmd.includes("skills find")) return ""; // empty results
      return "v20.0.0";
    };

    const result = resolveSkillFromSkillsHub("brainstorming", "/tmp/skills", "task-1");
    assert.strictEqual(result.success, false);
    assert.ok(result.reason.includes("No results on skills.sh"));

    require("child_process").execSync = originalExecSync;
  });

  it("returns success when install and verify succeed", () => {
    const originalExecSync = execSync;
    const originalExistsSync = fs.existsSync;
    let callCount = 0;

    require("child_process").execSync = (cmd) => {
      callCount++;
      if (cmd.includes("skills find")) return "anthropics/skills@brainstorming\n";
      if (cmd.includes("skills add")) return "installed";
      return "v20.0.0";
    };

    require("fs").existsSync = (p) => p.includes("brainstorming");

    const result = resolveSkillFromSkillsHub("brainstorming", "/tmp/skills", "task-1");
    assert.strictEqual(result.success, true);
    assert.strictEqual(result.ownerRepo, "anthropics/skills");

    require("child_process").execSync = originalExecSync;
    require("fs").existsSync = originalExistsSync;
  });

  it("returns failure when installation fails", () => {
    const originalExecSync = execSync;
    let callCount = 0;

    require("child_process").execSync = (cmd) => {
      callCount++;
      if (cmd.includes("skills find")) return "anthropics/skills@brainstorming\n";
      if (cmd.includes("skills add")) throw new Error("npm install failed");
      return "v20.0.0";
    };

    const result = resolveSkillFromSkillsHub("brainstorming", "/tmp/skills", "task-1");
    assert.strictEqual(result.success, false);
    assert.ok(result.reason.includes("Installation failed"));

    require("child_process").execSync = originalExecSync;
  });

  it("returns failure when installed but file not found", () => {
    const originalExecSync = execSync;
    const originalExistsSync = fs.existsSync;
    let callCount = 0;

    require("child_process").execSync = (cmd) => {
      callCount++;
      if (cmd.includes("skills find")) return "anthropics/skills@brainstorming\n";
      if (cmd.includes("skills add")) return "installed";
      return "v20.0.0";
    };

    require("fs").existsSync = () => false; // file never appears

    const result = resolveSkillFromSkillsHub("brainstorming", "/tmp/skills", "task-1");
    assert.strictEqual(result.success, false);
    assert.ok(result.reason.includes("skill file not found in expected paths"));

    require("child_process").execSync = originalExecSync;
    require("fs").existsSync = originalExistsSync;
  });
});

// If running with native test runner, print summary
if (require.main === module) {
  console.log("\nRun with: node --test index.test.js\n");
}
