#!/bin/bash
# PostToolUse hook: validates backlog tasks after edit/create
# Runs deterministic structural checks and optionally emits an LLM nudge.

set -uo pipefail

# Read tool input from stdin (JSON)
INPUT=$(cat)

# Extract the command that was run
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only process backlog task edit/create commands
if ! echo "$CMD" | grep -qE '^backlog task (edit|create)\b'; then
  exit 0
fi

# Extract task ID from command
TASK_ID=$(echo "$CMD" | grep -oE '\btask (edit|create)[[:space:]]+([0-9]+)' | grep -oE '[0-9]+$')
if [[ -z "$TASK_ID" ]]; then
  exit 0
fi

# Find the task file
TASK_FILE=$(find backlog/tasks -maxdepth 1 -name "task-${TASK_ID} -*" -o -name "task-${TASK_ID}-*" 2>/dev/null | head -1)
if [[ -z "$TASK_FILE" ]] || [[ ! -f "$TASK_FILE" ]]; then
  exit 0
fi

# === Deterministic Checks ===
DET_ISSUES=()

# Read task file content
TASK_CONTENT=$(<"$TASK_FILE")

# 1. Description body is non-empty after stripping frontmatter and title heading
DESC_SECTION=$(echo "$TASK_CONTENT" | sed -n '/<!-- SECTION:description -->/,/<!-- SECTION:/p' | sed '1d;$d')
if [[ -z "$DESC_SECTION" ]]; then
  DESC_SECTION=$(echo "$TASK_CONTENT" | sed -n '/^## Description/,/^## /p' | sed '1d;$d' | sed '/^$/d')
fi
if [[ -z "$(echo "$DESC_SECTION" | sed '/^[[:space:]]*$/d')" ]]; then
  DET_ISSUES+=("Description body is empty")
fi

# 2. At least one acceptance criterion present
AC_LINES=$(echo "$TASK_CONTENT" | grep -E '^\s*- \[(x| )\]' || true)
AC_COUNT=$(echo "$AC_LINES" | grep -c '.' 2>/dev/null || echo "0")
if [[ "$AC_COUNT" -eq 0 ]]; then
  DET_ISSUES+=("No acceptance criteria defined")
fi

# 3. No empty AC line ('- [ ]' or '- [x]' with no content after checkbox)
if echo "$AC_LINES" | grep -qE '^\s*- \[(x| )\]\s*$'; then
  DET_ISSUES+=("Empty acceptance criterion line (checkbox with no text)")
fi

# 4. No identical AC strings after normalization
if [[ "$AC_COUNT" -gt 1 ]]; then
  NORMALIZED_ACS=$(echo "$AC_LINES" | sed 's/^\s*- \[(x| )\]\s*//' | sed 's/^#[0-9]* //' | tr '[:upper:]' '[:lower:]' | sed 's/[[:space:]]\+/ /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  UNIQUE_COUNT=$(echo "$NORMALIZED_ACS" | sort -u | grep -c '.' 2>/dev/null || echo "0")
  TOTAL_COUNT=$(echo "$NORMALIZED_ACS" | grep -c '.' 2>/dev/null || echo "0")
  if [[ "$UNIQUE_COUNT" -lt "$TOTAL_COUNT" ]]; then
    DET_ISSUES+=("Duplicate acceptance criteria detected")
  fi
fi

# 5. Status Done consistent with all AC checked (and vice versa)
STATUS=$(echo "$TASK_CONTENT" | grep -oE 'status:\s*\S+' | head -1 | sed 's/status:\s*//')
if [[ -z "$STATUS" ]]; then
  STATUS=$(echo "$TASK_CONTENT" | grep -E '^Status:' | head -1 | sed 's/^Status:[[:space:]]*//' | sed 's/^[^[:alpha:]]*//')
fi
ALL_CHECKED=true
ANY_AC=false
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  ANY_AC=true
  if echo "$line" | grep -qE '^\s*- \[ \]'; then
    ALL_CHECKED=false
    break
  fi
done <<< "$AC_LINES"

if [[ "$ANY_AC" == true ]]; then
  if [[ "$STATUS" == *"Done"* ]] && [[ "$ALL_CHECKED" == false ]]; then
    DET_ISSUES+=("Status is Done but not all AC are checked")
  fi
  if [[ "$ALL_CHECKED" == true ]] && [[ "$STATUS" != *"Done"* ]] && [[ "$AC_COUNT" -gt 0 ]]; then
    DET_ISSUES+=("All AC are checked but status is not Done")
  fi
fi

# 6. Dependencies resolve to existing task IDs
DEPS=$(echo "$TASK_CONTENT" | grep -E '^dependencies:' | sed 's/^dependencies:\s*//' | tr ',' '\n' | grep -oE '[0-9]+' || true)
for dep_id in $DEPS; do
  DEP_FILE=$(find backlog/tasks -maxdepth 1 -name "task-${dep_id} -*" -o -name "task-${dep_id}-*" 2>/dev/null | head -1)
  if [[ -z "$DEP_FILE" ]] || [[ ! -f "$DEP_FILE" ]]; then
    DET_ISSUES+=("Dependency TASK-${dep_id} not found in backlog/tasks/")
  fi
done

# 7. File-path references in backtick spans or markdown links exist
IN_FENCE=false
while IFS= read -r line; do
  if echo "$line" | grep -qE '^```'; then
    if [[ "$IN_FENCE" == true ]]; then
      IN_FENCE=false
    else
      IN_FENCE=true
    fi
    continue
  fi
  [[ "$IN_FENCE" == true ]] && continue

  # Extract backtick-quoted paths
  BACKTICK_PATHS=$(echo "$line" | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' || true)
  # Extract markdown link paths
  LINK_PATHS=$(echo "$line" | grep -oE '\]\([^)]+\)' | sed 's/^\](//' | sed 's/)$//' || true)

  for path in $BACKTICK_PATHS $LINK_PATHS; do
    # Skip URLs
    echo "$path" | grep -qE '^https?://|^www\.' && continue
    # Skip wildcards/globs
    echo "$path" | grep -qE '[*?]|\.\.\.' && continue
    # Skip non-path-like strings (must contain / or end with known extension)
    if ! echo "$path" | grep -qE '/|\.sh$|\.js$|\.ts$|\.py$|\.md$|\.json$|\.yaml$|\.yml$|\.toml$'; then
      continue
    fi
    # Check existence
    if [[ ! -e "$path" ]]; then
      DET_ISSUES+=("Referenced path '$path' does not exist")
    fi
  done
done <<< "$TASK_CONTENT"

# === Output deterministic check results ===
# Suppressed entirely when RALPH_AUTONOMOUS=1
if [[ "${RALPH_AUTONOMOUS:-}" != "1" ]]; then
  for issue in "${DET_ISSUES[@]+"${DET_ISSUES[@]}"}"; do
    echo "Validator [det]: $issue"
  done
fi

# === LLM Nudge ===
# Short-circuit if autonomous mode
if [[ "${RALPH_AUTONOMOUS:-}" == "1" ]]; then
  exit 0
fi

# Substantive-edit predicate: check if description body or AC text changed
DIFF_OUTPUT=$(git diff HEAD -- "backlog/tasks/task-${TASK_ID}"* 2>/dev/null || true)
if [[ -z "$DIFF_OUTPUT" ]]; then
  if ! echo "$CMD" | grep -qE '^backlog task create\b'; then
    exit 0
  fi
fi

# Check if changes are substantive (affect description or AC lines)
SUBSTANTIVE=false
if echo "$CMD" | grep -qE '^backlog task create\b'; then
  SUBSTANTIVE=true
else
  ADDED_LINES=$(echo "$DIFF_OUTPUT" | grep '^+' | grep -v '^+++' || true)
  REMOVED_LINES=$(echo "$DIFF_OUTPUT" | grep '^-' | grep -v '^---' || true)

  SUBST_ADDED=$(echo "$ADDED_LINES" | grep -vE '^\+(status:|updated:|notes:|<!-- |[[:space:]]*$)' | grep -vE '^\+- \[(x| )\] #[0-9]+ [A-Z]' || true)
  SUBST_REMOVED=$(echo "$REMOVED_LINES" | grep -vE '^\-(status:|updated:|notes:|<!-- |[[:space:]]*$)' | grep -vE '^\-- \[(x| )\] #[0-9]+ [A-Z]' || true)
  AC_TEXT_CHANGED=$(echo "$DIFF_OUTPUT" | grep -E '^\+.*- \[(x| )\]' | grep -vE '^\+- \[(x| )\] #[0-9]+\s' || true)

  if [[ -n "$SUBST_ADDED" ]] || [[ -n "$SUBST_REMOVED" ]] || [[ -n "$AC_TEXT_CHANGED" ]]; then
    SUBSTANTIVE=true
  fi
fi

if [[ "$SUBSTANTIVE" == false ]]; then
  exit 0
fi

# Check if task body contains URLs (for reachability rubric item)
HAS_URLS=false
if echo "$TASK_CONTENT" | grep -qE 'https?://|www\.'; then
  HAS_URLS=true
fi

# Build rubric items
RUBRIC=""
ITEM_NUM=1

RUBRIC="${RUBRIC}${ITEM_NUM}. Logical contradictions between description and AC, or between AC items.\n"
ITEM_NUM=$((ITEM_NUM + 1))

RUBRIC="${RUBRIC}${ITEM_NUM}. Semantic AC duplication (same requirement stated differently).\n"
ITEM_NUM=$((ITEM_NUM + 1))

RUBRIC="${RUBRIC}${ITEM_NUM}. AC implementability (each AC is concrete, testable, and scoped to one thing).\n"
ITEM_NUM=$((ITEM_NUM + 1))

if [[ "$HAS_URLS" == true ]]; then
  RUBRIC="${RUBRIC}${ITEM_NUM}. Reference reachability — verify URLs are accessible. Check allowed hosts in .devcontainer/init-firewall.sh.\n"
  ITEM_NUM=$((ITEM_NUM + 1))
fi

RUBRIC="${RUBRIC}${ITEM_NUM}. Self-containment (task can be completed without unstated context).\n"

# Emit system-reminder with LLM nudge
printf '<system-reminder>\n'
printf 'Task validator triggered for TASK-%s.\n' "$TASK_ID"
printf 'File: %s\n\n' "$TASK_FILE"
printf 'Read the task file and evaluate against this rubric:\n'
printf '%b\n' "$RUBRIC"
printf 'Output format: "Validator [llm]: task-%s OK" if no issues, or "Validator [llm]: task-%s" followed by terse one-line issues. No remediation suggestions, no rewrites.\n' "$TASK_ID" "$TASK_ID"
printf '</system-reminder>\n'
