"""Bash↔Python parity tests for ``usage-check``.

Each scenario stages a deterministic ``ccusage`` mock binary on PATH and runs
both helpers from the same PWD. Asserts byte-identical stdout/stderr AND
exit code.
"""

from __future__ import annotations

import json
import stat
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "skills" / "ralph-run" / "scripts"
BASH_USAGE = SCRIPTS_DIR / "usage-check.sh"
SYS_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def _executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _mock(bin_dir: Path, name: str, body: str) -> Path:
    script = bin_dir / name
    script.write_text(f"#!/bin/bash\n{body}\n")
    _executable(script)
    return script


@dataclass(frozen=True)
class Scenario:
    project_dir: Path
    bin_dir: Path
    path_value: str


@pytest.fixture
def scenario(tmp_path: Path) -> Iterator[Scenario]:
    project = tmp_path / "project"
    project.mkdir()
    bin_dir = project / "bin"
    bin_dir.mkdir()
    yield Scenario(project, bin_dir, f"{bin_dir}:{SYS_PATH}")


def _env(scenario: Scenario, path_override: str | None = None) -> dict[str, str]:
    return {
        "PATH": path_override if path_override is not None else scenario.path_value,
        "HOME": str(scenario.project_dir),
        "LANG": "C",
        "LC_ALL": "C",
    }


def _run_bash(scenario: Scenario, args: list[str], path_override: str | None = None):
    return subprocess.run(
        ["bash", str(BASH_USAGE), *args],
        env=_env(scenario, path_override),
        cwd=str(scenario.project_dir),
        capture_output=True,
        text=True,
        check=False,
    )


def _run_python(scenario: Scenario, args: list[str], path_override: str | None = None):
    env = _env(scenario, path_override)
    env["PYTHONPATH"] = str(SCRIPTS_DIR)
    return subprocess.run(
        [sys.executable, "-m", "ralph.usage_check", *args],
        env=env,
        cwd=str(scenario.project_dir),
        capture_output=True,
        text=True,
        check=False,
    )


def _assert_parity(
    scenario: Scenario, args: list[str], path_override: str | None = None
) -> None:
    bash_result = _run_bash(scenario, args, path_override)
    py_result = _run_python(scenario, args, path_override)
    assert bash_result.stdout == py_result.stdout, (
        f"stdout mismatch\nbash: {bash_result.stdout!r}\npy:   {py_result.stdout!r}"
    )
    assert bash_result.stderr == py_result.stderr, (
        f"stderr mismatch\nbash: {bash_result.stderr!r}\npy:   {py_result.stderr!r}"
    )
    assert bash_result.returncode == py_result.returncode, (
        f"exit code mismatch (bash={bash_result.returncode} "
        f"py={py_result.returncode})"
    )


def test_parity_buffer_zero(scenario: Scenario) -> None:
    _assert_parity(scenario, ["0"])


def test_parity_empty_buffer(scenario: Scenario) -> None:
    _assert_parity(scenario, [])


def test_parity_non_numeric_buffer(scenario: Scenario) -> None:
    _assert_parity(scenario, ["abc"])


def test_parity_ccusage_missing(scenario: Scenario) -> None:
    _assert_parity(scenario, ["5"], path_override=SYS_PATH)


def test_parity_active_block_within_buffer(scenario: Scenario) -> None:
    # +3 minutes 30 seconds places the integer-minute count (3) safely inside
    # the second's wide-margin from a wall-clock boundary so bash and Python
    # both compute `REMAINING_MIN = 3` despite a few hundred milliseconds of
    # subprocess startup jitter between the two samples.
    end_time = (datetime.now(tz=UTC) + timedelta(minutes=3, seconds=30)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    payload = json.dumps(
        {"blocks": [{"isActive": True, "isGap": False, "endTime": end_time}]}
    )
    _mock(scenario.bin_dir, "ccusage", f"cat <<'JSON'\n{payload}\nJSON")
    _assert_parity(scenario, ["5"])


def test_parity_active_block_outside_buffer(scenario: Scenario) -> None:
    end_time = (datetime.now(tz=UTC) + timedelta(hours=2)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    payload = json.dumps(
        {"blocks": [{"isActive": True, "isGap": False, "endTime": end_time}]}
    )
    _mock(scenario.bin_dir, "ccusage", f"cat <<'JSON'\n{payload}\nJSON")
    _assert_parity(scenario, ["5"])


def test_parity_inactive_block(scenario: Scenario) -> None:
    payload = json.dumps({"blocks": [{"isActive": False, "isGap": False}]})
    _mock(scenario.bin_dir, "ccusage", f"cat <<'JSON'\n{payload}\nJSON")
    _assert_parity(scenario, ["5"])


def test_parity_ccusage_nonzero_exit(scenario: Scenario) -> None:
    _mock(scenario.bin_dir, "ccusage", 'echo "broken"; exit 9')
    _assert_parity(scenario, ["5"])


def test_parity_unparseable_json(scenario: Scenario) -> None:
    _mock(scenario.bin_dir, "ccusage", 'echo "not json at all"')
    _assert_parity(scenario, ["5"])


def test_parity_missing_endtime(scenario: Scenario) -> None:
    payload = json.dumps({"blocks": [{"isActive": True, "isGap": False}]})
    _mock(scenario.bin_dir, "ccusage", f"cat <<'JSON'\n{payload}\nJSON")
    _assert_parity(scenario, ["5"])
