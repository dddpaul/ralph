#!/bin/bash
# naming-guard.sh — Guard backlog artifact titles and branch names
# Trigger: Bash(backlog task create *), Bash(backlog task edit *),
#          Bash(backlog doc create *), Bash(backlog decision create *),
#          Bash(backlog draft create *), Bash(git checkout -b *)
# Action: deny JSON (PreToolUse)
# Input: tool_input JSON on stdin
#
# Two rules, both rooted in the fact that artifact filenames are derived from
# titles:
#   1. ASCII — a non-ASCII title yields a non-ASCII filename (NFC/NFD drift,
#      broken sync targets).
#   2. Length — a title over 100 characters yields a filename that blows the
#      125-byte cap enforced at commit time by filename-length-guard.sh. The
#      tightest artifact overhead is `decision-9999 - <title>.md` (19 bytes),
#      leaving 106 of title room; 100 is the round cap covering every artifact
#      type. The title->slug transform never expands (alphanumerics pass 1:1,
#      spaces collapse to single dashes, other symbols are dropped), so the raw
#      title is a sound upper bound needing no slugify replication here.
#
# This hook is prevention, not the guarantee: filename-length-guard.sh in
# pre-commit is the backstop that catches anything this extraction misses.

TITLE_MAX=100

cmd=$(jq -r '.tool_input.command')

# Extract the first double- or single-quoted string after a command prefix.
# $1 = POSIX BRE matching the prefix (kept BRE for BSD/GNU sed parity, R5).
extract_quoted() {
  prefix="$1"
  out=$(printf '%s' "$cmd" | sed -n "s/^${prefix}[[:space:]]*\"\([^\"]*\)\".*/\1/p")
  if [ -z "$out" ]; then
    out=$(printf '%s' "$cmd" | sed -n "s/^${prefix}[[:space:]]*'\([^']*\)'.*/\1/p")
  fi
  printf '%s' "$out"
}

target=""
kind=""

# --- Artifact creation: `backlog <noun> create "<title>"` -------------------
for noun in task doc decision draft; do
  [ -n "$target" ] && break
  target=$(extract_quoted "backlog[[:space:]]\{1,\}${noun}[[:space:]]\{1,\}create")
  [ -n "$target" ] && kind="title"
done

# --- Rename: `backlog task edit <id> --title "<t>"` (also -t) ---------------
# The title is not the first argument here, so anchor on the flag. The leading
# `[[:space:]]` keeps `--type` and `--title` from matching the `-t` form.
if [ -z "$target" ]; then
  edit_prefix="backlog[[:space:]]\{1,\}task[[:space:]]\{1,\}edit[[:space:]]"
  target=$(extract_quoted "${edit_prefix}.*[[:space:]]--title")
  if [ -z "$target" ]; then
    target=$(extract_quoted "${edit_prefix}.*[[:space:]]-t")
  fi
  [ -n "$target" ] && kind="title"
fi

# --- Branch name: `git checkout -b <name>` ---------------------------------
if [ -z "$target" ]; then
  target=$(printf '%s' "$cmd" | sed -n 's/^git checkout -b[[:space:]]*\([^[:space:]]*\).*/\1/p')
  [ -n "$target" ] && kind="branch"
fi

[ -z "$target" ] && exit 0

if printf '%s' "$target" | LC_ALL=C grep -q '[^[:print:][:space:]]'; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: title/branch must be ASCII English (filenames are derived from titles). Put translations in -d or --ac."}}'
  exit 0
fi

# Only titles feed the artifact-filename budget; branch names do not.
if [ "$kind" = "title" ] && [ "${#target}" -gt "$TITLE_MAX" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: title is %d chars, max %d — artifact filenames are derived from titles and must stay within the 125-byte cap. Shorten the title and move the detail into -d or --ac."}}\n' \
    "${#target}" "$TITLE_MAX"
  exit 0
fi

exit 0
