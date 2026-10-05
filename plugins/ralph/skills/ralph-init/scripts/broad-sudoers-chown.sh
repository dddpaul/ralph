#!/usr/bin/env bash
# Find (check) or fix (patch) a devcontainer sudoers grant that lets node run
# /bin/chown with any arguments, in an assembled .devcontainer/Dockerfile.
#
#   broad-sudoers-chown.sh check <Dockerfile>
#       Prints one line per broad grant. Exit 0 = clean, 1 = broad grant found.
#   broad-sudoers-chown.sh patch <Dockerfile> <devcontainer.json>
#       Prints the patched Dockerfile on stdout; never writes the file.
#       Exit 0 = patched text printed, 1 = nothing to patch, 3 = patch by hand.
#   Exit 2 = usage error or unreadable input.
#
# The finding is the pre-TASK-271 rule: the
# echo "node ALL=(root) NOPASSWD: ..." > /etc/sudoers.d/node-firewall grant
# lists a bare /bin/chown. With it node can take over the root-owned,
# sudo-allowed init-firewall.sh and so get root. Instructions are read with
# backslash continuations joined and comment lines dropped.
#
# patch rewrites the grant to the Dockerfile.base one, which allows only the
# chown postCreateCommand runs, and ends the RUN with visudo -cf when it does
# not already. It refuses (exit 3) when the grant lists anything but
# init-firewall.sh and the bare chown, when the echo spans several lines, and
# when devcontainer.json's postCreateCommand runs a sudo command other than
# "sudo chown node:node /workspace/.venv" — narrowing would break it.
set -euo pipefail

usage() {
  echo "usage: broad-sudoers-chown.sh check <Dockerfile> | patch <Dockerfile> <devcontainer.json>" >&2
  exit 2
}
[ $# -ge 2 ] || usage
mode=$1
file=$2
config=
case $mode in
  check) [ $# -eq 2 ] || usage ;;
  patch)
    [ $# -eq 3 ] || usage
    config=$3
    ;;
  *) usage ;;
esac
for f in "$file" ${config:+"$config"}; do
  [ -r "$f" ] || { echo "broad-sudoers-chown: cannot read $f" >&2; exit 2; }
done

# shellcheck disable=SC2016  # $-fields belong to awk, not the shell
prog='
function trim(s) { sub(/^[ \t]+/, "", s); sub(/[ \t\r]+$/, "", s); return s }
function by_hand(why) { print "broad-sudoers-chown: " why "; patch by hand" > "/dev/stderr"; exit 3 }
# Why postCreateCommand would break under the narrow grant, or "" when it would not.
function post_create_problem(path,   line, rc, s, v, i, c, n, seg) {
  while ((rc = (getline line < path)) > 0) {
    if (line ~ /^[ \t]*\/\//) continue
    if (line ~ /"postCreateCommand"[ \t]*:/) { s = line; break }
  }
  close(path)
  if (rc < 0) { print "broad-sudoers-chown: cannot read " path > "/dev/stderr"; exit 2 }
  if (s == "") return ""
  s = trim(substr(s, index(s, ":") + 1))
  if (substr(s, 1, 1) != "\"") return "postCreateCommand is not a one-line string"
  v = ""
  for (i = 2; i <= length(s); i++) {
    c = substr(s, i, 1)
    if (c == "\\") { v = v substr(s, i + 1, 1); i++; continue }
    if (c == "\"") break
    v = v c
  }
  if (i > length(s)) return "postCreateCommand is not a one-line string"
  gsub(/&&|\|\||;|\|/, "\001", v)
  n = split(v, seg, "\001")
  for (i = 1; i <= n; i++) {
    seg[i] = trim(seg[i])
    if (seg[i] ~ /(^|[ \t])sudo([ \t]|$)/ && seg[i] != "sudo chown node:node /workspace/.venv")
      return "postCreateCommand runs \047" seg[i] "\047, which the narrowed grant refuses"
  }
  return ""
}
BEGIN {
  SUDOERS = "/etc/sudoers.d/node-firewall"
  FIREWALL = "/usr/local/bin/init-firewall.sh"
  GRANT = "echo \"node ALL=\\(root\\) NOPASSWD: [^\"]*\""
  NARROW = "echo \"node ALL=(root) NOPASSWD: " FIREWALL ", /bin/chown node\\:node /workspace/.venv\""
}
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
  for (i = 1; i <= n; i++) {
    t = trim(IT[i])
    if (toupper(substr(t, 1, 4)) != "RUN " || !index(t, SUDOERS)) continue
    if (!match(t, GRANT " *> *" SUDOERS)) continue
    match(t, GRANT)
    grant = substr(t, RSTART, RLENGTH)
    cmds = substr(grant, index(grant, "NOPASSWD:") + 9)
    sub(/"$/, "", cmds)
    k = split(cmds, C, ",")
    bare = 0
    for (j = 1; j <= k; j++) if (trim(C[j]) == "/bin/chown") bare = 1
    if (!bare) continue
    gl = 0
    for (j = IS[i]; j <= IE[i]; j++) if (index(L[j], SUDOERS) && index(L[j], "NOPASSWD:")) gl = j
    nf++; FI[nf] = i; FL[nf] = gl; FC[nf] = cmds
    msg[nf] = sprintf("line %d: sudoers grant to node allows /bin/chown with any arguments (%s)", \
      gl ? gl : IS[i], trim(cmds))
  }
  if (mode == "check") {
    for (f = 1; f <= nf; f++) print msg[f]
    exit (nf > 0)
  }
  if (nf == 0) { print "broad-sudoers-chown: nothing to patch" > "/dev/stderr"; exit 1 }
  if (nf > 1) by_hand("more than one broad node-firewall grant")
  i = FI[1]; gl = FL[1]
  k = split(FC[1], C, ",")
  fw = 0; ch = 0
  for (j = 1; j <= k; j++) {
    c = trim(C[j])
    if (c == FIREWALL) fw++
    else if (c == "/bin/chown") ch++
    else by_hand("the grant also lists \047" c "\047")
  }
  if (fw != 1 || ch != 1) by_hand("the grant is not exactly " FIREWALL " and /bin/chown")
  if (!gl || !match(L[gl], GRANT " *> *" SUDOERS)) by_hand("the grant echo spans several lines")
  why = post_create_problem(config)
  if (why != "") by_hand(why)
  match(L[gl], GRANT)
  L[gl] = substr(L[gl], 1, RSTART - 1) NARROW substr(L[gl], RSTART + RLENGTH)
  last = IE[i]
  add_visudo = (IT[i] !~ /visudo -cf \/etc\/sudoers\.d\/node-firewall/)
  for (j = 1; j <= NR; j++) {
    if (j == last && add_visudo) {
      s = L[j]; sub(/[ \t\r]+$/, "", s)
      print s " \\"
      print " && visudo -cf " SUDOERS
    } else print L[j]
  }
}
'
exec awk -v mode="$mode" -v config="$config" "$prog" "$file"
