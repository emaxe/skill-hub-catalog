# Линтинг и форматирование

## ESLint

- Расширения: `.ts`, `.tsx`, `.js`, `.jsx`, `.vue`.
- Запуск из каталога `app/` приложения:

```bash
# Admin.UI
cd Admin.UI/app && npm run lint

# Company.UI
cd Company.UI/app && npm run lint

# Widget.UI
cd Widget.UI/app && npm run lint
```

## Prettier

Используется совместно с ESLint через `eslint-config-prettier`. При форматировании учитывать оба набора правил.

## TypeScript

- В TS-файлах — строгая типизация; интерфейсы предпочтительнее type-алиасов (расширяемость).
- В `.vue` — допускается `<script setup lang="ts">` или `<script setup>` (JS) — по соглашению модуля.
- Проверка TS через Quasar (`supportTS.tsCheckerConfig.eslint`).
- Избегать `enum`; использовать `const` объекты или maps.

## После изменений

Всегда проверять затронутые файлы через `read_lints`. Исправлять введённые ошибки; не трогать предсуществующие, если это не требуется задачей.

## Язык текстов

Все тексты в UI — на **русском языке**: лейблы, сообщения об ошибках, плейсхолдеры, подсказки, заголовки диалогов, кнопки.

```javascript
// Правильно
$q.notify({ color: 'negative', message: 'Не удалось сохранить QR-код' })
label="Внешний ID"
title="Ссылка на прохождение проверки"

// Неправильно
$q.notify({ color: 'negative', message: 'Failed to save QR code' })
```
