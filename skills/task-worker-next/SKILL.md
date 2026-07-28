---
name: task-worker-next
description: "Slash-command worker that auto-selects the next available task and executes it. Invoke via /task-worker-next in a dedicated chat. Finds the first pending task with dependencies met, then runs it exactly like task-worker [ID]. Triggers: task-worker-next, next task, run next task. | Воркер с автовыбором следующей доступной задачи. Вызывать через /task-worker-next в отдельном чате."
tags: [workflow]
author: maksimklisin
version: "1.0.0"
scope: global
platforms: [claude-code, cursor, copilot]
dependencies: [task-approach, task-worker]
language: any
---

# Task Worker Next

Формат и конвенции: прочитай скилл `task-approach` первым.

Ты -- агент-воркер. Найди следующую доступную задачу и выполни её.

## Шаг 1: Найди каталог задач

Используй glob с паттерном `**/.agents/tasks/catalog.md` -- `**` обязателен.
Если каталогов несколько -- выбери тот, в котором есть доступные задачи.
Если ни одного не найдено -- сообщи "Каталог задач не найден" и остановись.

## Шаг 2: Найди следующую доступную задачу

Всегда читай catalog.md свежим -- не полагайся на кэшированную версию.
Найди первую строку (наименьший номер) где:

- Статус = строго `pending`
- Зависимости = `--`, или все перечисленные задачи имеют статус `done`

Если такой задачи нет -- сообщи "Нет доступных задач" и перечисли
заблокированные с причинами. Остановись.

## Шаг 3: Выполни

У тебя есть ID задачи. Продолжай по шагам из `task-worker`:
- Перечитай catalog.md, возьми задачу установив `in-progress` (Шаг 3 task-worker)
- Выполни задачу (Шаг 4 task-worker)
- Перечитай catalog.md, отметь `done` (Шаг 5 task-worker)
