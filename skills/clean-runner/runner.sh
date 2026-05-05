#!/usr/bin/env bash
# clean-runner — запуск команд с фильтрацией мусорного вывода.
# Использование: bash runner.sh "command" [--profile NAME] [--tail N] [--head N]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FILTERS_DIR="$SCRIPT_DIR/filters"
CONFIG_FILE="$SCRIPT_DIR/config.json"

# ── Параметры по умолчанию ──

COMMAND=""
PROFILE=""
TAIL_LINES=0
HEAD_LINES=0
STRIP_ANSI=true
COLLAPSE_BLANK=true
SHOW_EXIT_CODE=true

# ── Чтение config.json (если есть jq) ──

if command -v jq &>/dev/null && [ -f "$CONFIG_FILE" ]; then
  TAIL_LINES=$(jq -r '.defaultTail // 0' "$CONFIG_FILE" 2>/dev/null || echo 0)
  PROFILE=$(jq -r '.defaultProfile // ""' "$CONFIG_FILE" 2>/dev/null || echo "")
  STRIP_ANSI=$(jq -r '.stripAnsi // true' "$CONFIG_FILE" 2>/dev/null || echo true)
  COLLAPSE_BLANK=$(jq -r '.collapseBlankLines // true' "$CONFIG_FILE" 2>/dev/null || echo true)
  SHOW_EXIT_CODE=$(jq -r '.exitCodeInOutput // true' "$CONFIG_FILE" 2>/dev/null || echo true)
fi

# ── Парсинг аргументов ──

if [ $# -lt 1 ]; then
  echo "Использование: bash runner.sh \"command\" [--profile NAME] [--tail N] [--head N]"
  echo "Профили: npm, build, pip, go"
  exit 1
fi

COMMAND="$1"
shift

while [ $# -gt 0 ]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --tail)    TAIL_LINES="$2"; shift 2 ;;
    --head)    HEAD_LINES="$2"; shift 2 ;;
    --no-ansi) STRIP_ANSI=false; shift ;;
    --no-collapse) COLLAPSE_BLANK=false; shift ;;
    *) echo "Неизвестный параметр: $1"; exit 1 ;;
  esac
done

# ── Сборка pipeline фильтрации ──

build_filter_pipeline() {
  local pipeline="cat"

  # 1. Убираем ANSI escape-коды
  if [ "$STRIP_ANSI" = "true" ]; then
    pipeline="$pipeline | sed 's/\x1b\[[0-9;]*[a-zA-Z]//g' | sed 's/\x1b\][^\x07]*\x07//g'"
  fi

  # 2. Убираем \r (carriage return от прогресс-баров)
  pipeline="$pipeline | tr -d '\r'"

  # 3. Общий фильтр (common.grep) — всегда
  if [ -f "$FILTERS_DIR/common.grep" ]; then
    pipeline="$pipeline | grep -vf '$FILTERS_DIR/common.grep'"
  fi

  # 4. Профильный фильтр
  if [ -n "$PROFILE" ] && [ -f "$FILTERS_DIR/${PROFILE}.grep" ]; then
    pipeline="$pipeline | grep -vf '$FILTERS_DIR/${PROFILE}.grep'"
  fi

  # 5. Схлопываем множественные пустые строки
  if [ "$COLLAPSE_BLANK" = "true" ]; then
    pipeline="$pipeline | cat -s"
  fi

  # 6. Обрезка head/tail
  if [ "$HEAD_LINES" -gt 0 ] 2>/dev/null; then
    pipeline="$pipeline | head -n $HEAD_LINES"
  fi
  if [ "$TAIL_LINES" -gt 0 ] 2>/dev/null; then
    pipeline="$pipeline | tail -n $TAIL_LINES"
  fi

  echo "$pipeline"
}

# ── Выполнение ──

TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT

# Запускаем команду, объединяем stdout и stderr
EXIT_CODE=0
eval "$COMMAND" > "$TMPFILE" 2>&1 || EXIT_CODE=$?

# Прогоняем через фильтры
PIPELINE=$(build_filter_pipeline)
eval "cat '$TMPFILE' | $PIPELINE" 2>/dev/null || cat "$TMPFILE"

# Код выхода
if [ "$SHOW_EXIT_CODE" = "true" ]; then
  if [ "$EXIT_CODE" -eq 0 ]; then
    echo ""
    echo "✓ Команда завершилась успешно (exit code: 0)"
  else
    echo ""
    echo "✗ Команда завершилась с ошибкой (exit code: $EXIT_CODE)"
  fi
fi

exit "$EXIT_CODE"
