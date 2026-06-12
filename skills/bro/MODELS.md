# Model Reference

Tier-лейблы — абстракции. Подставьте актуальные модели вашего провайдера.

| Tier | Description | Recommended Models | Fallback | Notes |
|---|---|---|---|---|
| **Smart** | Maximum reasoning, planning, architecture, complex analysis | `claude-3-opus-20240229`, `gpt-4o`, `gemini-2.5-pro-preview-03-25`, `deepseek-reasoner`, `kimi-k1.5` | Base tier | Use for Architecture, Review, high-stakes analysis |
| **Base** | Balanced capability and speed for coding, review, testing | `claude-3-5-sonnet-20241022`, `gpt-4o-mini`, `gemini-2.0-flash`, `deepseek-chat`, `qwen2.5-72b-instruct` | Fast tier | Default for Developer, Code Reviewer, Tester |
| **Fast / Light** | Quick, low-cost tasks: simple edits, formatting, lightweight checks | `claude-3-5-haiku-20241022`, `gpt-4o-mini`, `qwen2.5-coder-32b-instruct`, `deepseek-chat` (small) | Base tier | Use for trivial edits, linting, comment fixes |

> **Fallback rule**: If the model required for a role is not available in the runtime, use the **Base** tier instead. Never leave a role without an assigned model.
