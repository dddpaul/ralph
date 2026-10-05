"""ralph-status-watch parses ``iteration_started_at`` as UTC (TASK-266).

BSD ``date -j -f`` matches the trailing ``Z`` as a literal but still reads the
fields as local time, so without ``-u`` the epoch shifts by the host's UTC
offset and the "stuck" rule silently never fires off-UTC. The line is run
straight out of SKILL.md so the test follows the shipped text, and only under
non-UTC zones on both sides of UTC — a UTC host would pass with the bug present.

GNU ``date -d`` honours the ``Z`` and wins first on Linux, so the BSD branch is
exercised directly only where BSD ``date`` exists (macOS); elsewhere the static
check that the branch carries ``-u`` is what guards it.
"""

from __future__ import annotations

import os
import re
import subprocess

import pytest
from devcontainer_config import REPO_ROOT

SKILL_MD = REPO_ROOT / "plugins/ralph/skills/ralph-status-watch/SKILL.md"
PLACEHOLDER = "<iteration_started_at>"
STAMP = "2026-10-05T06:21:39Z"
EPOCH = 1791181299
ZONES = ["Europe/Moscow", "America/New_York"]


def conversion_line() -> str:
    """Return the shipped epoch-conversion line from SKILL.md."""
    lines = [
        ln
        for ln in SKILL_MD.read_text("utf-8").splitlines()
        if ln.startswith("date ") and PLACEHOLDER in ln
    ]
    assert len(lines) == 1, f"expected one conversion line in {SKILL_MD}, got {lines}"
    return lines[0]


def bsd_branch() -> str:
    """Return the BSD fallback half of the conversion line."""
    _, _, bsd = conversion_line().partition(" || ")
    assert bsd.startswith("date -j "), f"no BSD fallback in: {conversion_line()}"
    return bsd


def run_in_zone(command: str, zone: str) -> str:
    """Run ``command`` with the fixed timestamp substituted, under ``TZ=zone``."""
    script = command.replace(PLACEHOLDER, STAMP)
    env = {**os.environ, "TZ": zone}
    return subprocess.run(
        ["bash", "-c", script], env=env, capture_output=True, text=True
    ).stdout.strip()


def has_bsd_date() -> bool:
    """Report whether the host ``date`` accepts BSD ``-j -f``."""
    probe = subprocess.run(
        ["date", "-j", "-f", "%s", "0", "+%s"], capture_output=True, text=True
    )
    return probe.returncode == 0 and probe.stdout.strip() == "0"


def test_bsd_branch_parses_as_utc() -> None:
    assert re.match(r"date -j -u -f ", bsd_branch()), bsd_branch()


@pytest.mark.parametrize("zone", ZONES)
def test_shipped_line_yields_utc_epoch(zone: str) -> None:
    assert run_in_zone(conversion_line(), zone) == str(EPOCH)


@pytest.mark.skipif(
    not has_bsd_date(),
    reason="BSD date unavailable; the static -u check guards this branch",
)
@pytest.mark.parametrize("zone", ZONES)
def test_bsd_branch_yields_utc_epoch(zone: str) -> None:
    assert run_in_zone(bsd_branch(), zone) == str(EPOCH)
