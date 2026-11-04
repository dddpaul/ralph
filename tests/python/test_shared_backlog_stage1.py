"""Baseline for the imported stage-1 shared-backlog script (TASK-303).

The plugin's ``plugins/ralph/scripts/shared-backlog.sh`` starts as a
byte-identical copy of a sibling project's proven stage-1 script, pinned at that
project's commit ``af5b1f8``. Later tasks harden the plugin copy. This baseline
keeps testing the unchanged script: ``tests/shell/stage1/`` holds the original
script as ``shared-backlog.sh.orig``, its pre-push hook and its own test suite,
all pinned by sha256.

The stage-1 suite expects its original layout. It resolves its source root as
``<suite>/../..`` and copies ``scripts/shared-backlog.sh``,
``scripts/hooks/pre-push`` and ``backlog/config.yml`` from there. The harness
therefore rebuilds that layout in a temp directory and runs the suite in place.
It never points the suite at the hardened plugin copy.

Two inputs are isolated from the host so that only the frozen script decides
the outcome:

- the backlog config comes from the pinned fixture ``tests/shell/stage1/config.yml``,
  not this repo's live ``backlog/config.yml``;
- the suite runs without ``SHARED_BACKLOG_*`` variables, which change the
  script's behaviour, and without git's repository-location variables.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT

STAGE1 = REPO_ROOT / "tests" / "shell" / "stage1"

# sha256 of each file at the source commit af5b1f8.
PINNED = {
    "shared-backlog.sh.orig": "0da8293dff6254cf13bd6bbf806f5ed86a6f835d1ec597adbf1e614b55b75b0a",
    "pre-push": "db0cc145ef6102b6bf745102bb527b2c66b9dbfe9c34f59e8053b7ae5f9a994b",
    "shared-backlog-test.sh": "b94ed435e5e30a4794405cc1210ddfa36a924b0581a5075ecdd016b7e5b0f498",
}


def sha256(path: Path) -> str:
    """Return the hex sha256 of ``path``."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("name", sorted(PINNED))
def test_stage1_file_is_unchanged(name: str) -> None:
    """Every stage-1 reference file still matches its source-commit sha256."""
    assert sha256(STAGE1 / name) == PINNED[name]


def build_stage1_layout(root: Path) -> Path:
    """Recreate the stage-1 layout under ``root``; return the suite path."""
    (root / "scripts" / "hooks").mkdir(parents=True)
    (root / "scripts" / "tests").mkdir()
    (root / "backlog").mkdir()
    shutil.copy2(
        STAGE1 / "shared-backlog.sh.orig", root / "scripts" / "shared-backlog.sh"
    )
    shutil.copy2(STAGE1 / "pre-push", root / "scripts" / "hooks" / "pre-push")
    suite = root / "scripts" / "tests" / "shared-backlog-test.sh"
    shutil.copy2(STAGE1 / "shared-backlog-test.sh", suite)
    shutil.copy2(STAGE1 / "config.yml", root / "backlog" / "config.yml")
    return suite


def suite_env() -> dict[str, str]:
    """Return the host environment minus variables that steer the frozen script or git."""
    git_location = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"}
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SHARED_BACKLOG_") and key not in git_location
    }


@pytest.mark.skipif(shutil.which("backlog") is None, reason="backlog CLI not on PATH")
def test_stage1_suite_passes(tmp_path: Path) -> None:
    """The unchanged stage-1 suite passes against the unchanged stage-1 script."""
    suite = build_stage1_layout(tmp_path / "stage1")
    result = subprocess.run(
        ["bash", str(suite)],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
        env=suite_env(),
    )
    report = result.stdout[-4000:] + result.stderr[-2000:]
    assert result.returncode == 0, report
    assert "FAIL - " not in result.stdout, report
    assert "passed: " in result.stdout, report
