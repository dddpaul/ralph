"""How create of the shared-backlog script allocates task IDs in a temporary worktree (TASK-307).

``tests/shell/shared-backlog-create-test.sh`` drives
``plugins/ralph/scripts/shared-backlog.sh`` in scratch repos: create publishes
an ID free on origin from clones that are behind origin, ahead of it, dirty and
on a task branch while leaving their branch, index and working tree unchanged;
its ``Shared-Backlog-Op`` trailer stays the same across a retried push; offline
it exits 2 with no commit and no task file; the clone's hook shim resolves the
plugin with the clone's project identity during a real commit in the worktree;
and sync and integrate refuse while an untracked task file is present. This
harness runs that suite with the host's ``SHARED_BACKLOG_*``,
``RALPH_RUN_LOCK_TOKEN`` and git repository-location variables removed.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest
from devcontainer_config import REPO_ROOT

SUITE = REPO_ROOT / "tests" / "shell" / "shared-backlog-create-test.sh"


def suite_env() -> dict[str, str]:
    """Return the host environment minus variables that steer the script or git."""
    dropped = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "RALPH_RUN_LOCK_TOKEN"}
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SHARED_BACKLOG_") and key not in dropped
    }


@pytest.mark.skipif(shutil.which("backlog") is None, reason="backlog CLI not on PATH")
def test_create_suite_passes() -> None:
    """The temporary-worktree create suite passes against the plugin's script."""
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
