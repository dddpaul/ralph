"""Bash↔Python parity tests for ``wait-heartbeat``.

Both helpers sleep up to 10 seconds — to keep the test suite quick we put a
fresh heartbeat in place upfront so they finish on the first poll, OR we
patch the sleep and use a stale heartbeat for the failure paths.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "skills" / "ralph-run" / "scripts"
BASH_WAIT = SCRIPTS_DIR / "wait-heartbeat.sh"
SYS_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


@dataclass(frozen=True)
class Scenario:
    project_dir: Path


@pytest.fixture
def scenario(tmp_path: Path) -> Iterator[Scenario]:
    project = tmp_path / "project"
    project.mkdir()
    yield Scenario(project)


def _env(scenario: Scenario) -> dict[str, str]:
    return {
        "PATH": SYS_PATH,
        "HOME": str(scenario.project_dir),
        "LANG": "C",
        "LC_ALL": "C",
    }


def _run_bash(scenario: Scenario):
    return subprocess.run(
        ["bash", str(BASH_WAIT)],
        env=_env(scenario),
        cwd=str(scenario.project_dir),
        capture_output=True,
        text=True,
        check=False,
    )


def _run_python(scenario: Scenario):
    env = _env(scenario)
    env["PYTHONPATH"] = str(SCRIPTS_DIR)
    return subprocess.run(
        [sys.executable, "-m", "ralph.wait_heartbeat"],
        env=env,
        cwd=str(scenario.project_dir),
        capture_output=True,
        text=True,
        check=False,
    )


def _assert_parity_normalized(scenario: Scenario, normalize_age: bool = True) -> None:
    """Run both helpers, optionally normalize the age field to absorb timing jitter."""
    bash_result = _run_bash(scenario)
    py_result = _run_python(scenario)
    assert bash_result.returncode == py_result.returncode

    if normalize_age:
        bash_out = _normalize_ok_line(bash_result.stdout)
        py_out = _normalize_ok_line(py_result.stdout)
    else:
        bash_out = bash_result.stdout
        py_out = py_result.stdout
    assert bash_out == py_out, (
        f"stdout mismatch\nbash: {bash_result.stdout!r}\npy:   {py_result.stdout!r}"
    )


def _normalize_ok_line(text: str) -> str:
    """Replace `age=Ns after Ms` with `age=*s after *s` to absorb scheduling jitter."""
    import re

    return re.sub(
        r"OK heartbeat age=\d+s after \d+s",
        "OK heartbeat age=*s after *s",
        text,
    )


def test_parity_no_backlog_dir(scenario: Scenario) -> None:
    # backlog/ intentionally missing
    bash_result = _run_bash(scenario)
    py_result = _run_python(scenario)
    assert bash_result.stdout == py_result.stdout
    assert bash_result.returncode == py_result.returncode == 2


def test_parity_fresh_heartbeat_ok(scenario: Scenario) -> None:
    (scenario.project_dir / "backlog").mkdir()
    hb = scenario.project_dir / "backlog" / ".ralph-heartbeat"
    hb.touch()
    _assert_parity_normalized(scenario)


def test_parity_fresh_heartbeat_unlinks_launch_log(scenario: Scenario) -> None:
    (scenario.project_dir / "backlog").mkdir()
    (scenario.project_dir / "backlog" / ".ralph-heartbeat").touch()
    launch_log = scenario.project_dir / "backlog" / ".ralph-launch.log"
    launch_log.write_text("some noise\n")

    bash_result = _run_bash(scenario)
    assert bash_result.returncode == 0
    assert not launch_log.exists()

    # Re-create the launch log so the python side has identical preconditions.
    launch_log.write_text("some noise\n")
    py_result = _run_python(scenario)
    assert py_result.returncode == 0
    assert not launch_log.exists()


def test_parity_stale_heartbeat_fails(scenario: Scenario) -> None:
    (scenario.project_dir / "backlog").mkdir()
    hb = scenario.project_dir / "backlog" / ".ralph-heartbeat"
    hb.touch()
    old = time.time() - 3600
    os.utime(hb, (old, old))

    bash_result = _run_bash(scenario)
    py_result = _run_python(scenario)
    assert bash_result.returncode == py_result.returncode == 1
    # Both flush an opening header line.
    for out in (bash_result.stdout, py_result.stdout):
        assert "FAIL no fresh heartbeat after 10s" in out
        assert "--- launch log (last 20 lines) ---" in out
        assert "--- run log (last 20 lines) ---" in out
        assert "(launch log not created)" in out
        assert "(run log not created)" in out


def test_parity_stale_heartbeat_with_logs(scenario: Scenario) -> None:
    (scenario.project_dir / "backlog").mkdir()
    hb = scenario.project_dir / "backlog" / ".ralph-heartbeat"
    hb.touch()
    old = time.time() - 3600
    os.utime(hb, (old, old))
    launch_log = scenario.project_dir / "backlog" / ".ralph-launch.log"
    launch_log.write_text("L1\nL2\nL3\n")
    run_log = scenario.project_dir / "backlog" / ".ralph-run.log"
    run_log.write_text("R1\nR2\nR3\n")

    bash_result = _run_bash(scenario)
    py_result = _run_python(scenario)
    assert bash_result.returncode == py_result.returncode == 1
    assert bash_result.stdout == py_result.stdout
