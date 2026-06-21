"""Pytest fixtures shared by US-002 unit + parity tests."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "skills" / "ralph-run" / "scripts"
BASH_PREFLIGHT = SCRIPTS_DIR / "preflight.sh"
BASH_WAIT_HEARTBEAT = SCRIPTS_DIR / "wait-heartbeat.sh"
BASH_USAGE_CHECK = SCRIPTS_DIR / "usage-check.sh"
SYS_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_mock_bin(bin_dir: Path, name: str, body: str) -> Path:
    """Write a bash script under ``bin_dir/name`` and make it executable."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / name
    script.write_text(f"#!/bin/bash\n{body}\n")
    _make_executable(script)
    return script


@dataclass(frozen=True)
class PreflightFixture:
    project_dir: Path
    bin_dir: Path
    ralph_sh: Path
    path_value: str

    def env(self, **extra: str) -> dict[str, str]:
        base = {
            "PATH": self.path_value,
            "HOME": str(self.project_dir),
            "LANG": "C",
            "LC_ALL": "C",
        }
        if "TMPDIR" in os.environ:
            base["TMPDIR"] = os.environ["TMPDIR"]
        base.update(extra)
        return base


@pytest.fixture
def preflight_fixture(tmp_path: Path) -> Iterator[PreflightFixture]:
    project_dir = tmp_path / "project"
    (project_dir / "backlog").mkdir(parents=True)
    bin_dir = project_dir / "bin"
    bin_dir.mkdir()
    ralph_sh = project_dir / "ralph.sh"
    ralph_sh.write_text("#!/bin/bash\necho hello\n")
    _make_executable(ralph_sh)
    path_value = f"{bin_dir}:{SYS_PATH}"
    yield PreflightFixture(project_dir, bin_dir, ralph_sh, path_value)
