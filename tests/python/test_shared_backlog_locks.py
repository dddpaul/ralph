"""Lock primitives and deadlines of the hardened shared-backlog script (TASK-304).

``tests/shell/shared-backlog-lock-test.sh`` drives
``plugins/ralph/scripts/shared-backlog.sh`` in scratch repos: lock acquire and
release, token mismatch, stale reclaim and its race, the run-lock gate with
token passthrough, ``check-dupes`` under a held protocol lock, and deadline
expiry. This harness runs that suite with the host's ``SHARED_BACKLOG_*``,
``RALPH_RUN_LOCK_TOKEN`` and git repository-location variables removed.
"""

from __future__ import annotations

import os
import subprocess

from devcontainer_config import REPO_ROOT

SUITE = REPO_ROOT / "tests" / "shell" / "shared-backlog-lock-test.sh"


def suite_env() -> dict[str, str]:
    """Return the host environment minus variables that steer the script or git."""
    dropped = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "RALPH_RUN_LOCK_TOKEN"}
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SHARED_BACKLOG_") and key not in dropped
    }


def test_lock_suite_passes() -> None:
    """The lock and deadline suite passes against the plugin's script."""
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
