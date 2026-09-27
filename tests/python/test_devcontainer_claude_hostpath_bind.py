"""The second bind of the host ~/.claude at its own host path (TASK-240).

Claude Code resolves a plugin through an absolute path recorded in a registry:
plugins/known_marketplaces.json stores installLocation and installed_plugins.
json stores installPath, both as *host* paths (e.g. /Users/<user>/.claude/
plugins/marketplaces/<name>). The template already binds the host ~/.claude at
/home/node/.claude, which is the same directory under a different name — and a
different name is exactly what the registry cannot follow. Every user plugin
then dies with "Marketplace <name> failed to load: cache-miss", the
task-reviewer agent shipped by ralph@dddpaul-ralph never registers, and the
Review step of the Task Lifecycle degrades to a plain agent reading a rules
file while still reporting APPROVED. Binding the same directory a second time
at target=${localEnv:HOME}/.claude makes the recorded path resolve.

Nothing else in the suite would notice if the mount were dropped as an apparent
duplicate of the /home/node/.claude bind, reworded into a volume, or retargeted
— the failure is silent by construction. These tests pin it on the live file
AND on the ralph-init template, and the last test mutation-checks them by
deriving the pre-fix copy of each file and asserting the detector goes quiet.

The shared project .claude is covered by test_devcontainer_claude_share.py; the
.venv overlay by test_devcontainer_venv_overlay.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from devcontainer_config import (
    LIVE,
    TEMPLATE,
    comment_text,
    each_copy,
    load_jsonc,
    loads_jsonc,
    mounts_matching,
    source_pattern,
    target_pattern,
)

HOST_CLAUDE = "${localEnv:HOME}/.claude"


def hostpath_mount(config: dict[str, Any]) -> str | None:
    """The mount targeting the literal host ~/.claude path, or None.

    This is the detector the mutation test drives to None.
    """
    found = mounts_matching(config, target_pattern(HOST_CLAUDE))
    return found[0] if found else None


def home_node_mount(config: dict[str, Any]) -> str | None:
    """The mount targeting /home/node/.claude, or None."""
    found = mounts_matching(config, target_pattern("/home/node/.claude"))
    return found[0] if found else None


@each_copy
def test_devcontainer_json_is_valid_jsonc(path: Path) -> None:
    assert isinstance(load_jsonc(path), dict)


@each_copy
def test_a_mount_targets_the_host_claude_path(path: Path) -> None:
    assert hostpath_mount(load_jsonc(path)), (
        f"{path} has no bind at the literal host ~/.claude path; every user "
        "plugin will fail to load with cache-miss"
    )


@each_copy
def test_host_path_mount_binds_host_claude_to_itself(path: Path) -> None:
    mount = hostpath_mount(load_jsonc(path))
    assert mount is not None
    # Source and target must be the same host path: the whole point is that the
    # absolute path the registry recorded resolves to the same bytes inside.
    assert f"source={HOST_CLAUDE}" in mount
    assert f"target={HOST_CLAUDE}" in mount
    assert "type=bind" in mount
    # A volume would mount an empty directory over the path — the registry
    # would resolve it and then find no marketplace there.
    assert "type=volume" not in mount


@each_copy
def test_home_node_claude_bind_is_still_there(path: Path) -> None:
    # $HOME inside the container is /home/node, so this bind is what makes a
    # bare ~/.claude (used by any tool that ignores CLAUDE_CONFIG_DIR) land on
    # the same shared directory as the config root.
    mount = home_node_mount(load_jsonc(path))
    assert mount is not None
    assert f"source={HOST_CLAUDE}" in mount
    assert "type=bind" in mount


@each_copy
def test_config_dir_points_at_the_path_this_mount_provides(path: Path) -> None:
    # TASK-241 repointed the config root here. The mount above is what makes
    # that path exist inside the container, so the two must not drift apart:
    # drop the mount and Claude Code starts against a config root that is an
    # empty auto-created directory. The write-direction argument is in
    # test_devcontainer_claude_config_root.py.
    assert load_jsonc(path)["containerEnv"]["CLAUDE_CONFIG_DIR"] == HOST_CLAUDE


@each_copy
def test_exactly_two_mounts_bind_the_host_claude_directory(path: Path) -> None:
    # One for CLAUDE_CONFIG_DIR, one for registry path resolution. A third
    # would mean someone added an alias instead of fixing the registry.
    assert len(mounts_matching(load_jsonc(path), source_pattern(HOST_CLAUDE))) == 2


@each_copy
def test_host_path_mount_comment_names_cache_miss(path: Path) -> None:
    # Without the rationale in the file, the next reader sees two binds of the
    # same source and prunes one as a copy-paste slip.
    comments = comment_text(path.read_text(encoding="utf-8")).lower()
    assert "cache-miss" in comments, f"{path} has no comment naming cache-miss"
    assert "not a duplicate" in comments, (
        f"{path} has no comment warning the mount is not a duplicate"
    )


def test_live_and_template_stay_byte_identical() -> None:
    # R11 parity is also asserted in template-parity.bats; repeated here so a
    # failure of these tests points at the right file straight away.
    assert LIVE.read_bytes() == TEMPLATE.read_bytes()


@each_copy
def test_mount_assertion_fails_on_pre_fix_copy(path: Path) -> None:
    # Mutation check: without it, a detector with a typo'd regex would pass on
    # both files forever and the suite would prove nothing. Derive the pre-fix
    # version by deleting the mount line and its comment markers from a copy,
    # then assert the detector goes quiet on it — an over-broad regex such as
    # target=.*\.claude would still match there and is caught only here.
    text = path.read_text(encoding="utf-8")
    pre = "\n".join(
        line
        for line in text.splitlines()
        if f"target={HOST_CLAUDE}" not in line
        and "cache-miss" not in line
        and "NOT a duplicate" not in line
    )
    assert pre != text, "mutation did not land"

    # The pre-fix copy is still valid JSONC — so a green suite could not have
    # been explained away as "the old file was broken anyway".
    pre_config = loads_jsonc(pre)

    # The detector finds nothing: this is the defect state.
    assert hostpath_mount(pre_config) is None, (
        "mutation check is vacuous: the detector still matches after the "
        f"host-path mount was removed from {path}"
    )

    # And the /home/node/.claude bind survived the mutation, proving the two
    # binds are distinguishable and only the new one was removed.
    assert home_node_mount(pre_config) is not None

    # The real file is not in that state.
    assert hostpath_mount(load_jsonc(path)) is not None
