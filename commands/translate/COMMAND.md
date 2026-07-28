---
name: translate
description: "Проверяет наличие переводов и добавляет недостающие RU→EN переводы в файлы translates/ проекта Web.Nx24.UI."
tags: [ui, workflow]
author: maksimklisin
version: "1.0.0"
scope: project
platforms: [claude-code]
dependencies: [web-nx24-translations]
projects: [nx24]
---

- проверь наличие перевода/переводов
- если его нет, то добавь перевод/переводы в файлы переводов ("translates")
- конкретный файл перевода выбери логически, в зависимости от компонента в котором этот перевод используется (переводы, которые используются в разных местах приложения можно добавлять в файл "translates/main-en.json")
