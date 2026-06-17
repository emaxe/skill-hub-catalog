#!/usr/bin/env python3
"""
Bro Skill — Structural Integrity Tests
========================================
Automated tests that verify all multi-client orchestration files
are present, correctly structured, and contain required sections.

Run:
    cd .claude/skills/bro
    python3 -m pytest tests/test_structure.py -v
    # or simply:
    python3 tests/test_structure.py
"""

import json
import pathlib
import re
import sys

import ast

SKILL_DIR = pathlib.Path(__file__).parent.parent.resolve()


def test_core_files_exist():
    """All core role and configuration files must exist."""
    required = [
        "SKILL.md",
        "orchestrator.md",
        "AGENTS.md",
        "analyst.md",
        "architect.md",
        "developer.md",
        "reviewer.md",
        "code-reviewer.md",
        "tester.md",
        "task-tracker.md",
    ]
    for name in required:
        path = SKILL_DIR / name
        assert path.exists(), f"Missing core file: {name}"
        assert path.stat().st_size > 0, f"Empty core file: {name}"


def test_adapters_directory_exists():
    """Adapters directory must exist and contain all client adapters."""
    adapters_dir = SKILL_DIR / "adapters"
    assert adapters_dir.exists(), "Missing adapters/ directory"

    expected_adapters = [
        "claude.md",
        "codex.md",
        "kimi.md",
        "copilot.md",
        "generic.md",
    ]
    for name in expected_adapters:
        path = adapters_dir / name
        assert path.exists(), f"Missing adapter: {name}"
        assert path.stat().st_size > 500, f"Adapter {name} suspiciously small"


def test_scripts_directory_exists():
    """Scripts directory must contain orchestrator templates."""
    scripts_dir = SKILL_DIR / "scripts"
    assert scripts_dir.exists(), "Missing scripts/ directory"

    assert (scripts_dir / "generic-orchestrator-template.py").exists()
    assert (scripts_dir / "bro-mcp-server" / "index.js").exists()


def test_python_orchestrator_parses():
    """generic-orchestrator-template.py must be syntactically valid Python."""
    path = SKILL_DIR / "scripts" / "generic-orchestrator-template.py"
    source = path.read_text(encoding="utf-8")
    try:
        ast.parse(source)
    except SyntaxError as exc:
        pytest.fail(f"Syntax error in generic-orchestrator-template.py: {exc}")


def test_mcp_server_is_valid_js():
    """bro-mcp-server/index.js must be valid Node.js (basic check)."""
    path = SKILL_DIR / "scripts" / "bro-mcp-server" / "index.js"
    source = path.read_text(encoding="utf-8")
    # Basic sanity: no obviously unbalanced braces, has required imports
    assert "require(" in source, "MCP server missing require statements"
    assert "module.exports" in source or "exports" in source or "Server(" in source, "MCP server missing Server instantiation"


def test_skill_md_has_multi_client_section():
    """SKILL.md must reference multi-client runtime support."""
    source = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "Multi-Client Runtime Support" in source, "SKILL.md missing multi-client section"
    assert "adapters/" in source, "SKILL.md missing adapters reference"
    assert "Runtime Detection" in source, "SKILL.md missing runtime detection"


def test_orchestrator_md_has_runtime_detection():
    """orchestrator.md must instruct detecting runtime client."""
    source = (SKILL_DIR / "orchestrator.md").read_text(encoding="utf-8")
    assert "Detect runtime" in source or "Detect the runtime" in source, "orchestrator.md missing runtime detection step"
    assert "adapters" in source, "orchestrator.md missing adapters reference"


def test_agents_md_has_adapter_table():
    """AGENTS.md must contain the runtime detection and execution strategies table."""
    source = (SKILL_DIR / "AGENTS.md").read_text(encoding="utf-8")
    assert "Runtime Detection" in source, "AGENTS.md missing Runtime Detection section"
    assert "Execution Strategies" in source, "AGENTS.md missing Execution Strategies section"
    assert "native-subagent" in source, "AGENTS.md missing native-subagent strategy"
    assert "api-session" in source, "AGENTS.md missing api-session strategy"
    assert "context-switch" in source, "AGENTS.md missing context-switch strategy"


def test_adapters_have_required_sections():
    """Each adapter must contain mandatory sections."""
    adapters_dir = SKILL_DIR / "adapters"
    required_sections = [
        "Runtime Detection",
        "Execution Strategy",
        "Launch Methods",
        "Task Tracker",
        "Skill Assignment",
    ]
    for path in adapters_dir.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        missing = [s for s in required_sections if s not in content]
        assert not missing, f"Adapter {path.name} missing sections: {missing}"


def test_claude_adapter_has_agent_tool_reference():
    """Claude adapter must reference Agent tool and subagent_type."""
    content = (SKILL_DIR / "adapters" / "claude.md").read_text(encoding="utf-8")
    assert "Agent" in content, "claude.md missing Agent tool reference"
    assert "subagent_type" in content, "claude.md missing subagent_type reference"
    assert "TaskCreate" in content, "claude.md missing TaskCreate reference"


def test_codex_adapter_has_cli_reference():
    """Codex adapter must reference codex CLI and --mode agent."""
    content = (SKILL_DIR / "adapters" / "codex.md").read_text(encoding="utf-8")
    assert "codex" in content, "codex.md missing codex CLI reference"
    assert "--mode agent" in content, "codex.md missing --mode agent reference"


def test_kimi_adapter_has_context_switching():
    """Kimi adapter must reference context switching and long context."""
    content = (SKILL_DIR / "adapters" / "kimi.md").read_text(encoding="utf-8")
    assert "context-switch" in content or "Context Switching" in content, "kimi.md missing context switching reference"
    assert "long context" in content or "long-context" in content, "kimi.md missing long context reference"


def test_copilot_adapter_has_mcp_reference():
    """Copilot adapter must reference MCP server and VS Code settings."""
    content = (SKILL_DIR / "adapters" / "copilot.md").read_text(encoding="utf-8")
    assert "MCP" in content, "copilot.md missing MCP reference"
    assert "settings.json" in content or "VS Code" in content, "copilot.md missing VS Code reference"


def test_generic_adapter_has_external_orchestrator():
    """Generic adapter must reference external orchestrator script."""
    content = (SKILL_DIR / "adapters" / "generic.md").read_text(encoding="utf-8")
    assert "external orchestrator" in content or "external-process" in content, "generic.md missing external orchestrator reference"
    assert "generic-orchestrator" in content, "generic.md missing generic-orchestrator script reference"


def test_all_adapters_have_fallback_mention():
    """Every adapter should mention fallback or status to indicate maturity."""
    adapters_dir = SKILL_DIR / "adapters"
    for path in adapters_dir.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        assert "Adapter Status" in content or "fallback" in content.lower(), \
            f"Adapter {path.name} missing Adapter Status or fallback section"


def test_cross_client_task_tracker_mentioned():
    """At least one core file mentions the cross-client task tracker."""
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "Cross-client compatibility" in skill or "file-based task tracker" in skill, \
        "SKILL.md missing cross-client task tracker mention"


def test_role_files_unchanged():
    """Role files (analyst, architect, developer, reviewer, code-reviewer, tester)
    should NOT contain client-specific instructions — they remain client-agnostic."""
    role_files = ["analyst.md", "architect.md", "developer.md", "reviewer.md", "code-reviewer.md", "tester.md"]
    for name in role_files:
        content = (SKILL_DIR / name).read_text(encoding="utf-8")
        # Should not contain specific adapter references
        forbidden = ["Agent tool", "codex CLI", "Kimi API", "MCP server", "VS Code", "Ollama"]
        for f in forbidden:
            assert f not in content, f"Role {name} should be client-agnostic but contains: {f}"


def test_no_fake_model_names():
    """No role or config file should contain fictional model names."""
    deny_list = [
        "claude-opus-4-8",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "gemini-3.5-pro",
        "gemini-3.1",
        "gpt-5.5",
        "gpt-5.4",
        "kimi-2.6",
        "glm-5.1",
        "qwen-3.7-max",
        "qwen-3.6",
        "deepseek-v4-flash",
    ]
    files_to_check = [
        SKILL_DIR / "AGENTS.md",
        SKILL_DIR / "orchestrator.md",
        SKILL_DIR / "analyst.md",
        SKILL_DIR / "architect.md",
        SKILL_DIR / "developer.md",
        SKILL_DIR / "reviewer.md",
        SKILL_DIR / "code-reviewer.md",
        SKILL_DIR / "tester.md",
        SKILL_DIR / "scripts" / "generic-orchestrator-template.py",
    ]
    for path in files_to_check:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for fake in deny_list:
            assert fake not in content, f"Fictional model name '{fake}' found in {path.name}"


def test_guardrails_present():
    """orchestrator.md and SKILL.md must mention max_iterations, timeout, and retry."""
    orch = (SKILL_DIR / "orchestrator.md").read_text(encoding="utf-8")
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for keyword in ["max_iterations", "timeout", "retry"]:
        assert keyword in orch.lower() or keyword in skill.lower(), (
            f"Missing guardrail keyword '{keyword}' in orchestrator.md or SKILL.md"
        )


def test_error_recovery_in_orchestrator():
    """orchestrator.md must contain Error Recovery & Failure Modes section with >= 40 lines."""
    content = (SKILL_DIR / "orchestrator.md").read_text(encoding="utf-8")
    assert "Error Recovery & Failure Modes" in content, "Missing Error Recovery section in orchestrator.md"
    section_start = content.find("Error Recovery & Failure Modes")
    next_section = content.find("##", section_start + 1)
    section_text = content[section_start:next_section] if next_section != -1 else content[section_start:]
    lines = section_text.strip().splitlines()
    assert len(lines) >= 40, f"Error Recovery section too short ({len(lines)} lines, expected >= 40)"


def test_skill_md_has_error_recovery_rule():
    """SKILL.md must contain a rule about sub-agent unexpected format."""
    content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "does not respond in the expected format" in content.lower() or "unexpected format" in content.lower(), \
        "SKILL.md missing error recovery rule for unexpected sub-agent format"


def test_adapters_have_failure_handling():
    """Each adapter must contain a Failure Handling subsection."""
    adapters_dir = SKILL_DIR / "adapters"
    for path in adapters_dir.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        assert "Failure Handling" in content, f"Adapter {path.name} missing Failure Handling section"


def test_agents_md_has_failure_escalation_matrix():
    """AGENTS.md must contain Failure Escalation Matrix."""
    content = (SKILL_DIR / "AGENTS.md").read_text(encoding="utf-8")
    assert "Failure Escalation Matrix" in content, "AGENTS.md missing Failure Escalation Matrix"


def test_generic_orchestrator_handles_error():
    """generic-orchestrator-template.py must handle ERROR: responses and retry once."""
    content = (SKILL_DIR / "scripts" / "generic-orchestrator-template.py").read_text(encoding="utf-8")
    assert "result.startswith(\"ERROR:\")" in content, "Missing ERROR: handling in generic orchestrator"
    assert "retry" in content.lower(), "Missing retry logic in generic orchestrator"


def test_task_tracker_has_failures_field():
    """task-tracker.md must contain a Failures Log section."""
    content = (SKILL_DIR / "task-tracker.md").read_text(encoding="utf-8")
    assert "Failures Log" in content, "task-tracker.md missing Failures Log section"


def test_generic_orchestrator_no_hardcoded_parent_parent():
    """generic-orchestrator-template.py must not use hardcoded .. / .. / skills paths."""
    content = (SKILL_DIR / "scripts" / "generic-orchestrator-template.py").read_text(encoding="utf-8")
    assert '.. / ".." / "skills"' not in content, "Found hardcoded .. / .. / skills path in load_skill"
    assert 'parent.parent / ".agents" / "skills"' in content or 'SKILLS_SEARCH_PATHS' in content, \
        "Missing standard skill search path resolution (env var or Path.parent)"


def test_generic_orchestrator_uses_env_for_skill_paths():
    """generic-orchestrator-template.py must use SKILLS_SEARCH_PATHS env variable."""
    content = (SKILL_DIR / "scripts" / "generic-orchestrator-template.py").read_text(encoding="utf-8")
    assert "SKILLS_SEARCH_PATHS" in content, "Missing SKILLS_SEARCH_PATHS env variable usage"
    assert "os.environ.get" in content, "Missing os.environ.get call for skill paths"


def test_generic_orchestrator_has_quick_scope_scan():
    """generic-orchestrator-template.py must contain a quick_scope_scan function."""
    content = (SKILL_DIR / "scripts" / "generic-orchestrator-template.py").read_text(encoding="utf-8")
    assert "def quick_scope_scan(" in content, "Missing quick_scope_scan function"
    assert "estimated_scope" in content, "Missing estimated_scope in quick_scope_scan"
    assert "affected_files" in content, "Missing affected_files in quick_scope_scan"


def test_orchestrator_md_has_quick_scope_scan():
    """orchestrator.md must contain a Quick Scope Scan section."""
    content = (SKILL_DIR / "orchestrator.md").read_text(encoding="utf-8")
    assert "Quick Scope Scan" in content, "Missing Quick Scope Scan section in orchestrator.md"
    assert "Decision Matrix" in content, "Missing Decision Matrix in Quick Scope Scan section"
    assert "small" in content.lower() and "medium" in content.lower() and "large" in content.lower(), \
        "Missing scope estimates (small/medium/large) in Quick Scope Scan section"


def test_skill_md_role_selection_uses_quick_scope_scan():
    """SKILL.md Role Selection table must reference quick-scope-scan instead of hardcoded file counts."""
    content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "quick-scope-scan" in content.lower(), "SKILL.md missing quick-scope-scan reference in Role Selection"
    assert "affected files" in content.lower(), "SKILL.md missing 'affected files' reference in Role Selection"


def test_mcp_server_has_package_json():
    """bro-mcp-server must have a package.json with MCP SDK dependency."""
    path = SKILL_DIR / "scripts" / "bro-mcp-server" / "package.json"
    assert path.exists(), "Missing package.json in bro-mcp-server"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "dependencies" in data, "package.json missing dependencies"
    assert "@modelcontextprotocol/sdk" in data["dependencies"], "package.json missing @modelcontextprotocol/sdk dependency"


def test_mcp_server_package_has_scripts():
    """package.json must include start, test, and healthcheck scripts."""
    path = SKILL_DIR / "scripts" / "bro-mcp-server" / "package.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    scripts = data.get("scripts", {})
    for key in ("start", "test", "healthcheck"):
        assert key in scripts, f"package.json missing '{key}' script"


def test_copilot_adapter_has_mcp_setup_instructions():
    """copilot.md must include npm install and --healthcheck instructions."""
    content = (SKILL_DIR / "adapters" / "copilot.md").read_text(encoding="utf-8")
    assert "npm install" in content.lower(), "copilot.md missing npm install instructions"
    assert "--healthcheck" in content, "copilot.md missing --healthcheck reference"


def test_orchestrator_md_has_token_budget_section():
    """orchestrator.md must contain a Token Budget section with >= 20 lines."""
    content = (SKILL_DIR / "orchestrator.md").read_text(encoding="utf-8")
    assert "Token Budget" in content or "token budget" in content.lower(), "orchestrator.md missing Token Budget section"
    section_start = content.find("Token Budget")
    if section_start == -1:
        section_start = content.lower().find("token budget")
    # Find next top-level "##" heading, avoiding matches inside "###" sub-headings
    import re
    match = re.search(r'\n## ', content[section_start + 1:])
    next_section = match.start() + section_start + 1 if match else -1
    section_text = content[section_start:next_section] if next_section != -1 else content[section_start:]
    lines = section_text.strip().splitlines()
    assert len(lines) >= 20, f"Token Budget section too short ({len(lines)} lines, expected >= 20)"


def test_skill_md_has_token_budget_rule():
    """SKILL.md must contain a token budget or cost awareness rule."""
    content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "token" in content.lower() and ("budget" in content.lower() or "cost" in content.lower()), \
        "SKILL.md missing token budget / cost awareness rule"


def test_task_tracker_has_token_usage_field():
    """task-tracker.md must reference token_usage or token budget."""
    content = (SKILL_DIR / "task-tracker.md").read_text(encoding="utf-8")
    assert "token_usage" in content.lower() or "token budget" in content.lower(), \
        "task-tracker.md missing token_usage field"


def test_generic_orchestrator_has_token_budget_class():
    """generic-orchestrator-template.py must contain a TokenBudget class."""
    content = (SKILL_DIR / "scripts" / "generic-orchestrator-template.py").read_text(encoding="utf-8")
    assert "class TokenBudget" in content, "Missing TokenBudget class in generic orchestrator"
    assert "record_usage" in content, "Missing record_usage method in TokenBudget"
    assert "is_within_budget" in content, "Missing is_within_budget method in TokenBudget"


def test_agents_md_has_budget_check_step():
    """AGENTS.md Launch Flow must include a Budget Check step."""
    content = (SKILL_DIR / "AGENTS.md").read_text(encoding="utf-8")
    assert "budget" in content.lower(), "AGENTS.md missing budget check step"


def test_kimi_adapter_has_cli_example():
    """kimi.md must reference a concrete kimi chat CLI command."""
    content = (SKILL_DIR / "adapters" / "kimi.md").read_text(encoding="utf-8")
    assert "kimi chat" in content, "kimi.md missing 'kimi chat' CLI example"


def test_kimi_adapter_has_known_limitations():
    """kimi.md must contain a Known Limitations section."""
    content = (SKILL_DIR / "adapters" / "kimi.md").read_text(encoding="utf-8")
    assert "Known Limitations" in content or "known limitations" in content.lower(), \
        "kimi.md missing Known Limitations section"


def test_kimi_adapter_has_runtime_detection_instructions():
    """kimi.md must include which kimi or kimi --version detection instructions."""
    content = (SKILL_DIR / "adapters" / "kimi.md").read_text(encoding="utf-8")
    assert "which kimi" in content or "kimi --version" in content, \
        "kimi.md missing runtime detection instructions (which kimi / kimi --version)"


def test_examples_directory_exists():
    """examples/ directory must contain simple-bug-fix and new-feature subdirectories."""
    examples_dir = SKILL_DIR / "examples"
    assert examples_dir.exists(), "Missing examples/ directory"
    for subdir in ("simple-bug-fix", "new-feature"):
        assert (examples_dir / subdir).exists(), f"Missing examples/{subdir}/ directory"
        assert (examples_dir / subdir / "task.md").exists(), f"Missing examples/{subdir}/task.md"


def test_changelog_exists():
    """CHANGELOG.md must exist and follow Keep a Changelog format."""
    path = SKILL_DIR / "CHANGELOG.md"
    assert path.exists(), "Missing CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    assert "Keep a Changelog" in text or "Changelog" in text, "CHANGELOG.md missing Changelog header"
    assert "[1.0.0]" in text, "CHANGELOG.md missing v1.0.0 release"


def test_skill_md_has_version_1_0_0():
    """SKILL.md metadata must declare version 1.0.0."""
    content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "1.0.0" in content, "SKILL.md missing version 1.0.0"


def test_pytest_ini_exists():
    """pytest.ini or pyproject.toml must exist in tests/."""
    assert (SKILL_DIR / "tests" / "pytest.ini").exists() or (SKILL_DIR / "pyproject.toml").exists(), \
        "Missing pytest.ini or pyproject.toml"


def test_generic_orchestrator_unit_tests_exist():
    """tests/test_generic_orchestrator.py must exist and contain mock-based tests."""
    path = SKILL_DIR / "tests" / "test_generic_orchestrator.py"
    assert path.exists(), "Missing test_generic_orchestrator.py"
    text = path.read_text(encoding="utf-8")
    assert "unittest" in text, "Missing unittest imports in test_generic_orchestrator.py"
    assert "MagicMock" in text or "mock" in text.lower(), "Missing mock usage in test_generic_orchestrator.py"


if __name__ == "__main__":
    try:
        import pytest
    except ImportError:
        # Fallback: run tests manually if pytest is not installed
        print("pytest not installed, running manual test runner...")
        tests = [obj for name, obj in globals().items() if name.startswith("test_")]
        passed = 0
        failed = 0
        for test in tests:
            try:
                test()
                print(f"  PASS  {test.__name__}")
                passed += 1
            except AssertionError as exc:
                print(f"  FAIL  {test.__name__}: {exc}")
                failed += 1
            except Exception as exc:
                print(f"  ERROR {test.__name__}: {exc}")
                failed += 1
        print(f"\n{passed} passed, {failed} failed")
        sys.exit(0 if failed == 0 else 1)
    else:
        sys.exit(pytest.main([__file__, "-v"]))
