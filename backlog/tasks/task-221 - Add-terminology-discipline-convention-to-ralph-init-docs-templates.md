---
id: TASK-221
title: Add terminology-discipline convention to ralph-init docs templates
status: Done
assignee: []
created_date: '2026-08-06 17:28'
updated_date: '2026-08-09 10:48'
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
- [x] #1 CLAUDE.conventions.docs.md содержит подсекцию «### Terminology discipline» после блока ### Code Style, с пунктами: не транслитерировать, не выдумывать термины/кальки, вводить жаргон определением при первом употреблении, проектный keep-list, равнение на словарь домена, убирать commit-SHA из прозы (grep находит заголовок и пункты).
- [x] #2 task-reviewer-rules.docs.md содержит правило R-DOCS-2 «Terminology discipline», которое ссылается на секцию CLAUDE.md как источник истины и не дублирует её текст.
- [x] #3 R-DOCS-2 перечисляет условия CHANGES REQUESTED (транслитерация, выдуманные термины/кальки, жаргон без определения, необъяснённый латинский тех-термин, commit-SHA в прозе) и явно не флагует keep-list термины.
- [x] #4 Новый reviewer-шаблон НЕ создаётся и новый шаг ralph-init НЕ добавляется этой задачей (владение TASK-220); задача только дописывает в существующие после TASK-220 файлы.
- [x] #5 Code-only поведение и CLAUDE.conventions.python.md не изменены.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
LANGUAGE RECONCILIATION (owner decision 2026-08-09): land this task in ENGLISH. The template CLAUDE.conventions.docs.md and task-reviewer-rules.docs.md are English-only. The two Russian code blocks in the description ("Convention text" and "Reviewer rule text") are SUPERSEDED — insert the English versions below VERBATIM instead. Section headings and rule IDs are unchanged. Everything else in the description (Why / Scope / Files / Before-starting / ACs) still applies as guidance. This convention is language-INDEPENDENT: it governs discipline in whatever "working language" a docs project uses; the English text keeps that generality.

=== Convention text — insert verbatim into CLAUDE.conventions.docs.md after the "### Code Style" block (next to the Obsidian section from TASK-220) ===

### Terminology discipline

The documents in this project (and your own answers) are written in the project's working language — plainly and consistently. Headings are in English (naming-guard); everything else is prose in the working language. Apply this proactively, without waiting for review comments; proofread YOUR OWN wording before submitting.

- **Do not transliterate foreign technical terms** into the working language's alphabet where a plain or established term exists. Take the replacement from the canon/domain — do not invent one.
- **Do not invent terms, metaphors, or calques.** If the canon already named a thing, use that name.
- **Introduce jargon with a definition on first use**, then use it consistently. Jargon thrown straight into use without a definition is a defect.
- **Keep a project keep-list** of established domain/canonical terms that must NOT be rewritten; extend it per project.
- **Follow the vocabulary of the referenced project/domain** — do not \"fix\" an established term to your taste.
- **Remove commit SHAs from prose**; references to task IDs (e.g. TASK-N) are fine (provenance).

=== Reviewer rule text — append to task-reviewer-rules.docs.md after R-DOCS-1 ===

## R-DOCS-2: Terminology discipline

Apply to any `.md` change that adds or edits prose in the project's working language. The source of truth is the \"Terminology discipline\" section in CLAUDE.md (do NOT duplicate it here). Return CHANGES REQUESTED if the change introduces:

- transliteration of a foreign word into the working language's alphabet where a plain/established term exists;
- an invented term, metaphor, or calque absent from the canon;
- jargon without a definition on first use;
- an unexplained Latin-script technical term in working-language prose (no definition/phrasing);
- a specific commit SHA in prose (references to task IDs are allowed).

Do NOT flag the project's keep-list terms — they are canon.

Plan: (1) Append '### Terminology discipline' subsection to templates/root/CLAUDE.conventions.docs.md after the Obsidian section (itself after ### Code Style), using the ENGLISH verbatim text from Implementation Notes with PLAIN double quotes (the \" in the notes is a shell-escaping artifact; sibling R-DOCS-1 uses plain quotes). (2) Append 'R-DOCS-2: Terminology discipline' to templates/claude/task-reviewer-rules.docs.md after R-DOCS-1, referencing the CLAUDE.md section as source of truth. (3) No hard-wrap (verbatim; matches TASK-220 long-line style). (4) Do NOT touch python conventions, do NOT create new template or ralph-init step. (5) Lint (ruff) + pytest, check ACs, task-reviewer, bump-version --auto (files are shipped plugins/ralph/skills/**), merge --no-ff.

Commit: `96668a8` - task-221: seed terminology-discipline convention + R-DOCS-2 in ralph-init docs templates

Done: Appended '### Terminology discipline' to templates/root/CLAUDE.conventions.docs.md (after ### Code Style, grouped next to the TASK-220 Obsidian section) and 'R-DOCS-2: Terminology discipline' to templates/claude/task-reviewer-rules.docs.md (after R-DOCS-1). Landed in ENGLISH per the owner LANGUAGE RECONCILIATION note; inserted text is byte-verbatim except the shell-escaping \" was rendered as plain " (matches sibling R-DOCS-1). No hard-wrap (matches TASK-220 long-line style). R-DOCS-2 points to the CLAUDE.md section as source of truth, does not duplicate it. Gates: ruff clean, pytest 346 passed. task-reviewer: APPROVED. Files are shipped plugins/ralph/skills/** -> version bump via bump-version.sh --auto at merge.

Commit: `5cbb683` - task-221: bump plugin version to 0.3.1 (patch)
<!-- SECTION:NOTES:END -->
