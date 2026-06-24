"""Shared subprocess executor for ``ralph.tools.claude`` and ``ralph.tools.opencode``.

Both concrete tools spawn a CLI subprocess, tee its combined stdout/stderr to
a temp file, and enforce a wall-clock timeout via ``SIGTERM`` → grace →
``SIGKILL`` on the child's process group. The only branch-level difference is
how the prompt reaches the child: ``claude`` reads it from stdin (bash
heredoc), ``opencode`` takes it as its second positional argv element. Both
shapes are funneled through :func:`execute` here.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import IO, Final

from ralph.signals import parse_file
from ralph.tools import OnSpawn, ToolResult

TIMEOUT_EXIT_CODE: Final[int] = 124
"""Exit code GNU ``timeout`` uses; the orchestrator's main loop branches on
this value to decide "iteration timed out, continue" rather than running the
``--on-error`` strategy. The Python tools MUST translate
``subprocess.TimeoutExpired`` into this same code."""

TERMINATE_GRACE_SEC: Final[int] = 5
"""Seconds between ``SIGTERM`` and ``SIGKILL`` when reaping a timed-out
child's process group. Matches the convention "polite first, then forceful"
the bash trap relied on (TASK-23)."""

READER_JOIN_SEC: Final[int] = 2
"""Bounded join for the stdout reader thread after the child exits. The
thread is a daemon so a hung pipe never strands the orchestrator; the join
is a best-effort drain so the tee file is fully flushed before
``parse_file`` reads it."""

def execute(
    argv: list[str],
    prompt: str,
    timeout_sec: int,
    *,
    tee_prefix: str,
    on_spawn: OnSpawn | None = None,
    run_log_path: Path | None = None,
) -> ToolResult:
    """Spawn ``argv``, tee its combined stdout/stderr, return a ``ToolResult``.

    Args:
        argv: Fully-assembled argv list (already includes any devcontainer
            prefix and — for opencode — the prompt as a positional element).
        prompt: Stdin payload, fed verbatim (bash equivalent: heredoc). Pass
            ``""`` when the prompt is already in ``argv``.
        timeout_sec: Wall-clock budget. On expiry the child's process group
            is SIGTERM'd, given :data:`TERMINATE_GRACE_SEC` seconds, then
            SIGKILL'd; the returned ``exit_code`` is :data:`TIMEOUT_EXIT_CODE`.
        tee_prefix: ``tempfile.mkstemp`` ``prefix`` for the transcript file
            (e.g. ``"ralph-claude-"`` or ``"ralph-opencode-"``).
        on_spawn: Test hook invoked synchronously with the live ``Popen``
            immediately after launch.
        run_log_path: Project-rooted run log to append to in addition to the
            per-iteration tempfile. Parity with ``ralph.sh:692``'s
            ``exec > >(tee -a "$RUN_LOG")`` so downstream consumers (e.g.
            ``wait_heartbeat.py``) can ``tail`` a single canonical file
            across iterations. Per-iteration tempfile is still produced for
            sentinel parsing (TASK-176 AC #4).

    Returns:
        A :class:`ralph.tools.ToolResult` with the tee path, the resolved
        exit code, and the iteration sentinels parsed from the tee file.
    """
    tee_fd, tee_path_str = tempfile.mkstemp(prefix=tee_prefix, suffix=".out")
    tee_path = Path(tee_path_str)

    with contextlib.ExitStack() as stack:
        tee_file = stack.enter_context(os.fdopen(tee_fd, "wb"))
        run_log_file: IO[bytes] | None = None
        if run_log_path is not None:
            run_log_file = stack.enter_context(run_log_path.open("ab"))
        exit_code = _spawn_and_stream(
            argv, prompt, timeout_sec, tee_file, on_spawn, run_log_file
        )

    signals = parse_file(tee_path)
    return ToolResult(stdout_path=tee_path, exit_code=exit_code, signals=signals)


def _spawn_and_stream(
    argv: list[str],
    prompt: str,
    timeout_sec: int,
    tee_file: IO[bytes],
    on_spawn: OnSpawn | None,
    run_log_file: IO[bytes] | None = None,
) -> int:
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    if on_spawn is not None:
        on_spawn(proc)

    if proc.stdin is not None:
        try:
            if prompt:
                proc.stdin.write(prompt.encode("utf-8"))
        except (BrokenPipeError, OSError):
            pass
        finally:
            with contextlib.suppress(OSError):
                proc.stdin.close()

    reader = threading.Thread(
        target=_stream_to_tee,
        args=(proc.stdout, tee_file, run_log_file),
        name="ralph-tool-stdout",
        daemon=True,
    )
    reader.start()

    try:
        exit_code = proc.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        terminate_tree(proc)
        exit_code = TIMEOUT_EXIT_CODE
    finally:
        reader.join(timeout=READER_JOIN_SEC)
        with contextlib.suppress(OSError):
            tee_file.flush()
        if run_log_file is not None:
            with contextlib.suppress(OSError):
                run_log_file.flush()

    return exit_code


def _stream_to_tee(
    stdout: IO[bytes] | None,
    tee_file: IO[bytes],
    run_log_file: IO[bytes] | None = None,
) -> None:
    """Drain ``stdout`` line-by-line, mirroring each line into ``tee_file``,
    ``sys.stdout``, and (when set) the project-rooted ``run_log_file``.

    Line-iteration (``iter(readline, b"")``) is the real-time sentinel-
    scanner contract: each line reaches the tee file immediately, so a post-
    mortem ``parse_file`` (or live terminal observer) sees data as the child
    emits it rather than buffering until exit.
    """
    if stdout is None:
        return
    out_bytes = getattr(sys.stdout, "buffer", None)
    for line in iter(stdout.readline, b""):
        try:
            tee_file.write(line)
            tee_file.flush()
        except OSError:
            pass
        if run_log_file is not None:
            try:
                run_log_file.write(line)
                run_log_file.flush()
            except OSError:
                pass
        if out_bytes is not None:
            try:
                out_bytes.write(line)
                out_bytes.flush()
            except OSError:
                pass


def terminate_tree(proc: subprocess.Popen[bytes]) -> None:
    """SIGTERM the child's process group, wait grace, SIGKILL if still alive.

    Safe to call on a child that has already exited or been reaped — every
    ``killpg`` is guarded against ``ProcessLookupError``. The function
    returns only once the child is no longer running (or the SIGKILL grace
    elapses, in which case the OS will reap eventually and the caller treats
    it as a timeout regardless).
    """
    try:
        pgid = os.getpgid(proc.pid)
    except ProcessLookupError:
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=TERMINATE_GRACE_SEC)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        return
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=TERMINATE_GRACE_SEC)
