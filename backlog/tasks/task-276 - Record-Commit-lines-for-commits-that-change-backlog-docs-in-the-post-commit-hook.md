---
id: TASK-276
title: >-
  Record Commit lines for commits that change backlog docs in the post-commit
  hook
status: Done
assignee: []
created_date: '2026-10-08 06:10'
updated_date: '2026-10-10 07:19'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Шаблон git-хука post-commit пропускает любой коммит, в котором меняются только файлы под backlog/, чтобы не засорять задачи коммитами вида «отметил AC». В проектах-документациях, созданных ralph-init, рабочий результат задачи лежит в backlog/docs/ (backlog doc), поэтому все содержательные коммиты задачи тоже попадают под пропуск: в файл задачи не пишется ни одной строки Commit, и /ralph-review останавливается с «BLOCKED: No Commit: hashes found in task files». Воспроизведено в проекте-источнике: восемь коммитов task-1 и task-2 меняли только backlog/docs/doc-1 и backlog/tasks/*, строк Commit нет ни одной; коммит task-4, менявший .gitignore, строку записал. Пропуск должен касаться только служебных коммитов файлов задач.

## Scope

In scope:
- Сузить условие пропуска в шаблоне хука: пропускать коммит, только если все изменённые пути лежат под backlog/tasks/ (по решению исполнителя также backlog/archive/ и backlog/completed/ — это тоже перемещения файлов задач). Изменения backlog/docs/, backlog/decisions/, backlog/drafts/ и любые пути вне backlog/ должны давать строку Commit.
- Обновить комментарий в начале хука под новое условие.
- Добавить bats-тест поведения хука.
- Обновить живой .git/hooks/post-commit этого репозитория, чтобы проходила проверка паритета R11.
- Поднять версию плагина по принятой в репозитории схеме, чтобы изменение шаблона дошло до установленных копий; существующие проекты получат хук через ralph-init upgrade (managed-file-drift покажет его как outdated).

Out of scope:
- Изменения /ralph-review (например, вывод базы diff из истории, когда строк Commit нет) — отдельная задача при необходимости.
- Логика amend и формат строки Commit — без изменений.
- Хуки pre-commit и commit-msg.

## Files

- plugins/ralph/skills/ralph-init/templates/git-hooks/post-commit (exists) — условие пропуска и комментарий.
- .git/hooks/post-commit (exists, не трекается) — живая копия для R11.
- tests/unit/post-commit-hook.bats (to-create) — тест поведения по образцу commit-msg-hook.bats и pre-commit-hook.bats.
- tests/unit/template-parity.bats (exists) — проверка паритета, менять не требуется.
- plugins/ralph/.claude-plugin/plugin.json (exists) — версия, сейчас 0.14.2.

Текущее условие пропуска в шаблоне:

```bash
# Skip if only backlog files changed (avoid noise on task-only commits)
CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD)
if echo "$CHANGED_FILES" | grep -qE '^backlog/'; then
    if ! echo "$CHANGED_FILES" | grep -qvE '^backlog/'; then
        exit 0
    fi
fi
```

## Source

Source: /Users/paul/Private/Alfa/Projects/af_comm@2a1ae98dc820-dirty
Source design doc (read-only context, do NOT modify): /Users/paul/Private/Alfa/Projects/af_comm/design/partner-auth-analysis-review-2026-10-07.md

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All (exists) file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Шаблон plugins/ralph/skills/ralph-init/templates/git-hooks/post-commit пропускает коммит, только если все изменённые пути лежат под backlog/tasks/ (допустимо также backlog/archive/ и backlog/completed/)
- [x] #2 Новый тест tests/unit/post-commit-hook.bats во временном репозитории на ветке task-1 проверяет: коммит только backlog/tasks/ — строки Commit нет; коммит backlog/docs/ вместе с backlog/tasks/ — строка Commit есть; коммит файла вне backlog/ — строка Commit есть
- [x] #3 Живой .git/hooks/post-commit обновлён, и bats tests/unit/template-parity.bats проходит
- [x] #4 Версия плагина в plugins/ralph/.claude-plugin/plugin.json поднята по принятой схеме, bats tests/unit/version-bump-guard.bats проходит
- [x] #5 uv run pytest и uv run ruff check . проходят
- [x] #6 На хосте macOS: uv run pytest tests/python/test_bash32_syntax.py проходит без skip (/bin/bash 3.2), и LC_ALL=C node_modules/.bin/bats tests/unit/post-commit-hook.bats проходит с /usr/bin первым в PATH (BSD grep/sed/awk); вывод записан в заметки задачи
- [x] #7 Строка .git/hooks/post-commit в .claude/managed-file-drift.accept пересоздана командой bash plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh accept . .git/hooks/post-commit, и на хосте macOS bash plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh check . завершается с кодом 0 без вывода; вывод записан в заметки задачи
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Handoff gate (destination): yellow, clarified with the user. Y1 — TASK-275's .claude/managed-file-drift.accept pins the hashes of both the template and the live .git/hooks/post-commit; this task changes both, so the acceptance line must be regenerated or the drift warning returns (new AC). Y2 — tests/python/test_bash32_syntax.py skips without /bin/bash 3.2, so in the Linux devcontainer AC #4 would pass vacuously; the bash 3.2 / BSD half is now a macOS-host AC, deferred to the host after the Ralph run (as in TASK-270..275). In the container, managed-file-drift.sh check . also reports .claude/settings.local.json (virtiofs mount, see TASK-275 notes) — the exit-0 check is host-only.

Plan: narrow the post-commit skip to commits whose changed paths all match ^backlog/(tasks|archive|completed)/ (diff-tree with core.quotepath=off so Cyrillic task filenames are not octal-quoted); same edit in live .git/hooks/post-commit; new tests/unit/post-commit-hook.bats (temp repo, task-1 branch, stub backlog on PATH); regenerate the .git/hooks/post-commit accept line; bump version via bump-version.sh --auto. Host-only AC #6/#7 deferred.

Commit: `ae55935` - task-276: record Commit lines for commits that change backlog docs; skip only task-file commits

Commit: `7f88197` - task-276: bump plugin version to 0.14.3 (patch)

Gates (container): ruff clean; pytest 900 passed, 3 skipped, 1 failed — test_shared_plugin_registries_hold_no_container_rooted_path fails because the shared /Users/paul/.claude/plugins/known_marketplaces.json currently records /home/node paths (machine state, independent of this diff). LC_ALL=C bats tests/unit in a clean detached worktree of task-276: 1..160, no 'not ok' (in /workspace only R11 settings.local.json fails — the known container virtiofs mount baseline, TASK-275). post-commit-hook.bats against the master hook: 3/6 fail (non-ASCII task file, docs+tasks, docs-only), against the new hook 6/6 pass. Hook also reads diff-tree with core.quotepath=off: without it a non-ASCII task filename is octal-quoted, does not match ^backlog/, and the task-only commit was recorded. Accept line for .git/hooks/post-commit regenerated via managed-file-drift.sh accept (container sha256sum); container check . now prints only the .claude/settings.local.json baseline line. Version bumped to 0.14.3 via bump-version.sh --auto. Host commands for AC #6/#7: PATH=/usr/bin:/bin:$PATH uv run pytest tests/python/test_bash32_syntax.py ; PATH=/usr/bin:/bin:$PATH LC_ALL=C node_modules/.bin/bats tests/unit/post-commit-hook.bats ; bash plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh check . ; echo rc=$?

Review 1 (task-reviewer): APPROVED, 0 blocking / 0 minor. Left In Progress and unmerged on task-276: Done and merge wait for the AC #6 and AC #7 macOS host runs (commands above).

AC #6 host (macOS): PATH=/usr/bin:/bin:$PATH gives bash=/bin/bash 3.2.57(1)-release and grep/sed/awk from /usr/bin. uv run pytest -v tests/python/test_bash32_syntax.py: 2 passed, none skipped. LC_ALL=C bats tests/unit/post-commit-hook.bats: 1..6, ok 1-6 (tasks-only, non-ASCII task file and archive-only commits record no Commit line; docs+tasks, docs-only and outside-backlog commits record one). AC #7 host: bash plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh check . -> exit 0, no output; the committed .git/hooks/post-commit accept line equals the accept subcommand's output (template=aa7b7918..., project=e7bc0dc3...). Host gates: ruff clean; LC_ALL=C bats tests/unit 160 ok, 0 not ok; uv run pytest first run 899 passed, 1 failed — test_shared_plugin_registries_hold_no_container_rooted_path, because the host's ~/.claude/plugins/known_marketplaces.json held 11 /home/node installLocations (written at 06:21Z, before this run, by the claude-skills devcontainer, which still runs with CLAUDE_CONFIG_DIR=/home/node/.claude; the test file is untouched by this diff). With the user's approval the registry was repaired per ralph-init SKILL.md (every /home/node/.claude/ prefix rewritten to /Users/paul/.claude/, backup at ~/.claude/plugins/known_marketplaces.json.bak-20261010, all install locations exist); re-run: uv run pytest 900 passed, 4 skipped.
<!-- SECTION:NOTES:END -->
