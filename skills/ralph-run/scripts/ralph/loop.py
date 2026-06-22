"""Main iteration loop — orchestrates one Ralph run end-to-end.

The shape mirrors the bash ``for i in $(seq 1 "$MAX_ITERATIONS"); do … done``
block at ``ralph.sh:719-887``. AC #5 pins the within-iteration ordering:

    usage check → task pick → MODE prefix + prompt → tool invoke →
    signal parse → done diff → status update → sleep 2s

The loop terminates on one of the AC #7 closed-set reasons:
``"all tasks done"``, ``"max iterations reached"``, ``"error"``,
``"interrupted"``. The summary is printed on every exit path — including
the SIGINT/SIGTERM branch — via the ``finally`` block.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ralph import tasks as tasks_module
from ralph.args import ParsedArgs, timeout_to_seconds
from ralph.heartbeat import Heartbeat
from ralph.prompts import build_prompt
from ralph.status import ErrorEntry, StatusFile
from ralph.summary import EXIT_REASONS, RunSummary, print_summary
from ralph.tools import Tool, ToolResult
from ralph.tools._subprocess import TIMEOUT_EXIT_CODE
from ralph.tools.claude import ClaudeTool
from ralph.tools.opencode import OpencodeTool
from ralph.usage import check_and_pause, clear_pause

ITER_SLEEP_SEC = 2.0
"""Bash equivalent: ``sleep 2`` between iterations (AC #5)."""


def _now_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_epoch() -> int:
    return int(datetime.now(tz=UTC).timestamp())


@dataclass
class _Interrupted(BaseException):  # noqa: N818
    """Signal-handler trampoline; raised inside the loop on SIGINT/SIGTERM."""

    signum: int = 0


@dataclass
class _RunState:
    """Mutable state accumulated across iterations."""

    tasks_completed: int = 0
    failed_iterations: int = 0
    iter_durations: list[int] = field(default_factory=list[int])
    tasks_done_ids: list[str] = field(default_factory=list[str])
    errors: list[ErrorEntry] = field(default_factory=list[ErrorEntry])
    exit_reason: str = "max iterations reached"
    exit_code: int = 0


def build_tool(args: ParsedArgs, project_root: Path) -> Tool:
    """Construct the concrete :class:`Tool` for ``args.tool``."""
    if args.tool == "opencode":
        return OpencodeTool(
            devcontainer=args.devcontainer,
            workspace_folder=project_root if args.devcontainer else None,
        )
    return ClaudeTool(
        model=args.model,
        effort=args.effort,
        devcontainer=args.devcontainer,
        workspace_folder=project_root if args.devcontainer else None,
    )


def load_prompt_file(path: str) -> str:
    """Read ``--prompt-file`` once at startup. Raises ``SystemExit(1)`` on failure.

    AC #6: missing file is a hard fail BEFORE the loop starts. Validation
    already covers ``os.access(path, R_OK)``; this catches the residual
    races (file deleted between validate and load).
    """
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Error: failed to read --prompt-file '{path}': {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def run(args: ParsedArgs, project_root: Path) -> int:
    """Execute one Ralph run; return the process exit code.

    Args:
        args: Parsed & validated CLI args.
        project_root: Resolved project root (from RALPH_PROJECT_ROOT or
            the ``--script-dir`` fallback). All project-relative paths
            (``backlog/.ralph-status.json``, ``backlog/.ralph-heartbeat``)
            are anchored here.
    """
    prompt_file_body = load_prompt_file(args.prompt_file) if args.prompt_file else None

    status_path = _status_file_path(project_root)
    heartbeat_path = _heartbeat_file_path(project_root)
    timeout_sec = timeout_to_seconds(args.timeout)

    state = _RunState()
    started_at_iso = _now_iso()
    started_epoch = _now_epoch()
    status = StatusFile(
        pid=os.getpid(),
        started_at=started_at_iso,
        state="running",
        iteration=0,
        max_iterations=args.max_iterations,
        tool=args.tool,
        tasks_done=[],
        tasks_remaining=tasks_module.count_remaining(args.task_whitelist or None),
        current_task=None,
        last_iteration_duration=None,
        elapsed=0,
        errors=[],
        completed_at=None,
        exit_code=None,
        iteration_started_at=None,
        timeout_sec=timeout_sec,
    )
    status.write_atomic(status_path)

    tool = build_tool(args, project_root)
    installer = _SignalInstaller()
    installer.install()
    try:
        with Heartbeat(heartbeat_path):
            _run_loop(
                args=args,
                project_root=project_root,
                tool=tool,
                timeout_sec=timeout_sec,
                prompt_file_body=prompt_file_body,
                status=status,
                status_path=status_path,
                started_epoch=started_epoch,
                state=state,
                installer=installer,
            )
    except _Interrupted:
        state.exit_reason = "interrupted"
        state.exit_code = 130
    finally:
        installer.restore()
        _finalize(status, status_path, started_epoch, state, args)

    assert state.exit_reason in EXIT_REASONS, (
        f"exit_reason {state.exit_reason!r} not in closed set {EXIT_REASONS!r}"
    )
    return state.exit_code


def _run_loop(
    *,
    args: ParsedArgs,
    project_root: Path,
    tool: Tool,
    timeout_sec: int,
    prompt_file_body: str | None,
    status: StatusFile,
    status_path: Path,
    started_epoch: int,
    state: _RunState,
    installer: _SignalInstaller,
) -> None:
    _ = project_root  # reserved for future per-iteration relative paths
    whitelist = args.task_whitelist or None

    for i in range(1, args.max_iterations + 1):
        installer.raise_if_pending()

        if check_and_pause(status, args.block_end_buffer_min):
            status.state = "paused"
            status.completed_at = _now_iso()
            status.exit_code = 0
            status.elapsed = _now_epoch() - started_epoch
            status.write_atomic(status_path)
            state.exit_reason = "paused"
            state.exit_code = 0
            return

        clear_pause(status)

        next_task = tasks_module.pick_next_task(whitelist=whitelist)
        if next_task is None:
            state.exit_reason = "all tasks done"
            state.exit_code = 0
            return

        iteration_started_at = _now_iso()
        iter_start = _now_epoch()
        status.iteration = i
        status.current_task = next_task
        status.iteration_started_at = iteration_started_at
        status.state = "running"
        status.tasks_remaining = tasks_module.count_remaining(whitelist)
        status.elapsed = iter_start - started_epoch
        status.write_atomic(status_path)

        prompt = build_prompt(
            iteration=i,
            max_iterations=args.max_iterations,
            whitelist_task_id=next_task if whitelist else None,
            prompt_file_body=prompt_file_body,
        )

        done_before = set(tasks_module.done_task_ids())
        result = _invoke_tool(tool, prompt, timeout_sec, installer)

        iter_elapsed = _now_epoch() - iter_start
        state.iter_durations.append(iter_elapsed)

        # A signal pending here means the tool was killed mid-run by the
        # forwarded SIGTERM (handler at _SignalInstaller._handler). Raise
        # before the failure accounting so this surfaces as "interrupted"
        # rather than a generic iteration error.
        installer.raise_if_pending()

        if result.exit_code == TIMEOUT_EXIT_CODE:
            msg = f"Iteration {i} timed out after {args.timeout}m"
            state.errors.append(
                ErrorEntry(iteration=i, at=_now_iso(), message=msg)
            )
            state.failed_iterations += 1
            _update_after_iteration(
                status, status_path, started_epoch, state, iter_elapsed
            )
            installer.raise_if_pending()
            time.sleep(ITER_SLEEP_SEC)
            continue

        if result.exit_code != 0:
            error_message = (
                result.signals.error_text
                or f"Iteration {i} failed with exit code {result.exit_code}"
            )
            state.errors.append(
                ErrorEntry(iteration=i, at=_now_iso(), message=error_message)
            )
            state.failed_iterations += 1
            _update_after_iteration(
                status, status_path, started_epoch, state, iter_elapsed
            )
            if args.on_error == "stop":
                state.exit_reason = "error"
                state.exit_code = result.exit_code
                return
            installer.raise_if_pending()
            time.sleep(ITER_SLEEP_SEC)
            continue

        done_after = set(tasks_module.done_task_ids())
        new_done = sorted(done_after - done_before, key=lambda tid: int(tid.removeprefix("TASK-")))
        for tid in new_done:
            if tid not in state.tasks_done_ids:
                state.tasks_done_ids.append(tid)

        state.tasks_completed += 1
        _update_after_iteration(
            status, status_path, started_epoch, state, iter_elapsed
        )

        if result.signals.complete:
            state.exit_reason = "all tasks done"
            state.exit_code = 0
            return

        installer.raise_if_pending()
        time.sleep(ITER_SLEEP_SEC)

    if state.tasks_completed == 0 or state.failed_iterations > 0:
        state.exit_code = 1


def _invoke_tool(
    tool: Tool,
    prompt: str,
    timeout_sec: int,
    installer: _SignalInstaller,
) -> ToolResult:
    try:
        return tool.run(
            prompt,
            timeout_sec,
            on_spawn=installer.set_active_subprocess,
        )
    finally:
        installer.set_active_subprocess(None)


def _update_after_iteration(
    status: StatusFile,
    status_path: Path,
    started_epoch: int,
    state: _RunState,
    last_iter_dur: int,
) -> None:
    status.tasks_done = list(state.tasks_done_ids)
    status.errors = list(state.errors)
    status.last_iteration_duration = last_iter_dur
    status.elapsed = _now_epoch() - started_epoch
    status.tasks_remaining = tasks_module.count_remaining()
    status.write_atomic(status_path)


def _finalize(
    status: StatusFile,
    status_path: Path,
    started_epoch: int,
    state: _RunState,
    args: ParsedArgs,
) -> None:
    elapsed = _now_epoch() - started_epoch
    if status.state == "paused":
        pass  # pause path already wrote its terminal state
    elif state.exit_reason == "interrupted":
        status.state = "failed"
    elif state.exit_code == 0:
        status.state = "completed"
    else:
        status.state = "failed"
    status.tasks_done = list(state.tasks_done_ids)
    status.errors = list(state.errors)
    status.elapsed = elapsed
    status.completed_at = _now_iso()
    status.exit_code = state.exit_code
    with suppress(OSError):
        status.write_atomic(status_path)

    summary = RunSummary(
        exit_reason=state.exit_reason,
        tasks_completed=state.tasks_completed,
        tasks_remaining=tasks_module.count_remaining(args.task_whitelist or None),
        iterations_used=len(state.iter_durations),
        max_iterations=args.max_iterations,
        failed_iterations=state.failed_iterations,
        wall_time_sec=elapsed,
        iter_durations_sec=state.iter_durations,
    )
    print_summary(summary, sys.stdout)


def _status_file_path(project_root: Path) -> Path:
    env = os.environ.get("RALPH_STATUS_FILE")
    if env:
        return Path(env)
    return project_root / "backlog" / ".ralph-status.json"


def _heartbeat_file_path(project_root: Path) -> Path:
    env = os.environ.get("RALPH_HEARTBEAT_FILE")
    if env:
        return Path(env)
    return project_root / "backlog" / ".ralph-heartbeat"


class _SignalInstaller:
    """Install SIGINT/SIGTERM handlers that set a flag the loop polls AND
    forward the signal to the active tool subprocess's process group.

    The flag-and-poll shape keeps the iteration accounting boundary at
    well-defined points (``raise_if_pending`` between phases) — avoids
    tearing the status file mid-write or stranding a subprocess before the
    tee has flushed.

    Forwarding the signal to the registered subprocess's process group is
    the TASK-160 parity gap closer: bash's ``_kill_children`` trap
    (ralph.sh:582-593) walked ``pgrep -P $$`` and SIGTERM'd each direct
    child immediately. Without this, a SIGTERM mid-``tool.run()`` would
    leave the child running until its own per-iteration timeout.
    """

    def __init__(self) -> None:
        self._pending: int = 0
        self._prev_int: object = None
        self._prev_term: object = None
        self._installed = False
        self._active_pgid: int | None = None
        # RLock (not Lock): Python signal handlers run synchronously on the
        # main thread. If a signal arrives while the main thread is inside
        # ``set_active_subprocess``'s ``with self._active_lock:`` block, the
        # handler runs on top of the same stack and re-acquires the lock —
        # a non-reentrant Lock would deadlock there.
        self._active_lock = threading.RLock()

    def install(self) -> None:
        self._prev_int = signal.signal(signal.SIGINT, self._handler)
        self._prev_term = signal.signal(signal.SIGTERM, self._handler)
        self._installed = True

    def restore(self) -> None:
        if not self._installed:
            return
        with suppress(TypeError, ValueError):
            signal.signal(signal.SIGINT, self._prev_int)  # type: ignore[arg-type]
            signal.signal(signal.SIGTERM, self._prev_term)  # type: ignore[arg-type]
        self._installed = False

    def raise_if_pending(self) -> None:
        if self._pending:
            signum, self._pending = self._pending, 0
            raise _Interrupted(signum=signum)

    def is_pending(self) -> bool:
        return self._pending != 0

    def set_active_subprocess(
        self, proc: subprocess.Popen[bytes] | None
    ) -> None:
        """Register or clear the currently-active tool subprocess.

        Called by ``_invoke_tool`` via the tool's ``on_spawn`` hook (after
        the ``Popen``) and again with ``None`` after the tool returns. The
        signal handler reads the registered pgid to forward SIGTERM.

        Passing a ``Popen`` whose pid has already exited is a no-op — the
        ``os.getpgid`` lookup raises ``ProcessLookupError`` and we leave
        the slot empty so a stray late signal can't target a recycled pid.

        Race close: if a SIGINT/SIGTERM arrived AFTER ``Popen`` returned
        but BEFORE this register call ran, ``_handler`` set ``_pending``
        with no pgid to forward to. We retry the forward here so the
        just-registered child is killed promptly instead of running until
        its per-iteration timeout.
        """
        with self._active_lock:
            if proc is None:
                self._active_pgid = None
                return
            try:
                self._active_pgid = os.getpgid(proc.pid)
            except ProcessLookupError:
                self._active_pgid = None
            pgid = self._active_pgid
        if pgid is not None and self._pending:
            with suppress(ProcessLookupError, PermissionError, OSError):
                os.killpg(pgid, signal.SIGTERM)

    def _handler(self, signum: int, _frame: object) -> None:
        self._pending = signum
        with self._active_lock:
            pgid = self._active_pgid
        if pgid is None:
            return
        with suppress(ProcessLookupError, PermissionError, OSError):
            os.killpg(pgid, signal.SIGTERM)
