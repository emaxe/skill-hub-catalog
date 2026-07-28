---
name: code-review
description: "Use when the user invokes /code-review to perform a structured code review of current branch changes. Analyzes logic, security, performance, architecture and testing."
tags: [workflow, safety]
author: maksimklisin
version: "1.0.0"
scope: global
platforms: [claude-code, cursor, copilot]
dependencies: []
---

# /code-review

## Overview

Проводит структурированное код-ревью изменений в текущей ветке. Анализирует логику, безопасность, производительность, архитектуру и тестирование.

## Process

1. **Сбор контекста:**
   ```bash
   git diff --stat
   git diff
   ```

2. **Анализ каждого изменённого файла на предмет:**
   - **Баги и логические ошибки** — неправильные условия, edge cases, null reference
   - **Безопасность** — SQL injection, XSS, утечка секретов, OWASP Top 10
   - **Производительность** — N+1 запросы, утечки памяти, неэффективные алгоритмы
   - **Архитектура** — нарушение SOLID, DRY, KISS, связанность компонентов
   - **Тестирование** — отсутствие тестов для критической логики

3. **Формирование отчёта:**

```markdown
## Code Review Report

### Summary
- Files changed: N | Lines: +X/-Y
- **Verdict: Approve / Request Changes / Needs Discussion**

### Critical Issues (must fix)
- `file.ts:42` — [Bug] Описание проблемы

### Warnings (should fix)
- `file.ts:15` — [Performance] Описание

### Suggestions (consider fixing)
- `file.ts:8` — [Architecture] Описание

### Positive Notes
- Что сделано хорошо
```

## Arguments

- `--scope` — область ревью: `branch` (default), `staged`, `commit`
- `--focus` — фокус: `all` (default), `security`, `performance`, `architecture`

## Rules

- Приоритет: баги > безопасность > производительность > архитектура
- Не предлагай стилистические изменения
- Указывай файл и номер строки для каждого замечания
- Отмечай позитивные моменты
- Если изменений слишком много (>20 файлов), предложи разбить ревью
