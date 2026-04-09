---
name: move-component-to-shared
description: "Use when moving a Vue component from Admin.UI, Company.UI, or Widget.UI to Shared.UI for reuse. Covers inject/provide pattern for store and app-specific config (routes, permissions). Triggers: 'перенеси в Shared', 'вынеси в Shared.UI', 'сделай переиспользуемым'."
tags: [ui, vue, architecture]
author: maksimklisin
version: "1.0.0"
scope: global
platforms: [claude-code, cursor, copilot]
dependencies: [ui-code-style]
projects: [kyc]
language: typescript
---

# Перенос компонента в Shared.UI

## Когда использовать

- Пользователь просит перенести компонент в Shared.UI
- Компонент планируется использовать в нескольких приложениях
- Нужно вынести переиспользуемый UI без дублирования доменной логики

## Стратегия

Store и app-specific константы (роуты, права) **остаются в приложении**. Компонент в Shared получает их через **inject**. Общие константы (rowsPerPageOptions, enum, attrs) берутся из `_sCONST` в Shared.

```
┌─────────────────────┐     provide      ┌─────────────────────┐
│ App (Company/Admin) │ ──────────────► │ Shared.UI component │
│ store, _CONST       │   inject Keys   │ inject(store, config)│
└─────────────────────┘                 └─────────────────────┘
```

## Шаги

### 1. Анализ зависимостей

Проверь компонент и вложенные (blocks, dialogs):

- **Store** (`use*Store`) — остаётся в app, заменить на `inject('storeKey')`
- **Constants** — `_CONST.route.*`, `_CONST.permissions.*` → inject config; `rowsPerPageOptions`, `enum`, `attrs` → `_sCONST` из `@rt/shared/constants/sharedConst`
- **Shared** — XPageBlock, XDialog, cells и т.д. уже из `@rt/shared`, пути не менять
- **Локальные** — blocks, dialogs переносить вместе с основным компонентом

### 2. Создание структуры в Shared.UI

```
Shared.UI/components/{domain}/
├── {domain}Component.vue      # основной компонент
├── blocks/
│   ├── {domain}Filters.vue
│   └── {domain}Table.vue
└── dialogs/
    └── {domain}AddDialog.vue
```

### 3. Адаптация перенесённых компонентов

**Store:**
```javascript
// Было
import { useApplicantsStore } from '@stores/repo/members'
const applicantsStore = useApplicantsStore()

// Стало
const applicantsStore = inject('applicantsStore')
```

**Константы из Shared:**
```javascript
import { _sCONST } from '@rt/shared/constants/sharedConst'
// rowsPerPageOptions, enum.MemberKycStatus, attrs.field — из _sCONST
```

**App-specific config (роут, права):**
```javascript
const membersConfig = inject('membersConfig', {})
// membersConfig.routeMember, membersConfig.permissionCreate
```

**Импорты внутри Shared:**
- К Shared: `@rt/shared/...` или `@shared/...`
- К локальным: `./blocks/...`, `./dialogs/...`

**Защита от отсутствия provide:**
```javascript
if (!applicantsStore) return
applicantsStore?.clearMembers()
```

### 4. Обновление страницы в приложении

```vue
<script setup>
import { provide } from 'vue'
import XPage from '@shared/components/page/xPage'
import MembersComponent from '@shared/components/members/membersComponent.vue'
import { useApplicantsStore } from '@stores/repo/members'
import { _CONST } from '@constants/constants'

provide('applicantsStore', useApplicantsStore())
provide('membersConfig', {
  routeMember: _CONST.route.member,
  permissionCreate: _CONST.permissions.Applicants.Create,
})
</script>
```

### 5. Удаление файлов из приложения

Удалить перенесённые файлы из `App/components/{domain}/`.

### 6. Проверка

- Сборка приложения без ошибок
- Линтер без ошибок
- Страница работает: список, фильтры, диалоги, кнопки

## Контракт inject

| Ключ | Назначение | Пример |
|------|------------|--------|
| `{domain}Store` | Store приложения | `applicantsStore` |
| `{domain}Config` | Роуты, права, прочий app config | `{ routeMember, permissionCreate }` |

## Что не переносить

- **Store** — остаётся в `App/stores/repo/`
- **Детальные компоненты** — если используются только в одном месте
- **Файлы, использующиеся в других страницах** — проверить через grep перед удалением

## Чеклист

- [ ] Перенесены основной компонент + blocks + dialogs
- [ ] Store заменён на inject
- [ ] _CONST заменён на _sCONST или membersConfig
- [ ] В странице добавлены provide
- [ ] Импорт из @shared/components/...
- [ ] Удалены оригиналы из приложения
- [ ] Сохранены v-model и props (pagination, paginationModel и т.д.)
