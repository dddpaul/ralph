"""Claim rules, the holder, check-dupes and --help of the shared-backlog script (TASK-305).

``tests/shell/shared-backlog-claim-test.sh`` drives
``plugins/ralph/scripts/shared-backlog.sh`` in scratch repos: a bare ``@claude``
assignee counts as unassigned, any other assignee besides the holder means
taken, a held claim still passes the status and dependency checks, the holder
order ``--as`` > ``SHARED_BACKLOG_HOLDER`` > ``git config ralph.holder``,
``check-dupes REV`` reading REV's own config and drafts, and the full ``--help``.
This harness runs that suite with the host's ``SHARED_BACKLOG_*``,
``RALPH_RUN_LOCK_TOKEN`` and git repository-location variables removed.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest
from devcontainer_config import REPO_ROOT

SUITE = REPO_ROOT / "tests" / "shell" / "shared-backlog-claim-test.sh"


def suite_env() -> dict[str, str]:
    """Return the host environment minus variables that steer the script or git."""
    dropped = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "RALPH_RUN_LOCK_TOKEN"}
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SHARED_BACKLOG_") and key not in dropped
    }


@pytest.mark.skipif(shutil.which("backlog") is None, reason="backlog CLI not on PATH")
def test_claim_suite_passes() -> None:
    """The claim, holder, check-dupes and help suite passes against the plugin's script."""
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
