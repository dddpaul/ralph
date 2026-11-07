"""The plugin pre-push body that refuses pushes carrying duplicate task IDs (TASK-311).

``tests/shell/shared-backlog-prepush-test.sh`` pushes from scratch clones through
the real plugin shim, with a registry whose ralph entry is this repo's
``plugins/ralph``: ``plugins/ralph/git-hooks/pre-push`` refuses a tip carrying a
duplicate task or draft ID and a push without the backlog CLI, passes a ref
deletion and a push of several refs, keeps enforcing on the clone switch after
the marker is removed, and leaves an existing hook running as ``pre-push.local``
with the same stdin. A real ``create`` push runs the hook while create holds the
protocol lock and completes before its deadline, and a bumped push still runs
this repo's version-bump guard as ``pre-push.local``. This harness runs that
suite with the host's ``SHARED_BACKLOG_*``, ``RALPH_RUN_LOCK_TOKEN``, Claude
config and git repository-location variables removed.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest
from devcontainer_config import REPO_ROOT

SUITE = REPO_ROOT / "tests" / "shell" / "shared-backlog-prepush-test.sh"


def suite_env() -> dict[str, str]:
    """Return the host environment minus variables that steer the script, git or Claude."""
    dropped = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "RALPH_RUN_LOCK_TOKEN", "CLAUDE_CONFIG_DIR", "BASH_ENV"}
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SHARED_BACKLOG_") and key not in dropped
    }


@pytest.mark.skipif(
    shutil.which("backlog") is None or shutil.which("jq") is None, reason="backlog CLI or jq not on PATH"
)
def test_prepush_suite_passes() -> None:
    """The pre-push duplicate-check suite passes against the plugin's hook body."""
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
