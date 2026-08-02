#!/usr/bin/env bats
# Unit tests for .claude/hooks/bump-version.sh — the per-task auto-bump helper
# that raises the plugin version when shipped plugin files change, so the
# pre-push version-bump-guard passes with no human in the loop. Mirrors
# tests/unit/version-bump-guard.bats. See TASK-217.
#
# The real script + real .claude/hooks/lib/shipped-set.sh are exercised (the
# helper resolves its lib via $0), but every git operation happens inside a
# throwaway repo created per test, so nothing here touches the project repo.

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
HELPER="$PROJECT_ROOT/.claude/hooks/bump-version.sh"
PLUGIN="plugins/ralph/.claude-plugin/plugin.json"
MARKET=".claude-plugin/marketplace.json"
SKILL="plugins/ralph/skills/ralph-run/SKILL.md"

# Write both manifests at the given version, mirroring the real JSON shape
# (top-level version in plugin.json, metadata.version in marketplace.json).
set_versions() { # $1=version
  mkdir -p "$(dirname "$PLUGIN")" "$(dirname "$MARKET")"
  printf '{\n  "name": "ralph",\n  "version": "%s"\n}\n' "$1" > "$PLUGIN"
  printf '{\n  "name": "dddpaul-ralph",\n  "metadata": {\n    "version": "%s"\n  }\n}\n' "$1" > "$MARKET"
}

ver_of() { sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$1" | head -n1; }
plugin_version() { ver_of "$PLUGIN"; }
market_version() { ver_of "$MARKET"; }

setup() {
  TEST_DIR=$(mktemp -d)
  cd "$TEST_DIR"
  git init -q -b master
  git config user.email test@example.com
  git config user.name Test

  # Base commit on master: both manifests at 0.1.0, a shipped skill, a doc.
  set_versions "0.1.0"
  mkdir -p "$(dirname "$SKILL")"
  echo "base skill" > "$SKILL"
  echo "# readme" > README.md
  git add -A
  git commit -q -m "base"
}

teardown() {
  if [[ -n "${TEST_DIR:-}" ]]; then
    rm -rf "$TEST_DIR"
  fi
}

@test "auto: no-op when no shipped-set file changed in master..HEAD" {
  git checkout -q -b task-1
  echo "notes" > NOTES.md            # non-shipped path
  git add -A && git commit -q -m "task-1: docs only"

  run bash "$HELPER" --auto
  [ "$status" -eq 0 ]
  [[ "$output" == *"nothing to bump"* ]]
  [ "$(plugin_version)" = "0.1.0" ]  # untouched
  [ "$(market_version)" = "0.1.0" ]
}

@test "auto: patch bump when an existing shipped file is modified" {
  git checkout -q -b task-2
  echo "changed skill" > "$SKILL"    # modified (M), not added
  git add -A && git commit -q -m "task-2: edit skill"

  run bash "$HELPER" --auto
  [ "$status" -eq 0 ]
  [ "$(plugin_version)" = "0.1.1" ]  # patch: 0.1.0 -> 0.1.1
  [ "$(market_version)" = "0.1.1" ]  # both manifests move together
}

@test "auto: minor bump when a new skill dir is added" {
  git checkout -q -b task-3
  mkdir -p plugins/ralph/skills/ralph-new
  echo "new skill" > plugins/ralph/skills/ralph-new/SKILL.md   # added (A)
  git add -A && git commit -q -m "task-3: add skill"

  run bash "$HELPER" --auto
  [ "$status" -eq 0 ]
  [ "$(plugin_version)" = "0.2.0" ]  # minor: 0.1.0 -> 0.2.0
  [ "$(market_version)" = "0.2.0" ]
}

@test "auto: minor bump when a new agent file is added" {
  git checkout -q -b task-3a
  mkdir -p plugins/ralph/agents
  echo "new agent" > plugins/ralph/agents/new-agent.md          # added (A)
  git add -A && git commit -q -m "task-3a: add agent"

  run bash "$HELPER" --auto
  [ "$status" -eq 0 ]
  [ "$(plugin_version)" = "0.2.0" ]
}

@test "auto: idempotent — second run does not bump again" {
  git checkout -q -b task-4
  echo "changed skill" > "$SKILL"
  git add -A && git commit -q -m "task-4: edit skill"

  run bash "$HELPER" --auto
  [ "$status" -eq 0 ]
  [ "$(plugin_version)" = "0.1.1" ]
  after_first=$(git rev-parse HEAD)

  run bash "$HELPER" --auto           # re-run on the already-bumped branch
  [ "$status" -eq 0 ]
  [[ "$output" == *"already ahead"* ]]
  [ "$(plugin_version)" = "0.1.1" ]   # still 0.1.1, not 0.1.2
  [ "$(git rev-parse HEAD)" = "$after_first" ]   # no new commit
}

@test "auto: commit message is branch-aware (task-N: prefix, single line)" {
  git checkout -q -b task-217
  echo "changed skill" > "$SKILL"
  git add -A && git commit -q -m "task-217: edit skill"

  run bash "$HELPER" --auto
  [ "$status" -eq 0 ]
  run git log -1 --format=%s
  [ "$output" = "task-217: bump plugin version to 0.1.1 (patch)" ]
  # exactly one line in the body-less message
  run git log -1 --format=%B
  [ "${#lines[@]}" -eq 1 ]
}

@test "auto --no-commit: edits + stages both manifests but creates no commit" {
  git checkout -q -b task-5
  echo "changed skill" > "$SKILL"
  git add -A && git commit -q -m "task-5: edit skill"
  before=$(git rev-parse HEAD)

  run bash "$HELPER" --auto --no-commit
  [ "$status" -eq 0 ]
  [ "$(plugin_version)" = "0.1.1" ]                # edited in working tree
  [ "$(git rev-parse HEAD)" = "$before" ]          # but no new commit
  run git diff --cached --name-only
  [[ "$output" == *"$PLUGIN"* ]]                   # both staged
  [[ "$output" == *"$MARKET"* ]]
}

@test "explicit increment overrides inference: minor on a modified file" {
  git checkout -q -b task-6
  echo "changed skill" > "$SKILL"    # a modify would infer patch
  git add -A && git commit -q -m "task-6: edit skill"

  run bash "$HELPER" minor           # force minor
  [ "$status" -eq 0 ]
  [ "$(plugin_version)" = "0.2.0" ]
}

@test "explicit major is honored when requested (never auto)" {
  git checkout -q -b task-7
  echo "changed skill" > "$SKILL"
  git add -A && git commit -q -m "task-7: edit skill"

  run bash "$HELPER" major
  [ "$status" -eq 0 ]
  [ "$(plugin_version)" = "1.0.0" ]  # 0.1.0 -> 1.0.0
}

@test "tag: creates an annotated vX.Y.Z once, then no-ops; sets push.followTags" {
  # HEAD is master at 0.1.0.
  run bash "$HELPER" --tag
  [ "$status" -eq 0 ]

  run git tag -l "v0.1.0"
  [ "$output" = "v0.1.0" ]
  run git cat-file -t "v0.1.0"       # annotated tag object, not a lightweight ref
  [ "$output" = "tag" ]
  run git config --get push.followTags
  [ "$output" = "true" ]

  run bash "$HELPER" --tag           # second run: tag already present
  [ "$status" -eq 0 ]
  [[ "$output" == *"already exists"* ]]
}

@test "nudge: prints a non-blocking reminder on a shipped change without a bump" {
  git checkout -q -b task-8
  echo "changed skill" > "$SKILL"
  git add -A && git commit -q -m "task-8: edit skill"

  run bash "$HELPER" --nudge
  [ "$status" -eq 0 ]                 # never blocks
  [[ "$output" == *"bump-version.sh --auto"* ]]
  [[ "$output" == *"patch"* ]]        # suggested increment surfaced
}

@test "nudge: silent once the version is already ahead of master" {
  git checkout -q -b task-9
  echo "changed skill" > "$SKILL"
  git add -A && git commit -q -m "task-9: edit skill"
  bash "$HELPER" --auto              # bump first

  run bash "$HELPER" --nudge
  [ "$status" -eq 0 ]
  [ -z "$output" ]                   # nothing to remind about
}

@test "nudge: silent on master (HEAD == master)" {
  run bash "$HELPER" --nudge         # still on master from setup
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}
