#!/usr/bin/env bats
# task-reviewer rule tiers: the agent loads every non-empty tier additively,
# in the order user-global, shared docs, project; ralph-init upgrade hints at
# project-file headings that duplicate the managed docs file.
#
# Both snippets are extracted from the shipped files and run as-is against
# fixtures, so the test follows the documented code rather than a copy of it.

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
AGENT="$PROJECT_ROOT/plugins/ralph/agents/task-reviewer.md"
SKILL="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/SKILL.md"

load '../helpers/common'

# Print the first ```bash fence that follows the first line matching $2 in $1.
# The fence may be indented (as inside a markdown list item); the indent is
# stripped.
extract_snippet() {
  awk -v anchor="$2" '
    !found && index($0, anchor) { found = 1; next }
    found && !in_block && $0 ~ /^[ \t]*```bash[ \t]*$/ {
      in_block = 1; match($0, /^[ \t]*/); indent = RLENGTH; next
    }
    in_block && $0 ~ /^[ \t]*```[ \t]*$/ { exit }
    in_block { print substr($0, indent + 1) }
  ' "$1"
}

setup() {
  WORK="$(make_temp_dir)"
  FAKE_HOME="$(make_temp_dir)"
  mkdir -p "$WORK/.claude" "$FAKE_HOME/.claude"
  LOADER="$WORK/loader.sh"
  extract_snippet "$AGENT" "## Custom Rules Loading" > "$LOADER"
  HINTER="$WORK/hinter.sh"
  extract_snippet "$SKILL" '- **`.claude/task-reviewer-rules.md`** — project-owned' > "$HINTER"
}

run_loader() {
  run bash -c 'cd "$1" && HOME="$2" bash "$3"' _ "$WORK" "$FAKE_HOME" "$LOADER"
}

@test "loader snippet is extracted from the agent file" {
  [ -s "$LOADER" ]
  grep -q 'task-reviewer-rules.docs.md' "$LOADER"
}

@test "all three tiers load additively in order user-global, shared docs, project" {
  echo "GLOBAL-RULE" > "$FAKE_HOME/.claude/task-reviewer-rules.md"
  echo "DOCS-RULE" > "$WORK/.claude/task-reviewer-rules.docs.md"
  echo "PROJECT-RULE" > "$WORK/.claude/task-reviewer-rules.md"
  run_loader
  [ "$status" -eq 0 ]
  [[ "$output" == *GLOBAL-RULE*DOCS-RULE*PROJECT-RULE* ]]
  # The tier report names every applied tier, in the same order.
  [[ "${lines[0]}" == "user-global ("*"), shared docs (.claude/task-reviewer-rules.docs.md), project (.claude/task-reviewer-rules.md)" ]]
}

@test "empty and missing tiers are skipped without masking the others" {
  : > "$WORK/.claude/task-reviewer-rules.docs.md"
  echo "PROJECT-RULE" > "$WORK/.claude/task-reviewer-rules.md"
  run_loader
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "project (.claude/task-reviewer-rules.md)" ]
  [[ "$output" == *PROJECT-RULE* ]]
  [[ "$output" != *"shared docs"* ]]
  [[ "$output" != *"user-global"* ]]
}

@test "a project rules file no longer hides the user-global tier" {
  echo "GLOBAL-RULE" > "$FAKE_HOME/.claude/task-reviewer-rules.md"
  echo "PROJECT-RULE" > "$WORK/.claude/task-reviewer-rules.md"
  run_loader
  [[ "$output" == *GLOBAL-RULE*PROJECT-RULE* ]]
}

@test "no tier at all loads nothing" {
  run_loader
  [ "$status" -eq 0 ]
  [ -z "$(printf '%s' "$output" | tr -d '[:space:]')" ]
}

@test "agent states that an explicit project override of a named shared rule wins" {
  grep -q 'project rule explicitly names a rule ID' "$AGENT"
  grep -q 'the project rule wins' "$AGENT"
}

@test "upgrade hint names each project heading duplicated in the managed file" {
  [ -s "$HINTER" ]
  printf '# T\n\n## R-DOCS-1: A\n\n## R-DOCS-2: B\n' > "$WORK/.claude/task-reviewer-rules.docs.md"
  printf '# P\n\n## R-DOCS-1: A\n\n## R-LOCAL-1: mine\n' > "$WORK/.claude/task-reviewer-rules.md"
  run bash -c 'cd "$1" && bash "$2"' _ "$WORK" "$HINTER"
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 1 ]
  [[ "${lines[0]}" == 'hint: .claude/task-reviewer-rules.md repeats "## R-DOCS-1: A"'* ]]
}

@test "upgrade hint is silent without overlap or without a project file" {
  printf '## R-DOCS-1: A\n' > "$WORK/.claude/task-reviewer-rules.docs.md"
  run bash -c 'cd "$1" && bash "$2"' _ "$WORK" "$HINTER"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  printf '## R-LOCAL-1: mine\n' > "$WORK/.claude/task-reviewer-rules.md"
  run bash -c 'cd "$1" && bash "$2"' _ "$WORK" "$HINTER"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}
