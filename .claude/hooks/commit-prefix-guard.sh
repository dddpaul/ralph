#!/bin/bash
# commit-prefix-guard.sh — Enforce task-<id> prefix on commit messages
# Trigger: Bash(git commit *)
# Action: deny JSON (PreToolUse)
# Input: tool_input JSON on stdin

cmd=$(jq -r '.tool_input.command')

# The settings.json `if:` filter is best-effort: Claude Code still runs the
# hook for commands it cannot fully parse (unquoted $VAR, $(...), backticks).
# Self-gate on a real `git commit` at a command position, ignoring text
# inside quotes and heredoc bodies, so a command that merely mentions the
# phrase (e.g. backlog notes quoting it) is never checked.
skeleton=$(printf '%s\n' "$cmd" | awk '
  BEGIN { sq = "\047"; dq = "\"" }
  inbody != "" { t = $0; sub(/^\t+/, "", t); if (t == inbody) inbody = ""; print ""; next }
  {
    out = ""; n = length($0)
    for (i = 1; i <= n; i++) {
      c = substr($0, i, 1)
      if (q == sq) { if (c == sq) q = ""; continue }
      if (q == dq) { if (c == "\\") i++; else if (c == dq) q = ""; continue }
      if (c == "\\") { i++; continue }
      if (c == sq || c == dq) { q = c; out = out "_"; continue }
      if (substr($0, i, 2) == "<<" && substr($0, i + 2, 1) != "<") {
        j = i + 2
        if (substr($0, j, 1) == "-") j++
        while (substr($0, j, 1) ~ /[ \t]/) j++
        if (substr($0, j, 1) == sq || substr($0, j, 1) == dq) j++
        w = ""
        while (substr($0, j, 1) ~ /[A-Za-z0-9_]/) { w = w substr($0, j, 1); j++ }
        if (substr($0, j, 1) == sq || substr($0, j, 1) == dq) j++
        if (w != "") { pending = w; out = out "<<_"; i = j - 1; continue }
      }
      out = out c
    }
    if (pending != "") { inbody = pending; pending = "" }
    print out
  }')
nl=$'\n'
sep="(^|[;&|(]|${nl})[[:space:]]*"
git_re="${sep}git([[:space:]]+-[Cc][[:space:]]+[^[:space:];&|]+|[[:space:]]+-[^[:space:];&|]+)*[[:space:]]+commit([[:space:];&|)]|$)"
[[ $skeleton =~ $git_re ]] || exit 0

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)
case "$branch" in task-*) ;; *) exit 0;; esac

task_id=$(echo "$branch" | grep -oE '^task-[0-9]+' | sed 's/task-//')

# Look for the message only from the commit invocation onward.
rest=$cmd
[[ $cmd =~ $git_re ]] && rest=${cmd#*"${BASH_REMATCH[0]}"}

# first_line TEXT — first non-blank line of TEXT, leading whitespace trimmed.
first_line() {
  local text=$1 line
  while [ -n "$text" ]; do
    line=${text%%"$nl"*}
    line=${line#"${line%%[![:space:]]*}"}
    if [ -n "$line" ]; then printf '%s' "$line"; return; fi
    [ "$text" = "${text#*"$nl"}" ] && return
    text=${text#*"$nl"}
  done
}

# heredoc_line TEXT — first body line of the first heredoc in TEXT.
heredoc_re="<<-?[[:space:]]*[\"']?[A-Za-z0-9_]+[\"']?[^${nl}]*${nl}(.*)$"
heredoc_line() {
  [[ $1 =~ $heredoc_re ]] && first_line "${BASH_REMATCH[1]}"
}

# Message sources, in order: -m/--message (any quoting, may span lines, may
# wrap a $(cat <<EOF) heredoc), -F/--file (named file, or - for a heredoc),
# then a bare heredoc. Multi-line values work because bash regex matching is
# not line-bound, unlike sed.
val='("(([^"\\]|\\.)*)"|'"'([^']*)'"'|([^[:space:]\"'"'"';&|]+))'
msg_re="(^|[[:space:]])(-[[:alnum:]]*m|--message)(=|[[:space:]]*)${val}"
file_re="(^|[[:space:]])(-[[:alnum:]]*F|--file)(=|[[:space:]]+)${val}"
msg=
if [[ $rest =~ $msg_re ]]; then
  value="${BASH_REMATCH[5]}${BASH_REMATCH[7]}${BASH_REMATCH[8]}"
  case "$value" in
    '$('*) msg=$(heredoc_line "$value") ;;
    *) msg=$(first_line "$value") ;;
  esac
elif [[ $rest =~ $file_re ]]; then
  file="${BASH_REMATCH[5]}${BASH_REMATCH[7]}${BASH_REMATCH[8]}"
  if [ "$file" = "-" ]; then
    msg=$(heredoc_line "$rest")
  elif [ -f "$file" ] && [ -r "$file" ]; then
    msg=$(first_line "$(cat "$file")")
  fi
else
  msg=$(heredoc_line "$rest")
fi

# No extractable message (editor, --no-edit, -C, $VAR, unreadable file):
# allow. A false deny blocks legitimate work; the git commit-msg hook still
# sees the final message.
case "$msg" in ''|'$'*) exit 0 ;; esac

if echo "$msg" | grep -qiE '^Merge branch'; then exit 0; fi

if ! echo "$msg" | grep -qE "^task-${task_id}: "; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: commit message on task-%s branch must start with `task-%s: `."}}' "$task_id" "$task_id"
fi
