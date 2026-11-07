#!/bin/bash
# clone-hooks-session-check.sh — SessionStart hook (THIS REPO ONLY, TASK-331).
# Runs install-clone-hooks.sh --check in the session's clone. When a hook is
# missing or differs, it gives the session one line naming the hooks and the
# install command through hookSpecificOutput.additionalContext; when both are in
# place it prints nothing. It never fails the session: it always exits 0.

script_dir="$(cd "$(dirname "$0")" && pwd)"
cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null || exit 0

report="$("$script_dir/install-clone-hooks.sh" --check 2>&1 >/dev/null)" && exit 0

names=""
while IFS= read -r line; do
  line="${line#install-clone-hooks: }"
  [ -n "$line" ] || continue
  names="${names:+$names; }$line"
done <<EOF
$report
EOF

msg="This clone's git hooks are not in place: $names. Run .claude/hooks/install-clone-hooks.sh once in this clone; the version-bump and release-tag guard runs only from them."
msg="$(printf '%s' "$msg" | tr -d '\000-\037' | sed 's/\\/\\\\/g; s/"/\\"/g')"
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$msg"
exit 0
