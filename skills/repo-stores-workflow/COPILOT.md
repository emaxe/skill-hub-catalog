# Workflow сторов репозиториев (stores/repo)

Workflow и проектные конвенции для работы со сторами в `Admin.UI`, `Company.UI`, `Widget.UI`. Детали структуры и API — см. скилл **store-repo-api**.

## Когда применять

- Создание нового стора для домена
- Добавление методов или полей в существующий стор
- Редактирование структуры стора, адаптеров, экспортов

## Именование и расположение

- Файл: `app/src/stores/repo/<домен>.js` (camelCase)
- Pinia store: PascalCase (`'Applicants'`, `'Companies'`), исключения: `'auth'`, `'settings'`
- Контроллер в getPath: совпадает с API
- Методы getPath: как на бэкенде

## Адаптеры

| Адаптер | Использование |
|---------|---------------|
| useCollectionAdapter | Списки (getAll, getList) |
| useRefAdapter | Одна сущность (getById), результат операции (*Result) |

Один адаптер = один эндпоинт. Для каждой мутирующей операции — свой `*Result` useRefAdapter.

## Методы repoHelper

| Метод | Когда |
|-------|-------|
| useRepoGetRequest | GET |
| useRepoPostRequest | POST |
| useRepoPutRequest | PUT |
| useRepoPostFormRequest | POST multipart |
| useRepoDeleteRequest | DELETE |
| useRepoGetUrlString | Только URL |
| useRepoGetCollectionRequest / useRepoPostCollectionRequest | Коллекция с пагинацией |

## Паттерны

- **getAll(query)** — model: collectionAdapter
- **clear*()** — `adapter.reset()`
- **getById(id)** — model: refAdapter
- **add / update / create** — model: отдельный *Result refAdapter
- `query` — тело POST/PUT или query-строка GET; `queryParams` — только URL params

## Чеклист

- [ ] Имя контроллера и методов getPath совпадают с API
- [ ] Каждая мутирующая операция — свой *Result refAdapter
- [ ] Есть clear* для сброса
- [ ] Импорты через @shared / @rt/shared
- [ ] В компонентах — только use*Store, не use*Repo
