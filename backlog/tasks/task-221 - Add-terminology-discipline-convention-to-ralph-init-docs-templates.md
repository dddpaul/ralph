---
id: TASK-221
title: Add terminology-discipline convention to ralph-init docs templates
status: To Do
assignee: []
created_date: '2026-08-06 17:28'
labels: []
dependencies:
  - TASK-220
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Docs/Mixed-проекты, которые ralph-init разворачивает как Obsidian-vault, нуждаются не только в
конвенции вики-ссылок (TASK-220), но и в дисциплине терминологии: авторы (и сам агент)
систематически транслитерируют иностранные тех-термины, выдумывают кальки/метафоры и роняют
жаргон без определения — каноны из-за этого расходятся и становятся нечитаемы для другого
агента. Конвенция уже закреплена в реальном docs-проекте (stacks: секция CLAUDE.md + reviewer
R-DOCS-2). Нужно поднять её языко-НЕзависимый механизм в шаблоны ralph-init как ВТОРУЮ
конвенцию рядом с Obsidian, чтобы новые docs-проекты получали обе на init.

## Scope

In scope:
- Дописать в `CLAUDE.conventions.docs.md` подсекцию «Terminology discipline» (языко-независимую,
  после `### Code Style`, рядом с секцией Obsidian из TASK-220).
- Дописать правило `R-DOCS-2: Terminology discipline` в `task-reviewer-rules.docs.md` (файл
  создаётся TASK-220) — ссылается на секцию CLAUDE.md как источник истины, не дублирует текст.

Out of scope:
- НЕ создавать `task-reviewer-rules.docs.md` и НЕ добавлять шаг ralph-init / правку Step 4 — их
  владелец TASK-220 (эта задача от него зависит).
- НЕ трогать `CLAUDE.conventions.python.md` и Code-only поведение.
- НЕ засевать конвенцией существующие проекты (только шаблоны для новых).
- НЕ вводить автоматический линтер/хук — только текстовая конвенция + правило ревьюера.

## Files

- `plugins/ralph/skills/ralph-init/templates/root/CLAUDE.conventions.docs.md` (exists) —
  дописать подсекцию «Terminology discipline» после блока `### Code Style`.
- `plugins/ralph/skills/ralph-init/templates/claude/task-reviewer-rules.docs.md`
  (создаётся TASK-220 — dep) — дописать правило R-DOCS-2 в конец файла.

## Convention text (вставить дословно в CLAUDE.conventions.docs.md, после `### Code Style`)

```
### Terminology discipline

Документы этого проекта (и твои собственные ответы) пишутся на рабочем языке проекта — плоско и
единообразно. Заголовки — на английском (naming-guard), остальное — проза на рабочем языке.
Применять проактивно, не дожидаясь замечаний; вычитывать и СВОИ формулировки перед отправкой.

- **Не транслитерировать иностранные тех-термины** в алфавит рабочего языка там, где есть
  плоский или устоявшийся термин. Замену бери из канона/домена, не выдумывай.
- **Не выдумывать термины, метафоры и кальки.** Если канон уже назвал вещь — используй это имя.
- **Жаргон вводить определением при первом употреблении**, дальше — единообразно. Жаргон без
  определения, брошенный сразу в действие, — дефект.
- **Держать проектный keep-list** устоявшихся доменных/канон-терминов, которые НЕ переписывать;
  расширять его под проект.
- **Равняться на словарь referenced-проекта/домена** — не «чинить» устоявшийся термин под себя.
- **Убирать commit-SHA из прозы**; ссылки на ID задач (напр. TASK-N) — норма (provenance).
```

## Reviewer rule text (дописать в task-reviewer-rules.docs.md, после R-DOCS-1)

```
## R-DOCS-2: Terminology discipline

Применять к любой правке `.md`, добавляющей/меняющей прозу на рабочем языке проекта. Источник
истины — секция «Terminology discipline» в CLAUDE.md (НЕ дублировать её здесь). Отклонять
(CHANGES REQUESTED), если правка вносит:

- транслитерацию иностранного слова в алфавит рабочего языка там, где есть плоский/устоявшийся
  термин;
- выдуманный термин, метафору или кальку, отсутствующие в каноне;
- жаргон без определения при первом употреблении;
- необъяснённый латинский тех-термин в прозе рабочего языка (без определения/формулировки);
- конкретный commit-SHA в прозе (ссылки на ID задач допустимы).

НЕ флагуй keep-list термины проекта — они канон.
```

## Source

Source: /Users/paul/Private/Alfa/Projects/standard/stacks@5c0b14bea3f8
Source design context (read-only, do NOT modify): конвенция закреплена в stacks — CLAUDE.md
секция «Plain-Russian terminology convention» и `.claude/task-reviewer-rules.md` R-DOCS-2
(TASK-166, слито в master). Русская таблица замен и keep-list — локальны для stacks; в шаблон
ralph поднимается только языко-независимый механизм.

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. TASK-220 — status Done: файл `task-reviewer-rules.docs.md` и шаг ralph-init уже существуют
   (эта задача только дописывает в них). Если TASK-220 не Done — STOP.
2. `(exists)` путь `CLAUDE.conventions.docs.md` присутствует; целевая вставка — после `### Code Style`.
3. Каждый AC объективно проверяем (grep по файлу).
4. Out-of-scope (создание шаблона / шаг init / Step 4, python-конвенции, Code-only, засев
   существующих проектов) не затронут.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CLAUDE.conventions.docs.md содержит подсекцию «### Terminology discipline» после блока ### Code Style, с пунктами: не транслитерировать, не выдумывать термины/кальки, вводить жаргон определением при первом употреблении, проектный keep-list, равнение на словарь домена, убирать commit-SHA из прозы (grep находит заголовок и пункты).
- [ ] #2 task-reviewer-rules.docs.md содержит правило R-DOCS-2 «Terminology discipline», которое ссылается на секцию CLAUDE.md как источник истины и не дублирует её текст.
- [ ] #3 R-DOCS-2 перечисляет условия CHANGES REQUESTED (транслитерация, выдуманные термины/кальки, жаргон без определения, необъяснённый латинский тех-термин, commit-SHA в прозе) и явно не флагует keep-list термины.
- [ ] #4 Новый reviewer-шаблон НЕ создаётся и новый шаг ralph-init НЕ добавляется этой задачей (владение TASK-220); задача только дописывает в существующие после TASK-220 файлы.
- [ ] #5 Code-only поведение и CLAUDE.conventions.python.md не изменены.
<!-- AC:END -->
