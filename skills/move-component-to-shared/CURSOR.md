---
description: Move Vue component from app to Shared.UI — inject/provide pattern for store and app-specific config, directory structure, migration checklist
alwaysApply: false
---

# Перенос компонента в Shared.UI

## Когда использовать

- Компонент планируется использовать в нескольких приложениях
- Нужно вынести переиспользуемый UI без дублирования доменной логики

## Стратегия

Store и app-specific константы (роуты, права) **остаются в приложении**. Компонент в Shared получает их через **inject**.

## Шаги

### 1. Анализ зависимостей

- **Store** (`use*Store`) — заменить на `inject('storeKey')`
- **Constants** — `_CONST.route.*`, `_CONST.permissions.*` → inject config; общие → `_sCONST`
- **Локальные** — blocks, dialogs переносить вместе

### 2. Создание структуры в Shared.UI

```
Shared.UI/components/{domain}/
├── {domain}Component.vue
├── blocks/
└── dialogs/
```

### 3. Адаптация перенесённых компонентов

```javascript
// Store → inject
const applicantsStore = inject('applicantsStore')

// App config → inject
const membersConfig = inject('membersConfig', {})

// Shared constants
import { _sCONST } from '@rt/shared/constants/sharedConst'
```

### 4. Обновление страницы в приложении

```vue
<script setup>
import { provide } from 'vue'
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

### 5. Удаление файлов из приложения и проверка

## Чеклист

- [ ] Перенесены основной компонент + blocks + dialogs
- [ ] Store заменён на inject
- [ ] _CONST заменён на _sCONST или config через inject
- [ ] В странице добавлены provide
- [ ] Удалены оригиналы из приложения
