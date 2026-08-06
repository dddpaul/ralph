---
id: TASK-220
title: Add Obsidian cross-link convention to ralph-init docs templates
status: To Do
assignee: []
created_date: '2026-08-04 13:06'
updated_date: '2026-08-04 13:13'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Проекты типа Документация (и Mixed), которые `ralph-init` разворачивает как Obsidian-vault,
систематически получают битые вики-ссылки между каноническими `.md`-документами. Наивная
запись `[[doc-2 §1.3]]` не резолвится (имя файла — `doc-2 - Architecture-…`, а `§1.3` — не
якорь), и по клику Obsidian создаёт пустые заметки-пустышки. Отдельная ловушка — вики-ссылка
с display-алиасом внутри ячейки markdown-таблицы: символ `|` алиаса ломает разметку таблицы.
Обе проблемы недавно всплыли в реальном docs-проекте (stacks, doc-9) и потребовали трёх
последовательных правок. Конвенцию нужно (1) дать автору заранее — чтобы он писал ссылки
правильно, и (2) дать ревьюеру — чтобы ловить нарушения. Сейчас ни того, ни другого в
шаблонах `ralph-init` нет.

## Scope

In scope:
- Добавить секцию «Obsidian cross-link convention» в docs-шаблон CLAUDE-конвенций
  (`CLAUDE.conventions.docs.md`) — это единый источник правды для АВТОРА. `ralph-init` уже
  дописывает этот файл в CLAUDE.md для типа Документация (Step 3.2, lang=docs), так что новая
  секция автоматически попадёт в каждый новый docs/mixed-проект без изменения самого потока.
- Создать НОВЫЙ шаблон правила ревьюера `templates/claude/task-reviewer-rules.docs.md` —
  краткое правило для АГЕНТА task-reviewer, которое НЕ дублирует текст конвенции, а ссылается
  на секцию в CLAUDE.md как на источник правды (иначе две формулировки разойдутся).
- Добавить в SKILL.md ralph-init новый шаг записи `task-reviewer-rules.docs.md` в проект как
  `.claude/task-reviewer-rules.md`, ГЕЙТ на тип проекта Documentation/Mixed (по образцу того,
  как Step 3.7b/c гейтит pptx-правила: Code-only — пропускать с печатью `[skip]`). Обновить
  Step 4 (итоговый список файлов) и, если есть, verify-блок.

Out of scope:
- НЕ менять поведение для Code-only проектов (там нет vault и `[[…]]` — правило было бы шумом).
- НЕ трогать `CLAUDE.conventions.python.md` и прочие языковые конвенции.
- НЕ засевать этой конвенцией уже существующие проекты (это делает владелец каждого проекта
  отдельно; здесь — только шаблоны для НОВЫХ проектов).
- НЕ вводить автоматический линтер/хук, проверяющий ссылки — только текстовая конвенция +
  правило ревьюера. (Хук — потенциальная отдельная задача.)

## Files

- `plugins/ralph/skills/ralph-init/templates/root/CLAUDE.conventions.docs.md` (exists) —
  добавить секцию «Obsidian cross-link convention» (текст ниже) после блока `### Code Style`.
- `plugins/ralph/skills/ralph-init/templates/claude/task-reviewer-rules.docs.md` (to-create) —
  новый файл: короткое правило ревьюера, ссылающееся на конвенцию из CLAUDE.md.
- `plugins/ralph/skills/ralph-init/SKILL.md` (exists) — добавить шаг записи docs-правила
  ревьюера под гейтом Documentation/Mixed; обновить Step 4 file-list.

## Convention text (вставить дословно в CLAUDE.conventions.docs.md)

```
### Obsidian cross-link convention

Документы этого проекта живут в Obsidian-vault. Ссылки между ними должны резолвиться —
иначе по клику Obsidian создаёт пустые заметки-пустышки.

- **Ссылка на канон-документ:** `[[<полный-basename-без-.md>#<дословный-заголовок>|<короткий display>]]`.
  Имя файла — ПОЛНОЕ (`doc-2 - Architecture-layers-and-system-classes`), не `doc-2`.
  `§X.Y` — это НЕ якорь; якорь = точный текст заголовка раздела (`#1.3. Кросс-продуктовые сервисы`).
- **Документы без заголовков-пунктов** (напр. глоссарий TERMS) — ссылка на файл целиком:
  `[[TERMS|TERMS #14]]`. Прыжок к конкретному пункту невозможен, если у него нет заголовка.
- **Внутри ячеек markdown-таблиц** пайп display-алиаса ОБЯЗАТЕЛЬНО экранировать: `[[…\|display]]`.
  Неэкранированный `|` таблица трактует как разделитель столбца и ломает разметку.
  В прозе (вне таблиц) экранирование не нужно.
- **Ссылка в соседний vault (cross-vault):** `obsidian://open?vault=<vault>&file=<полный-basename>`;
  пробелы в имени файла кодировать как `%20`.
```

## Reviewer rule text (содержимое нового task-reviewer-rules.docs.md)

```
# Task reviewer rules (Documentation projects)

## R-DOCS-1: Obsidian cross-link convention

Применять к любой правке `.md`, добавляющей/меняющей вики-ссылки `[[…]]` или `obsidian://` URI.
Источник истины по формату — секция «Obsidian cross-link convention» в CLAUDE.md (НЕ дублировать
её здесь). Отклонять (CHANGES REQUESTED), если:

- вики-ссылка на канон использует короткое имя (`[[doc-2 …]]`) вместо полного basename, или
  `§X.Y` как якорь вместо дословного заголовка раздела;
- внутри ячейки markdown-таблицы display-пайп вики-ссылки НЕ экранирован (`|` вместо `\|`) —
  проверить, что число столбцов во всех строках таблицы консистентно;
- cross-vault `obsidian://…file=` использует короткое имя вместо полного basename, либо пробелы
  не закодированы как `%20`.
```

## Source

Source: /Users/paul/Private/Alfa/Projects/standard/stacks@acc9f0ccf3be
Source design context (read-only, do NOT modify): реальные правки, породившие конвенцию —
stacks doc-9, задачи TASK-146 (починка битых ссылок) и TASK-147 (экранирование пайпов в таблицах).

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. `(exists)` пути присутствуют: `CLAUDE.conventions.docs.md` и `SKILL.md` под
   `plugins/ralph/skills/ralph-init/…`.
2. Каждый AC объективно проверяем (grep по файлу / визуальная проверка вставленного блока).
3. Гейт Documentation/Mixed реализуется по УЖЕ существующему в SKILL.md образцу (Step 3.7b/c
   pptx-гейт) — свериться с ним перед написанием нового шага, стиль должен совпасть.
4. Out-of-scope (Code-only, python-конвенции, засев существующих проектов) не затронут.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CLAUDE.conventions.docs.md содержит секцию «Obsidian cross-link convention» с правилами: полный basename + дословный заголовок-якорь, §X.Y не якорь, ссылка на файл целиком для документов без заголовков-пунктов, экранирование \| в ячейках таблиц, cross-vault obsidian:// с %20
- [ ] #2 Создан templates/claude/task-reviewer-rules.docs.md с правилом R-DOCS-1, которое ссылается на конвенцию в CLAUDE.md как на источник истины и не дублирует её текст
- [ ] #3 SKILL.md ralph-init содержит новый шаг записи task-reviewer-rules.docs.md в .claude/task-reviewer-rules.md, гейтированный на тип проекта Documentation/Mixed (Code-only пропускается с печатью [skip])
- [ ] #4 Новый шаг следует существующему образцу гейта Documentation/Mixed (как Step 3.7b/c для pptx-правил); Step 4 file-list обновлён новым файлом
- [ ] #5 Поведение для Code-only проектов не изменено: ни секция конвенции в CLAUDE.md, ни docs-правило ревьюера туда не попадают
<!-- AC:END -->
