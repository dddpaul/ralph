#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Drop-in ``claude-code`` shim for E2E orchestrator tests.

Behavior is selected via the ``FAKE_CLAUDE_MODE`` env var (PRD §6):

* ``success`` (default): emits canned "doing things" text, calls
  ``backlog task edit <id> -s Done`` for the task ID extracted from the
  prompt, emits ``## Task Summary``, emits ``<promise>COMPLETE</promise>``,
  exits 0.
* ``task_done_no_summary``: same as ``success`` minus the Summary block —
  tests the orchestrator's heuristic robustness when the agent forgets the
  summary marker.
* ``fail``: emits ``ERROR: fake_claude.py fail mode`` to stderr, exits 1.
* ``hang``: sleeps forever — tests the orchestrator's per-iteration
  timeout enforcement.

Invocation matches real ``claude-code``: positional flags ``--model``,
``--effort``, ``--print``, ``--dangerously-skip-permissions`` are
**accepted but ignored**, and the prompt is read from stdin. The shim
emits all of its output to stdout (with explicit flushing) so the
orchestrator's tee thread observes it in real time.
"""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import sys
import time

_PROMPT_TASK_RE = re.compile(r"TASK-(\d+)")


def _emit(line: str) -> None:
    sys.stdout.write(line)
    if not line.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()


def _extract_task_id(prompt: str) -> str | None:
    match = _PROMPT_TASK_RE.search(prompt)
    return match.group(1) if match else None


def _mark_task_done(task_id: str) -> None:
    """Invoke ``backlog task edit <id> -s Done``; swallow errors.

    The shim does NOT escalate backlog CLI failures: the E2E test asserts
    success-mode behavior (transcript markers, exit 0); if backlog is
    missing on PATH the test environment is responsible for providing a
    stub. The orchestrator picks up the Done transition via its own
    DONE_BEFORE/DONE_AFTER diff against backlog.
    """
    with contextlib.suppress(FileNotFoundError, OSError):
        subprocess.run(
            ["backlog", "task", "edit", task_id, "-s", "Done"],
            check=False,
            capture_output=True,
        )


def _run_success(prompt: str) -> int:
    _emit("fake_claude: starting work on task")
    task_id = _extract_task_id(prompt)
    if task_id:
        _emit(f"fake_claude: marking TASK-{task_id} as Done")
        _mark_task_done(task_id)
    _emit("")
    _emit("## Task Summary")
    _emit("")
    _emit(f"- **Task:** TASK-{task_id or 'unknown'} — fake success")
    _emit("- **What was implemented:** nothing (shim)")
    _emit("- **Files changed:** none")
    _emit("- **Key decisions:** none")
    _emit("")
    _emit("<promise>COMPLETE</promise>")
    return 0


def _run_task_done_no_summary(prompt: str) -> int:
    _emit("fake_claude: starting work on task")
    task_id = _extract_task_id(prompt)
    if task_id:
        _emit(f"fake_claude: marking TASK-{task_id} as Done")
        _mark_task_done(task_id)
    _emit("fake_claude: done (no summary block emitted)")
    return 0


def _run_fail() -> int:
    sys.stderr.write("ERROR: fake_claude.py fail mode\n")
    sys.stderr.flush()
    return 1


def _run_hang() -> int:
    _emit("fake_claude: entering hang mode — sleeping until killed")
    while True:
        time.sleep(3600)


def main() -> int:
    mode = os.environ.get("FAKE_CLAUDE_MODE", "success")
    prompt = sys.stdin.read()
    if mode == "success":
        return _run_success(prompt)
    if mode == "task_done_no_summary":
        return _run_task_done_no_summary(prompt)
    if mode == "fail":
        return _run_fail()
    if mode == "hang":
        return _run_hang()
    sys.stderr.write(f"ERROR: fake_claude.py: unknown FAKE_CLAUDE_MODE '{mode}'\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
