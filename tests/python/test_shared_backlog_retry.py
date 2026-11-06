"""How claim, release and create of the shared-backlog script retry a refused push (TASK-306).

``tests/shell/shared-backlog-retry-test.sh`` drives
``plugins/ralph/scripts/shared-backlog.sh`` in scratch repos with two clones:
two claims racing for one task land exactly once and the loser names the winner
with its master equal to origin, a release racing a claim, a claim and a release
retried after an unrelated commit landed on origin, the 3-push limit, a create
race, and no ``git rebase`` left in the script. This harness runs that suite
with the host's ``SHARED_BACKLOG_*``, ``RALPH_RUN_LOCK_TOKEN`` and git
repository-location variables removed.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest
from devcontainer_config import REPO_ROOT

SUITE = REPO_ROOT / "tests" / "shell" / "shared-backlog-retry-test.sh"


def suite_env() -> dict[str, str]:
    """Return the host environment minus variables that steer the script or git."""
    dropped = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "RALPH_RUN_LOCK_TOKEN"}
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SHARED_BACKLOG_") and key not in dropped
    }


@pytest.mark.skipif(shutil.which("backlog") is None, reason="backlog CLI not on PATH")
def test_retry_suite_passes() -> None:
    """The claim, release and create retry suite passes against the plugin's script."""
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
