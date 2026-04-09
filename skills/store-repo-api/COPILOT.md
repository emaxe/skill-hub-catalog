# Сторы репозиториев (stores/repo) и работа с API

Правила и паттерны для сторов в `stores/repo`. Сторы оборачивают состояние и запросы к API через адаптеры и repoHelper.

## Расположение и именование

| Элемент | Правило | Примеры |
|--------|--------|---------|
| Файл | `stores/repo/<домен>.js`, camelCase | `applicants.js`, `companies.js` |
| Имя store | PascalCase | `'Companies'`, `'Applicants'` |
| Экспорт стора | `use<Домен>Store` | `useCompaniesStore` |
| Экспорт репо | `use<Домен>Repo` | `useCompaniesRepo` |
| Контроллер | Имя контроллера API | `'Companies'`, `'user-roles'` |

## Шаблон стора

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
      return await useRepoGetRequest({ query, path: getPath('getAll'), model: list })
    },
    async clearList() { list.reset() },
    async getById(id) {
      return await useRepoGetRequest({ query: { id }, path: getPath('getById'), model: item })
    },
    async clearItem() { item.reset() },
    async add(query) {
      await useRepoPostRequest({ query, path: getPath('add'), model: addResult })
    }
  }
}

export const useDomainRepo = () => reactive(getState())
export const useDomainStore = defineStore('Domain', () => getState())
```

## Адаптеры

- **useCollectionAdapter()** — для списков (getAll)
- **useRefAdapter()** — для одной сущности и результатов операций

Один адаптер = один эндпоинт. Каждый *Result — отдельный useRefAdapter().

## Методы repoHelper

| Метод | Назначение |
|-------|------------|
| useRepoGetRequest | GET |
| useRepoPostRequest | POST |
| useRepoPutRequest | PUT |
| useRepoPostFormRequest | POST multipart |
| useRepoDeleteRequest | DELETE |
| useRepoGetUrlString | Только URL |
| useRepoGetCollectionRequest / useRepoPostCollectionRequest | Коллекция с пагинацией |

Сигнатура: `{ path, query?, queryParams?, model, options? }`.

## Чеклист

- [ ] defineStore с именем в PascalCase
- [ ] useRefAdapter / useCollectionAdapter для состояния
- [ ] Запросы через useRepo*, path через getPath
- [ ] Каждый *Result — свой refAdapter
- [ ] clear* для сброса
- [ ] Импорты через @shared / @rt/shared
