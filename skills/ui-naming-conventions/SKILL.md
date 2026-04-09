---
name: ui-naming-conventions
description: "Use when creating or renaming Vue components, files, stores, constants, or variables in UI projects. Covers PascalCase components, store naming (use*Store/use*Repo), constant objects (_CONST/_sCONST), and variable prefixes."
tags: [ui, vue]
author: maksimklisin
version: "1.0.0"
scope: global
platforms: [claude-code, cursor, copilot]
dependencies: []
language: typescript
---

# Именование в UI-проектах

## Компоненты Vue

- **PascalCase** для имён компонентов в коде и шаблонах.
- **Суффикс по роли:**

| Суффикс | Назначение | Пример |
|---------|------------|--------|
| `*Component.vue` | Корневой компонент домена | `companiesComponent.vue` |
| `*Block.vue` | Блок UI (таблица, фильтр, секция) | `companiesTable.vue`, `memberDetailsInfoBlock.vue` |
| `*Dialog.vue` | Диалог | `companyAddDialog.vue`, `memberAddDialog.vue` |
| `*Page.vue` | Страница | `CompaniesPage.vue` |

- **Shared.UI:** общие компоненты — префикс `x-` (`xForm`, `xPageBlock`, `xDialog`); ячейки — `Cell*` (`cellKycStatus.vue`, `cellDateTime.vue`, `cellDefault.vue`).

## Файлы

- JS/TS файлы: **camelCase** (`configStore.ts`, `repoHelper.js`).
- Vue файлы: **camelCase** для блоков и диалогов (`memberAddDialog.vue`), **PascalCase** для страниц (`CompaniesPage.vue`).
- Следовать существующему соглашению в папке.

## Сторы и репозитории

| Что | Конвенция | Пример |
|-----|-----------|--------|
| Pinia-стор | `use*Store` | `useCompaniesStore`, `useAuthStore` |
| Репозиторий (внутренний) | `use*Repo` | `useCompaniesRepo` |
| Имя в defineStore | PascalCase, домен | `defineStore('Companies', ...)` |

В компонентах — только `use*Store`, не обращаться к `use*Repo` напрямую.

## Константы

| Объект | Источник | Пример |
|--------|----------|--------|
| `_CONST` | Приложение (`constants/constants.ts`) | `_CONST.route.companies`, `_CONST.permissions.Companies.Manage` |
| `_sCONST` | Shared.UI (`sharedConst`) | `_sCONST.attrs.field` |

## Переменные в компонентах

- Приватные computed / ref, используемые только в шаблоне, именовать с префиксом `_`: `_model`, `_loading`, `_env`, `_hasManagePermission`.
- Булевые переменные — с глаголом: `isLoading`, `hasError`, `_canEdit`, `_isStep2Error`.
- Обработчики событий: `on*Click`, `on*Change`, `on*Done` (`onSaveClick`, `onDialogHide`).
- Функции сброса: `clear*` (`clearWidgetLink`, `clearForm`).
