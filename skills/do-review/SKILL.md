---
name: do-review
description: Code review orchestrator. Invoke when asked to review, check, or validate code changes or AI convention files. | Оркестратор ревью. Вызывать когда просят проверить или сделать ревью изменений кода или AI-конфигурации.
tags: [review]
author: maksimklisin
version: "1.0.0"
scope: global
platforms: [claude-code, cursor, copilot]
dependencies: []
language: any
---

# do-review

Оркестратор ревью. Определяет затронутые области и запускает соответствующие валидации.

## Шаг 1: Определи область ревью

- Указана директория или файлы -- область = они
- Указана ветка -- область = `git diff master...<branch> --name-only`
- Ничего не указано -- область = `git diff --name-only HEAD`
- Если пусто -- спроси: "Что нужно проверить? Укажи файлы, директорию или ветку."

## Шаг 2: Запусти валидации

- Выполни [validate-conventions.md](validate-conventions.md) -- всегда
- Добавь domain-specific валидации для проекта (пример: `validate-backend.md`, `validate-ui.md`)

## Шаг 3: Сформируй сводный отчёт

Сведи результаты всех валидаций. Группировка по файлам.
Для каждого нарушения: файл, описание отклонения, ссылка на правило.

Если нарушений нет -- "Нарушений не найдено".
