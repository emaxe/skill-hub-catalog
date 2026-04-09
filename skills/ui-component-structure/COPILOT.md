# Структура Vue-компонентов

## Роли компонентов

| Роль | Что делает | Логика |
|------|------------|--------|
| **Страница** (`*Page.vue`) | Подключает layout + один корневой компонент домена | Минимум (мета, заголовок) |
| **Домен** (`*Component.vue`) | Держит состояние (pagination, dialog flags), вызывает `use*Store`, рендерит blocks и dialogs | Основная |
| **Блок** (`*Block.vue`, `*Table.vue`, `*Filter.vue`) | Получает данные через props/inject, emit события | Отображение, мелкая логика |
| **Диалог** (`*Dialog.vue`) | Получает данные через props, emit результат | Форма, валидация |

Блоки и диалоги **не** дублируют обращение к store, если данные уже переданы родителем.

## Порядок блоков в `<script setup>`

Строгий порядок; между блоками — разделитель `//----------------------`. Пустые блоки пропускать.

1. **Импорты** — все `import`.
2. **Локальные константы** — `const PAGE_SIZE = 20`, массивы опций и т.п.
3. **Composable** — `useQuasar()`, `inject(...)`, `useConfigStore()`, `useAppPermissions()`, `useRouter()`.
4. **Props / Emit** — `defineProps`, `withDefaults`, `defineEmits`.
5. **Ref / Reactive** — `ref(...)`, `reactive(...)`.
6. **Computed** — все `computed(...)`.
7. **Watch** — `watch`, `watchEffect`.
8. **Методы** — обычные функции (обработчики, хелперы).
9. **Lifecycle** — `onMounted`, `onBeforeMount`, `onUnmounted`.

### Пример

```vue
<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import XPageBlock from '@rt/shared/components/page/xPageBlock.vue'
import { useCompaniesStore } from '@stores/repo/companies'

//----------------------
const PAGE_SIZE = 20

//----------------------
const companiesStore = useCompaniesStore()

//----------------------
const props = defineProps<{ companyId: string }>()
const emit = defineEmits(['go'])

//----------------------
const loading = ref(false)
const list = ref<Item[]>([])

//----------------------
const hasItems = computed(() => list.value.length > 0)

//----------------------
watch(() => props.companyId, (id) => { load(id) })

//----------------------
function load(id: string) {
  loading.value = true
  companiesStore.fetchById(id).finally(() => { loading.value = false })
}

//----------------------
onMounted(() => load(props.companyId))
</script>
```

## Template: блок диалогов

Диалоги в шаблоне отделять комментарием `<!--  DIALOGS  -->` (два пробела после `<!--` и два перед `-->`). Комментарий — на отдельной строке перед первым диалогом.

```vue
<template>
  <div class="my-component">
    <!-- основная разметка -->

    <!--  DIALOGS  -->
    <my-add-dialog v-model="showAdd" @go="onAdded" />
    <my-edit-dialog v-model="showEdit" :item="selected" @go="onEdited" />
  </div>
</template>
```
