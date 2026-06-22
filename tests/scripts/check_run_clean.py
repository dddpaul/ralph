# /// script
# requires-python = ">=3.14"
# ///
"""Cutover clean-run gate for TASK-156.

Two modes:

* ``--run-only <status.json>`` codifies the 6-check clean-run gate
  (AC #1): state=completed, exit_code=0, errors[] empty, >=1 task moved
  To Do->Done this run, heartbeat file removed at exit (proxy for "fresh
  throughout"), no leftover orchestrator process (proxy for "no leftover
  child processes" since well-behaved children exit with their parent).

* ``--parity <bash.json> <python.json>`` performs a schema-parity check
  (AC #2): same field set, same value types (None matches anything for
  nullable fields).

Exit 0 if all checks pass, 1 otherwise. Stdlib only -- no external deps
so the script is invokable from anywhere via ``uv run`` even after the
inner bash helpers are gone.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _proc_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def run_only(status_path: Path) -> int:
    failures: list[str] = []
    try:
        status = json.loads(status_path.read_text())
    except OSError as e:
        print(f"FAIL: cannot read {status_path}: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"FAIL: status file is not valid JSON: {e}", file=sys.stderr)
        return 1

    state = status.get("state")
    if state == "completed":
        print("PASS check 1: state=completed")
    else:
        print(f"FAIL check 1: state={state!r}, expected 'completed'")
        failures.append("state")

    exit_code = status.get("exit_code")
    if exit_code == 0:
        print("PASS check 2: exit_code=0")
    else:
        print(f"FAIL check 2: exit_code={exit_code!r}, expected 0")
        failures.append("exit_code")

    errors = status.get("errors") or []
    if not errors:
        print("PASS check 3: errors[] empty")
    else:
        print(f"FAIL check 3: errors[] has {len(errors)} entries: {errors}")
        failures.append("errors")

    tasks_done = status.get("tasks_done") or []
    if len(tasks_done) >= 1:
        print(f"PASS check 4: >=1 task moved To Do->Done ({len(tasks_done)} this run: {tasks_done})")
    else:
        print("FAIL check 4: no tasks moved To Do->Done this run (tasks_done is empty)")
        failures.append("tasks_done")

    heartbeat = status_path.parent / ".ralph-heartbeat"
    if not heartbeat.exists():
        print("PASS check 5: heartbeat file removed at exit (cleanup ran)")
    else:
        print(f"FAIL check 5: heartbeat file still present at {heartbeat}")
        failures.append("heartbeat")

    pid = status.get("pid")
    if isinstance(pid, int) and _proc_alive(pid):
        print(f"FAIL check 6: orchestrator PID {pid} still alive post-run (possible leftover children)")
        failures.append("leftover_pid")
    else:
        print(f"PASS check 6: orchestrator PID {pid} exited (no leftover children traceable)")

    if failures:
        print(f"\nFAIL: {len(failures)} of 6 checks failed: {', '.join(failures)}")
        return 1
    print("\nPASS: all 6 checks passed")
    return 0


def parity(bash_path: Path, python_path: Path) -> int:
    try:
        bash = json.loads(bash_path.read_text())
        py = json.loads(python_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"FAIL: cannot load one of the status files: {e}", file=sys.stderr)
        return 1

    if not isinstance(bash, dict) or not isinstance(py, dict):
        print("FAIL: both status files must be JSON objects", file=sys.stderr)
        return 1

    bash_keys = set(bash.keys())
    py_keys = set(py.keys())

    fail = False
    only_bash = bash_keys - py_keys
    only_py = py_keys - bash_keys
    if only_bash:
        print(f"FAIL: keys only in bash: {sorted(only_bash)}")
        fail = True
    if only_py:
        print(f"FAIL: keys only in python: {sorted(only_py)}")
        fail = True

    common = bash_keys & py_keys
    for key in sorted(common):
        bv, pv = bash[key], py[key]
        if bv is None or pv is None:
            continue
        bt, pt = type(bv).__name__, type(pv).__name__
        if bt != pt:
            print(f"FAIL: type mismatch for {key!r}: bash={bt}, python={pt}")
            fail = True

    if fail:
        return 1
    print(f"PASS: schema parity ({len(common)} fields match)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--run-only",
        metavar="STATUS_JSON",
        help="path to .ralph-status.json from a completed run",
    )
    group.add_argument(
        "--parity",
        nargs=2,
        metavar=("BASH_JSON", "PYTHON_JSON"),
        help="paths to two .ralph-status.json files for schema-parity comparison",
    )
    args = parser.parse_args()

    if args.run_only:
        return run_only(Path(args.run_only))
    return parity(Path(args.parity[0]), Path(args.parity[1]))


if __name__ == "__main__":
    sys.exit(main())
