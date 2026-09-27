#!/usr/bin/env bats
# Unit tests for the language fragments' Python runtime (TASK-242).
#
# The docs and python fragments used to declare `FROM python:3.14 AS
# python-runtime` and then `COPY --from=python-runtime /usr/local /usr/local`
# into a `FROM node:20` base. The official python:3.14 image is built on a
# newer Debian than node:20 (bookworm, glibc 2.36), so what landed in the
# image — first in PATH, at /usr/local/bin/python3 — was an interpreter linked
# against a glibc the image does not have:
#
#   python3 -c '' -> libm.so.6: version `GLIBC_2.38' not found
#
# Nothing in the suite noticed, because Ralph's orchestrator runs through
# `uv run` with its own interpreter. The pre-commit hook did notice: it picked
# that python3 as its NFC normalizer and aborted every commit made inside a
# devcontainer (see pre-commit-hook.bats for that half).
#
# These tests pin the invariant rather than the current wording: a fragment may
# not drop a foreign stage's shared-library-linked binaries into the image's own
# /usr/local, /usr/local/bin or /usr/local/lib unless that stage's image and
# Dockerfile.base's base image pin the SAME explicit Debian suite. A future
# re-pin is therefore allowed; a bare `FROM python:3.14` is not. The guard is
# exercised against a synthetic reproduction of the old defect so it cannot pass
# merely by having nothing to look at.

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
DEVCONTAINER="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/templates/devcontainer"
LANG_DIR="$DEVCONTAINER/lang"
BASE="$DEVCONTAINER/Dockerfile.base"

# Debian codename carried by an image reference, or empty when unpinned.
# A codename substring match keeps this working for node:20-bookworm,
# python:3.14-slim-bookworm and bookworm-only refs alike.
suite_of() {
  local ref="$1" s
  for s in buster bullseye bookworm trixie forky sid; do
    case "$ref" in
      *"$s"*)
        printf '%s' "$s"
        return 0
        ;;
    esac
  done
  return 0
}

# The base image of the devcontainer stage (the only FROM in Dockerfile.base).
base_image() {
  awk '$1 == "FROM" { print $2 }' "$1" | tail -1
}

# `--from=<ref> <src>` pairs from every install fragment, one per line, where
# <src> lands in the image's own interpreter paths. /usr/local/go is deliberately
# not one of them: the Go toolchain is a self-contained directory, not binaries
# dropped into the paths the base image's own libraries and binaries live in.
guarded_copies() {
  awk '
    $1 == "COPY" {
      from = ""; src = ""
      for (i = 2; i <= NF; i++) {
        if ($i ~ /^--from=/) { from = substr($i, 8); src = $(i + 1) }
      }
      if (from == "") next
      if (src == "/usr/local" || src == "/usr/local/bin" || src == "/usr/local/lib" \
          || src ~ "^/usr/local/bin/" || src ~ "^/usr/local/lib/") {
        print FILENAME "|" from "|" src
      }
    }
  ' "$1"/Dockerfile.install.*
}

# Resolve a `--from=` target to an image reference: a stage name declared by a
# lang fragment resolves to that stage's image, anything else is already one.
resolve_stage() {
  local dir="$1" name="$2"
  case "$name" in
    *:* | */*)
      printf '%s' "$name"
      return 0
      ;;
  esac
  awk -v want="$name" '
    $1 == "FROM" && toupper($3) == "AS" && $4 == want { print $2; exit }
  ' "$dir"/Dockerfile.lang.*
}

# Prints one line per violation; returns 1 when there is at least one.
check_copies() {
  local dir="$1" base="$2"
  local base_img base_suite line file from src img suite rc=0
  base_img="$(base_image "$base")"
  base_suite="$(suite_of "$base_img")"
  while IFS='|' read -r file from src; do
    [ -n "$from" ] || continue
    img="$(resolve_stage "$dir" "$from")"
    [ -n "$img" ] || img="$from"
    suite="$(suite_of "$img")"
    if [ -z "$base_suite" ] || [ -z "$suite" ] || [ "$suite" != "$base_suite" ]; then
      echo "$(basename "$file"): COPY --from=$from $src — stage image '$img' suite '${suite:-unpinned}' vs base '$base_img' suite '${base_suite:-unpinned}'"
      rc=1
    fi
  done <<EOF
$(guarded_copies "$dir")
EOF
  return "$rc"
}

@test "no language fragment declares a python:* runtime stage" {
  run grep -n -E '^FROM[[:space:]]+python:' "$LANG_DIR"/Dockerfile.lang.*
  [ "$status" -ne 0 ] || {
    echo "a python:* stage is back; the base image already provides uv + python3:"
    echo "$output"
    return 1
  }
}

@test "no install fragment copies a foreign stage into the image's /usr/local" {
  run check_copies "$LANG_DIR" "$BASE"
  [ "$status" -eq 0 ] || {
    echo "$output"
    return 1
  }
}

@test "the guard rejects a stage built on a newer Debian than the base" {
  # Verbatim reproduction of the defect, so the guard above cannot pass merely
  # because there is nothing left for it to inspect.
  local dir
  dir="$(mktemp -d)"
  printf 'FROM node:20\n' > "$dir/Dockerfile.base"
  printf 'FROM python:3.14 AS python-runtime\n' > "$dir/Dockerfile.lang.repro"
  printf 'COPY --from=python-runtime /usr/local /usr/local\n' > "$dir/Dockerfile.install.repro"

  run check_copies "$dir" "$dir/Dockerfile.base"
  [ "$status" -eq 1 ]
  [[ "$output" == *"python:3.14"* ]]
  [[ "$output" == *"unpinned"* ]]

  # Pinning only the base is not enough — the copied stage is still unpinned.
  printf 'FROM node:20-bookworm\n' > "$dir/Dockerfile.base"
  run check_copies "$dir" "$dir/Dockerfile.base"
  [ "$status" -eq 1 ]

  # Both pinned to the same suite is the one shape that is allowed.
  printf 'FROM python:3.14-bookworm AS python-runtime\n' > "$dir/Dockerfile.lang.repro"
  run check_copies "$dir" "$dir/Dockerfile.base"
  [ "$status" -eq 0 ]

  # A different suite on either side is not.
  printf 'FROM python:3.14-trixie AS python-runtime\n' > "$dir/Dockerfile.lang.repro"
  run check_copies "$dir" "$dir/Dockerfile.base"
  [ "$status" -eq 1 ]
  [[ "$output" == *"trixie"* ]]

  rm -rf "$dir"
}

@test "the guard ignores the uv binary copy and the Go toolchain directory" {
  # Both are real copies in the shipped fragments and must stay allowed: uv is a
  # single static binary, and /usr/local/go is a self-contained toolchain.
  local dir
  dir="$(mktemp -d)"
  printf 'FROM node:20\n' > "$dir/Dockerfile.base"
  printf 'FROM golang:1.25 AS golang\n' > "$dir/Dockerfile.lang.repro"
  printf '%s\n' \
    'COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv' \
    'COPY --from=golang /usr/local/go /usr/local/go' \
    > "$dir/Dockerfile.install.repro"

  run check_copies "$dir" "$dir/Dockerfile.base"
  [ "$status" -eq 0 ]

  rm -rf "$dir"
}

@test "the docs and python fragments still provide uv" {
  local f
  for f in "$LANG_DIR/Dockerfile.install.docs" "$LANG_DIR/Dockerfile.install.python"; do
    grep -q 'astral-sh/uv' "$f"
  done
}

@test "the base image installs the Python the orchestrator needs" {
  # Dropping the copied interpreter is only safe because the base image is
  # unconditionally uv-managed; if this line goes, the fragments need revisiting.
  grep -q 'uv python install' "$BASE"
}
