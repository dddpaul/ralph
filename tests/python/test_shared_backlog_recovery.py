"""How create of the shared-backlog script reconciles uncertain pushes and keeps recovery refs (TASK-308).

``tests/shell/shared-backlog-recovery-test.sh`` drives
``plugins/ralph/scripts/shared-backlog.sh`` in scratch repos: a lost race
reallocates with the same ``Shared-Backlog-Op`` at most 3 times; an ambiguous
push that origin accepted is found by its operation ID and not repeated; a
failed reconciliation stops without allocating again and keeps the commit under
``refs/ralph/recovery/<op-id>``, which survives the worktree's removal and can
be finished or dropped as printed; a deadline or a signal mid-push also keeps
the commit and removes the temporary worktree. This harness runs that suite
with the host's ``SHARED_BACKLOG_*``, ``RALPH_RUN_LOCK_TOKEN`` and git
repository-location variables removed.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest
from devcontainer_config import REPO_ROOT

SUITE = REPO_ROOT / "tests" / "shell" / "shared-backlog-recovery-test.sh"


def suite_env() -> dict[str, str]:
    """Return the host environment minus variables that steer the script or git."""
    dropped = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "RALPH_RUN_LOCK_TOKEN"}
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SHARED_BACKLOG_") and key not in dropped
    }


@pytest.mark.skipif(shutil.which("backlog") is None, reason="backlog CLI not on PATH")
@pytest.mark.skipif(shutil.which("ps") is None, reason="ps not on PATH")
def test_recovery_suite_passes() -> None:
    """The create reconciliation and recovery suite passes against the plugin's script."""
    result = subprocess.run(
        ["bash", str(SUITE)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        env=suite_env(),
    )
    report = result.stdout[-4000:] + result.stderr[-2000:]
    assert result.returncode == 0, report
    assert "FAIL - " not in result.stdout, report
    assert "passed: " in result.stdout, report
