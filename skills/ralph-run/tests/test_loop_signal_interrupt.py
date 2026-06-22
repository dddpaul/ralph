"""Signal-interrupt parity tests for the Python orchestrator (TASK-160).

The bash trap ``_kill_children`` (ralph.sh:582-593) walked ``pgrep -P $$``
and SIGTERM'd each direct child immediately. Before TASK-160 the Python
orchestrator only set a pending-signal flag between iterations, so a
SIGTERM mid-``tool.run()`` left the child running until its own per-iter
timeout.

These tests pin the new contract:

* AC #1/#2 — SIGTERM/SIGINT mid-run kills the registered subprocess's
  process group via ``_SignalInstaller._handler``.
* AC #3 — the orchestrator surfaces ``state="failed"``/``exit_code=130``
  in the status JSON and ``Exit reason: interrupted`` in the summary
  stdout.
* AC #4 — an end-to-end run of the orchestrator over a hanging tool
  exits within ``TERMINATE_GRACE_SEC * 2`` of SIGTERM.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from ralph import loop as loop_module

REPO_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR = REPO_ROOT / "skills" / "ralph-run" / "scripts" / "ralph_orchestrator.py"
FAKE_CLAUDE = REPO_ROOT / "skills" / "ralph-run" / "tests" / "fixtures" / "fake_claude.py"
BACKLOG_BIN = shutil.which("backlog")
UV_BIN = shutil.which("uv")
SYS_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def test_handler_forwards_sigterm_to_active_subprocess_pgroup() -> None:
    """AC #1 — the handler SIGTERMs the registered subprocess's pgroup.

    Drives ``_SignalInstaller._handler`` directly so the test does NOT
    actually deliver a signal to the test process (which would race pytest).
    """
    proc = subprocess.Popen(
        ["sleep", "30"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        installer = loop_module._SignalInstaller()
        installer.set_active_subprocess(proc)
        installer._handler(signal.SIGTERM, None)

        # The handler sent SIGTERM to the pgroup; the child should die fast.
        assert proc.wait(timeout=5) != 0, "child survived handler-forwarded SIGTERM"
        assert installer.is_pending(), "handler must set the pending flag"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_handler_forwards_sigint_to_active_subprocess_pgroup() -> None:
    """AC #2 — SIGINT path uses the same handler/forwarding as SIGTERM.

    The handler is installed for both signals (``signal.signal(SIGINT,
    self._handler)`` and same for SIGTERM); the forwarded signal to the
    child is always SIGTERM (matching bash ``_kill_children``).
    """
    proc = subprocess.Popen(
        ["sleep", "30"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        installer = loop_module._SignalInstaller()
        installer.set_active_subprocess(proc)
        installer._handler(signal.SIGINT, None)

        assert proc.wait(timeout=5) != 0
        assert installer.is_pending()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_handler_is_noop_when_no_active_subprocess() -> None:
    """No registered subprocess → handler only sets the pending flag.

    Regression guard against any future change that tries to dereference
    a missing pgid (would raise ``TypeError`` from ``os.killpg(None, …)``).
    """
    installer = loop_module._SignalInstaller()
    installer._handler(signal.SIGTERM, None)
    assert installer.is_pending()


def test_set_active_subprocess_handles_already_exited_child() -> None:
    """Registering an already-reaped Popen must not raise.

    ``os.getpgid`` raises ``ProcessLookupError`` on a dead pid; the
    installer is expected to swallow it and leave the slot empty so a
    later signal does not target a recycled pid.
    """
    proc = subprocess.Popen(
        ["true"], stdout=subprocess.DEVNULL, start_new_session=True
    )
    proc.wait(timeout=5)
    installer = loop_module._SignalInstaller()
    installer.set_active_subprocess(proc)
    # No assertion on _active_pgid value — important is no exception raised
    # and that a subsequent handler call is harmless.
    installer._handler(signal.SIGTERM, None)
    assert installer.is_pending()


def test_handler_does_not_deadlock_when_lock_already_held() -> None:
    """Regression: signal handler must not deadlock against the active-lock.

    Python signal handlers run synchronously on the main thread. If a
    signal arrives while ``set_active_subprocess`` is inside the ``with
    self._active_lock:`` block, the handler runs on the same stack and
    re-acquires the lock. A non-reentrant ``Lock`` would deadlock.
    """
    installer = loop_module._SignalInstaller()
    installer._active_lock.acquire()
    try:
        # Must return promptly — RLock allows the same-thread re-acquire.
        installer._handler(signal.SIGTERM, None)
    finally:
        installer._active_lock.release()
    assert installer.is_pending()


def test_set_active_subprocess_kills_when_signal_already_pending() -> None:
    """Race close: SIGTERM that arrived BEFORE register is applied at register.

    Models the window between ``subprocess.Popen()`` and the ``on_spawn``
    callback: if a signal arrives in that gap, ``_handler`` sets
    ``_pending`` with no pgid to forward to. The next
    ``set_active_subprocess(proc)`` must retry the forward so the
    just-registered child gets killed promptly.
    """
    proc = subprocess.Popen(
        ["sleep", "30"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        installer = loop_module._SignalInstaller()
        # Signal arrives before registration (handler runs with pgid=None,
        # only sets _pending).
        installer._handler(signal.SIGTERM, None)
        assert installer.is_pending()
        # Now registration arrives: the queued kill must fire here.
        installer.set_active_subprocess(proc)
        assert proc.wait(timeout=5) != 0, (
            "child survived race-close kill in set_active_subprocess"
        )
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_set_active_subprocess_clears_on_none() -> None:
    """Passing ``None`` clears the registration (post-iteration cleanup)."""
    proc = subprocess.Popen(
        ["sleep", "10"], stdout=subprocess.DEVNULL, start_new_session=True
    )
    try:
        installer = loop_module._SignalInstaller()
        installer.set_active_subprocess(proc)
        installer.set_active_subprocess(None)
        # Now a handler fire must NOT kill the still-alive proc.
        installer._handler(signal.SIGTERM, None)
        time.sleep(0.5)
        assert proc.poll() is None, (
            "subprocess was killed even after set_active_subprocess(None)"
        )
    finally:
        proc.terminate()
        proc.wait(timeout=5)


_TASK_ID_RE = re.compile(r"TASK-(\d+)")


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _init_backlog_project(project_dir: Path) -> str:
    assert BACKLOG_BIN is not None
    env = os.environ.copy()
    env["PATH"] = f"{Path(BACKLOG_BIN).parent}:{SYS_PATH}"
    subprocess.run(
        [
            BACKLOG_BIN,
            "init",
            "ralph-signal",
            "--no-git",
            "--defaults",
            "--agent-instructions",
            "none",
            "--bypass-git-hooks",
            "true",
            "--zero-padded-ids",
            "0",
        ],
        cwd=project_dir,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            BACKLOG_BIN,
            "task",
            "create",
            "hang-target",
            "-d",
            "Signal interrupt fixture",
            "--ac",
            "Killed mid-run by SIGTERM",
            "--plain",
        ],
        cwd=project_dir,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    listing = subprocess.run(
        [BACKLOG_BIN, "task", "list", "-s", "To Do", "--plain"],
        cwd=project_dir,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    match = _TASK_ID_RE.search(listing.stdout)
    if match is None:
        raise RuntimeError(
            f"no TASK-N entry visible after create:\n{listing.stdout}"
        )
    return match.group(1)


def _install_claude_shim(bin_dir: Path) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    shim = bin_dir / "claude"
    shim.write_text(
        f"""#!/bin/bash
exec {sys.executable} {FAKE_CLAUDE} "$@"
"""
    )
    _make_executable(shim)


@pytest.fixture
def hang_project(tmp_path: Path) -> Iterator[tuple[Path, str, dict[str, str]]]:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    bin_dir = tmp_path / "bin"
    _install_claude_shim(bin_dir)
    task_id = _init_backlog_project(project_dir)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{Path(BACKLOG_BIN).parent}:{SYS_PATH}"
    env["RALPH_PROJECT_ROOT"] = str(project_dir)
    env["RALPH_STATUS_FILE"] = str(project_dir / "backlog" / ".ralph-status.json")
    env["RALPH_HEARTBEAT_FILE"] = str(project_dir / "backlog" / ".ralph-heartbeat")
    env["FAKE_CLAUDE_MODE"] = "hang"

    yield project_dir, task_id, env


def _reap_session(proc: subprocess.Popen[str]) -> None:
    """Kill the orchestrator's whole session group to avoid orphaned children.

    The orchestrator is spawned with ``start_new_session=True`` so its
    ``fake_claude.py`` child is in a different process group from pytest.
    Killing only ``proc`` would leak the child; killing its session group
    reaps both.
    """
    try:
        pgid = os.getpgid(proc.pid)
    except ProcessLookupError:
        return
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        os.killpg(pgid, signal.SIGKILL)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=5)


@pytest.mark.skipif(
    BACKLOG_BIN is None or UV_BIN is None,
    reason="E2E test requires both 'backlog' and 'uv' on PATH",
)
def test_orchestrator_exits_promptly_on_sigterm(
    hang_project: tuple[Path, str, dict[str, str]],
) -> None:
    """AC #4 — orchestrator + hanging tool + SIGTERM → exit in <10s.

    AC #3 — final status JSON carries ``state="failed"`` / ``exit_code=130``
    and the stdout summary carries ``Exit reason: interrupted``.

    Uses ``FAKE_CLAUDE_MODE=hang`` which sleeps indefinitely; without the
    TASK-160 plumbing the orchestrator would not interrupt the subprocess
    until ``--timeout`` (here: 60 minutes) elapsed.
    """
    project_dir, task_id, env = hang_project

    proc = subprocess.Popen(
        [
            sys.executable,
            str(ORCHESTRATOR),
            "--tool",
            "claude",
            "--tasks",
            task_id,
            "--timeout",
            "60",  # 60-minute per-iter timeout — the test must NOT wait this out.
            "3",
        ],
        cwd=project_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )

    try:
        # Wait for the orchestrator to spawn the child (status file appears).
        status_path = project_dir / "backlog" / ".ralph-status.json"
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            if status_path.exists():
                try:
                    snapshot = json.loads(status_path.read_text())
                except (OSError, json.JSONDecodeError):
                    snapshot = {}
                if snapshot.get("state") == "running":
                    break
            time.sleep(0.1)
        else:
            out, _ = proc.communicate(timeout=5)
            pytest.fail(
                f"orchestrator never entered 'running' state\n--stdout--\n{out}"
            )

        sigterm_sent_at = time.monotonic()
        proc.send_signal(signal.SIGTERM)

        try:
            stdout, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            stdout, _ = proc.communicate(timeout=5)
            pytest.fail(
                "orchestrator did NOT exit within 10s of SIGTERM\n"
                f"--stdout--\n{stdout}"
            )

        elapsed = time.monotonic() - sigterm_sent_at
        assert elapsed < 10, f"orchestrator took {elapsed:.1f}s to exit after SIGTERM"
        assert proc.returncode == 130, (
            f"exit code {proc.returncode}, expected 130\n--stdout--\n{stdout}"
        )

        assert status_path.exists(), "status file was not written"
        status = json.loads(status_path.read_text())
        assert status["state"] == "failed", status
        assert status["exit_code"] == 130, status

        assert "Exit reason:" in stdout
        assert "interrupted" in stdout
    finally:
        # If anything above fails, kill the whole session group so the
        # fake_claude.py orphan does not leak across runs.
        if proc.poll() is None:
            _reap_session(proc)
