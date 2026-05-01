#!/usr/bin/env bash
set -euo pipefail

[ -d backlog ] || { echo "ERROR: must be invoked from project root (no backlog/ here)"; exit 2; }

for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 1
  if [ -f backlog/.ralph-heartbeat ]; then
    HB=$(stat -c %Y backlog/.ralph-heartbeat 2>/dev/null || stat -f %m backlog/.ralph-heartbeat 2>/dev/null)
    NOW=$(date +%s)
    AGE=$((NOW - HB))
    if [ "$AGE" -lt 15 ]; then
      echo "OK heartbeat age=${AGE}s after ${i}s"
      rm -f backlog/.ralph-launch.log
      exit 0
    fi
  fi
done

echo "FAIL no fresh heartbeat after 10s"
echo "--- launch log (last 20 lines) ---"
tail -20 backlog/.ralph-launch.log 2>/dev/null || echo "(launch log not created)"
echo "--- run log (last 20 lines) ---"
tail -20 backlog/.ralph-run.log 2>/dev/null || echo "(run log not created)"
exit 1
