# Стили и CSS

## Обязательный комментарий `// $`

Каждый блок `<style scoped lang="scss">` (и любой scss-блок в .vue) **должен** начинаться с `// $` на первой строке.

```vue
<style scoped lang="scss">
// $
.my-class {
  display: flex;
}
</style>
```

Допускается также на одной строке с тегом:

```vue
<style scoped lang="scss"> //$
.my-class { ... }
</style>
```

При добавлении или изменении `<style>` всегда проверять наличие `// $`.

## Именование классов

**BEM-подобный подход** с именем компонента как блоком:

```scss
.member-details-info-block {
  &__wrap { ... }
  &__main { ... }
  &__photo { ... }
  &__photo-placeholder { ... }
  &__actions { ... }
}
```

- Блок = имя компонента в kebab-case (`member-add-dialog`, `member-details-info-block`).
- Элемент = `__element` (`__wrap`, `__form`, `__actions`).
- Модификатор (при необходимости) = `--modifier`.

**Shared.UI:** классы с префиксом `x-` (`x-form`, `x-form__title`, `x-page-block`, `x-dialog`).

## CSS-переменные (vars.scss)

Общие переменные определены в `Shared.UI/css/vars.scss`:

| Переменная | Значение |
|------------|----------|
| `--gap-default` | `20px` |
| `--gap-dense` | `10px` |
| `--gap-mid` | `25px` |
| `--gap-fat` | `30px` |
| `--primary` | `#1976D2` |
| `--positive` | `#27AE60` |
| `--negative` | `#EB5757` |
| `--warning` | `#FF9838` |
| `--border-color` | `rgba(150, 150, 150, 0.2)` |
| `--at` | `300ms` (анимации) |
| `--color-dark` | `#212121` |
| `--blue-grey` | `#607d8b` |

Использовать существующие переменные вместо хардкода значений. Не дублировать глобальные переменные в компонентах.

## Quasar-стили

- Переопределение Quasar — в `src/css/quasar.variables.scss` приложения.
- Глобальные стили приложения — в `src/css/app.scss`.
- Shared миксины (`@include row-gap(...)`, `@include column-gap(...)`) доступны через `Shared.UI/css/`.
