#!/bin/bash
# version-bump-guard.sh — pre-push version-bump guard (THIS REPO ONLY).
#
# Enforces a plugin version bump at the publish boundary: a push of master to
# origin. Claude Code runs plugin skills from the on-disk cache at
# ~/.claude/plugins/cache/dddpaul-ralph/ralph/<version>/, which `/plugin update`
# rebuilds ONLY when it detects a new version. If shipped skill/agent files
# change but the version stays put, update no-ops and consumers silently run a
# stale cache. This guard blocks such a push. See TASK-214.
#
# Installed via .git/hooks/pre-push (a thin wrapper that execs this tracked,
# reviewable script). git feeds the wrapper one line per ref update on stdin:
#     <local ref> SP <local sha> SP <remote ref> SP <remote sha> LF
# For the master ref, both shas are already local at push time, so the
# remote-sha..local-sha diff needs no network.
#
# Shipped set (a change here requires a strictly-greater version):
#   plugins/ralph/skills/**                     plugins/ralph/agents/**
#   plugins/ralph/.claude-plugin/plugin.json    .claude-plugin/marketplace.json
# Excluded (docs & tooling, not shipped-and-executed): README, design/,
# backlog/, .claude/.
#
# Pass-through (exit 0): non-master pushes, ranges touching no shipped-set
# file, and the first push (remote sha all-zeros). The guard enforces
# monotonic-only (any strictly-greater version), NOT a specific increment size.
#
# Portability (R5): POSIX case-glob matching, BRE sed parse, and `sort -V`
# (available on both GNU and modern BSD/macOS sort) — no grep -P, no GNU-only
# flags.

set -euo pipefail

# The plugin manifest whose version gates the on-disk cache rebuild.
MANIFEST="plugins/ralph/.claude-plugin/plugin.json"

# Is a repo-relative path part of the shipped-and-executed plugin surface?
is_shipped() {
  case "$1" in
    plugins/ralph/skills/*) return 0 ;;
    plugins/ralph/agents/*) return 0 ;;
    plugins/ralph/.claude-plugin/plugin.json) return 0 ;;
    .claude-plugin/marketplace.json) return 0 ;;
    *) return 1 ;;
  esac
}

# Parse the top-level (or only) "version": "X.Y.Z" from JSON read on stdin.
extract_version() {
  sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1
}

# Print the manifest version at a commit, or nothing if it cannot be read.
version_at() {
  git show "$1:$MANIFEST" 2>/dev/null | extract_version || true
}

# True iff $1 is strictly greater than $2 under version sort (sort -V).
version_gt() {
  [ "$1" = "$2" ] && return 1
  highest=$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -n1)
  [ "$highest" = "$1" ]
}

# A git null object name is all zeros (branch creation / deletion). Treat an
# empty field the same way. Returns 0 (true) when $1 is all-zeros or empty.
is_zero() {
  case "$1" in
    *[!0]*) return 1 ;;
    *) return 0 ;;
  esac
}

# git hands the hook every ref update on stdin, one per line. Only the master
# ref matters; everything else passes through.
while read -r local_ref local_sha remote_ref remote_sha; do
  [ "${remote_ref:-}" = "refs/heads/master" ] || continue

  # Deleting master (local all-zeros) ships nothing.
  is_zero "${local_sha:-}" && continue

  # First push of master (remote all-zeros): nothing to compare against.
  is_zero "${remote_sha:-}" && exit 0

  # Did any shipped-set file change between the remote tip and what we push?
  shipped_changed=false
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if is_shipped "$f"; then
      shipped_changed=true
      break
    fi
  done <<EOF
$(git diff --name-only "$remote_sha" "$local_sha")
EOF
  $shipped_changed || exit 0

  local_ver=$(version_at "$local_sha")
  remote_ver=$(version_at "$remote_sha")

  if [ -z "$local_ver" ]; then
    echo "BLOCKED: cannot read plugin version at $local_sha ($MANIFEST)." >&2
    exit 1
  fi

  # An unreadable remote version means the manifest is newly introduced in this
  # range, so any present version is an advance — let it through.
  if [ -n "$remote_ver" ] && ! version_gt "$local_ver" "$remote_ver"; then
    echo "BLOCKED: shipped plugin files changed but the plugin version was not bumped." >&2
    echo "  version at remote tip ($remote_sha): $remote_ver" >&2
    echo "  version at local tip  ($local_sha): $local_ver" >&2
    echo "  Bump $MANIFEST AND .claude-plugin/marketplace.json to a version" >&2
    echo "  strictly greater than $remote_ver (sort -V), commit, then push so" >&2
    echo "  '/plugin update' rebuilds the consumer skill cache." >&2
    exit 1
  fi

  exit 0
done

exit 0
