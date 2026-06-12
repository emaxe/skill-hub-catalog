# Changelog

All notable changes to the `bro` multi-agent coding system skill.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.0.0] - 2026-06-11

### Added
- Initial release of the `bro` multi-agent coding system.
- Support for five runtime clients: **Claude Code**, **Codex**, **Kimi Code**, **GitHub Copilot**, and **Generic** (OpenAI-compatible).
- Client-specific adapters in `adapters/` with runtime detection, execution strategies, launch methods, and failure handling.
- Role-based pipeline: Analyst → Architect → Reviewer → Developer → Code Reviewer → Tester.
- `SKILL.md` orchestrator instructions with multi-client runtime support, skill integration, and workflow phases.
- `orchestrator.md` reference role with guardrails, error recovery, quick scope scan, and token budget guidance.
- `AGENTS.md` agent configuration reference with model tiers, launch flow, and failure escalation matrix.
- `task-tracker.md` compact file-based tracker template for cross-client state persistence.
- `generic-orchestrator-template.py` reference Python implementation with `TaskTracker`, `LLMClient`, `BroOrchestrator`, and external skill resolution.
- `scripts/bro-mcp-server/` MCP server for Copilot with `bro_dispatch`, `bro_report_result`, and `bro_get_status` tools.
- `MODELS.md` tier-to-real-model reference table (Smart / Base / Fast).
- `examples/` with `simple-bug-fix` and `new-feature` sample pipelines.
- Structural and functional tests in `tests/`.
