#!/bin/bash
# usage-check.sh — Pause Ralph when the active Claude Code 5h block is about
# to end. Reads ccusage's blocks[0].endTime and compares (endTime - now) to
# the operator's buffer (in minutes).
#
# $1 = BUFFER_MIN  (integer >= 0; 0 disables the check entirely)
#
# Exit codes:
#   0 → buffer=0 disabled, OR no active block, OR remainingMinutes > buffer
#   1 → active block AND remainingMinutes <= buffer
#       prints "block_end_in_<rem>min_below_<buffer>min_buffer" to stdout
#   2 → cannot measure (ccusage missing, jq/date missing, ccusage nonzero,
#       JSON unparseable, endTime field missing or malformed)
#
# Stdout (exit 1 only): "block_end_in_<rem>min_below_<buffer>min_buffer"
# Stderr: warning lines on exit-2 paths so callers can surface a hint.

set -uo pipefail

BUFFER_MIN="${1:-}"

if [[ -z "$BUFFER_MIN" ]] || ! [[ "$BUFFER_MIN" =~ ^[0-9]+$ ]]; then
  echo "usage-check.sh: BUFFER_MIN must be a non-negative integer (got '${BUFFER_MIN:-<empty>}')" >&2
  exit 2
fi

# 0 disables — short-circuit before invoking ccusage so the PATH-mock test
# can prove no ccusage call is made.
if [[ "$BUFFER_MIN" -eq 0 ]]; then
  exit 0
fi

if ! command -v ccusage >/dev/null 2>&1; then
  echo "usage-check.sh: ccusage not found on PATH — block-end check skipped" >&2
  exit 2
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "usage-check.sh: jq not found on PATH — block-end check skipped" >&2
  exit 2
fi
if ! command -v date >/dev/null 2>&1; then
  echo "usage-check.sh: date not found on PATH — block-end check skipped" >&2
  exit 2
fi

# --token-limit max is irrelevant for the time-based heuristic but harmless;
# kept for forward compatibility with future ccusage versions that may
# surface a limit field.
CCUSAGE_OUT=$(ccusage blocks --active --token-limit max --json 2>/dev/null)
CCUSAGE_RC=$?
if [[ $CCUSAGE_RC -ne 0 ]]; then
  echo "usage-check.sh: ccusage exited $CCUSAGE_RC — block-end check skipped" >&2
  exit 2
fi

if ! echo "$CCUSAGE_OUT" | jq -e . >/dev/null 2>&1; then
  echo "usage-check.sh: ccusage produced unparseable JSON — block-end check skipped" >&2
  exit 2
fi

IS_ACTIVE=$(echo "$CCUSAGE_OUT" | jq -r '.blocks[0].isActive // false' 2>/dev/null)
IS_GAP=$(echo "$CCUSAGE_OUT" | jq -r '.blocks[0].isGap // false' 2>/dev/null)

# No active block — Ralph is not currently in a 5h window, so the boundary
# check does not apply.
if [[ "$IS_ACTIVE" != "true" || "$IS_GAP" == "true" ]]; then
  exit 0
fi

END_TIME=$(echo "$CCUSAGE_OUT" | jq -r '.blocks[0].endTime // empty' 2>/dev/null)
if [[ -z "$END_TIME" || "$END_TIME" == "null" ]]; then
  echo "usage-check.sh: ccusage JSON missing blocks[0].endTime — block-end check skipped" >&2
  exit 2
fi

# Convert ISO 8601 to epoch. GNU date first, BSD fallback.
END_EPOCH=$(date -u -d "$END_TIME" +%s 2>/dev/null)
if [[ -z "$END_EPOCH" ]]; then
  END_EPOCH=$(date -u -j -f "%Y-%m-%dT%H:%M:%S" "${END_TIME%.*}" +%s 2>/dev/null)
fi
if [[ -z "$END_EPOCH" ]] || ! [[ "$END_EPOCH" =~ ^[0-9]+$ ]]; then
  echo "usage-check.sh: could not parse endTime '$END_TIME' — block-end check skipped" >&2
  exit 2
fi

NOW_EPOCH=$(date -u +%s)
REMAINING_SEC=$(( END_EPOCH - NOW_EPOCH ))
# Integer minute math: round toward zero (matches operator's mental model —
# "5 minutes left" means at least 5 full minutes).
if [[ $REMAINING_SEC -le 0 ]]; then
  REMAINING_MIN=0
else
  REMAINING_MIN=$(( REMAINING_SEC / 60 ))
fi

if [[ $REMAINING_MIN -le $BUFFER_MIN ]]; then
  echo "block_end_in_${REMAINING_MIN}min_below_${BUFFER_MIN}min_buffer"
  exit 1
fi

exit 0
