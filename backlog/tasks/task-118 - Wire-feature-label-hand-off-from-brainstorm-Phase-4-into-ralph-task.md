---
id: TASK-118
title: Wire feature-label hand-off from brainstorm Phase 4 into ralph-task
status: In Progress
assignee: []
created_date: '2026-05-11 11:05'
updated_date: '2026-05-11 11:14'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Real-session симптом (наблюдён 2026-05-11 в соседнем проекте при использовании ralph-task + brainstorm):

После brainstorm-сессии «Save Design Conclusions» rule корректно записал design-файл в `design/<slug>-brainstorm.md` (Case A). В Phase 4 пользователь выбрал «Create backlog task(s)», и были созданы 2 implementation-таска. **Ни на один из них не был прикручен label `feature:<slug>`**, хотя оба явно принадлежали той же фиче что и только что сохранённый brainstorm.

Последствие: невозможно запустить `/ralph-review feature=<slug>` для cumulative-проверки task ↔ intent — нет lookup-механизма. Пользователю пришлось ретроспективно прикручивать label через `backlog task edit --add-label`.

**Корневая причина — gap в двух местах:**

1. **`skills/ralph-task/SKILL.md` MUST rule 3 (lines 67-73)** говорит: label — `optional / default off`, attach «only when the task is a missed/follow-on item for an existing feature» и «If the user names a feature». В brainstorm-Phase-4-hand-off ни одно условие не срабатывает буквально (task — primary item новой фичи; slug derived из brainstorm-контекста, а не «named» пользователем). Default-off остаётся в силе → label не прикручивается.

2. **`.claude/brainstorm-rules.md` Phase 4 Override (line 65)** говорит «Invoke the `ralph-task` skill with the brainstorm context» — но «brainstorm context» нигде формально не определён и не передаётся как arg. ralph-task узнать slug фактически не может.

## What

Связать оба конца:

### Изменение 1 — `skills/ralph-task/SKILL.md` MUST rule 3

Добавить новую ветку после текущей «(a)/(b)/(c)» развилки:

```markdown
3. **MUST: `feature:<slug>` label is optional.** Default off. Attach `-l "feature:<name>"` only when the task is a missed/follow-on item for an existing feature. If the user names a feature, **verify** that one of the design docs exists before attaching the label:

   ```bash
   ls design/<name>-prd.md design/<name>-brainstorm.md 2>/dev/null
   ```

   If neither exists, warn the user and ask whether to (a) skip the label, (b) create the design doc first via `ralph-prd`, or (c) attach anyway as a stub.

   **Brainstorm Phase 4 hand-off (default ON):** If the skill is invoked with `feature=<slug>` arg, attach `-l "feature:<slug>"` automatically to every created task in this invocation. Skip the verify-prompt — the brainstorm-rules «Save Design Conclusions» rule already verified the design file exists before the Phase 4 hand-off. Treat the slug as authoritative; do NOT re-run the `ls design/<slug>-*` check.
```

### Изменение 2 — `.claude/brainstorm-rules.md` Phase 4 Override (line 65)

Изменить с:

```markdown
- **Create backlog task(s)** — Invoke the `ralph-task` skill with the brainstorm context (selected approach, design decisions, acceptance criteria, testing strategy) sufficient for autonomous execution in a Ralph loop without human guidance. If the scope is PRD-shaped (≥3 user stories, multiple lanes), `ralph-task`'s pre-check will redirect to `ralph-prd` → `ralph-backlog`.
```

На:

```markdown
- **Create backlog task(s)** — Invoke the `ralph-task` skill with `feature=<slug>` (where `<slug>` matches the design-file slug saved in Phase 3 — e.g., `feature=auth-token-rotation` for `design/auth-token-rotation-brainstorm.md`) plus the brainstorm context (selected approach, design decisions, acceptance criteria, testing strategy) sufficient for autonomous execution in a Ralph loop without human guidance. Passing the slug enables ralph-task to auto-attach `feature:<slug>` label to every created task — required for downstream `/ralph-review feature=<slug>` cumulative consistency checks. If the scope is PRD-shaped (≥3 user stories, multiple lanes), `ralph-task`'s pre-check will redirect to `ralph-prd` → `ralph-backlog`.
```

### Что НЕ трогаем

- Никаких изменений в логике trigger-conditions ralph-task (English/Russian phrases по которым активируется skill — не меняем)
- Никаких изменений в самой 6-rule decomposition heuristic
- Никаких изменений в Save Design Conclusions rule (он сейчас корректный, проблема только в передаче slug DOWNSTREAM в ralph-task)
- Сохранять обратную совместимость: если `feature=<slug>` arg НЕ передан (не из brainstorm flow), поведение MUST rule 3 не меняется (default-off + verify-prompt)

## Источники

- `.claude/brainstorm-rules.md` line 65 — Phase 4 Override строчка для замены
- `skills/ralph-task/SKILL.md` lines 67-73 — MUST rule 3 для расширения
- Real-session симптом 2026-05-11 — приведён в Why-блоке
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 В skills/ralph-task/SKILL.md MUST rule 3 содержит явную подсекцию или абзац «Brainstorm Phase 4 hand-off (default ON)», описывающую поведение при наличии feature=<slug> arg: attach label automatically + skip verify-prompt
- [x] #2 В skills/ralph-task/SKILL.md новый текст явно ссылается на «Save Design Conclusions» правило из brainstorm-rules как justification пропуска verify-step
- [x] #3 В .claude/brainstorm-rules.md Phase 4 Override (line ~65) обновлён: явно требует передачу feature=<slug> при invocation ralph-task; даёт пример сопоставления slug ↔ design-file
- [x] #4 В .claude/brainstorm-rules.md обновлённая Phase 4 Override явно упоминает downstream-цель — поддержку /ralph-review feature=<slug> для cumulative consistency check
- [x] #5 Обратная совместимость: вызов ralph-task без feature=<slug> arg сохраняет существующее поведение default-off + verify-prompt (a/b/c); это видно из формулировки в SKILL.md
- [x] #6 Diff содержит ровно 2 файла (исключая task-файл): skills/ralph-task/SKILL.md и .claude/brainstorm-rules.md
- [ ] #7 task-reviewer agent APPROVED перед мержем
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Update skills/ralph-task/SKILL.md MUST rule 3 to add 'Brainstorm Phase 4 hand-off (default ON)' subsection that references the Save Design Conclusions rule as justification for skipping verify-prompt. 2) Update .claude/brainstorm-rules.md Phase 4 Override line 65 to require feature=<slug> arg with example slug↔file mapping and downstream /ralph-review feature=<slug> mention. 3) Preserve backwards compat: no feature= arg → existing default-off + verify-prompt behavior unchanged. 4) Diff = exactly 2 files (excl task file). 5) Spawn task-reviewer.
<!-- SECTION:NOTES:END -->
