"""Upgrade's re-offer of the uv pin patch (TASK-252).

The uv pin patch used to fire only while U4 was rewriting ``devcontainer.json``.
A user who declined it once had a current ``devcontainer.json`` on the next run,
so U4 never touched the file, the offer never fired, and the run reported every
file up to date while uv still came from ``ghcr.io/astral-sh/uv:latest``. U2 now
reads the Dockerfile itself through ``scripts/floating-uv-copy.sh check``, so
the status — and the offer keyed to it — comes back on every run until the file
is patched.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import LIVE_DIR, REPO_ROOT, TEMPLATE_DIR
from test_upgrade_stale_runtime_copy import (
    FLAVOURS,
    OLD_INSTALL,
    OLD_STAGE,
    assemble,
    current,
)
from test_upgrade_stale_runtime_copy import run as run_stale

SKILL_DIR = REPO_ROOT / "plugins/ralph/skills/ralph-init"
SCRIPT = SKILL_DIR / "scripts/floating-uv-copy.sh"
SKILL_MD = SKILL_DIR / "SKILL.md"
PINNED_STAGE = "FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv-bin\n"
PINNED_COPY = "COPY --from=uv-bin /uv /usr/local/bin/uv"
FLOATING_COPY = "COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv"


def pre_251(text: str) -> str:
    """``text`` with the pinned uv stage swapped back for the floating copy."""
    old = text.replace(PINNED_STAGE, "").replace(PINNED_COPY, FLOATING_COPY)
    assert old != text
    return old


def run(
    dockerfile: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), "check", str(dockerfile)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "Dockerfile"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("flavour", FLAVOURS)
def test_pre_251_dockerfile_is_flagged(tmp_path: Path, flavour: str) -> None:
    out = run(write(tmp_path, pre_251(current(flavour))))
    assert out.returncode == 1, out.stderr
    (line,) = out.stdout.splitlines()
    assert "COPY --from=ghcr.io/astral-sh/uv:latest" in line
    assert "floats" in line


@pytest.mark.parametrize("flavour", FLAVOURS)
def test_pinned_dockerfile_is_not_flagged(tmp_path: Path, flavour: str) -> None:
    out = run(write(tmp_path, current(flavour)))
    assert (out.returncode, out.stdout) == (0, ""), out.stderr


def test_live_dockerfile_is_not_flagged() -> None:
    out = run(LIVE_DIR / "Dockerfile")
    assert (out.returncode, out.stdout) == (0, ""), out.stderr


@pytest.mark.parametrize(
    "ref",
    (
        "ghcr.io/astral-sh/uv",
        "ghcr.io/astral-sh/uv:latest",
        "ghcr.io/astral-sh/uv:0.8",
        "ghcr.io/astral-sh/uv:${OTHER}",
    ),
)
def test_floating_refs_are_flagged(tmp_path: Path, ref: str) -> None:
    direct = f"FROM node:20\nCOPY --from={ref} /uv /usr/local/bin/uv\n"
    via_stage = f"FROM {ref} AS uv-bin\nFROM node:20\n{PINNED_COPY}\n"
    for text in (direct, via_stage):
        assert run(write(tmp_path, text)).returncode == 1, text


@pytest.mark.parametrize(
    "ref",
    (
        "ghcr.io/astral-sh/uv:${UV_VERSION}",
        "ghcr.io/astral-sh/uv:$UV_VERSION",
        "ghcr.io/astral-sh/uv:0.8.22",
        "ghcr.io/astral-sh/uv@sha256:" + "0" * 64,
    ),
)
def test_pinned_refs_are_not_flagged(tmp_path: Path, ref: str) -> None:
    direct = f"FROM node:20\nCOPY --from={ref} /uv /usr/local/bin/uv\n"
    via_stage = f"FROM {ref} AS uv-bin\nFROM node:20\n{PINNED_COPY}\n"
    for text in (direct, via_stage):
        out = run(write(tmp_path, text))
        assert (out.returncode, out.stdout) == (0, ""), text


def test_other_copies_are_ignored(tmp_path: Path) -> None:
    text = (
        "FROM golang:1.24 AS go\nFROM node:20\n"
        "COPY --from=go /usr/local/go /usr/local/go\n"
        "COPY --from=ghcr.io/astral-sh/uvx:latest /uvx /usr/local/bin/uvx\n"
        "COPY init-firewall.sh /usr/local/bin/\n"
    )
    assert run(write(tmp_path, text)).returncode == 0


def test_unreadable_input_is_a_usage_error(tmp_path: Path) -> None:
    assert run(tmp_path / "missing").returncode == 2


def test_both_detectors_fire_on_a_pre_242_file(tmp_path: Path) -> None:
    # The two U2 conditions are independent: a pre-242 docs project trips both,
    # which is why SKILL.md joins the statuses.
    path = write(tmp_path, assemble(OLD_STAGE["docs"], OLD_INSTALL["docs"]))
    assert run(path).returncode == 1
    assert run_stale("check", path).returncode == 1


def test_detector_runs_under_mawk(tmp_path: Path) -> None:
    mawk = shutil.which("mawk")
    if mawk is None:
        pytest.skip("mawk not installed")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "awk").symlink_to(mawk)
    env = {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"}
    assert run(write(tmp_path, pre_251(current("node"))), env).returncode == 1
    assert run(write(tmp_path, current("node")), env).returncode == 0


def _section(start: str, end: str) -> str:
    text = SKILL_MD.read_text("utf-8")
    body = text[text.index("## Upgrade Mode") :]
    return body[body.index(start) : body.index(end)]


def test_u2_derives_the_status_from_the_dockerfile() -> None:
    u2 = _section("### U2:", "### U3:")
    assert "floating-uv-copy.sh check .devcontainer/Dockerfile" in u2
    assert "skipped (assembled; floating uv copy)" in u2
    assert "skipped (assembled; floating uv copy; stale runtime copy)" in u2


def test_u3_treats_the_status_as_pending_work() -> None:
    u3 = _section("### U3:", "### U4:")
    shortcut = next(
        line for line in u3.splitlines() if line.startswith("If all files are")
    )
    assert "floating uv copy" in shortcut
    assert "stale runtime copy" in shortcut


def test_u4_offers_off_the_u2_status() -> None:
    u4 = _section("**uv version pin on upgrade", "**Stale language-runtime copy")
    assert (
        "U2's status for `.devcontainer/Dockerfile` includes `floating uv copy`" in u4
    )
    assert "whenever U4 adds or changes `UV_VERSION`" not in u4
    assert "skipped (assembled; floating uv copy, user declined)" in u4
    assert "next upgrade run offers the patch again" in u4


def test_u5_lists_the_labels() -> None:
    text = SKILL_MD.read_text("utf-8")
    u5 = text[text.index("### U5:") :]
    for label in (
        "skipped (assembled; uv pin patched)",
        "skipped (assembled; floating uv copy, user declined)",
        "skipped (assembled; floating uv copy, needs devcontainer.json)",
    ):
        assert label in u5


def test_template_dir_is_the_one_the_script_reads() -> None:
    # Guards the fixture: current() must assemble from the shipped fragments.
    assert (TEMPLATE_DIR / "Dockerfile.base").read_text("utf-8").count(
        PINNED_STAGE
    ) == 1
