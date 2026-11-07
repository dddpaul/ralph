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

from ralph import push as push_module
from ralph import tasks as tasks_module
from ralph.args import ParsedArgs, timeout_to_seconds
from ralph.devcontainer import start_devcontainer
from ralph.heartbeat import Heartbeat
from ralph.prompts import build_prompt
from ralph.status import ErrorEntry, SkippedTask, StatusFile
from ralph.summary import EXIT_REASONS, RunSummary, print_summary
from ralph.tools import IterationSignals, Tool, ToolResult
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
    skipped: list[SkippedTask] = field(default_factory=list[SkippedTask])
    exit_reason: str = "max iterations reached"
    exit_code: int = 0
    # TASK-312: publishing through shared-backlog integrate in an enforcing clone.
    shared_publish: bool = False
    published_rev: str | None = None
    publish_failed: bool = False
    last_task: str | None = None


def build_tool(
    args: ParsedArgs,
    project_root: Path,
    *,
    run_log_path: Path | None = None,
) -> Tool:
    """Construct the concrete :class:`Tool` for ``args.tool``."""
    if args.tool == "opencode":
        return OpencodeTool(
            devcontainer=args.devcontainer,
            workspace_folder=project_root if args.devcontainer else None,
            run_log_path=run_log_path,
        )
    return ClaudeTool(
        model=args.model,
        effort=args.effort,
        devcontainer=args.devcontainer,
        workspace_folder=project_root if args.devcontainer else None,
        run_log_path=run_log_path,
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

    # TASK-256: arm the handlers BEFORE the (possibly multi-minute) devcontainer
    # bring-up and the first ``state="running"`` write, so ``/ralph-stop``'s
    # SIGTERM is always handled instead of killing the process with signal 15.
    # Invariant: once the status file says ``running``, the handlers are armed.
    # Arming early is safe — with no tool subprocess registered the handler
    # only sets the pending flag.
    installer = _SignalInstaller()
    installer.install()
    try:
        return _run_armed(args, project_root, prompt_file_body, installer)
    finally:
        installer.restore()


def _run_armed(
    args: ParsedArgs,
    project_root: Path,
    prompt_file_body: str | None,
    installer: _SignalInstaller,
) -> int:
    """Body of :func:`run`, executed with the signal handlers already armed."""
    # --rebuild is scoped to this call, which is why it is a no-op unless
    # --devcontainer is also set (TASK-237).
    if args.devcontainer:
        rc = start_devcontainer(project_root, rebuild=args.rebuild)
        if rc != 0:
            return rc

    status_path = _status_file_path(project_root)
    heartbeat_path = _heartbeat_file_path(project_root)
    run_log_path = _run_log_file_path(project_root)
    _truncate_run_log(run_log_path)
    timeout_sec = timeout_to_seconds(args.timeout)

    state = _RunState()
    started_epoch = _now_epoch()
    status = _initial_status(args, timeout_sec)

    push_is_enabled = push_module.push_enabled(args.push)
    enforced = push_module.shared_backlog_enforced(project_root)
    state.shared_publish = enforced and push_is_enabled
    rev_before: str | None = None
    try:
        # A stop that arrived during the devcontainer bring-up exits here,
        # before the loop; _finalize still records the interrupted state.
        installer.raise_if_pending()
        status.write_atomic(status_path)

        # TASK-211: snapshot the master ref BEFORE the loop so we can detect
        # whether this run advanced it. The agent merges task branches to master
        # during the loop (loop.py itself never merges); an advanced ref is the
        # signal that there is new canon to publish to origin once the loop ends.
        if push_is_enabled:
            rev_before = push_module.current_rev(
                project_root, push_module.DEFAULT_MASTER_REF
            )
            state.published_rev = rev_before

        tool = build_tool(args, project_root, run_log_path=run_log_path)
        with Heartbeat(heartbeat_path):
            _run_loop(
                args=args,
                project_root=project_root,
                tool=tool,
                timeout_sec=timeout_sec,
                prompt_file_body=prompt_file_body,
                status=status,
                status_path=status_path,
                run_log_path=run_log_path,
                started_epoch=started_epoch,
                state=state,
                installer=installer,
            )
    except _Interrupted:
        # 130 for SIGTERM as well as SIGINT (TASK-256 decision): matches
        # ralph-refine's documented contract and the status-file consumers.
        state.exit_reason = "interrupted"
        state.exit_code = 130
    finally:
        installer.restore()
        _finalize(status, status_path, started_epoch, state, args)

    # TASK-211: after the loop has fully finished (and the summary printed),
    # publish the advanced master ref to origin. Skips cleanly when opted out,
    # when no origin remote exists, or when master did not advance. A push
    # failure is surfaced by carrying its non-zero code into the run's exit
    # code (without masking an already-failing loop). An enforcing clone
    # publishes through integrate instead and never runs the plain push
    # (TASK-312).
    if enforced:
        outcome = _publish_end_of_run(project_root, state)
    else:
        outcome = push_module.maybe_push_after_loop(
            project_root=project_root,
            enabled=push_is_enabled,
            rev_before=rev_before,
        )
    if outcome.exit_code != 0 and state.exit_code == 0:
        state.exit_code = outcome.exit_code

    assert state.exit_reason in EXIT_REASONS, (
        f"exit_reason {state.exit_reason!r} not in closed set {EXIT_REASONS!r}"
    )
    return state.exit_code


def _initial_status(args: ParsedArgs, timeout_sec: int) -> StatusFile:
    """Build the ``state="running"`` status record published at loop start."""
    return StatusFile(
        pid=os.getpid(),
        started_at=_now_iso(),
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


def _run_loop(
    *,
    args: ParsedArgs,
    project_root: Path,
    tool: Tool,
    timeout_sec: int,
    prompt_file_body: str | None,
    status: StatusFile,
    status_path: Path,
    run_log_path: Path,
    started_epoch: int,
    state: _RunState,
    installer: _SignalInstaller,
) -> None:
    whitelist = args.task_whitelist or None
    holder = tasks_module.resolve_holder()

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

        next_task = tasks_module.pick_next_task(
            whitelist=whitelist,
            holder=holder,
            exclude={entry.task for entry in state.skipped},
        )
        if next_task is None:
            state.exit_reason = (
                "all specified tasks done" if whitelist else "all tasks done"
            )
            state.exit_code = 0
            return

        state.last_task = next_task
        rev_iter_before = (
            push_module.current_rev(project_root) if state.shared_publish else None
        )
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
            excluded_task_ids=[entry.task for entry in state.skipped],
        )

        done_before = set(tasks_module.done_task_ids())
        result = _invoke_tool_with_retry(
            tool, prompt, timeout_sec, installer, args, iteration=i
        )

        iter_elapsed = _now_epoch() - iter_start
        state.iter_durations.append(iter_elapsed)

        # A signal pending here means the tool was killed mid-run by the
        # forwarded SIGTERM (handler at _SignalInstaller._handler). Raise
        # before the failure accounting so this surfaces as "interrupted"
        # rather than a generic iteration error.
        installer.raise_if_pending()

        # Bash ralph.sh:838-849 — the one-task-per-iteration summary warning
        # and the current_task re-derivation both run AFTER the retry loop on
        # every NON-stopping exit (success, timeout, on-error=continue). On a
        # stopping exit (--on-error stop, or retry exhausted) bash calls
        # cleanup_and_exit inside handle_error and never reaches them, so
        # current_task stays the picked task and no warning prints.
        terminal_error = result.exit_code not in (0, TIMEOUT_EXIT_CODE)
        stopping = terminal_error and args.on_error in ("stop", "retry")
        if not stopping:
            _warn_task_summary_count(i, result.signals)
            status.current_task = tasks_module.current_in_progress_task()
            _skip_if_left_in_todo(next_task, i, state, run_log_path)

        if result.exit_code == TIMEOUT_EXIT_CODE:
            msg = f"Iteration {i} timed out after {args.timeout}m"
            state.errors.append(
                ErrorEntry(iteration=i, at=_now_iso(), message=msg)
            )
            state.failed_iterations += 1
            _update_after_iteration(
                status, status_path, started_epoch, state, iter_elapsed, whitelist
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
                status, status_path, started_epoch, state, iter_elapsed, whitelist
            )
            if args.on_error == "stop":
                state.exit_reason = "error"
                state.exit_code = result.exit_code
                return
            if args.on_error == "retry":
                # Retries are exhausted here — _invoke_tool_with_retry would
                # have looped instead of returning a failure while attempts
                # remained. Bash printed this and stopped (ralph.sh:652);
                # on-error=continue falls through to the next iteration.
                print(
                    f"ERROR: AI tool failed after {args.retry_count} retries. "
                    "Stopping.",
                    file=sys.stderr,
                )
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
            status, status_path, started_epoch, state, iter_elapsed, whitelist
        )

        # TASK-312: a failed publish stops the run before the next claim,
        # whatever --on-error says.
        if state.shared_publish and not _publish_iteration(
            project_root, next_task, rev_iter_before, i, state
        ):
            return

        if result.signals.complete:
            state.exit_reason = "all tasks done"
            state.exit_code = 0
            return

        installer.raise_if_pending()
        time.sleep(ITER_SLEEP_SEC)

    if state.tasks_completed == 0 or state.failed_iterations > 0:
        state.exit_code = 1


def _publish_iteration(
    project_root: Path,
    task_id: str,
    rev_iter_before: str | None,
    iteration: int,
    state: _RunState,
) -> bool:
    """Run integrate when the iteration advanced master; ``False`` when that publish failed.

    A failure records the error and ends the run with the script's exit code.
    """
    rev_after = push_module.current_rev(project_root)
    if rev_iter_before is None or rev_after is None or rev_after == rev_iter_before:
        return True
    outcome = push_module.integrate(project_root=project_root, task_id=task_id)
    if outcome.exit_code == 0:
        state.published_rev = push_module.current_rev(project_root)
        return True
    message = (
        f"Publishing {task_id} after iteration {iteration} failed (exit {outcome.exit_code}); "
        f"{push_module.local_state(project_root)}. Stopping before the next task; not retried."
    )
    print(f"ERROR: {message}", file=sys.stderr)
    state.errors.append(ErrorEntry(iteration=iteration, at=_now_iso(), message=message))
    state.publish_failed = True
    state.exit_reason = "error"
    state.exit_code = outcome.exit_code
    return False


def _publish_end_of_run(project_root: Path, state: _RunState) -> push_module.PushOutcome:
    """Run the end-of-run integrate in an enforcing clone, unless a publish already failed."""
    if not state.shared_publish:
        return push_module.PushOutcome("skipped", "push disabled (opt-out)", 0)
    if state.publish_failed:
        print("A publish failed during this run; the end-of-run publish is not attempted.", file=sys.stderr)
        return push_module.PushOutcome("skipped", "an earlier publish failed", 0)
    rev_now = push_module.current_rev(project_root)
    if state.published_rev is None or rev_now is None or rev_now == state.published_rev:
        return push_module.PushOutcome("skipped", "master did not advance since the last publish", 0)
    outcome = push_module.integrate(project_root=project_root, task_id=state.last_task)
    if outcome.exit_code != 0:
        print(
            f"ERROR: end-of-run publish failed (exit {outcome.exit_code}); "
            f"{push_module.local_state(project_root)}.",
            file=sys.stderr,
        )
    return outcome


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


def _invoke_tool_with_retry(
    tool: Tool,
    prompt: str,
    timeout_sec: int,
    installer: _SignalInstaller,
    args: ParsedArgs,
    *,
    iteration: int,
) -> ToolResult:
    """Invoke the tool, re-running on failure when ``--on-error=retry``.

    Mirrors the bash retry loop (``ralph.sh:796-836``). A timed-out attempt
    (exit :data:`TIMEOUT_EXIT_CODE`) never retries — bash breaks straight out
    of the retry loop and continues to the next iteration regardless of
    ``--on-error``. A non-timeout failure with ``--on-error=retry`` re-invokes
    the tool up to ``--retry-count`` times; a later success is returned as-is
    so the failure is neither counted nor recorded. Every failed attempt (for
    all strategies, matching bash ``handle_error`` → ``log_error``) appends an
    ERROR line to ``--log-file``, independent of the once-per-iteration status
    error entry the caller records.
    """
    retry_attempt = 0
    while True:
        result = _invoke_tool(tool, prompt, timeout_sec, installer)
        installer.raise_if_pending()
        if result.exit_code in (0, TIMEOUT_EXIT_CODE):
            return result
        _append_error_log(
            args.log_file, iteration, result.exit_code, args.tool, retry_attempt
        )
        if args.on_error == "retry" and retry_attempt < args.retry_count:
            retry_attempt += 1
            print(
                f"WARNING: AI tool failed with exit code {result.exit_code}. "
                f"Retrying (attempt {retry_attempt} of {args.retry_count})...",
                file=sys.stderr,
            )
            installer.raise_if_pending()
            time.sleep(ITER_SLEEP_SEC)
            continue
        return result


def _append_error_log(
    log_file: str,
    iteration: int,
    exit_code: int,
    tool: str,
    retry_attempt: int,
) -> None:
    """Append a bash-parity ERROR line to ``--log-file`` when one is set.

    Mirrors ``log_error`` in ``ralph.sh:614-624`` — a no-op when ``--log-file``
    is empty. The message body matches the ``handle_error`` payload
    (``ralph.sh:631``) so an external log parser sees identical text. Write
    failures are swallowed: a broken log path must not abort the run.
    """
    if not log_file:
        return
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"[{timestamp}] ERROR: Iteration {iteration} failed with exit code "
        f"{exit_code} (tool: {tool}, retry: {retry_attempt})\n"
    )
    with suppress(OSError), Path(log_file).open("a", encoding="utf-8") as handle:
        handle.write(line)


def _warn_task_summary_count(iteration: int, signals: IterationSignals) -> None:
    """Emit the one-task-per-iteration warning to stderr (bash parity).

    Mirrors ``ralph.sh:838-843``: when the iteration transcript does NOT carry
    ``<promise>COMPLETE</promise>`` and the ``## Task Summary`` block count is
    not exactly 1, warn. Fires on timeout and ``--on-error=continue`` exits
    too — the transcript is parsed from whatever the tool emitted before it
    died, so a timed-out iteration with 0 blocks still warns.
    """
    if signals.complete or signals.task_summary_count == 1:
        return
    print(
        f"WARNING: Iteration {iteration} produced {signals.task_summary_count} "
        "'## Task Summary' blocks (expected 1). This may indicate the agent "
        "processed multiple tasks or none.",
        file=sys.stderr,
    )


def _skip_if_left_in_todo(
    task_id: str, iteration: int, state: _RunState, run_log_path: Path
) -> None:
    """Exclude ``task_id`` from the rest of the run when it is still ``To Do``.

    Without this the picker returns the same unchanged task every iteration
    (TASK-324): a blocked whitelist head starves the tasks behind it, and in
    default mode the lowest eligible task wins again. The exclusion is
    announced on stdout and appended to the run log.
    """
    task = tasks_module.fetch_task(task_id)
    if task is None or "To Do" not in task.status:
        return
    state.skipped.append(SkippedTask(task=task_id, iteration=iteration))
    line = (
        f"Ralph: {task_id} left in To Do by iteration {iteration}; "
        "skipping it for the rest of this run"
    )
    print(line, flush=True)
    with suppress(OSError), run_log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _update_after_iteration(
    status: StatusFile,
    status_path: Path,
    started_epoch: int,
    state: _RunState,
    last_iter_dur: int,
    whitelist: list[str] | None,
) -> None:
    status.tasks_done = list(state.tasks_done_ids)
    status.errors = list(state.errors)
    status.skipped_tasks = list(state.skipped)
    status.last_iteration_duration = last_iter_dur
    status.elapsed = _now_epoch() - started_epoch
    status.tasks_remaining = tasks_module.count_remaining(whitelist)
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
    status.skipped_tasks = list(state.skipped)
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
        skipped_tasks=[(entry.task, entry.iteration) for entry in state.skipped],
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


def _run_log_file_path(project_root: Path) -> Path:
    """Resolve the project-rooted run log path; honor ``RALPH_RUN_LOG`` env.

    Parity with ``ralph.sh:461``:
    ``RUN_LOG="${RALPH_RUN_LOG:-${RALPH_PROJECT_ROOT:-$SCRIPT_DIR}/backlog/.ralph-run.log}"``.
    """
    env = os.environ.get("RALPH_RUN_LOG")
    if env:
        return Path(env)
    return project_root / "backlog" / ".ralph-run.log"


def _truncate_run_log(run_log_path: Path) -> None:
    """Truncate the run log to zero bytes at orchestrator startup.

    Parity with ``ralph.sh:692``: ``: > "$RUN_LOG"``. Parent directory is
    created if missing (bash does ``mkdir -p`` immediately before).
    """
    run_log_path.parent.mkdir(parents=True, exist_ok=True)
    with run_log_path.open("wb"):
        pass


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
