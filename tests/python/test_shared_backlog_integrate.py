"""How integrate of the shared-backlog script merges, stops and publishes (TASK-309).

``tests/shell/shared-backlog-integrate-test.sh`` drives
``plugins/ralph/scripts/shared-backlog.sh`` in scratch repos with two clones:
a merge (never a rebase) with an ``Integrated-Origin`` trailer, an opt-in and
checks policy fixed from the pre-merge HEAD, refusals before merging without
checks or their execution context, a stop with an old-to-new mapping on
duplicate IDs, an interrupted merge left as it is, and push retries only on a
non-fast-forward rejection. This harness runs that suite with the host's
``SHARED_BACKLOG_*``, ``RALPH_RUN_LOCK_TOKEN`` and git repository-location
variables removed.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest
from devcontainer_config import REPO_ROOT

SUITE = REPO_ROOT / "tests" / "shell" / "shared-backlog-integrate-test.sh"


def suite_env() -> dict[str, str]:
    """Return the host environment minus variables that steer the script or git."""
    dropped = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "RALPH_RUN_LOCK_TOKEN"}
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SHARED_BACKLOG_") and key not in dropped
    }


@pytest.mark.skipif(shutil.which("backlog") is None, reason="backlog CLI not on PATH")
@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_integrate_suite_passes() -> None:
    """The integrate suite passes against the plugin's script."""
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
