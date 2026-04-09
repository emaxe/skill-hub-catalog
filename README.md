# Skill-Hub Catalog

Каталог расширений для [Skill-Hub](https://github.com/emaxe/skill-hub) — менеджера расширений для AI-ассистентов (Claude Code, Cursor, Copilot).

## Структура

```
skills/          — расширения-навыки (SKILL.md)
agents/          — расширения-агенты (AGENT.md)
commands/        — расширения-команды (COMMAND.md)
catalog.json     — автогенерируемый индекс всех расширений
schema/          — JSON-схемы для валидации frontmatter
scripts/         — скрипт генерации каталога
docs/            — гайды по созданию расширений
```

## Использование

Этот репозиторий используется CLI `@emaxe/skill-hub` как источник каталога расширений. CLI клонирует репозиторий в `~/.skill-hub/` и использует `catalog.json` для поиска и установки расширений.

```bash
npm install -g @emaxe/skill-hub
skill-hub search git
skill-hub install skill:git-commit
```

## Создание расширения

См. гайды в `docs/`:
- [SKILL-AUTHORING.md](docs/SKILL-AUTHORING.md)
- [AGENT-AUTHORING.md](docs/AGENT-AUTHORING.md)
- [COMMAND-AUTHORING.md](docs/COMMAND-AUTHORING.md)

Теги: [TAG-TAXONOMY.md](docs/TAG-TAXONOMY.md)

Расширения могут быть привязаны к конкретным проектам через поле `projects` в frontmatter. Подробнее: [SKILL-AUTHORING.md](docs/SKILL-AUTHORING.md#projects)

## Генерация каталога

```bash
bash scripts/generate-catalog.sh
```

## Лицензия

MIT
