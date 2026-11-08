#!/bin/bash
# install-clone-hooks.sh — install this repo's two per-clone git hooks (THIS
# REPO ONLY, TASK-331). Nothing under .git/ is committable, so each clone has to
# install them once, after `migrate-plugin-hooks.sh clone`:
#
#   pre-push     the TASK-214 wrapper that execs .claude/hooks/version-bump-guard.sh
#                (shipped-change bump check + TASK-319 release-tag check). It goes
#                to pre-push.local when pre-push is the plugin shim (TASK-328), or
#                to pre-push when the clone has no pre-push yet.
#   post-commit  the TASK-217 bump nudge, as post-commit.local behind the plugin
#                shim. post-commit must already be the shim.
#
# Usage: install-clone-hooks.sh [--check]
#   (no flag)  install what is missing. A hook file that differs from what this
#              script would install is left untouched and named on stderr; the
#              run then exits 1. A second run changes nothing and exits 0.
#   --check    change nothing; exit 0 when both hooks are in place, else name
#              each missing or differing hook on stderr and exit 1. The
#              SessionStart hook clone-hooks-session-check.sh runs this.
#
# Problem lines read "install-clone-hooks: <hook file>: <problem>".
# Works on the clone holding $PWD; the hooks dir is `git rev-parse --git-path hooks`.

set -u

script_dir="$(cd "$(dirname "$0")" && pwd)"
SHIM="$script_dir/../../plugins/ralph/skills/ralph-init/templates/shims/git-hook"
SHIPPED="$script_dir/../../plugins/ralph/skills/ralph-init/scripts/shipped-git-hooks.sha256"

check=0
case "${1:-}" in
  '') ;;
  --check) check=1 ;;
  *)
    echo "usage: install-clone-hooks.sh [--check]" >&2
    exit 2
    ;;
esac

hooks_dir="$(git rev-parse --git-path hooks 2>/dev/null)" || {
  echo "install-clone-hooks: $PWD is not inside a git work tree" >&2
  exit 2
}
if [ ! -f "$SHIM" ]; then
  echo "install-clone-hooks: plugin shim $SHIM not found" >&2
  exit 2
fi

wrapper_content() {
  cat <<'EOF'
#!/bin/bash
# pre-push wrapper (TASK-214). Standard hook location, so any other pre-push
# tooling keeps working. Delegates to the tracked, reviewable guard — nothing
# under .git/ is committable, so the guard SOURCE lives in .claude/hooks/ and
# this wrapper is installed once.
exec "$(git rev-parse --show-toplevel)/.claude/hooks/version-bump-guard.sh" "$@"
EOF
}

nudge_content() {
  cat <<'EOF'
#!/usr/bin/env bash
# This repo's addition to the plugin post-commit hook, run first by the
# plugin shim (TASK-302). The plugin's post-commit body records the commit in
# the task notes; this file only adds the version-bump reminder.
#
# TASK-217: non-blocking auto-bump nudge. If this commit touched a shipped
# plugin file but the plugin version is not yet ahead of master, remind to run
# the auto-bump helper before pushing (so the pre-push version guard passes).
# The helper self-gates (silent on master, when nothing shipped changed, or
# once already bumped) and never blocks; post-commit exit status is ignored.
BUMP_HELPER="$(git rev-parse --show-toplevel)/.claude/hooks/bump-version.sh"
if [ -x "$BUMP_HELPER" ]; then
    "$BUMP_HELPER" --nudge || true
fi
exit 0
EOF
}

tmp="$(mktemp "${TMPDIR:-/tmp}/install-clone-hooks.XXXXXX")" || exit 2
trap 'rm -f "$tmp"' EXIT
failed=0

problem() {
  echo "install-clone-hooks: $1: $2" >&2
  failed=1
}

# SHA-256 of stdin, hex only: shasum on macOS, sha256sum on GNU systems.
sha256() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | cut -d' ' -f1
  else
    sha256sum | cut -d' ' -f1
  fi
}

# Succeed when $1 is the checkout's shim or any shim version recorded in
# shipped-git-hooks.sha256, so a clone not yet refreshed with
# migrate-plugin-hooks.sh clone still passes (TASK-341).
is_shim() {
  [ -f "$1" ] || return 1
  cmp -s "$1" "$SHIM" && return 0
  [ -r "$SHIPPED" ] && grep -Fxq -- "shim $(sha256 <"$1")" "$SHIPPED"
}

# ensure <path> <content-function>: install <path> when absent, accept it when
# it already holds the content and is executable, report it otherwise.
ensure() {
  local path="$1" fn="$2"
  "$fn" >"$tmp"
  if [ -e "$path" ] || [ -L "$path" ]; then
    if ! cmp -s "$path" "$tmp"; then
      problem "$path" "differs from the hook this script installs; left untouched"
    elif [ ! -x "$path" ]; then
      problem "$path" "is not executable; left untouched"
    fi
    return 0
  fi
  if [ "$check" -eq 1 ]; then
    problem "$path" "missing"
    return 0
  fi
  mkdir -p "$hooks_dir" && cp "$tmp" "$path.tmp.$$" && chmod 755 "$path.tmp.$$" &&
    mv "$path.tmp.$$" "$path" || {
    rm -f "$path.tmp.$$"
    problem "$path" "could not be written"
    return 0
  }
  echo "install-clone-hooks: installed $path"
}

if is_shim "$hooks_dir/pre-push"; then
  ensure "$hooks_dir/pre-push.local" wrapper_content
else
  ensure "$hooks_dir/pre-push" wrapper_content
fi

if is_shim "$hooks_dir/post-commit"; then
  ensure "$hooks_dir/post-commit.local" nudge_content
else
  problem "$hooks_dir/post-commit" "is not the plugin shim; run migrate-plugin-hooks.sh clone first"
fi

exit "$failed"
