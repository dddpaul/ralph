#!/usr/bin/env bash
# Find (check) or fix (patch) a foreign language runtime copied over /usr/local
# in an assembled .devcontainer/Dockerfile.
#
#   stale-runtime-copy.sh check <Dockerfile>
#       Prints one line per offending COPY. Exit 0 = clean, 1 = stale copy found.
#   stale-runtime-copy.sh patch <Dockerfile>
#       Prints the patched Dockerfile on stdout; never writes the file.
#       Exit 0 = patched text printed, 1 = nothing to patch, 3 = patch by hand.
#   Exit 2 = usage error or unreadable input.
#
# The rule is the one tests/python/test_devcontainer_python_runtime.py pins on
# the fragments: a COPY --from=<stage or image> whose source is /usr/local,
# /usr/local/bin, /usr/local/lib or a path below bin/lib is stale unless the
# stage image and the devcontainer's base image (the last FROM) pin the SAME
# explicit Debian suite. An unpinned side never matches. /usr/local/go and the
# single-file uv copy are not guarded.
#
# patch replaces the stage block (the FROM ... AS <stage> line and the ###
# banner directly above it) with the current Dockerfile.lang.<flavour>, and the
# paragraph holding the COPY with the first paragraph of the current
# Dockerfile.install.<flavour>. The flavour is docs when the file carries the
# "# ---- Documentation Tools ----" block, python when the stage image is a
# python:* image; anything else is left for the user (exit 3), as is a copy
# paragraph holding anything but comments and COPY lines. Both fragments are
# read before anything is printed, so a failed read prints nothing.
set -euo pipefail

usage() {
  echo "usage: stale-runtime-copy.sh check|patch <Dockerfile>" >&2
  exit 2
}
[ $# -eq 2 ] || usage
mode=$1
file=$2
case $mode in check | patch) ;; *) usage ;; esac
[ -r "$file" ] || { echo "stale-runtime-copy: cannot read $file" >&2; exit 2; }
here=$(cd "$(dirname "$0")" && pwd)
lang_dir=${RALPH_LANG_DIR:-$here/../templates/devcontainer/lang}

# shellcheck disable=SC2016  # $-fields belong to awk, not the shell
prog='
function suite_of(ref,   i) {
  for (i = 1; i <= ns; i++) if (index(ref, S[i])) return S[i]
  return ""
}
function guarded(src) {
  return src == "/usr/local" || src ~ /^\/usr\/local\/(bin|lib)(\/.*)?$/
}
function blank(s) { return s ~ /^[ \t]*$/ }
function slurp(path, first_paragraph_only,   line, out, n, rc) {
  out = ""; n = 0
  while ((rc = (getline line < path)) > 0) {
    if (first_paragraph_only && blank(line)) break
    out = out line "\n"; n++
  }
  close(path)
  if (rc < 0 || n == 0) { print "stale-runtime-copy: cannot read " path > "/dev/stderr"; exit 2 }
  return out
}
function by_hand(why) { print "stale-runtime-copy: " why "; patch by hand" > "/dev/stderr"; exit 3 }
BEGIN { ns = split("buster bullseye bookworm trixie forky sid", S, " ") }
{ L[NR] = $0 }
toupper($1) == "FROM" && NF > 1 { base = $2; basel = NR }
toupper($1) == "FROM" && NF >= 4 && toupper($3) == "AS" { stage[$4] = $2; stagel[$4] = NR }
toupper($1) == "COPY" {
  origin = ""; src = ""
  for (i = 2; i <= NF; i++) {
    if ($i ~ /^--from=/) origin = substr($i, 8)
    else if ($i !~ /^--/) { src = $i; break }
  }
  if (origin != "" && guarded(src)) { nc++; CL[nc] = NR; CO[nc] = origin; CS[nc] = src }
}
END {
  bs = suite_of(base)
  for (c = 1; c <= nc; c++) {
    if (CL[c] < basel) continue
    o = CO[c]
    img = (o ~ /[:\/]/ || !(o in stage)) ? o : stage[o]
    s = suite_of(img)
    if (bs == "" || s != bs) {
      nv++; V[nv] = c; VI[nv] = img
      msg[nv] = sprintf("line %d: COPY --from=%s %s — stage image %s suite %s vs base %s suite %s", \
        CL[c], o, CS[c], "\047" img "\047", "\047" (s == "" ? "unpinned" : s) "\047", \
        "\047" base "\047", "\047" (bs == "" ? "unpinned" : bs) "\047")
    }
  }
  if (mode == "check") {
    for (v = 1; v <= nv; v++) print msg[v]
    exit (nv > 0)
  }
  if (nv == 0) { print "stale-runtime-copy: nothing to patch" > "/dev/stderr"; exit 1 }
  if (nv > 1) by_hand("more than one stale copy")
  flavour = ""
  for (i = 1; i <= NR; i++) if (L[i] ~ /^# ---- Documentation Tools ----\r?$/) flavour = "docs"
  if (flavour == "" && VI[1] ~ /(^|\/)python:/) flavour = "python"
  if (flavour == "") by_hand("no current fragment replaces stage image " VI[1])
  c = V[1]; cl = CL[c]; o = CO[c]
  ss = 0; se = -1
  if (o !~ /[:\/]/ && (o in stage)) {
    se = stagel[o]; ss = se
    while (ss > 1 && L[ss - 1] ~ /^###/) ss--
  }
  # The copy paragraph: bounded by blank lines and never reaching the base FROM.
  ps = cl; while (ps > basel + 1 && !blank(L[ps - 1])) ps--
  pe = cl; while (pe < NR && !blank(L[pe + 1])) pe++
  for (i = ps; i <= pe; i++)
    if (L[i] !~ /^[ \t]*#/ && toupper(substr(L[i], 1, 5)) != "COPY ")
      by_hand("line " i " shares a paragraph with the stale copy")
  if (se >= ps) by_hand("the stale stage is not above the devcontainer stage")
  lang_text = slurp(lang_dir "/Dockerfile.lang." flavour, 0)
  install_text = slurp(lang_dir "/Dockerfile.install." flavour, 1)
  for (i = 1; i <= NR; i++) {
    if (i == ss) printf "%s", lang_text
    if (i == ps) printf "%s", install_text
    if ((i >= ss && i <= se) || (i >= ps && i <= pe)) continue
    print L[i]
  }
}
'
exec awk -v mode="$mode" -v lang_dir="$lang_dir" "$prog" "$file"
