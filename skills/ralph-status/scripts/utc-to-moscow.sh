#!/usr/bin/env bash
set -euo pipefail
[ $# -eq 1 ] || { echo "usage: utc-to-moscow.sh <ISO 8601 UTC>" >&2; exit 2; }
utc=$1
# GNU date (Linux / devcontainer)
if out=$(TZ=Europe/Moscow date -d "$utc" "+%Y-%m-%d %H:%M:%S MSK" 2>/dev/null); then
  printf '%s\n' "$out"
  exit 0
fi
# BSD date — parse as explicit UTC, then format as Moscow
if epoch=$(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$utc" "+%s" 2>/dev/null); then
  TZ=Europe/Moscow date -r "$epoch" "+%Y-%m-%d %H:%M:%S MSK"
  exit 0
fi
echo "ERROR: could not parse '$utc' on either GNU or BSD date" >&2
exit 1
