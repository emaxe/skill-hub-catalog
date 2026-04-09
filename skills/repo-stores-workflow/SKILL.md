---
name: repo-stores-workflow
description: "Use when creating or modifying Pinia repository stores (stores/repo) in Vue UI apps. Covers naming, adapters, repoHelper methods, query patterns, and project conventions for Admin.UI, Company.UI, Widget.UI."
tags: [ui, vue, architecture]
author: maksimklisin
version: "1.0.0"
scope: global
platforms: [claude-code, cursor, copilot]
dependencies: [store-repo-api, ui-code-style]
projects: [kyc]
language: typescript
---

# Workflow сторов репозиториев (stores/repo)

Workflow и проектные конвенции для работы со сторами в `Admin.UI`, `Company.UI`, `Widget.UI`. Детали структуры и API — см. скилл **store-repo-api**.

## Когда применять

- Создание нового стора для домена
- Добавление методов или полей в существующий стор
- Редактирование структуры стора, адаптеров, экспортов

## Выбор приложения для стора

| Приложение | Назначение |
|------------|------------|
| Admin.UI | Сторы для админ-интерфейса (Applicants, Companies, entityChangeSet, admins, userRole, identifications) |
| Company.UI | Сторы для интерфейса компании (Applicants как members, identifications, contentSettings, userRole) |
| Widget.UI | Сторы для виджета (applicantIdentity и т.д.) |

Один и тот же контроллер API может использоваться в разных приложениях с разным набором методов.

## Общие подходы

### 1. Именование и расположение

- Файл: `app/src/stores/repo/<домен>.js` (camelCase)
- Pinia store: PascalCase (`'Applicants'`, `'Companies'`), исключения: `'auth'`, `'settings'`
- Контроллер в getPath: совпадает с API — PascalCase (`'Applicants'`), camelCase (`'Companies'`) или kebab-case (`'user-roles'`)
- Методы getPath: как на бэкенде — `getAll`, `GetAll`, `AddApplicant`, `get-all-permissions`

### 2. Адаптеры

| Адаптер | Использование |
|---------|---------------|
| useCollectionAdapter | Списки (getAll, getList), опционально для *Result, если возвращается коллекция |
| useRefAdapter | Одна сущность (getById), результат операции (*Result) |

**Правило:** один адаптер = один эндпоинт. Для каждой мутирующей операции — свой `*Result` useRefAdapter.

### 3. Методы repoHelper

| Метод | Когда использовать |
|-------|-------------------|
| useRepoGetRequest | GET — список, одна сущность, опции |
| useRepoPostRequest | POST — создание, мутации |
| useRepoPutRequest | PUT — обновление |
| useRepoPostFormRequest | POST multipart — загрузка файлов |
| useRepoPathRequest | PATCH |
| useRepoDeleteRequest | DELETE |
| useRepoGetUrlString | Только URL (например, для загрузки файла вне repoHelper) |
| useRepoGetWithPaginationRequest | GET с пагинацией (config: itemsField, summaryField) |
| useRepoGetCollectionRequest | GET коллекция с пагинацией |
| useRepoPostCollectionRequest | POST коллекция с пагинацией |
| useRepoDownloadFile | Скачивание файла (responseType: arraybuffer) |

### 4. Паттерны методов

- **getAll(query)** — model: collectionAdapter
- **clear*()** — `adapter.reset()` без аргументов
- **getById(id)** — model: refAdapter; иногда `getById(query)` если несколько параметров
- **add / update / create** — model: отдельный *Result refAdapter
- **getUploadUri*(query, options)** — `useRepoGetUrlString` для загрузки файлов снаружи

### 5. query vs queryParams

- `query` — тело POST/PUT или query-строка для GET
- `queryParams` — только query-параметры URL (отдельно от body)

### 6. wrapSort

repoHelper по умолчанию преобразует `page`, `rowsPerPage`, `sortBy`, `descending` в `pageNumber`, `pageSize`, `sorting`. Чтобы отключить: `options: { wrapSort: false }`.

## Специальные случаи

| Случай | Пример | Подход |
|--------|--------|--------|
| Auth | auth.js | Без repoHelper, без getPath; credentials, computed, login/logout |
| Стор без use*Repo | companyContentSettings.js | Экспортировать только use*Store |
| getById через POST | entityChangeSet.js | `useRepoPostRequest` + path getPath('getById') |
| Использование другого стора | userRole.js | `useConfigStore()` внутри метода |
| Kebab-case контроллер | user-roles | getPath('user-roles') |
| Домен ≠ контроллер | Company members.js | Внутри applicants, экспорт members; getPath('Applicants') |

## Чеклист при изменениях

- [ ] Имя контроллера и методов getPath совпадают с API
- [ ] Каждая мутирующая операция — свой *Result refAdapter
- [ ] Есть clear* для сброса при уходе со страницы или перед повторным запросом
- [ ] Импорты через @shared / @rt/shared
- [ ] В компонентах — только use*Store, не use*Repo
