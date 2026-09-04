#!/usr/bin/env bats
# R11 (.claude/task-reviewer-rules.md) — template parity.
#
# The repo ships a bootstrap tree at plugins/ralph/skills/ralph-init/templates/
# that mirrors this project's own live files. Drift between the two sides is a
# defect: TASK-227 shipped a template naming-guard.sh copied from an
# intermediate version of the live hook, and nothing automated caught it.
#
# This test walks every live/template pair in the R11 table and asserts the
# mirror holds. Documented carve-outs are *encoded* (a narrower assertion that
# still fails on real drift), never skipped wholesale. Two closure tests keep
# the registry from rotting: every template file and every live hook must be
# either a registered pair or a listed, justified non-mirror.
#
# See TASK-228.

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
TEMPLATES="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/templates"

# --------------------------------------------------------------------------
# Pair registry: "<mode>|<live path>|<template path>", both repo-relative.
#
# Modes:
#   exact  — diff must be silent.
#   region — only the region above "## Project-Specific" is compared, and every
#            differing line must be listed in claude_md_allowed_deviations.
#   prefix — live must open with the template verbatim; the trailing remainder
#            must be the documented repo-local block only.
#   keys   — gitignored per-developer override: compare JSON shape, not bytes.
#
# The R11 table drives the rows. Two more are the same class but absent from
# it — .claude/brainstorm-rules.md and git-hooks/pre-commit — and are in parity
# today, so they are registered here to keep them that way.
# --------------------------------------------------------------------------
registry() {
  cat <<'ROWS'
exact|.claude/settings.json|claude/settings.json
keys|.claude/settings.local.json|claude/settings.local.json
exact|.claude/hooks/commit-msg-guard.sh|claude/hooks/commit-msg-guard.sh
exact|.claude/hooks/commit-prefix-guard.sh|claude/hooks/commit-prefix-guard.sh
exact|.claude/hooks/filename-length-guard.sh|claude/hooks/filename-length-guard.sh
exact|.claude/hooks/master-branch-guard.sh|claude/hooks/master-branch-guard.sh
exact|.claude/hooks/naming-guard.sh|claude/hooks/naming-guard.sh
exact|.claude/hooks/notes-guard.sh|claude/hooks/notes-guard.sh
exact|.claude/hooks/task-validator.sh|claude/hooks/task-validator.sh
exact|.claude/brainstorm-rules.md|claude/brainstorm-rules.md
exact|ralph.sh|root/ralph.sh
exact|refine.sh|root/refine.sh
region|CLAUDE.md|root/CLAUDE.md
prefix|.git/hooks/post-commit|git-hooks/post-commit
exact|.git/hooks/commit-msg|git-hooks/commit-msg
exact|.git/hooks/pre-commit|git-hooks/pre-commit
exact|.devcontainer/devcontainer.json|devcontainer/devcontainer.json
exact|.devcontainer/init-firewall.sh|devcontainer/init-firewall.sh
ROWS
}

# Template files that are deliberately NOT mirrors of a live file. Entries
# ending in "/" match a whole subtree.
non_mirrored_templates() {
  cat <<'ROWS'
claude/task-reviewer-rules.docs.md
devcontainer/Dockerfile.base
devcontainer/lang/
obsidian/
root/CLAUDE.conventions.docs.md
root/CLAUDE.conventions.python.md
ROWS
}

# Live hooks with no template counterpart by design: plugin-marketplace
# governance that exists only in this repo (CLAUDE.md step 6 says so).
repo_local_hooks() {
  cat <<'ROWS'
.claude/hooks/bump-version.sh
.claude/hooks/version-bump-guard.sh
.claude/hooks/lib/shipped-set.sh
ROWS
}

# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

# Emit each line that differs between $1 and $2, prefix stripped. Identical
# inputs yield nothing instead of a non-zero exit, so a caller running under
# bats' errexit can still report on the empty case.
changed_lines() {
  diff "$1" "$2" | { grep '^[<>]' || true; } | cut -c3-
}

# Print the generic region of a CLAUDE.md: everything above ## Project-Specific.
generic_region() {
  sed -n '/^## Project-Specific/q;p' "$1"
}

# True when $1 (repo-relative) appears as the live or template side of a row.
in_registry() {
  registry | cut -d'|' -f2,3 | tr '|' '\n' | grep -Fxq "$1"
}

# Lines inside CLAUDE.md's generic region that are allowed to differ between
# the live file and the template, in order:
#
#   1. LIVE  step 6 — CARVE-OUT. Plugin-marketplace version governance is
#      repo-specific; the live text itself states the bump-version.sh helper
#      lives only under .claude/ and is NOT mirrored to ralph-init templates.
#   2. TMPL  step 6 — CARVE-OUT. The generic merge step a bootstrapped project
#      gets instead of (1).
#
# Both remaining entries are carve-outs; there is no pinned DRIFT left. An
# entry that no longer matches a real deviation is a failure, not dead weight,
# so pinning future drift here obliges whoever fixes it to delete the row too
# (TASK-229 removed the backlog-CLI pair that way).
claude_md_allowed_deviations() {
  cat <<'ROWS'
6. **Merge:** (a) on the task branch, run `.claude/hooks/bump-version.sh --auto` — it auto-bumps the plugin version (both manifests) and commits **iff** a shipped `plugins/ralph/**` file changed in `master..HEAD`, else no-ops (so the pre-push `version-bump-guard.sh` passes without a human); (b) commit the task file; (c) `git checkout master && git merge --no-ff <branch>`; (d) on master, run `.claude/hooks/bump-version.sh --tag` — it annotates the merge commit `vX.Y.Z` for the current version (no-op if the tag exists) so the tag rides the next push via `push.followTags`; (e) `git branch -d <branch>`. (Steps (a)/(d) are repo-specific plugin-marketplace governance — the helper lives only under `.claude/`; NOT mirrored to `ralph-init` templates.)
6. **Merge:** commit task file, `git checkout master && git merge <branch> && git branch -d <branch>`.
ROWS
}

# --------------------------------------------------------------------------
# exact pairs
# --------------------------------------------------------------------------

@test "R11: every exact pair is byte-identical to its template" {
  failures=""
  checked=0
  while IFS='|' read -r mode live tmpl; do
    [ "$mode" = "exact" ] || continue
    live_path="$PROJECT_ROOT/$live"
    tmpl_path="$TEMPLATES/$tmpl"

    if [ ! -f "$tmpl_path" ]; then
      failures="$failures
missing template for $live: $tmpl"
      continue
    fi

    # .git/hooks/* live outside the work tree and are absent in a fresh
    # checkout (CI). The template side above is still asserted.
    if [ ! -f "$live_path" ]; then
      case "$live" in
        .git/hooks/*) continue ;;
        *)
          failures="$failures
missing live file for $tmpl: $live"
          continue
          ;;
      esac
    fi

    if ! diff -q "$live_path" "$tmpl_path" >/dev/null 2>&1; then
      failures="$failures
R11 drift: $live vs $tmpl
$(diff "$live_path" "$tmpl_path" || true)"
    fi
    checked=$((checked + 1))
  done <<EOF
$(registry)
EOF

  [ -z "$failures" ] || {
    echo "$failures"
    return 1
  }
  # Anti-vacuity: 15 exact rows, 2 of which (.git/hooks/*) may be absent in CI.
  [ "$checked" -ge 13 ]
}

# --------------------------------------------------------------------------
# region carve-out: CLAUDE.md above ## Project-Specific
# --------------------------------------------------------------------------

@test "R11: CLAUDE.md generic region differs only where documented" {
  live_path="$PROJECT_ROOT/CLAUDE.md"
  tmpl_path="$TEMPLATES/root/CLAUDE.md"

  # The carve-out is region-scoped, so the boundary must exist on both sides —
  # a missing heading would silently widen or empty the comparison.
  grep -Fxq '## Project-Specific' "$live_path"
  grep -Fxq '## Project-Specific' "$tmpl_path"

  live_region="$(generic_region "$live_path")"
  tmpl_region="$(generic_region "$tmpl_path")"
  [ "$(printf '%s\n' "$live_region" | wc -l)" -ge 50 ]
  [ "$(printf '%s\n' "$tmpl_region" | wc -l)" -ge 50 ]

  changed="$(changed_lines \
    <(printf '%s\n' "$live_region") \
    <(printf '%s\n' "$tmpl_region"))"

  failures=""
  if [ -n "$changed" ]; then
    while IFS= read -r line; do
      printf '%s\n' "$line" \
        | grep -Fxq -f <(claude_md_allowed_deviations) \
        || failures="$failures
undocumented deviation in the CLAUDE.md generic region:
  $line"
    done <<EOF
$changed
EOF
  fi

  # A pinned deviation that no longer exists must be removed, or the list
  # slowly turns into a blanket exemption.
  while IFS= read -r entry; do
    printf '%s\n' "$changed" | grep -Fxq "$entry" || failures="$failures
stale claude_md_allowed_deviations entry (deviation is gone, delete it):
  $entry"
  done <<EOF
$(claude_md_allowed_deviations)
EOF

  [ -z "$failures" ] || {
    echo "$failures"
    return 1
  }
}

@test "R11: the CLAUDE.md ## Project-Specific section is outside the mirror" {
  # Encodes "generic section only" as a positive fact rather than an omission:
  # the template's project-local tail is an unfilled questionnaire, so a
  # whole-file mirror would be wrong and the region scoping is load-bearing.
  tmpl_tail="$(sed -n '/^## Project-Specific/,$p' "$TEMPLATES/root/CLAUDE.md")"
  live_tail="$(sed -n '/^## Project-Specific/,$p' "$PROJECT_ROOT/CLAUDE.md")"
  printf '%s\n' "$tmpl_tail" | grep -Fq '<FILL IN'
  ! printf '%s\n' "$live_tail" | grep -Fq '<FILL IN'
  [ "$tmpl_tail" != "$live_tail" ]
}

# --------------------------------------------------------------------------
# prefix carve-out: .git/hooks/post-commit
# --------------------------------------------------------------------------

@test "R11: .git/hooks/post-commit opens with its template verbatim" {
  live_path="$PROJECT_ROOT/.git/hooks/post-commit"
  tmpl_path="$TEMPLATES/git-hooks/post-commit"
  [ -f "$tmpl_path" ]
  [ -f "$live_path" ] || skip "git hooks are untracked and not installed here"

  tmpl_len="$(wc -l < "$tmpl_path" | tr -d '[:space:]')"
  [ "$tmpl_len" -ge 20 ]

  run diff <(head -n "$tmpl_len" "$live_path") "$tmpl_path"
  [ "$status" -eq 0 ] || {
    echo "R11 drift in the mirrored part of post-commit:"
    echo "$output"
    return 1
  }

  # The only permitted extra is the repo-local auto-bump nudge (TASK-217),
  # which calls a helper that exists solely in this repo. Anything else in the
  # tail is unmirrored logic and must fail.
  tail_block="$(tail -n +"$((tmpl_len + 1))" "$live_path")"
  if [ -n "$tail_block" ]; then
    printf '%s\n' "$tail_block" | grep -Fq 'bump-version.sh'
    [ "$(printf '%s\n' "$tail_block" | wc -l)" -le 12 ]
    unexpected="$(printf '%s\n' "$tail_block" \
      | grep -vE '^$|^#|^BUMP_HELPER=|^if \[ -x "\$BUMP_HELPER" \]; then$|^[[:space:]]*"\$BUMP_HELPER" --nudge [|][|] true$|^fi$' \
      || true)"
    [ -z "$unexpected" ] || {
      echo "unmirrored trailing content in post-commit:"
      echo "$unexpected"
      return 1
    }
  fi
}

# --------------------------------------------------------------------------
# keys carve-out: .claude/settings.local.json
# --------------------------------------------------------------------------

@test "R11: settings.local.json keeps the template's JSON shape" {
  live_path="$PROJECT_ROOT/.claude/settings.local.json"
  tmpl_path="$TEMPLATES/claude/settings.local.json"
  [ -f "$tmpl_path" ]
  command -v jq >/dev/null 2>&1 || skip "jq not available"
  run jq -e . "$tmpl_path"
  [ "$status" -eq 0 ]

  # The live file is gitignored: it accumulates per-developer permission grants
  # with machine-absolute paths, so its bytes are not a repo invariant and it
  # is absent in CI. What must hold is that the starter file a bootstrapped
  # project receives still has the same shape.
  [ -f "$live_path" ] || skip "settings.local.json is a gitignored local override"

  run diff <(jq -S 'to_entries | map({key, type: (.value | type)})' "$live_path") \
           <(jq -S 'to_entries | map({key, type: (.value | type)})' "$tmpl_path")
  [ "$status" -eq 0 ] || {
    echo "settings.local.json top-level shape drifted from the template:"
    echo "$output"
    return 1
  }

  run diff <(jq -S '.permissions | keys' "$live_path") \
           <(jq -S '.permissions | keys' "$tmpl_path")
  [ "$status" -eq 0 ] || {
    echo "settings.local.json permissions keys drifted from the template:"
    echo "$output"
    return 1
  }
}

# --------------------------------------------------------------------------
# closure: the registry cannot silently miss a file
# --------------------------------------------------------------------------

@test "R11: every template file is a registered mirror or a listed non-mirror" {
  failures=""
  seen=0
  while IFS= read -r tmpl_path; do
    rel="${tmpl_path#$TEMPLATES/}"
    seen=$((seen + 1))
    in_registry "$rel" && continue
    justified=""
    while IFS= read -r entry; do
      case "$entry" in
        */) case "$rel" in "$entry"*) justified=yes ;; esac ;;
        *) [ "$rel" = "$entry" ] && justified=yes ;;
      esac
    done <<EOF
$(non_mirrored_templates)
EOF
    [ -n "$justified" ] || failures="$failures
unregistered template (add a registry row or justify it in
non_mirrored_templates): $rel"
  done <<EOF
$(find "$TEMPLATES" -type f | sort)
EOF

  [ -z "$failures" ] || {
    echo "$failures"
    return 1
  }
  [ "$seen" -ge 20 ]
}

@test "R11: every live .claude hook is mirrored or an explicit repo-local hook" {
  failures=""
  seen=0
  while IFS= read -r hook_path; do
    rel="${hook_path#$PROJECT_ROOT/}"
    seen=$((seen + 1))
    in_registry "$rel" && continue
    printf '%s\n' "$(repo_local_hooks)" | grep -Fxq "$rel" || failures="$failures
unmirrored live hook (add a template + registry row, or list it in
repo_local_hooks with a reason): $rel"
  done <<EOF
$(find "$PROJECT_ROOT/.claude/hooks" -type f | sort)
EOF

  [ -z "$failures" ] || {
    echo "$failures"
    return 1
  }
  [ "$seen" -ge 9 ]
}

# --------------------------------------------------------------------------
# exclusions, encoded as assertions about what must NOT exist
# --------------------------------------------------------------------------

@test "R11: task-reviewer-rules.md is project-specific, so it has no mirror" {
  [ -f "$PROJECT_ROOT/.claude/task-reviewer-rules.md" ]
  [ ! -e "$TEMPLATES/claude/task-reviewer-rules.md" ]
  # ralph-init ships a generic starter under a distinct name instead, so the
  # absence above is a decision rather than an oversight.
  [ -f "$TEMPLATES/claude/task-reviewer-rules.docs.md" ]
  run diff "$PROJECT_ROOT/.claude/task-reviewer-rules.md" \
           "$TEMPLATES/claude/task-reviewer-rules.docs.md"
  [ "$status" -ne 0 ]
}

@test "R11: plugin-bundled agents are distributed, not mirrored" {
  [ ! -e "$TEMPLATES/claude/agents" ]
  agents=0
  while IFS= read -r agent_path; do
    agents=$((agents + 1))
    [ ! -e "$TEMPLATES/claude/agents/$(basename "$agent_path")" ]
  done <<EOF
$(find "$PROJECT_ROOT/plugins/ralph/agents" -name '*.md' -type f | sort)
EOF
  # Anti-vacuity: the exclusion only means something while agents exist.
  [ "$agents" -ge 2 ]
}

@test "R11: the canonical orchestrators are outside the shim mirror set" {
  # ralph.sh / refine.sh are mirrored shim-to-shim only. The orchestrators they
  # resolve are the single source of truth and have no template counterpart, so
  # editing one must not be read as half of a parity pair.
  scripts="$PROJECT_ROOT/plugins/ralph/skills/ralph-run/scripts"
  [ -f "$scripts/ralph_orchestrator.py" ]
  [ -f "$scripts/refine_orchestrator.py" ]
  run in_registry "plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py"
  [ "$status" -ne 0 ]
  run in_registry "plugins/ralph/skills/ralph-run/scripts/refine_orchestrator.py"
  [ "$status" -ne 0 ]
  # Each shim mirrors its own template and nothing else: R11 does not require
  # ralph.sh and refine.sh to match each other, so there is deliberately no
  # cross-shim assertion here.
}
