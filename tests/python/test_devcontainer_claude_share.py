"""The shared-.claude scheme in devcontainer.json (TASK-239, TASK-244).

The template used to mount a named volume over /workspace/.claude and fill it
once, in postCreateCommand, from a read-only bind of the host's project
.claude. Because postCreateCommand runs only at container creation, every later
run worked against a stale copy: host edits never reached the container, and
container commits carried the stale copy back into git, silently reverting
.claude/skills/** files after autonomous runs.

The fix shares the directory (it already arrives via workspaceMount) and
overrides exactly one file — .claude/settings.local.json — because bwrap cannot
create mount namespaces on Docker Desktop macOS, so the sandbox has to be off
in the container while the host keeps it on. Two lifecycle hooks go with it: an
initializeCommand that seeds the host file so Docker cannot leave a 0-byte
unparsable one in its place, and a postCreateCommand that grants git
safe.directory on /workspace (which presents as root-owned to the node user, so
git would otherwise refuse the repo with "detected dubious ownership").

All of this is config, not code: nothing else in the suite would notice if the
volume came back, the override widened into a permission allowlist, or either
hook were dropped. These tests pin it on the live file AND on the ralph-init
template that scaffolds it into new projects.

The .venv volume overlay is covered by test_devcontainer_venv_overlay.py.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from devcontainer_config import (
    LIVE_DIR,
    TEMPLATE,
    TEMPLATE_DIR,
    each_copy,
    load_jsonc,
    loads_jsonc,
    mounts_matching,
    target_pattern,
)

SETTINGS_NAME = "container-settings.local.json"
LIVE_SETTINGS = LIVE_DIR / SETTINGS_NAME
TEMPLATE_SETTINGS = TEMPLATE_DIR / SETTINGS_NAME
each_settings = pytest.mark.parametrize(
    "settings", (LIVE_SETTINGS, TEMPLATE_SETTINGS), ids=("live", "template")
)


def settings_mount(config: dict[str, Any]) -> str | None:
    """The mount targeting /workspace/.claude/settings.local.json, or None."""
    target = target_pattern("/workspace/.claude/settings.local.json")
    found = mounts_matching(config, target)
    return found[0] if found else None


def claude_dir_mounts(config: dict[str, Any]) -> list[str]:
    """Mounts over the /workspace/.claude directory itself — the defect."""
    return mounts_matching(config, target_pattern("/workspace/.claude"))


def key_paths(value: Any, prefix: tuple[str, ...] = ()) -> Iterator[str]:
    """Every object key path in a JSON value, dot-joined (like jq ``paths``)."""
    if isinstance(value, dict):
        for key, item in value.items():
            here = (*prefix, str(key))
            yield ".".join(here)
            yield from key_paths(item, here)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            here = (*prefix, str(index))
            yield ".".join(here)
            yield from key_paths(item, here)


def run_seed(cmd: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run initializeCommand the way Docker does: /bin/sh -c at the root."""
    return subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True, check=False
    )


@each_copy
def test_no_mount_targets_the_claude_directory_itself(path: Path) -> None:
    # A whole-directory mount is the defect: it hides host edits from the
    # container and lets container commits revert .claude files.
    offenders = claude_dir_mounts(load_jsonc(path))
    assert not offenders, f"{path} still mounts over .claude: {offenders}"


@each_copy
def test_no_read_only_bind_of_host_project_claude_remains(path: Path) -> None:
    # /workspace-host-claude was the staging bind the copy read from; with the
    # copy gone it has no purpose, and leaving it invites the copy back.
    text = path.read_text(encoding="utf-8")
    assert "workspace-host-claude" not in text
    assert "claude-code-project-config" not in text


@each_copy
def test_one_mount_binds_container_settings_over_settings_local(
    path: Path,
) -> None:
    mount = settings_mount(load_jsonc(path))
    assert mount is not None
    assert "type=bind" in mount
    assert "type=volume" not in mount
    # Sourced from the repo so it is reviewable and travels with a clone.
    assert f"${{localWorkspaceFolder}}/.devcontainer/{SETTINGS_NAME}" in mount


@each_copy
def test_exactly_one_mount_targets_anything_under_workspace_claude(
    path: Path,
) -> None:
    assert len(mounts_matching(load_jsonc(path), r"target=/workspace/\.claude")) == 1


def test_container_settings_file_ships_in_both_trees() -> None:
    for settings in (LIVE_SETTINGS, TEMPLATE_SETTINGS):
        assert settings.is_file()
        json.loads(settings.read_text(encoding="utf-8"))
    assert LIVE_SETTINGS.read_bytes() == TEMPLATE_SETTINGS.read_bytes()


@each_settings
def test_container_settings_carry_only_the_sandbox_switch(settings: Path) -> None:
    # Ralph runs claude with --dangerously-skip-permissions in the container,
    # so an allowlist here would be dead weight that drifts from the host's.
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert sorted(key_paths(data)) == ["sandbox", "sandbox.enabled"], (
        f"{settings} is not just the sandbox switch"
    )
    assert data["sandbox"]["enabled"] is False


@each_copy
def test_initialize_command_seeds_host_settings_when_missing_or_empty(
    path: Path,
) -> None:
    cmd = load_jsonc(path).get("initializeCommand")
    assert cmd is not None
    assert ".claude/settings.local.json" in cmd
    # [ -s ] is what makes it idempotent and leaves a real host file alone;
    # [ -f ] would leave a 0-byte file in place, which is the failure mode.
    assert "-s " in cmd
    # The directory must exist before the redirect: on a fresh clone with no
    # .claude, the redirect fails, sh exits non-zero, and the devcontainer CLI
    # aborts container creation.
    assert "mkdir -p .claude" in cmd


def test_seeding_command_is_idempotent_and_repairs_empty_file(
    tmp_path: Path,
) -> None:
    cmd = load_jsonc(TEMPLATE)["initializeCommand"]
    (tmp_path / ".claude").mkdir()
    target = tmp_path / ".claude" / "settings.local.json"

    # missing -> created and parseable
    assert run_seed(cmd, tmp_path).returncode == 0
    json.loads(target.read_text(encoding="utf-8"))

    # empty -> repaired
    target.write_text("", encoding="utf-8")
    assert run_seed(cmd, tmp_path).returncode == 0
    json.loads(target.read_text(encoding="utf-8"))

    # real file -> untouched
    target.write_text('{"sandbox":{"enabled":true}}\n', encoding="utf-8")
    assert run_seed(cmd, tmp_path).returncode == 0
    assert json.loads(target.read_text(encoding="utf-8"))["sandbox"]["enabled"]


@each_copy
def test_seeding_command_succeeds_without_a_claude_directory(
    path: Path, tmp_path: Path
) -> None:
    # A fresh clone may lack .claude entirely (gitignored or never committed).
    result = run_seed(load_jsonc(path)["initializeCommand"], tmp_path)
    assert result.returncode == 0, result.stderr
    seeded = tmp_path / ".claude" / "settings.local.json"
    assert seeded.read_text(encoding="utf-8").strip() == "{}"


@each_copy
def test_post_create_grants_git_safe_directory(path: Path) -> None:
    pcc = load_jsonc(path)["postCreateCommand"]
    # Without this the node user gets "detected dubious ownership" and Ralph
    # has no git at all — no status, no commit.
    assert "safe.directory" in pcc
    assert "/workspace" in pcc
    assert "--global" in pcc


@each_copy
def test_post_create_no_longer_copies_the_claude_directory(path: Path) -> None:
    pcc = load_jsonc(path)["postCreateCommand"]
    assert "workspace-host-claude" not in pcc
    assert "cp -a" not in pcc
    # The old command patched sandbox.enabled with jq in place; the bind does
    # that declaratively now.
    assert "sandbox.enabled" not in pcc


@each_copy
def test_project_claude_still_arrives_through_workspace_bind(path: Path) -> None:
    ws = load_jsonc(path)["workspaceMount"]
    # Sharing the directory only works because the whole project folder is
    # bind-mounted; if that ever changes, this scheme needs revisiting rather
    # than passing by accident.
    assert "type=bind" in ws
    assert "source=${localWorkspaceFolder}" in ws
    assert "target=/workspace" in ws


@each_copy
def test_detectors_fire_on_a_mutated_copy(path: Path, tmp_path: Path) -> None:
    # Mutation check: put the old whole-directory volume back and strip the
    # mkdir from the seeding command, then assert both defects are caught.
    text = path.read_text(encoding="utf-8")
    old_volume = (
        '"source=claude-code-project-config-${devcontainerId},'
        'target=/workspace/.claude,type=volume",\n'
    )
    anchor = '    "source=${localWorkspaceFolder}/.devcontainer/'
    pre = text.replace(anchor, f"    {old_volume}{anchor}", 1)
    pre = pre.replace("mkdir -p .claude && ", "", 1)
    assert pre != text, "mutation did not land"

    config = loads_jsonc(pre)
    assert claude_dir_mounts(config)
    assert len(mounts_matching(config, r"target=/workspace/\.claude")) == 2
    # The un-mkdir'd seed aborts on a clone with no .claude, as Docker would.
    assert run_seed(config["initializeCommand"], tmp_path).returncode != 0

    # The real file is not in that state.
    assert not claude_dir_mounts(load_jsonc(path))
