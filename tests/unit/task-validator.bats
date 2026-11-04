#!/usr/bin/env bats
# Unit tests for the task-validator PostToolUse hook (live copy and ralph-init template)

load '../helpers/common'
LIVE_VALIDATOR="$PROJECT_ROOT/.claude/hooks/task-validator.sh"
TEMPLATE_VALIDATOR="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/templates/claude/hooks/task-validator.sh"

setup() {
  TEST_DIR="$(make_temp_dir)"
  mkdir -p "$TEST_DIR/backlog/tasks"
}

teardown() {
  if [[ -n "${TEST_DIR:-}" ]]; then
    rm -rf "$TEST_DIR"
  fi
}

# Write task-1 whose ACs are pairwise identical except for case and whitespace
write_whitespace_duplicate_task() {
  printf '%s\n' \
    '---' \
    'id: TASK-1' \
    'title: Sample' \
    'status: To Do' \
    'dependencies: []' \
    '---' \
    '' \
    '## Description' \
    '' \
    '<!-- SECTION:description:BEGIN -->' \
    'Sample description.' \
    '<!-- SECTION:description:END -->' \
    '' \
    '## Acceptance Criteria' \
    '<!-- AC:BEGIN -->' \
    '- [ ] #1 Foo  bar' \
    '- [ ] #2 foo bar' \
    "- [ ] #3 other$(printf '\t')thing" \
    '- [ ] #4 other thing' \
    '<!-- AC:END -->' \
    > "$TEST_DIR/backlog/tasks/task-1 - Sample.md"
}

# Put a sed on PATH that reads BRE '\+' as a literal '+', as macOS /usr/bin/sed does
install_bsd_bre_sed_shim() {
  REAL_SED="$(command -v sed)"
  export REAL_SED
  mkdir -p "$TEST_DIR/bin"
  cat > "$TEST_DIR/bin/sed" <<'EOF'
#!/bin/bash
for a in "$@"; do [[ "$a" == -E ]] && exec "$REAL_SED" "$@"; done
args=()
for a in "$@"; do args+=("${a//\\+/[+]}"); done
exec "$REAL_SED" "${args[@]}"
EOF
  chmod +x "$TEST_DIR/bin/sed"
}

run_validator() {
  local script="$1"
  (unset CLAUDE_PROJECT_DIR RALPH_PROJECT_ROOT; cd "$TEST_DIR" && echo '{"tool_input":{"command":"backlog task edit 1 -s \"To Do\""}}' \
    | RALPH_AUTONOMOUS=0 bash "$script" 2>/dev/null)
}

# Write task-1 depending on the missing TASK-9, backticking one existing and one missing root-relative path
write_subdir_task() {
  mkdir -p "$TEST_DIR/sub" "$TEST_DIR/docs"
  : > "$TEST_DIR/docs/present.md"
  printf '%s\n' \
    '---' \
    'id: TASK-1' \
    'title: Sample' \
    'status: To Do' \
    'dependencies: [TASK-9]' \
    '---' \
    '' \
    '## Description' \
    '' \
    'See `docs/present.md` and `docs/absent.md`.' \
    '' \
    '## Acceptance Criteria' \
    '- [ ] #1 one' \
    > "$TEST_DIR/backlog/tasks/task-1 - Sample.md"
}

# Run the template validator from $1 (a cwd) with CLAUDE_PROJECT_DIR at the project root; $2 is the backlog command
run_validator_from() {
  local cwd="$1" cmd="$2"
  (unset RALPH_PROJECT_ROOT; cd "$cwd" && jq -n --arg c "$cmd" '{tool_input:{command:$c}}' \
    | CLAUDE_PROJECT_DIR="$TEST_DIR" RALPH_AUTONOMOUS=0 bash "$TEMPLATE_VALIDATOR" 2>/dev/null)
}

@test "task-validator: reports ACs differing only in whitespace as duplicates (live copy)" {
  write_whitespace_duplicate_task
  run run_validator "$LIVE_VALIDATOR"
  [[ "$output" == *"Duplicate acceptance criteria detected"* ]]
}

@test "task-validator: reports ACs differing only in whitespace as duplicates (template)" {
  write_whitespace_duplicate_task
  run run_validator "$TEMPLATE_VALIDATOR"
  [[ "$output" == *"Duplicate acceptance criteria detected"* ]]
}

@test "task-validator: whitespace duplicates still reported under BSD BRE sed semantics" {
  write_whitespace_duplicate_task
  install_bsd_bre_sed_shim
  # The shim really emulates BSD: a GNU-only BRE '\+' no longer collapses runs
  [[ "$(printf 'a  b\n' | PATH="$TEST_DIR/bin:$PATH" sed 's/[[:space:]]\+/ /g')" == "a  b" ]]
  PATH="$TEST_DIR/bin:$PATH" run run_validator "$TEMPLATE_VALIDATOR"
  [[ "$output" == *"Duplicate acceptance criteria detected"* ]]
}

@test "task-validator: neither copy uses the GNU-only BRE whitespace collapse" {
  run grep -F "sed 's/[[:space:]]\\+/ /g'" "$LIVE_VALIDATOR" "$TEMPLATE_VALIDATOR"
  [ "$status" -eq 1 ]
  grep -qF "sed -E 's/[[:space:]]+/ /g'" "$LIVE_VALIDATOR"
  grep -qF "sed -E 's/[[:space:]]+/ /g'" "$TEMPLATE_VALIDATOR"
}

@test "task-validator: reports a missing dependency from a subdirectory as from the root" {
  write_subdir_task
  run run_validator_from "$TEST_DIR" 'backlog task edit 1 -s "To Do"'
  [[ "$output" == *"Dependency TASK-9 not found"* ]]
  run run_validator_from "$TEST_DIR/sub" 'backlog task edit 1 -s "To Do"'
  [ "$status" -eq 0 ]
  [[ "$output" == *"[det] issues for TASK-1"* ]]
  [[ "$output" == *"Dependency TASK-9 not found"* ]]
}

@test "task-validator: checks root-relative paths from a subdirectory" {
  write_subdir_task
  run run_validator_from "$TEST_DIR/sub" 'backlog task create 1'
  [[ "$output" != *"'docs/present.md' does not exist"* ]]
  [[ "$output" == *"'docs/absent.md' does not exist"* ]]
}

@test "task-validator: rubric File: line is an absolute path that exists from a subdirectory" {
  write_subdir_task
  run run_validator_from "$TEST_DIR/sub" 'backlog task create 1'
  file_line=$(printf '%s' "$output" | jq -r '.hookSpecificOutput.additionalContext' | grep '^File: ')
  file_path="${file_line#File: }"
  [[ "$file_path" == /* ]]
  [ -f "$file_path" ]
  [ "$file_path" = "$TEST_DIR/backlog/tasks/task-1 - Sample.md" ]
}
