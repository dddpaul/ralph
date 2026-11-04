#!/usr/bin/env bats
# Hook commands in this repo's .claude/settings.json (the legacy guard wiring
# it keeps until it migrates to plugin hooks, and the local guards after) must
# be anchored at the project root. Claude Code runs a hook command from the session's current
# directory, which moves after any `cd <subdir> && …`; a relative
# `.claude/hooks/<name>.sh` then fails with "No such file or directory", which
# Claude Code treats as non-blocking, so the guard silently enforces nothing.
# See TASK-280.

load '../helpers/common'
SETTINGS="$PROJECT_ROOT/.claude/settings.json"

setup() {
  TEST_DIR="$(make_temp_dir)"
}

teardown() {
  if [[ -n "${TEST_DIR:-}" ]]; then
    rm -rf "$TEST_DIR"
  fi
}

# Print one line per offending hook command in settings file $1; exit 1 if any.
check_commands() {
  local file="$1" cmd name bad=0 prefix='"$CLAUDE_PROJECT_DIR"/.claude/hooks/'
  while IFS= read -r cmd; do
    case "$cmd" in
      "$prefix"*.sh) ;;
      *) echo "not anchored: $cmd"; bad=1; continue ;;
    esac
    name="${cmd#"$prefix"}"
    case "$name" in
      */*) echo "nested path: $cmd"; bad=1; continue ;;
    esac
    if [[ ! -f "$PROJECT_ROOT/.claude/hooks/$name" ]]; then
      echo "missing script: $cmd"
      bad=1
    fi
  done < <(jq -r '.. | .command? // empty' "$file")
  return "$bad"
}

@test "settings.json registers at least one hook command" {
  run jq -r '[.. | .command? // empty] | length' "$SETTINGS"
  [ "$status" -eq 0 ]
  [ "$output" -gt 0 ]
}

@test "every hook command is anchored at CLAUDE_PROJECT_DIR and names a live script" {
  run check_commands "$SETTINGS"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "a relative hook command is rejected" {
  sed 's|"\\"$CLAUDE_PROJECT_DIR\\"/\.claude/hooks/notes-guard\.sh"|".claude/hooks/notes-guard.sh"|' \
    "$SETTINGS" > "$TEST_DIR/settings.json"
  run check_commands "$TEST_DIR/settings.json"
  [ "$status" -ne 0 ]
  [[ "$output" == *'not anchored: .claude/hooks/notes-guard.sh'* ]]
}

@test "an anchored command naming a missing script is rejected" {
  sed 's|/\.claude/hooks/notes-guard\.sh|/.claude/hooks/no-such-guard.sh|' \
    "$SETTINGS" > "$TEST_DIR/settings.json"
  run check_commands "$TEST_DIR/settings.json"
  [ "$status" -ne 0 ]
  [[ "$output" == *'missing script: "$CLAUDE_PROJECT_DIR"/.claude/hooks/no-such-guard.sh'* ]]
}

@test "an unquoted CLAUDE_PROJECT_DIR is rejected" {
  sed 's|"\\"$CLAUDE_PROJECT_DIR\\"/\.claude/hooks/notes-guard\.sh"|"$CLAUDE_PROJECT_DIR/.claude/hooks/notes-guard.sh"|' \
    "$SETTINGS" > "$TEST_DIR/settings.json"
  run check_commands "$TEST_DIR/settings.json"
  [ "$status" -ne 0 ]
  [[ "$output" == *'not anchored: $CLAUDE_PROJECT_DIR/.claude/hooks/notes-guard.sh'* ]]
}
