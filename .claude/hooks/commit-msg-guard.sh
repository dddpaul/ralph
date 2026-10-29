#!/bin/bash
# commit-msg-guard.sh — Block forbidden trailers and headings in commits and PRs
# Trigger: Bash(git commit *), Bash(gh pr create *)
# Action: deny JSON (PreToolUse)
# Input: tool_input JSON on stdin

cmd=$(jq -r '.tool_input.command')

# The settings.json `if:` filter is best-effort: Claude Code still runs the
# hook for commands it cannot fully parse (unquoted $VAR, $(...), backticks).
# Self-gate on a real `git commit` / `gh pr create` at a command position,
# ignoring text inside quotes and heredoc bodies, so a command that merely
# mentions the forbidden names is never denied.
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
pr_re="${sep}gh[[:space:]]+pr[[:space:]]+create([[:space:];&|)]|$)"
[[ $skeleton =~ $git_re || $skeleton =~ $pr_re ]] || exit 0

if echo "$cmd" | grep -qiE 'Co-Authored-By|Generated with Claude Code' ||
   echo "$cmd" | grep -qE '##[[:space:]]*Test [Pp]lan'; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: forbidden trailer/heading. Remove Co-Authored-By, Generated-with, and Test plan sections."}}'
fi
