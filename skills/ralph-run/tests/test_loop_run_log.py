"""TASK-176: Python orchestrator writes ``backlog/.ralph-run.log`` (bash parity).

The bash orchestrator continuously tees subprocess output into
``<project_root>/backlog/.ralph-run.log`` (parity reference: ``ralph.sh:461``
for the env-or-default path, ``ralph.sh:692`` for the truncate). Without this
file, downstream debugging of a Python-orchestrated run loses its primary
signal — ``wait_heartbeat.py:73`` emits the literal ``(run log not created)``
on failure-path tails.

These tests exercise the orchestrator end-to-end via ``fake_claude.py`` to
prove parity:

* AC #5/#6 — a 2-iteration run leaves a non-empty file at
  ``backlog/.ralph-run.log`` whose contents include output from BOTH
  iterations (i.e. the file is appended, not overwritten per iteration —
  which is the strict reading of AC #3 at the e2e layer).
* AC #8 — ``RALPH_RUN_LOG`` redirects the destination; the default path is
  not touched when the override is set.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR = REPO_ROOT / "skills" / "ralph-run" / "scripts" / "ralph_orchestrator.py"
FAKE_CLAUDE = REPO_ROOT / "skills" / "ralph-run" / "tests" / "fixtures" / "fake_claude.py"
BACKLOG_BIN = shutil.which("backlog")
UV_BIN = shutil.which("uv")
SYS_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

_TASK_ID_RE = re.compile(r"TASK-(\d+)")


pytestmark = pytest.mark.skipif(
    BACKLOG_BIN is None or UV_BIN is None,
    reason="requires both 'backlog' and 'uv' on PATH",
)


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _init_two_task_project(project_dir: Path) -> tuple[str, str]:
    """Create a backlog project with two To Do tasks; return their bare IDs."""
    assert BACKLOG_BIN is not None
    env = os.environ.copy()
    env["PATH"] = f"{Path(BACKLOG_BIN).parent}:{SYS_PATH}"
    subprocess.run(
        [
            BACKLOG_BIN, "init", "ralph-runlog-e2e", "--no-git", "--defaults",
            "--agent-instructions", "none", "--bypass-git-hooks", "true",
            "--zero-padded-ids", "0",
        ],
        cwd=project_dir, env=env, check=True, capture_output=True,
    )
    for n in (1, 2):
        subprocess.run(
            [
                BACKLOG_BIN, "task", "create", f"runlog-target-{n}",
                "-d", f"E2E target {n}", "--ac", "Marked done by fake_claude",
                "--plain",
            ],
            cwd=project_dir, env=env, check=True, capture_output=True, text=True,
        )
    listing = subprocess.run(
        [BACKLOG_BIN, "task", "list", "-s", "To Do", "--plain"],
        cwd=project_dir, env=env, check=True, capture_output=True, text=True,
    )
    ids = _TASK_ID_RE.findall(listing.stdout)
    if len(ids) < 2:
        raise RuntimeError(f"expected 2 To Do tasks, got: {listing.stdout!r}")
    return ids[0], ids[1]


def _install_claude_shim(bin_dir: Path) -> None:
    """Drop a ``claude`` shim under ``bin_dir`` that wraps ``fake_claude.py``."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    shim = bin_dir / "claude"
    shim.write_text(
        f"""#!/bin/bash
exec {sys.executable} {FAKE_CLAUDE} "$@"
"""
    )
    _make_executable(shim)


@pytest.fixture
def two_task_project(
    tmp_path: Path,
) -> Iterator[tuple[Path, str, str, dict[str, str]]]:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    bin_dir = tmp_path / "bin"
    _install_claude_shim(bin_dir)
    task_a, task_b = _init_two_task_project(project_dir)

    assert BACKLOG_BIN is not None
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{Path(BACKLOG_BIN).parent}:{SYS_PATH}"
    env["RALPH_PROJECT_ROOT"] = str(project_dir)
    env["RALPH_STATUS_FILE"] = str(project_dir / "backlog" / ".ralph-status.json")
    env["RALPH_HEARTBEAT_FILE"] = str(project_dir / "backlog" / ".ralph-heartbeat")
    env["FAKE_CLAUDE_MODE"] = "success"

    yield project_dir, task_a, task_b, env


def _run_orchestrator(
    project_dir: Path,
    env: dict[str, str],
    *,
    task_csv: str,
    max_iter: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable, str(ORCHESTRATOR),
            "--tool", "claude",
            "--tasks", task_csv,
            "--timeout", "1",
            str(max_iter),
        ],
        cwd=project_dir, env=env, capture_output=True, text=True, timeout=180,
    )


def test_run_log_created_and_grows_across_iterations(
    two_task_project: tuple[Path, str, str, dict[str, str]],
) -> None:
    """AC #5, AC #6: a 2-iteration Python run leaves a non-empty
    ``backlog/.ralph-run.log`` whose contents include output from BOTH
    iterations (strict reading of AC #3 at the e2e layer — the file is
    appended, not overwritten per iteration)."""
    project_dir, task_a, task_b, env = two_task_project
    # ``task_done_no_summary`` marks the task Done but emits no
    # ``<promise>COMPLETE</promise>`` sentinel — so iter 1 does not short-
    # circuit the loop and iter 2 actually runs.
    env["FAKE_CLAUDE_MODE"] = "task_done_no_summary"

    proc = _run_orchestrator(
        project_dir, env, task_csv=f"{task_a},{task_b}", max_iter=2
    )
    assert proc.returncode == 0, (
        f"orchestrator exited {proc.returncode}\n--stdout--\n{proc.stdout}\n"
        f"--stderr--\n{proc.stderr}"
    )

    run_log = project_dir / "backlog" / ".ralph-run.log"
    assert run_log.exists(), "backlog/.ralph-run.log was not created (AC #6)"
    assert run_log.stat().st_size > 0, "backlog/.ralph-run.log is empty (AC #6)"

    contents = run_log.read_text()
    banner = "fake_claude: starting work on task"
    banner_count = contents.count(banner)
    assert banner_count == 2, (
        f"expected 2 fake_claude banners (one per iteration); got {banner_count}\n"
        f"--- run log ---\n{contents}"
    )
    assert f"TASK-{task_a}" in contents and f"TASK-{task_b}" in contents, (
        f"run log missing per-iteration task IDs (a={task_a}, b={task_b}):\n{contents}"
    )


def test_run_log_respects_RALPH_RUN_LOG_override(
    two_task_project: tuple[Path, str, str, dict[str, str]],
    tmp_path: Path,
) -> None:
    """AC #8: ``RALPH_RUN_LOG`` redirects the run log to a custom path; the
    default ``backlog/.ralph-run.log`` is NOT created when the override is set
    (parity with ``ralph.sh:461`` — the env wins, no fallback write)."""
    project_dir, task_a, _task_b, env = two_task_project
    custom_log = tmp_path / "custom-runlog" / "ralph.log"
    env["RALPH_RUN_LOG"] = str(custom_log)

    proc = _run_orchestrator(
        project_dir, env, task_csv=str(task_a), max_iter=1
    )
    assert proc.returncode == 0, (
        f"orchestrator exited {proc.returncode}\n--stdout--\n{proc.stdout}\n"
        f"--stderr--\n{proc.stderr}"
    )

    assert custom_log.exists(), (
        f"RALPH_RUN_LOG path was not created: {custom_log}"
    )
    assert custom_log.stat().st_size > 0, (
        f"RALPH_RUN_LOG override file is empty: {custom_log}"
    )
    default_log = project_dir / "backlog" / ".ralph-run.log"
    assert not default_log.exists(), (
        "default run log should not exist when RALPH_RUN_LOG is set; "
        f"found: {default_log}"
    )
