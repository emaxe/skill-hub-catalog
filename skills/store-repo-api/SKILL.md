---
name: store-repo-api
description: "Use when creating or editing Pinia repository stores for API interaction in Vue UI apps. Covers store file structure, adapters (useRefAdapter/useCollectionAdapter), repoHelper methods, getPath, and full store template."
tags: [ui, vue, architecture]
author: maksimklisin
version: "1.0.0"
scope: global
platforms: [claude-code, cursor, copilot]
dependencies: [ui-code-style]
projects: [kyc]
language: typescript
---

# Сторы репозиториев (stores/repo) и работа с API

Правила и паттерны для сторов в `Admin.UI/app/src/stores/repo` и `Company.UI/app/src/stores/repo` (и Widget.UI по аналогии). Сторы оборачивают состояние и запросы к API через адаптеры и repoHelper.

## Когда применять

- Создание нового стора для домена (новый контроллер API).
- Добавление методов/полей в существующий стор (новые эндпоинты или состояние).
- Редактирование структуры стора (адаптеры, экспорты, имена).

## Расположение и именование

| Элемент | Правило | Примеры |
|--------|--------|---------|
| Файл | `stores/repo/<домен>.js`, camelCase | `applicants.js`, `companies.js`, `identifications.js` |
| Имя store в Pinia | Домен в PascalCase, единственное число | `'Companies'`, `'Applicants'`, `'Identifications'` |
| Исключения для имени store | lowercase для auth/settings | `'auth'`, `'settings'` |
| Экспорт стора | `use<Домен>Store` | `useCompaniesStore`, `useApplicantsStore` |
| Экспорт репо (опционально) | `use<Домен>Repo` | `useCompaniesRepo` |
| Контроллер для getPath | Имя контроллера API | `'Companies'`, `'Applicants'`, `'user-roles'` |

## Структура файла

Порядок:

1. **Импорты** — из `@shared/stores/repo/repoHelper`, `vue`, `pinia`, адаптеры.
2. **Путь к API:** `const getPath = useGetPath('<ControllerName>')`.
3. **Состояние и методы:** `const getState = () => { ... }`.
4. **Экспорты:** `use*Repo` (если нужен), `use*Store`.

### Шаблон

```javascript
import { useGetPath, useRepoGetRequest, useRepoPostRequest } from '@shared/stores/repo/repoHelper'
import { reactive } from 'vue'
import { defineStore } from 'pinia'
import { useRefAdapter } from '@shared/stores/repo/adapters/refAdapter'
import { useCollectionAdapter } from '@rt/shared/stores/repo/adapters/collectionAdapter'

const getPath = useGetPath('ControllerName')

const getState = () => {
  const list = useCollectionAdapter()
  const item = useRefAdapter()
  const addResult = useRefAdapter()

  return {
    list: list.value,
    item: item.value,
    addResult: addResult.value,

    async getAll(query) {
      return await useRepoGetRequest({
        query,
        path: getPath('getAll'),
        model: list
      })
    },
    async clearList() {
      list.reset()
    },
    async getById(id) {
      return await useRepoGetRequest({
        query: { id },
        path: getPath('getById'),
        model: item
      })
    },
    async clearItem() {
      item.reset()
    },
    async add(query) {
      await useRepoPostRequest({
        query,
        path: getPath('add'),
        model: addResult
      })
    }
  }
}

export const useDomainRepo = () => reactive(getState())
export const useDomainStore = defineStore('Domain', () => getState())
```

## Адаптеры

- **useCollectionAdapter()** — для списков (getAll). Состояние: `loading`, `loaded`, `data`, `error`. Методы: `reset()`.
- **useRefAdapter()** — для одной сущности (getById) и для результата операции (*Result).

Один адаптер — один эндпоинт/одно место состояния. Для каждого результата POST/PUT заводить отдельный `useRefAdapter()`.

## Методы repoHelper (Shared.UI)

| Метод | Назначение |
|-------|------------|
| useRepoGetRequest | GET с query, результат в model |
| useRepoPostRequest | POST, body + query, результат в model |
| useRepoPutRequest | PUT |
| useRepoPostFormRequest | POST как form (multipart) |
| useRepoGetUrlString | Только URL для запроса |
| useRepoDeleteRequest | DELETE |
| useRepoGetWithPaginationRequest | GET с пагинацией (config: itemsField, summaryField) |
| useRepoGetCollectionRequest / useRepoPostCollectionRequest | Коллекция с пагинацией |

Сигнатура: `{ path, query?, queryParams?, model, options?, newApi? }`. `path` — из `getPath('methodName')`.

## Паттерны методов

- **getAll(query)** — список, model: useCollectionAdapter().
- **getById(id)** — одна сущность, model: useRefAdapter().
- **clear*()** — без аргументов, вызывает `adapter.reset()`.
- **add / update / create** — POST/PUT, model: отдельный *Result useRefAdapter().

## Специальные случаи

- **auth.js** — без repoHelper и getPath; локальное состояние.
- **Стор без use*Repo** — допустимо экспортировать только `use*Store`.
- **Использование другого стора** — допустимо при необходимости (пример: userRole.js и setPermissions).

## Чеклист

- [ ] Файл в `stores/repo/`, имя и контроллер согласованы с API.
- [ ] defineStore с именем в PascalCase.
- [ ] Используются только useRefAdapter / useCollectionAdapter.
- [ ] Все запросы через useRepo* из repoHelper, path через getPath.
- [ ] Для каждого результата мутирующей операции — свой *Result refAdapter.
- [ ] Есть clear* для сброса.
- [ ] Импорты: алиасы @shared / @rt/shared.
- [ ] В компонентах — только use*Store, не use*Repo.
