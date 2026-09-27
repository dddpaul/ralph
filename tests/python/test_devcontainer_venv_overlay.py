"""The .venv container-volume overlay in devcontainer.json (TASK-235, TASK-239).

``workspaceMount`` bind-mounts the host project folder at /workspace, so a
container-side ``uv sync`` writes .venv/pyvenv.cfg with a container-only
interpreter home onto the host, leaving .venv/bin/python3 a broken symlink
there. A named volume mounted over /workspace/.venv keeps the two apart.

The overlay is config, not code — nothing else in the suite would notice if the
mount were dropped, reworded into a bind, or left root-owned. These tests pin
the three properties that make it work, on the live file AND on the ralph-init
template that scaffolds it into new projects.

This is the only remaining volume overlay under /workspace; the .claude
directory is a plain shared bind, covered by test_devcontainer_claude_share.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from devcontainer_config import (
    LIVE,
    TEMPLATE,
    each_copy,
    load_jsonc,
    loads_jsonc,
    mounts_matching,
    target_pattern,
)


def venv_mount(config: dict[str, Any]) -> str | None:
    """The mount string for /workspace/.venv, or None when there is none."""
    found = mounts_matching(config, target_pattern("/workspace/.venv"))
    return found[0] if found else None


@each_copy
def test_devcontainer_json_is_valid_jsonc(path: Path) -> None:
    assert isinstance(load_jsonc(path), dict)


@each_copy
def test_a_mount_targets_workspace_venv(path: Path) -> None:
    assert venv_mount(load_jsonc(path))


@each_copy
def test_venv_overlay_is_a_volume_not_a_host_bind(path: Path) -> None:
    mount = venv_mount(load_jsonc(path))
    assert mount is not None
    # type=volume is what keeps the container venv off the host filesystem;
    # a bind here would reintroduce the exact bug this overlay fixes.
    assert "type=volume" in mount
    assert "type=bind" not in mount
    assert "${localWorkspaceFolder}" not in mount
    assert "${localEnv:" not in mount


@each_copy
def test_venv_volume_is_scoped_per_devcontainer(path: Path) -> None:
    mount = venv_mount(load_jsonc(path))
    assert mount is not None
    # Without ${devcontainerId} the volume would be shared by every project
    # on the machine, so one repo's virtualenv would land in another's.
    assert "${devcontainerId}" in mount


@each_copy
def test_post_create_chowns_venv_to_remote_user(path: Path) -> None:
    pcc = load_jsonc(path)["postCreateCommand"]
    # Docker mounts a fresh named volume root-owned; without the chown, uv
    # runs as node and cannot write the environment.
    assert "chown node:node" in pcc
    assert "/workspace/.venv" in pcc


@each_copy
def test_chown_runs_before_anything_else_in_post_create(path: Path) -> None:
    pcc = load_jsonc(path)["postCreateCommand"]
    head = pcc.split("&&", 1)[0]
    assert "/workspace/.venv" in head


@each_copy
def test_workspace_is_still_bind_mounted(path: Path) -> None:
    ws = load_jsonc(path)["workspaceMount"]
    # If this ever stops being a bind of the host folder, the overlay's
    # rationale changes and these tests should be revisited rather than kept
    # passing by accident.
    assert "type=bind" in ws
    assert "target=/workspace" in ws


def test_live_and_template_stay_byte_identical() -> None:
    # R11 parity is also asserted in template-parity.bats; repeated here so a
    # failure of these overlay tests points at the right file straight away.
    assert LIVE.read_bytes() == TEMPLATE.read_bytes()


@each_copy
def test_detectors_fire_on_a_mutated_copy(path: Path) -> None:
    # Mutation check: turn the overlay back into a host bind, then drop it
    # altogether, and assert the detectors notice each defect state.
    text = path.read_text(encoding="utf-8")
    volume = "source=claude-code-project-venv-${devcontainerId},"
    bind = "source=${localWorkspaceFolder}/.venv,"
    as_bind = text.replace(volume, bind).replace(
        "target=/workspace/.venv,type=volume", "target=/workspace/.venv,type=bind"
    )
    assert as_bind != text, "mutation did not land"
    mount = venv_mount(loads_jsonc(as_bind))
    assert mount is not None
    assert "type=volume" not in mount
    assert "${localWorkspaceFolder}" in mount

    dropped = "\n".join(
        line for line in text.splitlines() if "target=/workspace/.venv" not in line
    )
    # The mount was the last array element; the one before it now is and must
    # lose its trailing comma for the copy to stay valid JSON.
    dropped = dropped.replace(
        'settings.local.json,type=bind",', 'settings.local.json,type=bind"'
    )
    assert venv_mount(loads_jsonc(dropped)) is None
    assert venv_mount(load_jsonc(path)) is not None
