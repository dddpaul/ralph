"""End-to-end orchestrator test against ``fake_claude.py`` (US-005 AC #9).

Spins up an isolated backlog project in ``tmp_path``, drops a ``claude``
shim on PATH that wraps ``fake_claude.py``, invokes ``ralph_orchestrator.py``
as a subprocess, and asserts the final status JSON shape: ``state="completed"``,
``exit_code=0``, ``errors=[]``, and ``tasks_done`` contains the fake-marked
task.

The orchestrator is invoked via ``subprocess`` (not in-process) so PATH and
``RALPH_PROJECT_ROOT`` overrides hit the actual production code paths.
"""

from __future__ import annotations

import json
import os
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


pytestmark = pytest.mark.skipif(
    BACKLOG_BIN is None or UV_BIN is None,
    reason="E2E test requires both 'backlog' and 'uv' on PATH",
)


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


_TASK_ID_RE = __import__("re").compile(r"TASK-(\d+)")


def _init_backlog_project(project_dir: Path) -> str:
    """Create a backlog project with one To Do task; return the bare task ID."""
    assert BACKLOG_BIN is not None
    env = os.environ.copy()
    env["PATH"] = f"{Path(BACKLOG_BIN).parent}:{SYS_PATH}"
    subprocess.run(
        [
            BACKLOG_BIN,
            "init",
            "ralph-e2e",
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
            "fake-target",
            "-d",
            "E2E fake target task",
            "--ac",
            "Marked done by fake_claude shim",
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
    """Write a ``claude`` script under ``bin_dir`` that wraps ``fake_claude.py``.

    The orchestrator's ClaudeTool spawns ``["claude", "--model", ..., "--print"]``;
    this shim accepts and ignores all flags, then execs the fake.
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    shim = bin_dir / "claude"
    shim.write_text(
        f"""#!/bin/bash
exec {sys.executable} {FAKE_CLAUDE} "$@"
"""
    )
    _make_executable(shim)


@pytest.fixture
def e2e_project(tmp_path: Path) -> Iterator[tuple[Path, str, dict[str, str]]]:
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
    env["FAKE_CLAUDE_MODE"] = "success"

    yield project_dir, task_id, env


def test_orchestrator_completes_against_fake_claude_success(
    e2e_project: tuple[Path, str, dict[str, str]],
) -> None:
    """AC #9 — success mode → state=completed, exit_code=0, errors=[], tasks_done populated."""
    project_dir, task_id, env = e2e_project

    proc = subprocess.run(
        [
            sys.executable,
            str(ORCHESTRATOR),
            "--tool",
            "claude",
            "--tasks",
            task_id,
            "--timeout",
            "1",
            "3",
        ],
        cwd=project_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert proc.returncode == 0, (
        f"orchestrator exited {proc.returncode}\n--stdout--\n{proc.stdout}\n"
        f"--stderr--\n{proc.stderr}"
    )

    status_path = project_dir / "backlog" / ".ralph-status.json"
    assert status_path.exists(), "status file was not written"
    status = json.loads(status_path.read_text())

    assert status["state"] == "completed", status
    assert status["exit_code"] == 0, status
    assert status["errors"] == [], status
    assert f"TASK-{task_id}" in status["tasks_done"], status
    # AC #7: closed-set exit reasons surface in the summary block on stdout.
    assert "Exit reason:" in proc.stdout
    assert "all tasks done" in proc.stdout
