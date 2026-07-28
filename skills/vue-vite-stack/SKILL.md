---
name: vue-vite-stack
description: "Правила разработки на TypeScript, Vue.js 3, Vite, Pinia, VueUse. Используй при работе над Vue-приложениями на Vite, настройке компонентов, стилей и оптимизации сборки."
tags: [ui, vue, typescript]
author: maksimklisin
version: "1.0.0"
scope: global
platforms: [claude-code, cursor, copilot]
dependencies: []
language: typescript
---

# Vue + Vite + Pinia (TypeScript)

Правила кода и производительности для стека Vue 3, Vite, Pinia.

## Стиль и структура

- Лаконичный, поддерживаемый TypeScript с релевантными примерами.
- Функциональный и декларативный стиль; без классов.
- Итерация и модульность; следование DRY.
- Имена переменных с вспомогательными глаголами (например, `isLoading`, `hasError`).
- Файл: только связанный контент — экспорт компонента, подкомпоненты, хелперы, статика, типы.

## Именование

- Директории: lowercase с дефисами (например, `components/auth-wizard`).
- Функции: предпочтительно named exports.

## TypeScript

- TypeScript везде; интерфейсы предпочтительнее типов (расширяемость и merge).
- Избегать enums; использовать maps.
- Компоненты: функциональные с интерфейсами.

## Синтаксис и формат

- Чистые функции: ключевое слово `function`.
- **Vue:** всегда Composition API в стиле `<script setup>`.

## UI и стили

- Компоненты и стили: Headless UI, Element Plus, Tailwind.
- Адаптив: Tailwind, mobile-first.

## Производительность

- VueUse для реактивности и производительности где уместно.
- Асинхронные компоненты: обёртка в Suspense с fallback.
- Динамическая загрузка некритичных компонентов.
- Изображения: WebP, размеры, ленивая загрузка.
- Сборка Vite: код-сплиттинг и чанки для меньшего размера бандла.

## Конвенции

- Оптимизация Web Vitals (LCP, CLS, FID): Lighthouse или WebPageTest.
