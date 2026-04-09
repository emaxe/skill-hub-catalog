---
description: Permissions workflow for Vue UI apps — useAppPermissions, route guards, button visibility, form read-only mode, _CONST.permissions
alwaysApply: false
---

# Работа с правами (permissions) в UI

Проверка прав в проекте централизована в Pinia-сторе `useAppPermissions` (Shared.UI). Права приходят с бэкенда и сохраняются в `useConfigStore().permissions` (устанавливаются при логине/загрузке профиля через `userRole` store).

## Источник и инициализация

- **Стор:** `Shared.UI/stores/commonPermissions.js` — экспортирует `useAppPermissions`.
- **Импорт в приложении:** `import { useAppPermissions } from '@rt/shared/stores/commonPermissions'` или `import { useAppPermissions } from '@shared/stores/commonPermissions'`.
- **Данные прав:** хранятся в `useConfigStore().permissions` (массив строк). Заполняются при загрузке профиля через стор `userRole`.

## API useAppPermissions

| Метод | Назначение |
|-------|------------|
| `check(permission)` | Проверка одного права. Учитывает суперпользователя и `includedPermissions`. |
| `checkRoute(to)` | Проверка доступа к маршруту: все `to.meta.permissions` должны проходить `check`. |
| `onLoad()` | Promise, резолвится когда права загружены. Вызывать в guard перед проверкой. |

## Константы прав

- В каждом приложении: `app/src/constants/permissions.ts` — объект `permissions` и `includedPermissions`.
- В коде использовать через `_CONST`: `_CONST.permissions.Companies.Manage`, `_CONST.permissions.Settings.View` и т.д.

## Общие правила

### 1. Защита маршрутов
- `meta.permissions` + `beforeEnter: [guardAuth, guardPermission]`.
- В guard: `await appPermissions.onLoad()` → `appPermissions.checkRoute(to)`.

### 2. Скрытие пунктов меню
- `!link.route || appPermissions.checkRoute({ name: link.route })`.

### 3. Проверка прав в компонентах
- `const appPermissions = useAppPermissions()` в composable блоке.
- `computed(() => appPermissions.check(_CONST.permissions.Companies.Manage))`.

### 4. Кнопки и ссылки
- **btnsGenerator:** автоматически проверяет `checkRoute(btn.to)`.
- **xBtnLink:** автоматически `_disable` через `checkRoute(props.to)`.
- Кнопки без `to`: `isShow: () => _hasManagePermission.value`.

### 5. Формы и настройки
- Режим «только чтение»: `appPermissions.check(permissionManage)`.

### 6. Единый стиль
- `_hasManagePermission`, `_disableManage`, `_canEdit` — computed.
- View для страниц, Manage для действий.

## Примеры

```javascript
const _hasManagePermission = computed(() => appPermissions.check(_CONST.permissions.Companies.Manage))
```

```javascript
// Guard
if (to.meta?.permissions) {
  await appPermissions.onLoad()
  if (!appPermissions.checkRoute(to)) return { path: '/invoices' }
}
```

## Чеклист

- [ ] Маршруты: `meta.permissions` + `beforeEnter: [guardAuth, guardPermission]`
- [ ] `_CONST.permissions.*`, не строки напрямую
- [ ] `appPermissions.check(permission)` или `appPermissions.checkRoute(to)`
- [ ] В guard: `await appPermissions.onLoad()` перед `checkRoute`
