---
id: TASK-100
title: fix-task-validator-hook-system-reminder-and-path-tokenization
status: Done
assignee: []
created_date: '2026-05-08 05:04'
updated_date: '2026-05-08 05:21'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Исправить два бага в `.claude/hooks/task-validator.sh`, из-за которых хук отрабатывает корректно, но модель не видит часть его вывода и/или генерирует ложноположительные срабатывания.

## Контекст

Хук `task-validator.sh` запускается как PostToolUse для `backlog task create` и `backlog task edit`. Он проверяет структуру таска по 7 правилам (см. секцию "Deterministic Checks" в хуке) и опционально шлёт LLM-rubric.

В семантике Claude Code PostToolUse:
- stdout без обёртки `<system-reminder>...</system-reminder>` → показывается только в UI пользователя, **не отдаётся модели**
- stdout внутри `<system-reminder>` → отдаётся модели

## Bug 1: Детерминистические сообщения не доходят до модели

**Симптом:** при появлении дубликатов AC, пустых AC, недостающих зависимостей и т.п. хук печатает `Validator [det]: <issue>` обычным `echo`, без обёртки. Пользователь видит сообщение в UI, но модель (которая собирает AC через `backlog task edit --ac ...`) — нет, и продолжает штамповать ошибки.

**Где:** строки 134-138 в `task-validator.sh`:

```bash
if [[ "${RALPH_AUTONOMOUS:-}" \!= "1" ]]; then
  for issue in "${DET_ISSUES[@]+"${DET_ISSUES[@]}"}"; do
    echo "Validator [det]: $issue"
  done
fi
```

**Фикс:** обернуть все `[det]` сообщения в один блок `<system-reminder>`, чтобы модель тоже их получала. Например:

```bash
if [[ "${RALPH_AUTONOMOUS:-}" \!= "1" ]] && [[ ${#DET_ISSUES[@]} -gt 0 ]]; then
  printf '<system-reminder>\n'
  printf 'Task validator [det] issues for TASK-%s:\n' "$TASK_ID"
  for issue in "${DET_ISSUES[@]}"; do
    printf '  - %s\n' "$issue"
  done
  printf '</system-reminder>\n'
fi
```

Поведение в RALPH_AUTONOMOUS=1 (полная тишина) — сохранить.

LLM-rubric блок ниже (строки 250-256) уже корректно обёрнут в `<system-reminder>` — его не трогать.

## Bug 2: Ложные срабатывания на путях с пробелами

**Симптом:** хук жалуется `Validator [det]: Referenced path 'backlog/docs/doc-3' does not exist` хотя реальный путь — `backlog/docs/doc-3 - Core-System-Separation-Variants.md` (с пробелом + вторая часть имени). Хук разрезает путь по пробелам.

**Где:** строки 110-130 в `task-validator.sh`. Конкретно — извлечение и итерация:

```bash
BACKTICK_PATHS=$(echo "$line" | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' || true)
LINK_PATHS=$(echo "$line" | grep -oE '\]\([^)]+\)' | sed 's/^\](//' | sed 's/)$//' || true)

for path in $BACKTICK_PATHS $LINK_PATHS; do
```

Без кавычек `for path in $VAR` делает word-splitting по $IFS — пути с пробелами разваливаются.

**Фикс:** прочитать пути по строкам через `while IFS= read -r path`, объединив оба источника:

```bash
PATHS_TO_CHECK=$(printf '%s\n%s\n' "$BACKTICK_PATHS" "$LINK_PATHS" | sed '/^[[:space:]]*$/d')
while IFS= read -r path; do
  [[ -z "$path" ]] && continue
  # Skip URLs
  echo "$path" | grep -qE '^https?://|^www\.' && continue
  # Skip wildcards/globs
  echo "$path" | grep -qE '[*?]|\.\.\.' && continue
  # Skip non-path-like strings
  if \! echo "$path" | grep -qE '/|\.sh$|\.js$|\.ts$|\.py$|\.md$|\.json$|\.yaml$|\.yml$|\.toml$'; then
    continue
  fi
  if [[ \! -e "$path" ]]; then
    DET_ISSUES+=("Referenced path '$path' does not exist")
  fi
done <<< "$PATHS_TO_CHECK"
```

## Воспроизведение

1. Любой таск в `backlog/tasks/` со ссылкой на путь с пробелами в backtick-span (например, `\`backlog/docs/doc-3 - Core-System-Separation-Variants.md\``) — Bug 2.
2. Дублирующий AC: `backlog task edit <id> --ac "X"` потом ещё раз `backlog task edit <id> --ac "X"` → детектится дубль; в UI юзера видно «Duplicate acceptance criteria detected», но в чате ассистента — нет (Bug 1).

## Валидация

После фикса:
- При `backlog task edit` с дублирующим AC модель видит `<system-reminder>` с `Task validator [det] issues for TASK-N: - Duplicate acceptance criteria detected`.
- При таске с путём содержащим пробелы (`backlog/docs/some - file.md`, реально существующим) хук НЕ выдаёт ошибку «does not exist».
- Ложноположительных срабатываний на других проверках не появилось.
- Поведение в `RALPH_AUTONOMOUS=1` — полная тишина (как было).
- LLM-rubric блок продолжает работать как был.

## Ручной smoke test

```bash
# Прогон хука вручную (минуя backlog) для конкретного task-N:
echo '{"tool_input":{"command":"backlog task edit N --ac test"}}' | bash .claude/hooks/task-validator.sh
```

Должен вернуть либо `<system-reminder>` с issues, либо ничего (если всё ок), плюс LLM-rubric `<system-reminder>` если diff substantive.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Bug 1 исправлен: при дубликатах AC модель получает <system-reminder> с подробностями
- [x] #2 Bug 2 исправлен: пути с пробелами в backtick-spans больше не разваливаются по
- [x] #3 RALPH_AUTONOMOUS=1 → полная тишина (det и LLM nudge оба подавлены), как было
- [x] #4 LLM-rubric блок (строки 250+) не сломан
- [x] #5 Smoke test: echo input | bash .claude/hooks/task-validator.sh выдаёт ожидаемый формат
- [x] #6 Никаких других правил детерм. проверки (1, 2, 3, 5, 6) не сломано — все продолжают работать
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reviewer (Claude, manual triage) confirmed both bugs by reading .claude/hooks/task-validator.sh:
- Bug 1: lines 134-138 emit `Validator [det]: ...` outside any <system-reminder> wrapper. Per Claude Code PostToolUse semantics, plain stdout reaches the user UI but is NOT delivered to the model. Fix as described in the task.
- Bug 2: line 116 `for path in $BACKTICK_PATHS $LINK_PATHS` is unquoted; bash word-splits on $IFS, so a path with spaces (e.g. `backlog/docs/doc-3 - Core-System-Separation-Variants.md`) becomes 3 tokens and the first token fails the existence check. Fix as described in the task.

Refinement notes for the implementer:
- The `while IFS= read -r path` form proposed in the task description is correct AND additionally guards against glob expansion (which the old `for path in $VAR` could trigger if a path contained * or ?). Keep this form.
- After Bug 1 fix, double-check that the LLM-rubric block (lines 250-256) still emits its OWN <system-reminder>. Two separate blocks are fine; do NOT try to merge them into one — the det block fires unconditionally on issues, the rubric block only fires on substantive edits.
- Smoke test in the task uses the literal `task edit N` — replace `N` with an actual task ID that exists in backlog/tasks/ for the smoke run.
- Test BOTH branches of the fix: (a) a task with duplicate AC (synthesizable via `backlog task edit <id> --ac "X"` twice) → must produce a <system-reminder>; (b) a task whose body references a real path with spaces → must NOT produce a "does not exist" issue.

Plan: Fix Bug 1 (lines 134-138) by wrapping det issues in <system-reminder>. Fix Bug 2 (line 116) by replacing unquoted for-loop with while IFS= read -r. Run smoke tests.

Commit: `fef6bff` - task-100: Wrap det issues in <system-reminder> and fix path word-splitting

Commit: `82887f8` - task-100: Apply same fixes to ralph-init template for parity

Both bugs fixed. Reviewer APPROVED after template parity fix. Two commits: fef6bff (hook fix), 82887f8 (template parity).
<!-- SECTION:NOTES:END -->
