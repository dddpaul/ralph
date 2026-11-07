#!/bin/bash
# autonomous-create-guard.sh — Refuse task creation during an autonomous run in
#   a clone that enforces the shared-backlog protocol.
# Trigger: Bash (all), Skill (all)
# Action: exit 2 with the reason on stderr (PreToolUse)
# Input: hook input JSON on stdin
#
# A task ID becomes visible only after `shared-backlog.sh create` has pushed it,
# and an autonomous run (the container in particular) must not publish one, so
# it records follow-ups in its task notes instead. This guard refuses
# `backlog task create`, `backlog draft create` and `backlog draft promote`
# (anywhere in a compound command, so also after a cd into another repo),
# `shared-backlog.sh create` and the ralph:ralph-handoff skill when RALPH_AUTONOMOUS=1 and the run's clone has ralph.sharedBacklog
# true. hooks.json calls it directly, not through run.sh: it is not subject to
# the pluginHooks marker or localGuards. The run's clone is the git root of
# CLAUDE_PROJECT_DIR, never the command's cwd. Best effort, like every plugin
# hook: a command spelled in a way the patterns below miss is not refused, and a
# line of a multi-line string that starts with `backlog task create` is. A
# promote allocates the next task ID; a draft create allocates a DRAFT-N ID from
# a per-clone counter, which another host can allocate too.

unset CDPATH

[ "${RALPH_AUTONOMOUS:-}" = 1 ] || exit 0

dir=${CLAUDE_PROJECT_DIR:-${RALPH_PROJECT_ROOT:-.}}
root=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null) || exit 0
[ "$(git -C "$root" config --bool --get ralph.sharedBacklog 2>/dev/null)" = true ] || exit 0

jq_bin=$(command -v jq 2>/dev/null) || jq_bin=$(git -C "$root" config ralph.jq 2>/dev/null) || jq_bin=
if [ -z "$jq_bin" ] || [ ! -x "$jq_bin" ]; then
  echo "ralph hooks: jq not found (PATH or git config ralph.jq); autonomous-create-guard skipped" >&2
  exit 1
fi

input=$(cat)
tool=$(printf '%s' "$input" | "$jq_bin" -r '.tool_name // empty' 2>/dev/null)
skill=$(printf '%s' "$input" | "$jq_bin" -r '.tool_input.skill // empty' 2>/dev/null)
cmd=$(printf '%s' "$input" | "$jq_bin" -r '.tool_input.command // empty' 2>/dev/null)

what=
case "$tool:$skill" in
  Skill:ralph:ralph-handoff | Skill:ralph-handoff) what="the ralph:ralph-handoff skill" ;;
esac

if [ -z "$what" ] && [ -n "$cmd" ]; then
  # `backlog task create`, `backlog draft create` and `backlog draft promote` in
  # command position: at a line start or after a shell separator, past any
  # VAR=value assignments, wrapper words (sh -c "..." too) and a path prefix.
  sep='(^|[;&|({`!]|\$\()'
  lead='[[:space:]]*([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*'
  wrap='((then|do|else|time|command|exec|env|nohup|sudo|npx|bunx|xargs)[[:space:]]+|(ba|z)?sh[[:space:]]+-c[[:space:]]+["'"'"']?)*'
  backlog_cmd="${sep}${lead}${wrap}([^[:space:];&|()]*/)?backlog[[:space:]]+"
  backlog_create="${backlog_cmd}tasks?[[:space:]]+create([[:space:]]|$)"
  draft_create="${backlog_cmd}draft[[:space:]]+create([[:space:]]|$)"
  draft_promote="${backlog_cmd}draft[[:space:]]+promote([[:space:]]|$)"
  # The script name is distinctive enough to match anywhere, quoted or not.
  shared_create="shared-backlog\\.sh[\"']?[[:space:]]+create([[:space:]]|$)"
  if printf '%s\n' "$cmd" | grep -Eq "$shared_create"; then
    what="shared-backlog.sh create"
  elif printf '%s\n' "$cmd" | grep -Eq "$backlog_create"; then
    what="backlog task create"
  elif printf '%s\n' "$cmd" | grep -Eq "$draft_promote"; then
    what="backlog draft promote"
  elif printf '%s\n' "$cmd" | grep -Eq "$draft_create"; then
    what="backlog draft create"
  fi
fi

[ -n "$what" ] || exit 0

echo "BLOCKED: $what during an autonomous run: this clone enforces the shared-backlog protocol (git config ralph.sharedBacklog true), and an autonomous run must not allocate a task ID. Record the follow-up in the current task's notes instead (backlog task edit <id> --append-notes \"Follow-up: ...\"); a person creates the task later." >&2
exit 2
