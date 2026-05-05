---
name: clean-runner
description: Запуск консольных команд с фильтрацией мусорного вывода. Возвращает только полезную информацию.
version: 1.0.0
author: emaxe
tags: [shell, output, filter, runner]
---

# Clean Runner — умный запуск команд

Этот скилл помогает запускать консольные команды и получать **чистый, полезный вывод** без мусора: прогресс-баров, ANSI-кодов, спам-предупреждений, дублирующихся пустых строк и т.д.

## Когда использовать

Используй `clean-runner` когда:
- Запускаешь `npm install`, `npm run build`, `pip install` и другие шумные команды
- Нужно получить только ошибки и ключевые строки из длинного вывода
- Вывод содержит прогресс-бары, спиннеры, ANSI escape-коды
- Нужно ограничить объём вывода для экономии контекста

## Как использовать

### Вариант 1 — через runner.sh (рекомендуется)

Скрипт `runner.sh` из этой папки принимает команду и параметры фильтрации:

```bash
# Базовый запуск — убирает ANSI-коды, прогресс-бары, лишние пустые строки
bash .claude/skills/clean-runner/runner.sh "npm install"

# С фильтром по профилю (npm, build, pip, go)
bash .claude/skills/clean-runner/runner.sh "npm run build" --profile npm

# Только последние N строк (хвост)
bash .claude/skills/clean-runner/runner.sh "pytest -v" --tail 50

# Только первые N строк (голова)
bash .claude/skills/clean-runner/runner.sh "find . -name '*.ts'" --head 30

# Комбинация: профиль + хвост
bash .claude/skills/clean-runner/runner.sh "npm run build" --profile build --tail 80
```

### Вариант 2 — ручная пост-обработка

Если нужен нестандартный фильтр, используй файлы из `filters/`:

```bash
# Запустить команду и прогнать через grep -vf (инвертированный фильтр)
npm run build 2>&1 | grep -vf .claude/skills/clean-runner/filters/npm.grep | head -80
```

## Профили фильтрации

| Профиль | Файл | Что убирает |
|---------|------|-------------|
| `common` | `filters/common.grep` | ANSI-коды, прогресс-бары, пустые строки, спиннеры |
| `npm` | `filters/npm.grep` | npm WARN, timing, audit, funding, idealTree |
| `build` | `filters/build.grep` | webpack progress, esbuild/vite шум, sourcemap info |
| `pip` | `filters/pip.grep` | pip download progress, cache info, wheel building |
| `go` | `filters/go.grep` | go mod download, checksum noise |

Профиль `common` применяется **всегда** в дополнение к выбранному.

## Примеры

### npm install — было vs стало

**До (250+ строк):**
```
npm warn deprecated inflight@1.0.6: This module is not supported...
npm warn deprecated rimraf@3.0.2: Rimraf versions prior to v4...
npm warn deprecated glob@7.2.3: Glob versions prior to v9...

added 847 packages, and audited 848 packages in 32s
147 packages are looking for funding
  run `npm fund` for details
found 0 vulnerabilities
```

**После clean-runner (3 строки):**
```
added 847 packages, and audited 848 packages in 32s
found 0 vulnerabilities
```

### pytest — было vs стало

**До (100+ строк с прогресс-точками):**
```
tests/test_auth.py ........ [ 12%]
tests/test_api.py ..................... [ 45%]
...
```

**После с --tail 15 (только итог + failed):**
```
FAILED tests/test_api.py::test_create_user - AssertionError
= 1 failed, 89 passed, 2 skipped in 4.32s =
```

## Настройка

Файл `config.json` содержит настройки по умолчанию. Можно менять:
- `defaultTail` — лимит строк по умолчанию (0 = без лимита)
- `defaultProfile` — профиль по умолчанию (`""` = только common)
- `stripAnsi` — убирать ANSI-коды (true)
- `collapseBlankLines` — схлопывать множественные пустые строки (true)
- `exitCodeInOutput` — добавлять код выхода в вывод (true)
