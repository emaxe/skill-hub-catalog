#!/usr/bin/env python3
"""
Bro Generic Orchestrator — Functional Unit Tests
=================================================
Mock-based tests for the generic orchestrator template components:
- TaskTracker (JSON persistence, start/finish/rework, status)
- LLMClient (chat, error handling, token counting)
- BroOrchestrator (dispatch loop, pipeline execution, error recovery)
- load_skill (skills hub fallback via env var)
- quick_scope_scan (heuristic classification)

Run:
    cd .claude/skills/bro
    python3 -m pytest tests/test_generic_orchestrator.py -v
"""

import json
import os
import pathlib
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

# Ensure the script module is importable
SCRIPT_DIR = pathlib.Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

# Import the module under test (lazy openai import keeps tests lightweight)
import importlib.util
_spec = importlib.util.spec_from_file_location("generic_orchestrator_template", str(SCRIPT_DIR / "generic-orchestrator-template.py"))
bro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bro)
# Register in sys.modules so unittest.patch can target it by name
sys.modules["generic_orchestrator_template"] = bro


class TestTaskTracker(unittest.TestCase):
    """Unit tests for TaskTracker persistence and state management."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.patch_task_dir = patch.object(bro, "TASK_DIR", pathlib.Path(self.tmpdir.name) / "tasks")
        self.patch_task_dir.start()
        self.addCleanup(self.patch_task_dir.stop)

    def test_init_creates_tracker(self):
        t = bro.TaskTracker("task-001")
        self.assertTrue(t.tracker_path.exists())
        data = json.loads(t.tracker_path.read_text(encoding="utf-8"))
        self.assertEqual(data["task_id"], "task-001")
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["iterations"], 0)

    def test_start_role_increments_iterations(self):
        t = bro.TaskTracker("task-002")
        t.start_role("analyst")
        data = t.data
        self.assertEqual(data["current_role"], "analyst")
        self.assertEqual(data["iterations"], 1)

    def test_finish_role_records_result(self):
        t = bro.TaskTracker("task-003")
        t.start_role("developer")
        t.finish_role("developer", "result text", verdict="APPROVE")
        data = t.data
        self.assertIn("developer", data["completed_roles"])
        self.assertEqual(data["results"]["developer"], "result text")
        self.assertEqual(data["verdicts"]["developer"], "APPROVE")
        self.assertIsNone(data["current_role"])

    def test_record_rework(self):
        t = bro.TaskTracker("task-004")
        t.record_rework("developer")
        t.record_rework("developer")
        self.assertEqual(t.data["rework_count"]["developer"], 2)

    def test_set_status(self):
        t = bro.TaskTracker("task-005")
        t.set_status("blocked")
        self.assertEqual(t.data["status"], "blocked")

    def test_tracker_persistence(self):
        t = bro.TaskTracker("task-006")
        t.start_role("tester")
        # Create a fresh tracker pointing at the same path
        t2 = bro.TaskTracker("task-006")
        self.assertEqual(t2.data["current_role"], "tester")
        self.assertEqual(t2.data["iterations"], 1)

    def test_tracker_has_token_usage_field(self):
        t = bro.TaskTracker("task-007")
        data = t.data
        # token_usage is a dict that should be present in the tracker structure
        self.assertIn("token_usage", data)
        self.assertIsInstance(data["token_usage"], dict)


class TestLLMClient(unittest.TestCase):
    """Unit tests for LLMClient with mocked openai."""

    def _make_client(self, mock_openai_cls):
        patcher = patch("generic_orchestrator_template._get_openai", return_value=mock_openai_cls)
        patcher.start()
        self.addCleanup(patcher.stop)
        return bro.LLMClient(model="gpt-test", api_key="dummy-key", base_url="http://test/v1")

    def test_chat_success(self):
        mock_openai = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "Hello, world!"
        mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_resp
        client = self._make_client(mock_openai)
        result = client.chat("system prompt", "user prompt")
        self.assertEqual(result, "Hello, world!")

    def test_chat_error_returns_error_prefix(self):
        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value.chat.completions.create.side_effect = ConnectionError("boom")
        client = self._make_client(mock_openai)
        result = client.chat("system prompt", "user prompt")
        self.assertTrue(result.startswith("ERROR:"))
        self.assertIn("ConnectionError", result)

    def test_chat_empty_content(self):
        mock_openai = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = None
        mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_resp
        client = self._make_client(mock_openai)
        result = client.chat("system prompt", "user prompt")
        self.assertEqual(result, "")


class TestBroOrchestrator(unittest.TestCase):
    """Unit tests for the BroOrchestrator dispatch loop."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.patch_task_dir = patch.object(bro, "TASK_DIR", pathlib.Path(self.tmpdir.name) / "tasks")
        self.patch_task_dir.start()
        self.addCleanup(self.patch_task_dir.stop)
        # Suppress role file loading by pointing BRO_SKILL_DIR to a temp dir with fake roles
        self.fake_skill_dir = pathlib.Path(self.tmpdir.name) / "skills"
        self.fake_skill_dir.mkdir()
        for role in ("analyst", "developer", "tester", "architect"):
            (self.fake_skill_dir / f"{role}.md").write_text(f"# {role}\n", encoding="utf-8")
        self.patch_skill_dir = patch.object(bro, "BRO_SKILL_DIR", self.fake_skill_dir)
        self.patch_skill_dir.start()
        self.addCleanup(self.patch_skill_dir.stop)

    def _make_orchestrator(self, llm_mock=None, task="test task", skills=None):
        tracker = bro.TaskTracker("task-orch-001")
        llm = llm_mock or bro.LLMClient.__new__(bro.LLMClient)
        if llm_mock is None:
            llm.chat = MagicMock(return_value="OK result")
        return bro.BroOrchestrator(llm, tracker, task, skills=skills or [])

    def test_run_pipeline_completes_all_roles(self):
        llm = bro.LLMClient.__new__(bro.LLMClient)
        llm.chat = MagicMock(return_value="success")
        orch = self._make_orchestrator(llm_mock=llm)
        results = orch.run_pipeline(["analyst", "developer"])
        self.assertEqual(results["analyst"], "success")
        self.assertEqual(results["developer"], "success")
        self.assertEqual(orch.tracker.data["status"], "completed")
        self.assertEqual(orch.tracker.data["iterations"], 2)

    def test_dispatch_role_retries_on_error(self):
        llm = bro.LLMClient.__new__(bro.LLMClient)
        llm.chat = MagicMock(side_effect=["ERROR: timeout", "recovered"])
        orch = self._make_orchestrator(llm_mock=llm)
        result = orch.dispatch_role("developer")
        self.assertEqual(result, "recovered")
        self.assertEqual(llm.chat.call_count, 2)
        failures = orch.tracker.data.get("failures", [])
        self.assertEqual(len(failures), 0)  # recovered on retry

    def test_dispatch_role_skips_after_retry_exhaustion(self):
        llm = bro.LLMClient.__new__(bro.LLMClient)
        llm.chat = MagicMock(return_value="ERROR: timeout")
        orch = self._make_orchestrator(llm_mock=llm)
        result = orch.dispatch_role("developer")
        self.assertTrue(result.startswith("[SKIPPED"))
        failures = orch.tracker.data.get("failures", [])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["role"], "developer")

    def test_dispatch_role_aborts_on_critical_role_failure(self):
        llm = bro.LLMClient.__new__(bro.LLMClient)
        llm.chat = MagicMock(return_value="ERROR: timeout")
        orch = self._make_orchestrator(llm_mock=llm)
        with self.assertRaises(RuntimeError):
            orch.dispatch_role("architect")

    def test_max_iterations_guard(self):
        llm = bro.LLMClient.__new__(bro.LLMClient)
        llm.chat = MagicMock(return_value="ok")
        orch = self._make_orchestrator(llm_mock=llm)
        # Manually bump iterations to the limit
        orch.tracker.start_role("analyst")
        orch.tracker._data["iterations"] = 10
        orch.tracker._save()
        with self.assertRaises(RuntimeError) as ctx:
            orch.run_pipeline(["developer"])
        self.assertIn("MAX_ITERATIONS", str(ctx.exception))

    def test_build_system_prompt_inlines_skills(self):
        # Create a fake skill file
        skills_dir = self.fake_skill_dir.parent / "skills_extra"
        skills_dir.mkdir()
        (skills_dir / "my-skill.md").write_text("# My Skill\nDo X before Y.", encoding="utf-8")
        with patch.object(bro, "_DEFAULT_SKILL_SEARCH_PATHS", [skills_dir]):
            llm = bro.LLMClient.__new__(bro.LLMClient)
            llm.chat = MagicMock(return_value="ok")
            orch = self._make_orchestrator(llm_mock=llm, skills=["my-skill"])
            system = orch._build_system_prompt("analyst")
            self.assertIn("Do X before Y", system)


class TestQuickScopeScan(unittest.TestCase):
    """Unit tests for quick_scope_scan heuristic."""

    def test_small_scope(self):
        result = bro.quick_scope_scan("Fix typo in readme")
        self.assertEqual(result["estimated_scope"], "small")

    def test_large_scope(self):
        result = bro.quick_scope_scan("Design new microservice architecture for payments")
        self.assertEqual(result["estimated_scope"], "large")

    def test_medium_default(self):
        result = bro.quick_scope_scan("Do some work")
        self.assertEqual(result["estimated_scope"], "medium")

    def test_returns_keywords(self):
        result = bro.quick_scope_scan("Add new endpoint for user profiles")
        self.assertIsInstance(result["keywords"], list)
        self.assertTrue(len(result["keywords"]) > 0)

    def test_returns_affected_files_placeholder(self):
        result = bro.quick_scope_scan("anything")
        self.assertIsInstance(result["affected_files"], list)


class TestLoadSkill(unittest.TestCase):
    """Unit tests for load_skill with env-based search paths."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def test_load_skill_from_env_path(self):
        skill_dir = pathlib.Path(self.tmpdir.name) / "skills_dir"
        skill_dir.mkdir()
        (skill_dir / "my-skill.md").write_text("# My Skill", encoding="utf-8")
        with patch.dict(os.environ, {"SKILLS_SEARCH_PATHS": str(skill_dir)}):
            result = bro.load_skill("my-skill")
            self.assertEqual(result, "# My Skill")

    def test_load_skill_not_found(self):
        with patch.dict(os.environ, {"SKILLS_SEARCH_PATHS": self.tmpdir.name}):
            result = bro.load_skill("nonexistent")
            self.assertIsNone(result)


class TestTokenBudget(unittest.TestCase):
    """Unit tests for the TokenBudget helper class."""

    def test_init_with_defaults(self):
        budget = bro.TokenBudget(total_limit=100000)
        self.assertEqual(budget.total_limit, 100000)
        self.assertEqual(budget.spent, 0)
        self.assertTrue(budget.is_within_budget())

    def test_record_usage(self):
        budget = bro.TokenBudget(total_limit=100000)
        budget.record_usage(5000)
        self.assertEqual(budget.spent, 5000)
        self.assertTrue(budget.is_within_budget())

    def test_exceeds_budget(self):
        budget = bro.TokenBudget(total_limit=1000)
        budget.record_usage(1500)
        self.assertFalse(budget.is_within_budget())

    def test_remaining(self):
        budget = bro.TokenBudget(total_limit=10000)
        budget.record_usage(3000)
        self.assertEqual(budget.remaining(), 7000)

    def test_estimate_prompt_tokens(self):
        budget = bro.TokenBudget(total_limit=10000)
        # Rough estimate: ~1 token per 4 chars
        est = budget.estimate_prompt_tokens("Hello world" * 40)  # ~440 chars
        self.assertGreater(est, 0)
        self.assertLess(est, 500)

    def test_warn_threshold(self):
        budget = bro.TokenBudget(total_limit=10000, warn_threshold=0.8)
        budget.record_usage(8500)
        self.assertTrue(budget.is_over_threshold())
        budget.record_usage(-3500)  # back under
        self.assertFalse(budget.is_over_threshold())


if __name__ == "__main__":
    unittest.main(verbosity=2)
