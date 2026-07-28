---
name: design-implementation
description: ALWAYS use for ANY spacing/sizing work — measuring, debugging, implementing padding, margin, gap, height, width. Use when implementing Figma designs, debugging visual mismatch, fixing element heights, checking design compliance. Read BEFORE touching any CSS related to layout or spacing. Triggers: padding, margin, gap, height, width, spacing, отступ, расстояние, размер, Figma, пиксель, pixel, visual, визуальный, не совпадает, mismatch. | ВСЕГДА использовать для любой работы со spacing/sizing — измерение, отладка, реализация padding, margin, gap, height, width. Читать ПЕРЕД любым CSS для layout или spacing.
tags: [ui, vue]
author: maksimklisin
version: "1.0.0"
scope: global
platforms: [claude-code, cursor, copilot]
dependencies: []
language: any
---

# Design Implementation: Visual Measurement First

## Основной принцип

Измеряй, не предсказывай.

Предугадывание значений CSS приводит к итеративным правкам. Правильный путь:
сначала измерить каждый дочерний элемент в браузере, потом писать CSS.

## Типичная ошибка, которой нужно избегать

Смотреть на outer-атрибуты контейнера (padding, border-top, gap) и игнорировать
внутренние размеры дочерних элементов.

Пример: попытки починить высоту pagination-bar через padding контейнера.
Реальная причина -- Quasar устанавливает `height: 40px` (не min-height!) на
`.q-field--dense .q-field__control` и `min-height: 33.6px` на `.q-btn--round`.
Эти значения не перебиваются стандартными ожиданиями.

## Порядок работы

### Шаг 1. Измерить в браузере прежде всего

Запустить JavaScript в DevTools для измерения каждого дочернего элемента:

```javascript
// Пример: измерить все дочерние элементы контейнера
const container = document.querySelector('.your-container');
const children = [...container.children];

return children.map(el => {
  const rect = el.getBoundingClientRect();
  const styles = getComputedStyle(el);
  return {
    tag: el.tagName,
    class: el.className.slice(0, 60),
    height: rect.height,
    minHeight: styles.minHeight,
    computedHeight: styles.height,  // важно: height может быть задан явно
    padding: styles.padding,
  };
});
```

Ключевое: смотреть на `getComputedStyle(el).height`, а не только на `min-height`.
Quasar и другие UI-библиотеки часто устанавливают `height` явно.

### Шаг 2. Нарисовать ASCII-диаграмму до написания CSS

Сравнить текущее состояние браузера с Figma:

```
БРАУЗЕР (сейчас):
┏━━━━━━━━━━━━━━━━━━━━━━┓ <- .q-table__bottom  padding: 10px 16px
┃ ┌──────────────────┐ ┃ <- .q-field  height: 40px (Quasar default!)
┃ └──────────────────┘ ┃
┗━━━━━━━━━━━━━━━━━━━━━━┛
ИТОГО: 10 + 40 + 10 = 60px

FIGMA (нужно):
┏━━━━━━━━━━━━━━━━━━━━━━┓ <- .q-table__bottom  padding: 10px 16px
┃ ┌──────────────────┐ ┃ <- .q-field  height: 24px
┃ └──────────────────┘ ┃
┗━━━━━━━━━━━━━━━━━━━━━━┛
ИТОГО: 10 + 24 + 10 = 44px
```

### Шаг 3. Найти источник проблемы

Проверить применённые стили:

```javascript
const el = document.querySelector('.q-field__control');
const sheets = [...document.styleSheets];
const matches = sheets.flatMap(s => {
  try { return [...s.cssRules]; }
  catch { return []; }
}).filter(r => {
  try { return el.matches(r.selectorText); }
  catch { return false; }
});
return matches.map(r => ({ sel: r.selectorText, css: r.style.cssText }));
```

### Шаг 4. Исправить в источнике

Перебивать Quasar-стили явным значением, а не только min-height:

```scss
// НЕПРАВИЛЬНО: перебивает только min-height, но Quasar задаёт height явно
.q-field__control {
  min-height: 24px;
}

// ПРАВИЛЬНО: перебивает и height, и min-height
.q-field__control {
  height: 24px;
  min-height: 24px;
}
```

## Quasar 2: известные проблемные значения

Элементы, значения которых нужно проверять измерением, не предположением:

| Элемент | Дефолт Quasar | Перебивать через |
|---|---|---|
| `.q-field--dense .q-field__control` | `height: 40px` | `height: Npx; min-height: Npx` |
| `.q-field__append` | `height: 40px` (наследует `$field-height`, не от родителя) | `height: Npx; min-height: Npx` |
| `.q-btn--round` | `min-height: 33.6px` (2.1em) | `min-height: Npx; width: Npx; height: Npx` |
| `.q-field__native` | padding-top/bottom из theme | `padding: 0` |
| `.q-table__bottom` | `min-height: 48px` | `min-height: auto` + override children |

## Чеклист до написания CSS

- Измерил каждый дочерний элемент в браузере (getComputedStyle)
- Нарисовал диаграмму: браузер vs Figma
- Нашёл источник (не симптом) проблемы
- Не использую отрицательные margin без крайней необходимости
- Проверил в браузере после изменений
