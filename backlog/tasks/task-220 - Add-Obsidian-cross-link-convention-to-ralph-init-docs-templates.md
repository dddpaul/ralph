---
id: TASK-220
title: Add Obsidian cross-link convention to ralph-init docs templates
status: Done
assignee: []
created_date: '2026-08-04 13:06'
updated_date: '2026-08-09 10:38'
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
- [x] #1 CLAUDE.conventions.docs.md содержит секцию «Obsidian cross-link convention» с правилами: полный basename + дословный заголовок-якорь, §X.Y не якорь, ссылка на файл целиком для документов без заголовков-пунктов, экранирование \| в ячейках таблиц, cross-vault obsidian:// с %20
- [x] #2 Создан templates/claude/task-reviewer-rules.docs.md с правилом R-DOCS-1, которое ссылается на конвенцию в CLAUDE.md как на источник истины и не дублирует её текст
- [x] #3 SKILL.md ralph-init содержит новый шаг записи task-reviewer-rules.docs.md в .claude/task-reviewer-rules.md, гейтированный на тип проекта Documentation/Mixed (Code-only пропускается с печатью [skip])
- [x] #4 Новый шаг следует существующему образцу гейта Documentation/Mixed (как Step 3.7b/c для pptx-правил); Step 4 file-list обновлён новым файлом
- [x] #5 Поведение для Code-only проектов не изменено: ни секция конвенции в CLAUDE.md, ни docs-правило ревьюера туда не попадают
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
LANGUAGE RECONCILIATION (owner decision 2026-08-09): land this task in ENGLISH. The template CLAUDE.conventions.docs.md and the new task-reviewer-rules.docs.md are English-only. The two Russian code blocks in the description ("Convention text" and "Reviewer rule text") are SUPERSEDED — insert the English versions below VERBATIM instead. Section headings and rule IDs are unchanged. Everything else in the description (Why / Scope / Files / Before-starting / ACs) still applies as guidance.

=== Convention text — insert verbatim into CLAUDE.conventions.docs.md after the "### Code Style" block ===

### Obsidian cross-link convention

The documents in this project live in an Obsidian vault. Links between them must resolve — otherwise clicking a link makes Obsidian create empty stub notes.

- **Link to a canonical document:** `[[<full-basename-without-.md>#<verbatim-heading>|<short display>]]`. The filename is the FULL basename (`doc-2 - Architecture-layers-and-system-classes`), not `doc-2`. `§X.Y` is NOT an anchor; the anchor is the exact section-heading text (`#1.3. Cross-product services`).
- **Documents without item-headings** (e.g. the TERMS glossary) — link to the whole file: `[[TERMS|TERMS #14]]`. Jumping to a specific item is impossible if it has no heading.
- **Inside markdown table cells** the display-alias pipe MUST be escaped: `[[…\|display]]`. An unescaped `|` is read by the table as a column separator and breaks the markup. In prose (outside tables) no escaping is needed.
- **Link into an adjacent vault (cross-vault):** `obsidian://open?vault=<vault>&file=<full-basename>`; encode spaces in the filename as `%20`.

=== Reviewer rule text — full contents of the new templates/claude/task-reviewer-rules.docs.md ===

# Task reviewer rules (Documentation projects)

## R-DOCS-1: Obsidian cross-link convention

Apply to any `.md` change that adds or edits `[[…]]` wiki-links or `obsidian://` URIs. The source of truth for the format is the "Obsidian cross-link convention" section in CLAUDE.md (do NOT duplicate it here). Return CHANGES REQUESTED if:

- a wiki-link to a canonical doc uses a short name (`[[doc-2 …]]`) instead of the full basename, or `§X.Y` as an anchor instead of the verbatim section heading;
- inside a markdown table cell the wiki-link's display pipe is NOT escaped (`|` instead of `\|`) — check that the column count is consistent across all rows of the table;
- a cross-vault `obsidian://…file=` uses a short name instead of the full basename, or spaces are not encoded as `%20`.

RALPH-INIT UPGRADE PARITY (this repo's standing rule): ralph-init changes must update BOTH the Init flow (Step 3.x) AND Upgrade Mode (U1–U5), because existing projects only receive template changes via `ralph-init upgrade`. This task's ACs cover only the init-time gated write step + Step 4 file-list. When implementing, also add the matching Documentation/Mixed-gated Upgrade-Mode step so existing docs/mixed projects get `.claude/task-reviewer-rules.md` (from task-reviewer-rules.docs.md) on upgrade — mirroring how the pptx-gate is handled in both flows. If that meaningfully exceeds this task's scope, note it and the reviewer/owner can spin a follow-up; do not silently ship an init-only change.

Plan (impl 2026-08-09, English per owner reconciliation): (1) AC#1 insert '### Obsidian cross-link convention' verbatim into CLAUDE.conventions.docs.md after '### Code Style'. (2) AC#2 create templates/claude/task-reviewer-rules.docs.md with R-DOCS-1 (references CLAUDE.md as source of truth, no duplication). (3) AC#3/#4 add SKILL.md Step 3.7c (Documentation/Mixed-gated write of task-reviewer-rules.docs.md -> .claude/task-reviewer-rules.md; Code-only prints [skip], modeled on 3.7b); update Step 4 file-list. (4) UPGRADE PARITY (standing rule): add .claude/task-reviewer-rules.md to U2 table + U4 apply as create-if-missing for docs/mixed (detected via .obsidian/); NEVER clobber an existing project-owned file (this repo's own R1-R11 rules show why); Code-only skipped. Update U3/U5 example tables. (5) AC#5 Code-only untouched by construction. Then bump plugin version (both manifests), task-reviewer review, Done, merge, tag.

Commit: `cc41735` - task-220: seed Obsidian cross-link convention + docs reviewer rule in ralph-init templates

DONE 2026-08-09 (English per owner reconciliation). Implemented: AC#1 Obsidian cross-link convention section appended to CLAUDE.conventions.docs.md after Code Style (verbatim); AC#2 new templates/claude/task-reviewer-rules.docs.md with R-DOCS-1 (points at CLAUDE.md section as source of truth, no duplication); AC#3/#4 SKILL.md Step 3.7c (Documentation/Mixed-gated write to .claude/task-reviewer-rules.md, Code-only prints [skip] 3.7c, modeled byte-for-byte on 3.7b gate) + Step 4 file-list line; AC#5 Code-only untouched by construction. UPGRADE PARITY (standing rule): added U2 item 15 + U4 apply logic as CREATE-IF-MISSING (never overwrite an existing project-owned rules file; detect docs/mixed via .obsidian/), plus U3/U5 example rows. Gate: uv run ruff check . clean; uv run pytest 346 passed. Review: task-reviewer APPROVED on git diff master..HEAD (HEAD cc41735). Key decision: upgrade uses create-if-missing (not overwrite) because a project may hold its own reviewer rules (this repo's own R1-R16 is the exemplar). R11 reconciliation: the new docs template has no live<->template pair, so R11 parity is NOT triggered (carve-out forbids mirroring THIS repo's live rules, which is unchanged). NOTE for owner: R11 line-117 / R16 line-207 descriptive prose says task-reviewer-rules.md is written from scratch or starts empty; docs/mixed bootstraps now seed R-DOCS-1. The normative parity-exclusion is unaffected; refining that descriptive sentence would require a separate approved rules-file task per R13 (not done here).

Commit: `800e6a3` - task-220: bump plugin version to 0.3.0 (minor)
<!-- SECTION:NOTES:END -->
