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
# Installed via .git/hooks/pre-push.local, a thin wrapper that execs this
# tracked, reviewable script. The plugin's pre-push shim at .git/hooks/pre-push
# runs that wrapper first, with the same arguments and the buffered stdin
# (TASK-328); a clone that has not moved its pre-push yet runs the wrapper
# directly as .git/hooks/pre-push. git passes the remote name as $1 and feeds
# the hook one line per ref update on stdin:
#     <local ref> SP <local sha> SP <remote ref> SP <remote sha> LF
# For the master ref, both shas are already local at push time, so the
# remote-sha..local-sha diff needs no network.
#
# Shipped set (a change here requires a strictly-greater version; the list
# lives in lib/shipped-set.sh):
#   plugins/ralph/skills/**                     plugins/ralph/agents/**
#   plugins/ralph/hooks/**                      plugins/ralph/git-hooks/**
#   plugins/ralph/scripts/**                    plugins/ralph/user-settings.json
#   plugins/ralph/.claude-plugin/plugin.json    .claude-plugin/marketplace.json
# Excluded (docs & tooling, not shipped-and-executed): README, design/,
# backlog/, .claude/, tests/.
#
# Release tag check (TASK-319): two hosts can each bump to the same version
# with different content. The release commit of vX.Y.Z is the first commit,
# along the pushed tip's first-parent history (what becomes origin's master),
# where both manifests read X.Y.Z; when that commit is a merge bringing X.Y.Z
# in from another parent (a merge pull), that parent's release commit counts
# too. The guard refuses a master push when the two
# manifests disagree on the tip, when origin already has vX.Y.Z peeled to a
# different commit, or when origin cannot be reached within
# VERSION_GUARD_LS_REMOTE_TIMEOUT seconds (default 20). An absent tag passes
# (push.followTags carries it). An existing tag is never moved; see
# .claude/RELEASING.md for the manual re-bump.
#
# Pass-through (exit 0): non-master pushes, ranges touching no shipped-set
# file (bump check only), and the first push (remote sha all-zeros). The guard
# enforces monotonic-only (any strictly-greater version), NOT a specific
# increment size.
#
# Portability (R-INFRA-3): POSIX case-glob matching, BRE sed parse, `sort -V`
# (available on both GNU and modern BSD/macOS sort), and a sleep-loop watchdog
# instead of GNU `timeout` — no grep -P, no GNU-only flags.

set -euo pipefail

# The plugin manifest whose version gates the on-disk cache rebuild, and the
# marketplace manifest that must carry the same version.
MANIFEST="plugins/ralph/.claude-plugin/plugin.json"
MARKET_MANIFEST=".claude-plugin/marketplace.json"

# The remote being pushed to (git passes its name as $1).
REMOTE="${1:-origin}"
LS_REMOTE_TIMEOUT="${VERSION_GUARD_LS_REMOTE_TIMEOUT:-20}"

# The shipped-set predicate (is_shipped) is the single source of truth shared
# with the auto-bump helper (bump-version.sh) so the two cannot drift. Resolve
# the hooks dir to an absolute path first so the source works regardless of the
# caller's CWD (git invokes this hook from the repo root; bats from a temp dir).
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/shipped-set.sh
. "$HOOK_DIR/lib/shipped-set.sh"

# Parse the top-level (or only) "version": "X.Y.Z" from JSON read on stdin.
extract_version() {
  sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1
}

# Print the version of manifest $2 at commit $1, or nothing if unreadable.
manifest_version_at() {
  git show "$1:$2" 2>/dev/null | extract_version || true
}

# Print the plugin manifest version at a commit, or nothing if unreadable.
version_at() {
  manifest_version_at "$1" "$MANIFEST"
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

# Exit 1 when shipped-set files changed in $2..$1 without a version advance.
check_bump() { # $1=local_sha $2=remote_sha
  shipped_changed=false
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if is_shipped "$f"; then
      shipped_changed=true
      break
    fi
  done <<EOF
$(git diff --name-only "$2" "$1")
EOF
  $shipped_changed || return 0

  local_ver=$(version_at "$1")
  remote_ver=$(version_at "$2")

  if [ -z "$local_ver" ]; then
    echo "BLOCKED: cannot read plugin version at $1 ($MANIFEST)." >&2
    exit 1
  fi

  # An unreadable remote version means the manifest is newly introduced in this
  # range, so any present version is an advance — let it through.
  if [ -n "$remote_ver" ] && ! version_gt "$local_ver" "$remote_ver"; then
    echo "BLOCKED: shipped plugin files changed but the plugin version was not bumped." >&2
    echo "  version at remote tip ($2): $remote_ver" >&2
    echo "  version at local tip  ($1): $local_ver" >&2
    echo "  Bump $MANIFEST AND $MARKET_MANIFEST to a version" >&2
    echo "  strictly greater than $remote_ver (sort -V), commit, then push so" >&2
    echo "  '/plugin update' rebuilds the consumer skill cache." >&2
    exit 1
  fi
}

# Print the release commit of version $2 for tip $1: the oldest commit of the
# unbroken first-parent run, ending at the tip, where both manifests read $2.
release_commit() { # $1=tip $2=version
  release=""
  while IFS= read -r c; do
    [ -n "$c" ] || continue
    [ "$(manifest_version_at "$c" "$MANIFEST")" = "$2" ] || break
    [ "$(manifest_version_at "$c" "$MARKET_MANIFEST")" = "$2" ] || break
    release="$c"
  done <<EOF
$(git rev-list --first-parent "$1")
EOF
  printf '%s\n' "$release"
}

# True iff $3 is a release commit of version $2 for tip $1: the first-parent
# release commit, or — when that commit is a merge bringing the version in from
# another parent (a merge pull of another host's release) — a release commit
# of that parent's line.
is_release_of() { # $1=tip $2=version $3=candidate
  local rel parent
  rel=$(release_commit "$1" "$2")
  [ -n "$rel" ] || return 1
  [ "$rel" = "$3" ] && return 0
  for parent in $(git rev-list --parents -n 1 "$rel" | cut -d' ' -f3-); do
    [ "$(manifest_version_at "$parent" "$MANIFEST")" = "$2" ] || continue
    [ "$(manifest_version_at "$parent" "$MARKET_MANIFEST")" = "$2" ] || continue
    is_release_of "$parent" "$2" "$3" && return 0
  done
  return 1
}

# Run `git ls-remote` for tag $1 and its peeled ref on $REMOTE, killed after
# $LS_REMOTE_TIMEOUT seconds. Prints the listing; returns git's status (or the
# kill status on timeout).
ls_remote_tag() { # $1=tag
  GIT_TERMINAL_PROMPT=0 git ls-remote "$REMOTE" "refs/tags/$1" "refs/tags/$1^{}" &
  ls_pid=$!
  (
    i=0
    while [ "$i" -lt "$LS_REMOTE_TIMEOUT" ]; do
      sleep 1
      kill -0 "$ls_pid" 2>/dev/null || exit 0
      i=$((i + 1))
    done
    kill "$ls_pid" 2>/dev/null || true
  ) >/dev/null 2>&1 &
  watch_pid=$!
  ls_status=0
  wait "$ls_pid" || ls_status=$?
  kill "$watch_pid" 2>/dev/null || true
  wait "$watch_pid" 2>/dev/null || true
  return "$ls_status"
}

# Exit 1 when the pushed tip's version tag on $REMOTE does not peel to the
# tip's release commit, when the manifests disagree, or when $REMOTE is down.
check_release_tag() { # $1=local_sha
  plugin_ver=$(manifest_version_at "$1" "$MANIFEST")
  market_ver=$(manifest_version_at "$1" "$MARKET_MANIFEST")
  if [ "$plugin_ver" != "$market_ver" ]; then
    echo "BLOCKED: the two manifests disagree on the pushed tip ($1)." >&2
    echo "  $MANIFEST: ${plugin_ver:-<unreadable>}" >&2
    echo "  $MARKET_MANIFEST: ${market_ver:-<unreadable>}" >&2
    echo "  Set both to the same version, commit, then push." >&2
    exit 1
  fi
  [ -n "$plugin_ver" ] || return 0

  tag="v$plugin_ver"
  if ! listing=$(ls_remote_tag "$tag" 2>/dev/null); then
    echo "BLOCKED: cannot reach '$REMOTE' to check release tag $tag" >&2
    echo "  (git ls-remote failed or exceeded ${LS_REMOTE_TIMEOUT}s)." >&2
    echo "  Retry when '$REMOTE' is reachable; see .claude/RELEASING.md." >&2
    exit 1
  fi

  # A lightweight tag lists only refs/tags/vX.Y.Z; an annotated one also lists
  # the peeled refs/tags/vX.Y.Z^{}, which then wins.
  peeled=""
  while read -r sha ref; do
    case "$ref" in
      "refs/tags/$tag^{}") peeled="$sha" ;;
      "refs/tags/$tag") [ -n "$peeled" ] || peeled="$sha" ;;
    esac
  done <<EOF
$listing
EOF
  [ -n "$peeled" ] || return 0

  if ! is_release_of "$1" "$plugin_ver" "$peeled"; then
    release=$(release_commit "$1" "$plugin_ver")
    echo "BLOCKED: version conflict on $tag." >&2
    echo "  '$REMOTE' tags $tag at $peeled," >&2
    echo "  but the release commit of $plugin_ver on the pushed tip is ${release:-<none>}." >&2
    echo "  Another host released $plugin_ver with different content. Re-bump both" >&2
    echo "  manifests past $plugin_ver, commit, then push; never move $tag." >&2
    echo "  See .claude/RELEASING.md." >&2
    exit 1
  fi
}

# git hands the hook every ref update on stdin, one per line. Only the master
# ref matters; everything else passes through.
while read -r local_ref local_sha remote_ref remote_sha; do
  [ "${remote_ref:-}" = "refs/heads/master" ] || continue

  # Deleting master (local all-zeros) ships nothing.
  is_zero "${local_sha:-}" && continue

  # First push of master (remote all-zeros): nothing to compare against.
  is_zero "${remote_sha:-}" && exit 0

  check_bump "$local_sha" "$remote_sha"
  check_release_tag "$local_sha"
  exit 0
done

exit 0
