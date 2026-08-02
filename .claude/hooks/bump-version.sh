#!/bin/bash
# bump-version.sh — per-task auto-bump of the ralph plugin version when shipped
# plugin files change (THIS REPO ONLY). See TASK-217 for the design rationale.
#
# Claude Code runs plugin skills from an on-disk cache that `/plugin update`
# rebuilds ONLY on a version increase; the TASK-214 pre-push guard therefore
# blocks a master push that changes shipped files without a strictly-greater
# version. That guard is correct but manual, stalling autonomous loops. This
# helper performs the bump with no human in the loop, invoked as two explicit
# Task-Lifecycle Merge-step actions: `--auto` (on the task branch, pre-merge)
# and `--tag` (on master, post-merge).
#
# Modes:
#   --auto              Bump iff a shipped-set path changed in master..HEAD.
#                       Infers the increment (a newly-added skill dir or agent
#                       file -> minor; otherwise patch; major never auto), sets
#                       BOTH manifests to (local master version + increment),
#                       and commits with a branch-aware single-line message.
#                       No-op when nothing shipped changed or HEAD's version is
#                       already ahead of master (idempotent).
#   patch|minor|major   Force the increment (overrides --auto inference). major
#                       is never chosen automatically but may be requested here.
#   --tag               Create an annotated tag vX.Y.Z on HEAD when absent
#                       (no-op if present); also ensures push.followTags=true so
#                       the tag rides the normal `git push origin master`.
#   --nudge             Non-blocking: print one reminder line when HEAD touched
#                       shipped files but the version is not yet ahead of
#                       master. Always exits 0. Used by the post-commit hook.
#   --no-commit         With --auto / patch|minor|major: edit + stage the two
#                       manifests but do not commit.
#
# Why compare against LOCAL master, not origin/master: the guard only needs one
# version above origin for the whole unpushed range, and local master is always
# >= origin (git's non-fast-forward rejection stops a behind-push first). So a
# local bump guarantees HEAD > master >= origin — the guard passes with no
# network fetch, no staleness, and per-task semantic increments.
#
# Portability (R5): POSIX case-glob, BRE sed, `sort -V` (GNU + modern BSD),
# awk match/substr for the in-place edit — no GNU-only sed addresses, no
# grep -P, no readlink -f.

set -euo pipefail

# Resolve the hooks dir to an absolute path (independent of CWD) so the shared
# predicate sources cleanly whether invoked from the repo root or a bats tempdir.
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/shipped-set.sh
. "$HOOK_DIR/lib/shipped-set.sh"

# The two manifests carrying the gating version (kept identical).
PLUGIN_MANIFEST="plugins/ralph/.claude-plugin/plugin.json"
MARKET_MANIFEST=".claude-plugin/marketplace.json"
# Local reference the bump is computed against (never origin — see header).
BASE_REF="master"

usage() {
  cat <<'EOF'
Usage: bump-version.sh <mode> [--no-commit]
Modes:
  --auto              Bump both manifests (patch, or minor for a newly-added
                      skill dir / agent file) vs local master and commit, iff a
                      shipped plugins/ralph/** path changed in master..HEAD.
                      No-op otherwise / when already ahead of master.
  patch|minor|major   Force the increment (overrides --auto inference).
  --tag               Create annotated tag vX.Y.Z on HEAD if absent; ensure
                      push.followTags=true.
  --nudge             Non-blocking reminder when HEAD touched shipped files but
                      the version is not yet ahead of master (always exit 0).
  --no-commit         With --auto / patch|minor|major: edit + stage, no commit.
See TASK-217 for the design rationale.
EOF
}

# --- version helpers -------------------------------------------------------

# Parse the first "version": "X.Y.Z" from JSON on stdin.
extract_version() {
  sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1
}

# Plugin version recorded at a git ref (empty if unreadable).
version_at() {
  git show "$1:$PLUGIN_MANIFEST" 2>/dev/null | extract_version || true
}

# Plugin version in the working tree.
current_version() {
  extract_version < "$PLUGIN_MANIFEST"
}

# True iff $1 is strictly greater than $2 under version sort (sort -V).
version_gt() {
  [ "$1" = "$2" ] && return 1
  highest=$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -n1)
  [ "$highest" = "$1" ]
}

# Echo the version obtained by applying an increment to a semver X.Y.Z.
bump_semver() { # $1=version $2=patch|minor|major
  major="${1%%.*}"
  rest="${1#*.}"
  minor="${rest%%.*}"
  patch="${rest#*.}"
  case "$2" in
    major) major=$((major + 1)); minor=0; patch=0 ;;
    minor) minor=$((minor + 1)); patch=0 ;;
    patch) patch=$((patch + 1)) ;;
    *) echo "bump-version: bad increment: $2" >&2; return 1 ;;
  esac
  printf '%s.%s.%s' "$major" "$minor" "$patch"
}

# Replace only the FIRST "version": "..." in a file (top-level in plugin.json,
# metadata.version in marketplace.json — both the gating field). awk match/substr
# is portable, unlike GNU sed's `0,/re/` first-match address.
set_version_in() { # $1=file $2=new_version
  tmp="$1.bump.tmp"
  awk -v ver="$2" '
    !done && match($0, /"version"[[:space:]]*:[[:space:]]*"[^"]*"/) {
      $0 = substr($0, 1, RSTART - 1) "\"version\": \"" ver "\"" substr($0, RSTART + RLENGTH)
      done = 1
    }
    { print }
  ' "$1" > "$tmp" && mv "$tmp" "$1"
}

# --- diff classification ---------------------------------------------------

# True iff any shipped-set path changed in master..HEAD.
shipped_changed_in_range() {
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    is_shipped "$f" && return 0
  done <<EOF
$(git diff --name-only "$BASE_REF"..HEAD)
EOF
  return 1
}

# Echo the inferred increment for master..HEAD: minor when a newly-added
# (--diff-filter=A) path under skills/ or agents/ is present, else patch.
# major is never inferred.
infer_increment() {
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
      plugins/ralph/skills/*|plugins/ralph/agents/*) echo minor; return 0 ;;
    esac
  done <<EOF
$(git diff --name-only --diff-filter=A "$BASE_REF"..HEAD)
EOF
  echo patch
}

# True iff the working-tree version is already strictly greater than master's
# (the bump already happened on this branch — idempotence guard).
already_ahead() {
  mv=$(version_at "$BASE_REF")
  cv=$(current_version)
  [ -n "$mv" ] && [ -n "$cv" ] || return 1
  version_gt "$cv" "$mv"
}

# --- modes -----------------------------------------------------------------

do_auto() { # $1=forced increment ("" to infer)  $2=commit? (true/false)
  forced="$1"; do_commit="$2"

  if ! shipped_changed_in_range; then
    echo "bump-version: no shipped-set file changed in $BASE_REF..HEAD; nothing to bump."
    return 0
  fi
  if already_ahead; then
    echo "bump-version: version already ahead of $BASE_REF ($(current_version)); no-op."
    return 0
  fi

  base_ver=$(version_at "$BASE_REF")
  if [ -z "$base_ver" ]; then
    echo "bump-version: cannot read $BASE_REF version ($PLUGIN_MANIFEST)." >&2
    return 1
  fi
  if [ -n "$forced" ]; then increment="$forced"; else increment=$(infer_increment); fi
  target=$(bump_semver "$base_ver" "$increment")

  set_version_in "$PLUGIN_MANIFEST" "$target"
  set_version_in "$MARKET_MANIFEST" "$target"
  git add "$PLUGIN_MANIFEST" "$MARKET_MANIFEST"

  if [ "$do_commit" != true ]; then
    echo "bump-version: staged $PLUGIN_MANIFEST + $MARKET_MANIFEST at $target ($increment); no commit."
    return 0
  fi

  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')
  task_id=$(printf '%s' "$branch" | sed -n 's/^task-\([0-9][0-9]*\).*/\1/p')
  if [ -n "$task_id" ]; then
    msg="task-${task_id}: bump plugin version to ${target} (${increment})"
  else
    msg="bump plugin version to ${target} (${increment})"
  fi
  git commit -q -m "$msg"
  echo "bump-version: committed -> $msg"
}

do_tag() {
  # The annotated tag rides the normal autonomous push via push.followTags.
  git config push.followTags true

  ver=$(current_version)
  if [ -z "$ver" ]; then
    echo "bump-version: cannot read version for tag ($PLUGIN_MANIFEST)." >&2
    return 1
  fi
  tag="v${ver}"
  if git rev-parse -q --verify "refs/tags/${tag}" >/dev/null 2>&1; then
    echo "bump-version: tag ${tag} already exists; no-op."
    return 0
  fi
  git tag -a "${tag}" -m "ralph ${ver}"
  echo "bump-version: created annotated tag ${tag} on $(git rev-parse --short HEAD)."
}

do_nudge() {
  # Non-blocking reminder for the interactive/task-branch flow. Always exit 0.
  head=$(git rev-parse --verify -q HEAD 2>/dev/null) || return 0
  base=$(git rev-parse --verify -q "$BASE_REF" 2>/dev/null) || return 0
  [ "$head" = "$base" ] && return 0   # on master / at the merge commit -> silent

  touched=false
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if is_shipped "$f"; then touched=true; break; fi
  done <<EOF
$(git diff-tree --no-commit-id --name-only -r HEAD)
EOF
  $touched || return 0

  already_ahead && return 0   # already bumped -> no reminder needed

  echo "bump-version: shipped file changed but plugin version is not ahead of ${BASE_REF} -> run .claude/hooks/bump-version.sh --auto before pushing (suggested: $(infer_increment))."
  return 0
}

# --- argument parsing ------------------------------------------------------

mode=""
forced=""
do_commit=true
while [ $# -gt 0 ]; do
  case "$1" in
    --auto) mode="auto" ;;
    patch|minor|major) mode="auto"; forced="$1" ;;
    --tag) mode="tag" ;;
    --nudge) mode="nudge" ;;
    --no-commit) do_commit=false ;;
    -h|--help) usage; exit 0 ;;
    *) echo "bump-version: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ -z "$mode" ]; then
  echo "bump-version: no mode given (expected --auto, patch|minor|major, --tag, or --nudge)." >&2
  usage >&2
  exit 2
fi

# Operate from the repo root so the relative manifest paths resolve uniformly.
cd "$(git rev-parse --show-toplevel)"

case "$mode" in
  auto) do_auto "$forced" "$do_commit" ;;
  tag) do_tag ;;
  nudge) do_nudge ;;
esac
