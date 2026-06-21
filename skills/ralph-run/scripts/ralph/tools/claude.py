"""Concrete ``Tool`` for the claude-code CLI.

Mirrors the bash invocation in ``ralph.sh:804``::

    timeout "$TIMEOUT_SEC" <devcontainer-prefix?> \\
        claude --model "$MODEL" --effort "$EFFORT" \\
        --dangerously-skip-permissions --print <<< "$PROMPT" \\
        2>&1 | tee "$OUTFILE"

with the timeout wrapper rolled into ``Popen.wait()`` and the
``_kill_children`` tree-cleanup folded into an ``SIGTERM`` → 5s grace →
``SIGKILL`` reap of the child's process group on timeout.

The child is launched with ``start_new_session=True`` so the orchestrator's
top-level signal handler (US-005) can target its whole process group via
``os.killpg`` — bash relied on ``pgrep -P $$`` to find the direct children
and walked their pgids; the Python port front-loads the isolation at spawn
time, which is the recipe historical-context entry "Subprocess management /
process cleanup" (TASK-23, TASK-37) calls out as the cleanly portable shape.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import IO, Final

from ralph.signals import parse_file
from ralph.tools import Tool, ToolResult

TIMEOUT_EXIT_CODE: Final[int] = 124
"""Exit code GNU ``timeout`` uses; the orchestrator's main loop branches on
this value to decide "iteration timed out, continue" rather than running the
``--on-error`` strategy. The Python tool MUST translate
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


class ClaudeTool(Tool):
    """One iteration of the ``claude-code`` CLI.

    Construction binds the invariant flags (model, effort, optional
    devcontainer prefix); :meth:`run` is called per-iteration with the
    iteration-specific prompt body and the per-iteration timeout in seconds.

    The devcontainer prefix is assembled as an argv list (never a joined
    string) so workspace paths containing spaces survive — TASK-37's
    invariant from the bash port.

    Args:
        model: Value for ``claude --model`` (e.g. ``"claude-opus-4-7"``).
        effort: Value for ``claude --effort`` (e.g. ``"max"``).
        devcontainer: When True, prepend ``devcontainer exec
            --workspace-folder <path>`` to the argv list.
        workspace_folder: Required when ``devcontainer=True``; ignored when
            ``devcontainer=False``. Passed verbatim — no shell quoting.
    """

    def __init__(
        self,
        *,
        model: str,
        effort: str,
        devcontainer: bool = False,
        workspace_folder: Path | None = None,
    ) -> None:
        if devcontainer and workspace_folder is None:
            raise ValueError(
                "workspace_folder is required when devcontainer=True"
            )
        self._model = model
        self._effort = effort
        self._devcontainer = devcontainer
        self._workspace_folder = workspace_folder

    def build_argv(self) -> list[str]:
        """Assemble the argv list for this iteration's subprocess.

        Returns:
            The fully-assembled argv as a list. When ``devcontainer=True``
            the list begins with ``["devcontainer", "exec",
            "--workspace-folder", <path>, ...]`` — never a single joined
            string.
        """
        argv: list[str] = []
        if self._devcontainer and self._workspace_folder is not None:
            argv.extend(
                [
                    "devcontainer",
                    "exec",
                    "--workspace-folder",
                    str(self._workspace_folder),
                ]
            )
        argv.extend(
            [
                "claude",
                "--model",
                self._model,
                "--effort",
                self._effort,
                "--dangerously-skip-permissions",
                "--print",
            ]
        )
        return argv

    def run(self, prompt: str, timeout_sec: int) -> ToolResult:
        return _execute(self.build_argv(), prompt, timeout_sec)


_OnSpawn = Callable[[subprocess.Popen[bytes]], None]


def _execute(
    argv: list[str],
    prompt: str,
    timeout_sec: int,
    *,
    on_spawn: _OnSpawn | None = None,
) -> ToolResult:
    """Spawn ``argv``, tee its combined stdout/stderr, return a ``ToolResult``.

    The tee file is created via ``tempfile.mkstemp`` and its path is returned
    on the result so the orchestrator can grep it post-mortem; the orchestrator
    owns deletion via the ``_ralph_cleanup_files`` equivalent.

    Args:
        argv: Fully-assembled argv list (already includes any devcontainer
            prefix).
        prompt: Prompt body — fed via stdin (bash equivalent: heredoc).
        timeout_sec: Wall-clock budget. On expiry the child's process group
            is SIGTERM'd, given :data:`TERMINATE_GRACE_SEC` seconds, then
            SIGKILL'd; the returned ``exit_code`` is :data:`TIMEOUT_EXIT_CODE`.
        on_spawn: Test hook — invoked synchronously with the live ``Popen``
            immediately after launch. Production callers leave this ``None``.

    Returns:
        A :class:`ralph.tools.ToolResult` with the tee path, the resolved
        exit code, and the iteration sentinels parsed from the tee file.
    """
    tee_fd, tee_path_str = tempfile.mkstemp(prefix="ralph-claude-", suffix=".out")
    tee_path = Path(tee_path_str)

    with os.fdopen(tee_fd, "wb") as tee_file:
        exit_code = _spawn_and_stream(
            argv, prompt, timeout_sec, tee_file, on_spawn
        )

    signals = parse_file(tee_path)
    return ToolResult(stdout_path=tee_path, exit_code=exit_code, signals=signals)


def _spawn_and_stream(
    argv: list[str],
    prompt: str,
    timeout_sec: int,
    tee_file: IO[bytes],
    on_spawn: _OnSpawn | None,
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
            proc.stdin.write(prompt.encode("utf-8"))
        except (BrokenPipeError, OSError):
            pass
        finally:
            with contextlib.suppress(OSError):
                proc.stdin.close()

    reader = threading.Thread(
        target=_stream_to_tee,
        args=(proc.stdout, tee_file),
        name="ralph-claude-stdout",
        daemon=True,
    )
    reader.start()

    try:
        exit_code = proc.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        _terminate_tree(proc)
        exit_code = TIMEOUT_EXIT_CODE
    finally:
        reader.join(timeout=READER_JOIN_SEC)
        with contextlib.suppress(OSError):
            tee_file.flush()

    return exit_code


def _stream_to_tee(stdout: IO[bytes] | None, tee_file: IO[bytes]) -> None:
    """Drain ``stdout`` line-by-line, mirroring each line into ``tee_file`` AND
    ``sys.stdout``.

    Line-iteration (``iter(readline, b"")``) is the real-time sentinel-
    scanner contract called out in AC #3: each line reaches the tee file
    immediately, so a post-mortem ``parse_file`` (or live terminal observer)
    sees data as the child emits it rather than buffering until exit.
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
        if out_bytes is not None:
            try:
                out_bytes.write(line)
                out_bytes.flush()
            except OSError:
                pass


def _terminate_tree(proc: subprocess.Popen[bytes]) -> None:
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
