---
description: Import aliases and paths for Vue UI projects — alias table, usage patterns, import ordering rules
alwaysApply: false
---

# Импорты и алиасы

Всегда использовать алиасы вместо относительных путей.

## Таблица алиасов

| Алиас | Назначение |
|-------|------------|
| `@shared` / `@rt/shared` | Shared.UI (компоненты, сторы, сервисы, фильтры, константы) |
| `@components` | `src/components/` приложения |
| `@pages` | `src/pages/` |
| `@layouts` | `src/layouts/` |
| `@stores` | `src/stores/` |
| `@constants` | `src/constants/` |
| `@services` | `src/services/` |
| `@boot` | `src/boot/` |
| `@assets` | `src/assets/` |
| `@css` | `src/css/` |
| `@filters` | `src/filters/` (при наличии) |

## Shared: `@shared` vs `@rt/shared`

Оба алиаса указывают на `Shared.UI/`. В одном файле допустимо использовать оба варианта — следовать тому, что уже применяется в файле или модуле.

**Типичные паттерны:**

```javascript
// Компоненты Shared — обычно @rt/shared (полный путь до файла)
import XForm from '@rt/shared/components/form/xForm.vue'
import XDialog from '@rt/shared/components/dialog/xDialog.vue'
import CellDefault from '@rt/shared/components/_cells/cellDefault.vue'

// Сторы Shared — @shared или @rt/shared
import { useConfigStore } from '@shared/stores/configStore'
import { useAppPermissions } from '@rt/shared/stores/commonPermissions'

// Константы Shared
import { _sCONST } from '@rt/shared/constants/sharedConst'

// Фильтры Shared
import { useFilterMoment } from '@shared/filters/filters'
```

## Импорты приложения

```javascript
// Сторы приложения
import { useCompaniesStore } from '@stores/repo/companies'

// Константы приложения
import { _CONST } from '@constants/constants'

// Страницы (lazy import в routes.ts)
component: () => import('@pages/CompaniesPage.vue')
```

## Порядок импортов

1. Vue (`vue`, `vue-router`)
2. Внешние библиотеки (`quasar`, `@vuelidate/core`, `moment`, `qrcode.vue`)
3. Shared.UI (`@rt/shared/...`, `@shared/...`)
4. Приложение (`@stores/...`, `@components/...`, `@constants/...`)
