---
id: TASK-269
title: >-
  Stop managed-file-drift reporting permanent drift on files the upgrade itself
  mutates
status: Done
assignee: []
created_date: '2026-10-05 16:20'
updated_date: '2026-10-05 16:48'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Апгрейд ralph-init сам делает управляемый файл отличным от шаблона, а таблица состояния сверяет его с шаблоном побайтово. В результате проект, прошедший апгрейд строго по инструкции, навсегда числится отставшим, и предупреждение о дрейфе в preflight Ralph перестаёт быть сигналом — оно становится постоянным шумом, который оператор учится игнорировать. Обнаружено на живом документационном проекте при апгрейде на плагин 0.11.0.

Случай первый, самопротиворечие внутри SKILL.md. Шаг U4 для документационных и смешанных проектов предписывает после перезаписи settings.local.json домешать обратно два правила pptx, дословно: «If the project is Documentation or Mixed (detect via existing .obsidian/ directory), run the Step 3.7b pptx merge so the overwrite does not strip the Bash(python scripts/office/soffice.py:*) and Bash(pdftoppm:*) rules». При этом шаг U2 требует для того же файла «exact content match against templates/claude/settings.local.json», и managed-file-drift.sh реализует это как cmp -s. Итог: сразу после корректного апгрейда файл помечается outdated, и так на каждом последующем запуске.

Случай второй, та же природа. Шаблон devcontainer.json не предусматривает проектных добавок в массив runArgs. Проект-источник держит там --shm-size=1g, добавленную по замеру: без неё drawio-headless внутри контейнера падает на дефолтном /dev/shm в 64 МБ с «Empty export data» и крахом GPU-процесса, а --disable-dev-shm-usage не помогает, потому что drawio не передаёт флаг в Chromium. Строка несущая, снять её нельзя, и файл поэтому тоже навсегда outdated.

Решение не предписывается — выбор за этим проектом. Возможные направления: сверять settings.local.json на вхождение правил шаблона, а не на побайтовое равенство; либо внести правила pptx в шаблон безусловно; либо дать проектам объявляемый список осознанных отклонений, который читает managed-file-drift.sh. Для runArgs допустимо и честное решение «так и должно быть», но тогда это обязано быть явно написано в SKILL.md, а не выясняться оператором из чтения скрипта.

## Scope

In scope:
- Устранить самопротиворечие между U2 и U4 по settings.local.json так, чтобы корректно обновлённый документационный проект не числился отставшим.
- Определить и задокументировать, что происходит с проектной добавкой в runArgs devcontainer.json.
- Покрыть оба случая тестами в tests/python/.

Out of scope:
- Любые изменения в проекте-источнике.
- Прочие управляемые файлы, по которым противоречия нет.
- Пересмотр состава правил в шаблоне settings.local.json как таковой.

## Files

- `plugins/ralph/skills/ralph-init/SKILL.md` (exists) — разделы U2 и U4, таблица состояния и шаг слияния правил pptx.
- `plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh` (exists) — строка 49 задаёт режим сверки exact для settings.local.json, сравнение выполняется через cmp -s.
- `plugins/ralph/skills/ralph-init/templates/claude/settings.local.json` (exists) — шаблон без правил pptx.
- `plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json` (exists) — массив runArgs без механизма проектных добавок.
- `tests/python/test_managed_file_drift.py` (exists) — здесь закрепляется список управляемых файлов и их режимы сверки.

## Source

Source: /Users/paul/Private/Alfa/Projects/equation/services@0ebf9b4aadc6

Смежное: TASK-131 в этом проекте добавила слияние правил pptx и закрыта на 3 критерия из 4.

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Документационный проект, обновлённый по шагу U4 вместе со слиянием правил pptx, не сообщается скриптом managed-file-drift.sh как отставший по .claude/settings.local.json
- [x] #2 Тест в tests/python/ воспроизводит этот случай: фикстура с правилами pptx в settings.local.json не помечается отставшей
- [x] #3 Разделы U2 и U4 в SKILL.md согласованы по settings.local.json: ни один из них больше не требует условия, которое нарушает другой
- [x] #4 В SKILL.md явным абзацем описано: апгрейд сохраняет проектные добавки в массиве runArgs файла devcontainer.json, а managed-file-drift.sh считает такой файл актуальным, пока в нём есть все элементы runArgs шаблона
- [x] #5 Шаг U4 при перезаписи devcontainer.json сохраняет проектные элементы runArgs: тест в tests/python/ на фикстуре с --shm-size=1g подтверждает, что после апгрейда элемент на месте, а managed-file-drift.sh не помечает файл отставшим
- [x] #6 Сверка по вхождению по-прежнему ловит настоящий дрейф: тест в tests/python/ подтверждает, что settings.local.json без одного из правил шаблона и devcontainer.json без одного из элементов runArgs шаблона помечаются отставшими, а отличие в любом другом поле этих файлов — тоже
- [x] #7 uv run pytest проходит и LC_ALL=C node_modules/.bin/bats tests/unit проходит
- [x] #8 uv run ruff check . проходит
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Приёмка хендоффа (2026-10-05): жёлтый, уточнён пользователем. Все пути (exists) на месте; оба утверждения подтверждены: SKILL.md:684 (U4 перезаписывает settings.local.json и домешивает правила pptx) против SKILL.md:615 и managed-file-drift.sh:49/69 (exact, cmp -s). Дополнительно найдено: SKILL.md:697 — U4 перезаписывает devcontainer.json целиком, поэтому принятый апгрейд удаляет несущий --shm-size=1g и ломает экспорт drawio в проекте-источнике; вариант «только задокументировать» был бы документированием разрушительного шага.

Решения пользователя:
1. settings.local.json — сверка по вхождению: отставшим файл считается, только если в нём нет какого-либо правила шаблона; проектные добавки в permissions.allow (в том числе правила pptx) допустимы. Шаблон не меняется — это соответствует Out of scope. Вариант «внести правила pptx в шаблон» отклонён как противоречащий Out of scope.
2. devcontainer.json — сохранять и сверять по вхождению: U4 сохраняет проектные элементы runArgs при перезаписи, а сверка считает файл актуальным, пока в нём есть все элементы runArgs шаблона. AC про тест runArgs стал безусловным.

Инвариант для реализации: ослабляется только то, что названо, — добавочные правила permissions.allow и добавочные элементы runArgs. Всё остальное в обоих файлах сверяется точно, иначе сверка по вхождению перестанет ловить настоящий дрейф (на это отдельный AC). jq уже используется ralph-init в U4, новая зависимость не нужна.

Ограничение исполнения: новый bash-код обязан разбираться системным /bin/bash 3.2 (R-INFRA-3). В Linux-контейнере тест tests/python/test_bash32_syntax.py пропускается, поэтому после прогона Ralph его нужно выполнить на macOS-хосте до Done.

Plan: settings.local.json → rule 'allow' in managed-file-drift.sh (jq: everything but permissions.allow JSON-equal, template rules ⊆ project rules; no jq → exact). devcontainer.json → rule 'runargs': new scripts/merge-runargs.sh prints template with the project's extra single-line runArgs elements appended; U4 writes that output, drift calls the file current iff it equals it. SKILL.md U2 items 9/10 + U4 bullets + explicit runArgs paragraph. Tests in tests/python/test_managed_file_drift.py.

Commit: `c2db73e` - task-269: compare settings.local.json allow rules and devcontainer.json runArgs by containment

Commit: `c59b021` - task-269: document that the runArgs merge keeps elements a newer template dropped

Done. New scripts/merge-runargs.sh (template + project's extra single-line runArgs elements); managed-file-drift.sh rules 'allow' (jq containment of permissions.allow, rest JSON-equal, exact fallback without jq) and 'runargs' (byte-equal to merge-runargs.sh output). SKILL.md U2 items 9/10, U4 settings.local.json + devcontainer.json bullets, explicit 'Project runArgs' paragraph incl. limitation that template-dropped elements survive as extras (reviewer minor). Gates: ruff clean; pytest 807 passed/3 skipped; bats 147/148 — test 134 (R11 settings.local.json shape) fails identically on master in the container because the live file is masked by the container overlay; passes in a clean worktree per reviewer. Bash 3.2: ran with a real bash 3.2.57 build (/tmp/bash32) instead of the macOS host — test_bash32_syntax.py with BASH32_SYNTAX_SHELL=/tmp/bash32: 2 passed; test_managed_file_drift.py with bash 3.2 as PATH bash: 41 passed. task-reviewer: APPROVED (score 8).

Commit: `12736d5` - task-269: bump plugin version to 0.13.0 (minor)
<!-- SECTION:NOTES:END -->
