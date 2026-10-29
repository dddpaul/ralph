#!/bin/bash
# commit-msg-guard.sh — Block forbidden trailers and headings in commits and PRs
# Trigger: Bash(git commit *), Bash(gh pr create *)
# Action: deny JSON (PreToolUse)
# Input: tool_input JSON on stdin

cmd=$(jq -r '.tool_input.command')

# --- command lexer (keep identical in commit-prefix-guard.sh) -------------------
# The settings.json `if:` filter is best-effort: Claude Code still runs the
# hook for commands it cannot fully parse (unquoted $VAR, $(...), backticks).
# So split the command into simple commands and words the way the shell does
# (quotes, escapes, $(...), arithmetic, heredocs) and act only on a real
# `git commit` / `gh pr create`, never on text that merely mentions one.
# Prints nothing when there is none, else KIND, then each commit argument
# prefixed by \037, then \036 and the body of a heredoc fed to that command.
lexer='
function endword() { if (inw) { w[++nw] = cur; cur = ""; inw = 0 } }
function endcmd(   j, k) {
  endword()
  if (kind == "" && nw > 0) {
    j = 1
    while (j <= nw && (w[j] ~ /^[A-Za-z_][A-Za-z0-9_]*=/ || w[j] ~ /^(if|then|else|elif|do|while|until|time|!)$/ || w[j] == "{")) j++
    if (w[j] == "git") {
      for (j++; j <= nw && w[j] ~ /^-/; j++) if (w[j] == "-C" || w[j] == "-c") j++
      if (w[j] == "commit") { kind = "commit"; mcmd = ncmd; for (k = j + 1; k <= nw; k++) args = args US w[k] }
    } else if (w[j] == "gh" && w[j + 1] == "pr" && w[j + 2] == "create") { kind = "pr"; mcmd = ncmd }
  }
  for (k = 1; k <= nw; k++) delete w[k]
  nw = 0; ncmd++
}
function rawparen(i,   d, j, ch) {
  for (j = i + 1; j <= n; j++) {
    ch = substr(s, j, 1)
    if (ch == "(") d++
    else if (ch == ")" && --d == 0) break
  }
  cur = cur substr(s, i, j - i + 1); inw = 1
  return j + 1
}
function dquote(i,   ch, nx) {
  inw = 1
  while (i <= n) {
    ch = substr(s, i, 1); nx = substr(s, i + 1, 1)
    if (ch == dq) return i + 1
    if (ch == "\\") {
      if (nx != "\n") cur = cur (index("\"\\$`", nx) ? "" : ch) nx
      i += 2
    } else if (ch == "$" && nx == "(") i = rawparen(i)
    else { cur = cur ch; i++ }
  }
  return i
}
function heredoc(i,   dash, del, ch, e) {
  endword(); i += 2
  if (substr(s, i, 1) == "-") { dash = 1; i++ }
  while (substr(s, i, 1) == " " || substr(s, i, 1) == "\t") i++
  while (i <= n && index(" \t\n;&|<>()", ch = substr(s, i, 1)) == 0) {
    if (ch == sq || ch == dq) {
      e = index(substr(s, i + 1), ch); if (e == 0) e = n - i + 1
      del = del substr(s, i + 1, e - 1); i += e + 1
    } else if (ch == "\\") { del = del substr(s, i + 1, 1); i += 2 }
    else { del = del ch; i++ }
  }
  if (del != "") { pdel[++np] = del; pdash[np] = dash; pcmd[np] = ncmd }
  return i
}
function bodies(i,   p, e, line, t, body) {
  for (p = 1; p <= np; p++) {
    body = ""
    while (i <= n) {
      e = index(substr(s, i), "\n"); if (e == 0) e = n - i + 2
      line = substr(s, i, e - 1); i += e
      t = line; if (pdash[p]) sub(/^\t+/, "", t)
      if (t == pdel[p]) break
      body = body line "\n"
    }
    if (pcmd[p] == mcmd && kind != "" && !got) { doc = body; got = 1 }
  }
  np = 0
  return i
}
BEGIN { US = "\037"; sq = "\047"; dq = "\"" }
{ s = s (NR > 1 ? "\n" : "") $0 }
END {
  n = length(s); i = 1; ncmd = 1
  while (i <= n) {
    c = substr(s, i, 1); nx = substr(s, i + 1, 1)
    if (c == "\n") { endcmd(); i = bodies(i + 1) }
    else if (c == " " || c == "\t") { endword(); i++ }
    else if (c == "#" && !inw) { while (i <= n && substr(s, i, 1) != "\n") i++ }
    else if (c == "\\") { if (nx != "\n") { cur = cur nx; inw = 1 } i += 2 }
    else if (c == sq) {
      e = index(substr(s, i + 1), sq); if (e == 0) e = n - i + 1
      cur = cur substr(s, i + 1, e - 1); inw = 1; i += e + 1
    }
    else if (c == dq) i = dquote(i + 1)
    else if (c == "$" && nx == "(") i = rawparen(i)
    else if (c == "(" && nx == "(") { endcmd(); e = index(substr(s, i), "))"); i = e ? i + e + 1 : n + 1 }
    else if (substr(s, i, 3) == "<<<") { endword(); i += 3 }
    else if (c == "<" && nx == "<") i = heredoc(i)
    else if (c == "<" || c == ">" || (c == "&" && nx == ">")) { endword(); for (i++; index("&>|", substr(s, i, 1)) && i <= n; i++); }
    else if (index(";&|()", c)) { endcmd(); i++ }
    else { cur = cur c; inw = 1; i++ }
  }
  endcmd()
  if (kind != "") printf "%s%s\036%s", kind, args, doc
}'
parsed=$(printf '%s\n' "$cmd" | awk "$lexer")
# --- end command lexer -------------------------------------------------------
[ -n "$parsed" ] || exit 0

if echo "$cmd" | grep -qiE 'Co-Authored-By|Generated with Claude Code' ||
   echo "$cmd" | grep -qE '##[[:space:]]*Test [Pp]lan'; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: forbidden trailer/heading. Remove Co-Authored-By, Generated-with, and Test plan sections."}}'
fi
