#!/usr/bin/env bash
# Find a uv binary copied from a floating image tag in an assembled
# .devcontainer/Dockerfile.
#
#   floating-uv-copy.sh check <Dockerfile>
#       Prints one line per floating uv COPY. Exit 0 = clean, 1 = floating copy
#       found, 2 = usage error or unreadable input.
#
# A COPY --from=<stage or image> is a uv copy when its image (the stage's FROM
# image when --from names a stage) is ghcr.io/astral-sh/uv. It floats unless the
# image carries a digest (@sha256:...), the ${UV_VERSION} build arg that
# devcontainer.json supplies, or a concrete X.Y.Z tag; no tag at all means
# latest. The pre-TASK-251 COPY --from=ghcr.io/astral-sh/uv:latest line floats;
# the Dockerfile.base stage FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv-bin
# does not. The check is independent of devcontainer.json, so a project that
# declined the upgrade's uv patch is caught again on the next run.
set -euo pipefail

usage() {
  echo "usage: floating-uv-copy.sh check <Dockerfile>" >&2
  exit 2
}
[ $# -eq 2 ] || usage
[ "$1" = check ] || usage
file=$2
[ -r "$file" ] || { echo "floating-uv-copy: cannot read $file" >&2; exit 2; }

# shellcheck disable=SC2016  # $-fields belong to awk, not the shell
prog='
function floats(img,   tag, rest) {
  if (index(img, "@")) return 0
  rest = img; sub(/^.*\//, "", rest)
  tag = index(rest, ":") ? substr(rest, index(rest, ":") + 1) : ""
  if (tag == "${UV_VERSION}" || tag == "$UV_VERSION") return 0
  return tag !~ /^[0-9]+\.[0-9]+\.[0-9]+$/
}
toupper($1) == "FROM" && NF >= 4 && toupper($3) == "AS" { stage[$4] = $2 }
toupper($1) == "COPY" {
  origin = ""
  for (i = 2; i <= NF; i++) if ($i ~ /^--from=/) origin = substr($i, 8)
  if (origin == "") next
  img = (origin ~ /[:\/@]/ || !(origin in stage)) ? origin : stage[origin]
  if (img !~ /^ghcr\.io\/astral-sh\/uv([:@]|$)/ || !floats(img)) next
  n++
  printf "line %d: COPY --from=%s — uv image \047%s\047 floats\n", NR, origin, img
}
END { exit (n > 0) }
'
exec awk "$prog" "$file"
