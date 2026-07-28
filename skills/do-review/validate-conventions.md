Validate AI agent configuration against project conventions

Context: область передаётся из do-review. Проверяй файлы конфигурации AI в этой области.
Если область не содержит файлов `.agents/**`, `.github/instructions/**`, `.cursor/rules/**`, `.claude/**`, `AGENTS.md` --
сообщи "Конфигурация AI не затронута" и пропусти валидацию.

Steps:

1. Read `.agents/skills/agents-conventions/SKILL.md` -- это источник правил конвенции
2. Для каждого релевантного файла в области -- проверь соответствие прочитанным правилам
3. Зафиксируй нарушения: файл, строка (если применимо), описание отклонения, ссылка на правило
