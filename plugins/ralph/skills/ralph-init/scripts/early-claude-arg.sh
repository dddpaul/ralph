#!/usr/bin/env bash
# Find (check) or fix (patch) an ARG CLAUDE_CODE_VERSION declared too early in
# the final stage of an assembled .devcontainer/Dockerfile.
#
#   early-claude-arg.sh check <Dockerfile>
#       Prints one line per finding. Exit 0 = clean, 1 = early ARG found.
#   early-claude-arg.sh patch <Dockerfile>
#       Prints the patched Dockerfile on stdout; never writes the file.
#       Exit 0 = patched text printed, 1 = nothing to patch, 3 = patch by hand.
#   Exit 2 = usage error or unreadable input.
#
# A changed ARG value misses the cache for every RUN after its declaration,
# referenced or not, so a RUN between ARG CLAUDE_CODE_VERSION and the npm RUN
# that installs @anthropic-ai/claude-code@ rebuilds on every version bump. That
# is the pre-TASK-272 layout, and the rule placement_problems() in
# tests/python/test_devcontainer_claude_code_pin.py pins on the templates.
# Instructions are read with backslash continuations joined and comment lines
# dropped.
#
# patch moves the ARG line, together with the "# No default on purpose ..."
# comment lines directly above it, to just before
# LABEL dev.ralph.claude-code-version (before the npm RUN when there is no such
# LABEL). It refuses (exit 3) an ARG with a default — the pre-pin layout the
# upgrade's version-pin patch rewrites — an ARG declared more than once in the
# final stage, a missing npm RUN, and a RUN between the LABEL and the npm RUN.
set -euo pipefail

usage() {
  echo "usage: early-claude-arg.sh check|patch <Dockerfile>" >&2
  exit 2
}
[ $# -eq 2 ] || usage
mode=$1
file=$2
case $mode in check | patch) ;; *) usage ;; esac
[ -r "$file" ] || { echo "early-claude-arg: cannot read $file" >&2; exit 2; }

# shellcheck disable=SC2016  # $-fields belong to awk, not the shell
prog='
function trim(s) { sub(/^[ \t]+/, "", s); sub(/[ \t\r]+$/, "", s); return s }
function blank(s) { return s ~ /^[ \t\r]*$/ }
function keyword(i,   w) { w = trim(IT[i]); sub(/[ \t].*$/, "", w); return toupper(w) }
function by_hand(why) { print "early-claude-arg: " why "; patch by hand" > "/dev/stderr"; exit 3 }
{
  L[NR] = $0
  line = $0; sub(/\r$/, "", line)
  if (line ~ /^[ \t]*(#|$)/) next
  if (!cont) { n++; IS[n] = NR; IT[n] = "" }
  cont = (line ~ /\\[ \t]*$/)
  if (cont) sub(/\\[ \t]*$/, "", line)
  IT[n] = IT[n] " " line; IE[n] = NR
}
END {
  fs = 0
  for (i = 1; i <= n; i++) if (keyword(i) == "FROM") fs = i
  na = 0; np = 0; lb = 0
  for (i = fs + 1; i <= n; i++) {
    t = trim(IT[i])
    if (keyword(i) == "ARG" && t ~ /^[^ \t]+[ \t]+CLAUDE_CODE_VERSION([ \t=]|$)/) { na++; A[na] = i }
    else if (index(t, "@anthropic-ai/claude-code@") && np == 0) np = i
    else if (keyword(i) == "LABEL" && index(t, "dev.ralph.claude-code-version") && lb == 0) lb = i
  }
  between = 0
  if (na > 0 && np > A[1])
    for (i = A[1] + 1; i < np; i++) if (keyword(i) == "RUN") between++
  if (mode == "check") {
    if (between) printf "line %d: ARG CLAUDE_CODE_VERSION is declared %d RUN step(s) above the npm RUN on line %d; every version bump rebuilds them\n", IS[A[1]], between, IS[np]
    exit (between > 0)
  }
  if (na == 0) { print "early-claude-arg: nothing to patch" > "/dev/stderr"; exit 1 }
  if (np == 0) by_hand("no npm RUN installs @anthropic-ai/claude-code in the final stage")
  if (!between) { print "early-claude-arg: nothing to patch" > "/dev/stderr"; exit 1 }
  if (na > 1) by_hand("ARG CLAUDE_CODE_VERSION is declared " na " times in the final stage")
  a = A[1]
  if (trim(IT[a]) ~ /CLAUDE_CODE_VERSION[ \t]*=/)
    by_hand("ARG CLAUDE_CODE_VERSION has a default; the version-pin patch replaces it")
  if (IS[a] != IE[a]) by_hand("ARG CLAUDE_CODE_VERSION spans several lines")
  target = (lb > a && lb < np) ? lb : np
  for (i = target + 1; i < np; i++)
    if (keyword(i) == "RUN") by_hand("a RUN lies between LABEL dev.ralph.claude-code-version and the npm RUN")
  # The block: the ARG and the comment lines directly above it, from the
  # "No default on purpose" one; just the ARG when that comment is absent.
  bs = IS[a]
  for (k = IS[a] - 1; k >= 1 && L[k] ~ /^[ \t]*#/; k--)
    if (L[k] ~ /^[ \t]*# No default on purpose/) { bs = k; break }
  be = IS[a]
  # Drop one of the two blank lines the removal would leave next to each other.
  drop = ((bs == 1 || blank(L[bs - 1])) && be < NR && blank(L[be + 1])) ? be + 1 : 0
  at = IS[target]
  for (i = 1; i <= NR; i++) {
    if (i == at) for (k = bs; k <= be; k++) print L[k]
    if ((i >= bs && i <= be) || i == drop) continue
    print L[i]
  }
}
'
exec awk -v mode="$mode" "$prog" "$file"
