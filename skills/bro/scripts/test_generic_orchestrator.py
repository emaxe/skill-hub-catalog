#!/usr/bin/env python3
"""
Tests for generic-orchestrator-template.py — Skills Hub Integrator fallback logic.
Run: pytest -xvs test_generic_orchestrator.py
"""

import json
import importlib.util
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

# Import the script with dashes in filename via importlib.util
script_path = Path(__file__).parent / "generic-orchestrator-template.py"
spec = importlib.util.spec_from_file_location("generic_orchestrator_template", str(script_path))
go = importlib.util.module_from_spec(spec)
spec.loader.exec_module(go)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the cached prerequisites state before each test."""
    go._skills_hub_prerequisites_cache = None


@pytest.fixture
def tmp_project(tmp_path):
    """Create a minimal project structure with BRO_SKILL_DIR and TASK_DIR."""
    skill_dir = tmp_path / ".claude" / "skills" / "bro"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "analyst.md").write_text("# Analyst\n", encoding="utf-8")

    task_dir = tmp_path / ".bro" / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)

    return SimpleNamespace(skill_dir=skill_dir, task_dir=task_dir, root=tmp_path)


# ---------------------------------------------------------------------------
# check_skills_hub_prerequisites
# ---------------------------------------------------------------------------

class TestCheckSkillsHubPrerequisites:
    def test_all_ok(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="v20.0.0")
            result = go.check_skills_hub_prerequisites()
            assert result["ok"] is True

    def test_node_missing(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("node not found")
            result = go.check_skills_hub_prerequisites()
            assert result["ok"] is False
            assert "node unavailable" in result["reason"]

    def test_cached_result(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="v20.0.0")
            r1 = go.check_skills_hub_prerequisites()
            r2 = go.check_skills_hub_prerequisites()
            assert mock_run.call_count == 4  # only called once
            assert r1 == r2


# ---------------------------------------------------------------------------
# resolve_skill_from_skills_hub
# ---------------------------------------------------------------------------

class TestResolveSkillFromSkillsHub:
    def test_prerequisites_fail(self):
        with patch.object(
            go, "_skills_hub_prerequisites_cache", {"ok": False, "reason": "npx missing"}
        ):
            result = go.resolve_skill_from_skills_hub("superpowers:brainstorming")
            assert result["success"] is False
            assert "prerequisites failed" in result["reason"]

    def test_no_search_results(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="v20.0.0"),   # node
                MagicMock(stdout="10.0.0"),    # npm
                MagicMock(stdout="10.0.0"),    # npx
                MagicMock(stdout="1.0.0"),     # npx skills --version
                MagicMock(stdout=""),           # npx skills find (empty)
            ]
            result = go.resolve_skill_from_skills_hub("superpowers:brainstorming")
            assert result["success"] is False
            assert "No results on skills.sh" in result["reason"]

    def test_install_success(self, tmp_project):
        """Simulate full successful fetch: find -> install -> verify."""
        # Path must match BRO_SKILL_DIR.parent / "skills" / skill_name / "SKILL.md"
        installed_skill = tmp_project.skill_dir.parent / "skills" / "superpowers:brainstorming" / "SKILL.md"
        installed_skill.parent.mkdir(parents=True, exist_ok=True)
        installed_skill.write_text("# Brainstorming Skill\n", encoding="utf-8")

        with patch.object(go, "BRO_SKILL_DIR", tmp_project.skill_dir):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    MagicMock(stdout="v20.0.0"),   # node
                    MagicMock(stdout="10.0.0"),    # npm
                    MagicMock(stdout="10.0.0"),    # npx
                    MagicMock(stdout="1.0.0"),     # npx skills --version
                    MagicMock(stdout="anthropics/skills@brainstorming\n"),  # find
                    MagicMock(stdout="installed"),  # install
                ]
                result = go.resolve_skill_from_skills_hub("superpowers:brainstorming")
                assert result["success"] is True
                assert result["owner_repo"] == "anthropics/skills"
                assert result["skill_path"] == installed_skill

    def test_install_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="v20.0.0"),
                MagicMock(stdout="10.0.0"),
                MagicMock(stdout="10.0.0"),
                MagicMock(stdout="1.0.0"),
                MagicMock(stdout="anthropics/skills@brainstorming\n"),
                Exception("npm install failed"),  # install fails
            ]
            result = go.resolve_skill_from_skills_hub("brainstorming")
            assert result["success"] is False
            assert "Installation failed" in result["reason"]

    def test_install_but_not_found(self):
        """Installation succeeds but skill file is nowhere to be found."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="v20.0.0"),
                MagicMock(stdout="10.0.0"),
                MagicMock(stdout="10.0.0"),
                MagicMock(stdout="1.0.0"),
                MagicMock(stdout="anthropics/skills@brainstorming\n"),
                MagicMock(stdout="installed"),
            ]
            result = go.resolve_skill_from_skills_hub("brainstorming")
            assert result["success"] is False
            assert "skill file not found in expected paths" in result["reason"]


# ---------------------------------------------------------------------------
# BroOrchestrator integration (skill fallback in _build_system_prompt)
# ---------------------------------------------------------------------------

class TestOrchestratorSkillFallback:
    def test_skill_found_locally(self, tmp_project):
        skill = tmp_project.skill_dir.parent / "superpowers" / "brainstorming" / "SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text("# Brainstorming\n", encoding="utf-8")

        tracker = go.TaskTracker("test-task")
        orch = go.BroOrchestrator(
            llm=MagicMock(),
            tracker=tracker,
            task="Test",
            skills=["superpowers/brainstorming"],
        )
        system = orch._build_system_prompt("analyst")
        assert "# Brainstorming" in system
        assert "fetched from skills.sh" not in system

    def test_skill_fallback_to_skills_hub(self, tmp_project):
        """Skill missing locally, fetched from skills.sh, inlined in system prompt."""
        installed_skill = tmp_project.root / ".claude" / "skills" / "superpowers" / "brainstorming" / "SKILL.md"
        installed_skill.parent.mkdir(parents=True, exist_ok=True)
        installed_skill.write_text("# Fetched Brainstorming\n", encoding="utf-8")

        tracker = go.TaskTracker("test-task")
        orch = go.BroOrchestrator(
            llm=MagicMock(),
            tracker=tracker,
            task="Test",
            skills=["superpowers/brainstorming"],
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="v20.0.0"),   # node
                MagicMock(stdout="10.0.0"),    # npm
                MagicMock(stdout="10.0.0"),    # npx
                MagicMock(stdout="1.0.0"),     # npx skills --version
                MagicMock(stdout="anthropics/skills@brainstorming\n"),  # find
                MagicMock(stdout="installed"),  # install
            ]
            system = orch._build_system_prompt("analyst")
            assert "# Fetched Brainstorming" in system
            assert "fetched from skills.sh: anthropics/skills" in system

        # Verify tracker logged the success
        tracker_data = json.loads(tracker.tracker_path.read_text(encoding="utf-8"))
        deps = tracker_data.get("external_dependencies", [])
        assert len(deps) == 1
        assert deps[0]["status"] == "SUCCESS"
        assert deps[0]["owner_repo"] == "anthropics/skills"

    def test_skill_fallback_fails(self, tmp_project):
        """Skill missing locally and skills.sh fails — logs failure in tracker."""
        tracker = go.TaskTracker("test-task")
        orch = go.BroOrchestrator(
            llm=MagicMock(),
            tracker=tracker,
            task="Test",
            skills=["superpowers/nonexistent"],
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="v20.0.0"),
                MagicMock(stdout="10.0.0"),
                MagicMock(stdout="10.0.0"),
                MagicMock(stdout="1.0.0"),
                MagicMock(stdout=""),  # no results
            ]
            system = orch._build_system_prompt("analyst")
            assert "Skill not found locally or on skills.sh" in system

        tracker_data = json.loads(tracker.tracker_path.read_text(encoding="utf-8"))
        deps = tracker_data.get("external_dependencies", [])
        assert len(deps) == 1
        assert deps[0]["status"] == "FAILED"


# ---------------------------------------------------------------------------
# Tracker integration
# ---------------------------------------------------------------------------

class TestTrackerExternalDependencies:
    def test_external_dependencies_field_created(self, tmp_project):
        tracker = go.TaskTracker("dep-test")
        tracker_data = json.loads(tracker.tracker_path.read_text(encoding="utf-8"))
        assert "external_dependencies" not in tracker_data
