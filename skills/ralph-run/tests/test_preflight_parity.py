"""Bash↔Python parity tests for ``preflight``.

Each scenario invokes both ``preflight.sh`` and ``python -m ralph.preflight``
with identical args, env, and PWD. We assert byte-identical stdout AND exit
code (AC #5).
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "skills" / "ralph-run" / "scripts"
BASH_PREFLIGHT = SCRIPTS_DIR / "preflight.sh"
SYS_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def _executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _mock_bin(bin_dir: Path, name: str, body: str) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / name
    script.write_text(f"#!/bin/bash\n{body}\n")
    _executable(script)
    return script


@dataclass(frozen=True)
class Scenario:
    project_dir: Path
    bin_dir: Path
    ralph_sh: Path
    path_value: str


@pytest.fixture
def scenario(tmp_path: Path) -> Iterator[Scenario]:
    project = tmp_path / "project"
    (project / "backlog").mkdir(parents=True)
    bin_dir = project / "bin"
    bin_dir.mkdir()
    ralph_sh = project / "ralph.sh"
    ralph_sh.write_text("#!/bin/bash\necho hello\n")
    _executable(ralph_sh)
    yield Scenario(project, bin_dir, ralph_sh, f"{bin_dir}:{SYS_PATH}")


def _env_for(scenario: Scenario, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {
        "PATH": scenario.path_value,
        "HOME": str(scenario.project_dir),
        "LANG": "C",
        "LC_ALL": "C",
    }
    if "TMPDIR" in os.environ:
        env["TMPDIR"] = os.environ["TMPDIR"]
    if extra:
        env.update(extra)
    return env


def _run_bash(scenario: Scenario, args: list[str], extra_env: dict[str, str] | None = None):
    return subprocess.run(
        ["bash", str(BASH_PREFLIGHT), *args],
        env=_env_for(scenario, extra_env),
        cwd=str(scenario.project_dir),
        capture_output=True,
        text=True,
        check=False,
    )


def _run_python(
    scenario: Scenario, args: list[str], extra_env: dict[str, str] | None = None
):
    env = _env_for(scenario, extra_env)
    env["PYTHONPATH"] = str(SCRIPTS_DIR)
    return subprocess.run(
        [sys.executable, "-m", "ralph.preflight", *args],
        env=env,
        cwd=str(scenario.project_dir),
        capture_output=True,
        text=True,
        check=False,
    )


def _assert_parity(scenario: Scenario, args: list[str], extra_env: dict[str, str] | None = None):
    bash_result = _run_bash(scenario, args, extra_env)
    py_result = _run_python(scenario, args, extra_env)
    assert bash_result.stdout == py_result.stdout, (
        f"stdout mismatch\nbash: {bash_result.stdout!r}\npy:   {py_result.stdout!r}"
    )
    assert bash_result.returncode == py_result.returncode, (
        f"exit code mismatch (bash={bash_result.returncode} "
        f"py={py_result.returncode})\nbash stderr: {bash_result.stderr}\n"
        f"py stderr: {py_result.stderr}"
    )


def test_parity_no_todo_tasks(scenario: Scenario) -> None:
    _mock_bin(scenario.bin_dir, "backlog", 'echo "No tasks found"')
    _assert_parity(scenario, [str(scenario.ralph_sh), "false"])


def test_parity_success_path(scenario: Scenario) -> None:
    _mock_bin(
        scenario.bin_dir, "backlog", 'echo "To Do:"; echo "  TASK-1 - Test"'
    )
    _assert_parity(scenario, [str(scenario.ralph_sh), "false"])


def test_parity_ralph_running(scenario: Scenario) -> None:
    (scenario.project_dir / "backlog" / ".ralph-status.json").write_text(
        '{"pid":99999,"state":"running"}\n'
    )
    (scenario.project_dir / "backlog" / ".ralph-heartbeat").touch()
    _mock_bin(scenario.bin_dir, "backlog", 'echo "  TASK-1 - Something"')
    _assert_parity(scenario, [str(scenario.ralph_sh), "false"])


def test_parity_devcontainer_missing(scenario: Scenario) -> None:
    _mock_bin(scenario.bin_dir, "backlog", 'echo "  TASK-1 - Something"')
    # Default PATH already excludes devcontainer; no extra override needed.
    _assert_parity(scenario, [str(scenario.ralph_sh), "true"])


def test_parity_ralph_not_executable(scenario: Scenario) -> None:
    scenario.ralph_sh.chmod(0o644)
    _mock_bin(scenario.bin_dir, "backlog", 'echo "  TASK-1 - Something"')
    _assert_parity(scenario, [str(scenario.ralph_sh), "false"])


def test_parity_ralph_syntax_error(scenario: Scenario) -> None:
    scenario.ralph_sh.write_text('#!/bin/bash\necho "unterminated\n')
    _mock_bin(scenario.bin_dir, "backlog", 'echo "  TASK-1 - Something"')
    # bash and python both extract first non-locale-warning stderr line. The
    # exact wording of bash's syntax-error message can vary by bash version,
    # so we compare only the prefix + exit code rather than full byte equality.
    bash_result = _run_bash(scenario, [str(scenario.ralph_sh), "false"])
    py_result = _run_python(scenario, [str(scenario.ralph_sh), "false"])
    assert bash_result.returncode == py_result.returncode == 1
    assert bash_result.stdout.startswith("ERROR: ralph.sh has syntax errors:")
    assert py_result.stdout.startswith("ERROR: ralph.sh has syntax errors:")


def test_parity_invalid_devcontainer_usage(scenario: Scenario) -> None:
    _assert_parity(scenario, [str(scenario.ralph_sh), "maybe"])


def test_parity_tasks_whitelist_done(scenario: Scenario) -> None:
    _mock_bin(
        scenario.bin_dir,
        "backlog",
        'echo "Task TASK-1 - Test"; echo "Status: Done"',
    )
    _assert_parity(scenario, [str(scenario.ralph_sh), "false", "--tasks", "1"])


def test_parity_block_end_buffer_invalid(scenario: Scenario) -> None:
    _mock_bin(scenario.bin_dir, "backlog", 'echo "  TASK-1 - Something"')
    _assert_parity(
        scenario,
        [str(scenario.ralph_sh), "false", "--block-end-buffer-min", "-1"],
    )
