"""The container's Claude config root (TASK-241).

The devcontainer shares ONE Claude config directory between two machines with
different filesystem roots. Claude Code's plugin registries store *absolute*
paths — plugins/known_marketplaces.json stores installLocation and
plugins/installed_plugins.json stores installPath — and it writes whichever
root CLAUDE_CONFIG_DIR names. Rooted at /home/node/.claude a container run
bakes container-only paths into the shared registries; back on the host every
such entry is rejected outright ("Marketplace <name> has a corrupted
installLocation (/home/node/...) — expected a path inside
<config>/plugins/marketplaces"), so the whole plugin ecosystem stops resolving,
not just ralph@dddpaul-ralph. TASK-240's second bind fixes the read direction
only; this is the write direction.

The fix: point CLAUDE_CONFIG_DIR at ${localEnv:HOME}/.claude — the same
directory under its host name, which the second bind already makes present in
the container. Both machines then record and resolve one path shape.

The mount that makes that path exist is pinned by
test_devcontainer_claude_hostpath_bind.py; here we pin the config root itself
plus the registry-shape invariant it exists to protect.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from devcontainer_config import (
    LIVE,
    TEMPLATE,
    comment_text,
    each_copy,
    load_jsonc,
    loads_jsonc,
    mounts_matching,
    target_pattern,
)

HOST_ROOT = "${localEnv:HOME}/.claude"


def config_root(config: dict[str, Any]) -> str | None:
    """CLAUDE_CONFIG_DIR as declared, or None when the key is gone."""
    return config.get("containerEnv", {}).get("CLAUDE_CONFIG_DIR")


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def container_rooted_paths(registry: Any) -> list[str]:
    """Every string in a registry recorded under the container-only root.

    Non-empty means the registry was last written from a container that used
    /home/node/.claude as its config root — the defect this task removes.
    """
    return [s for s in _strings(registry) if s.startswith("/home/node/")]


@each_copy
def test_config_dir_is_the_host_claude_path(path: Path) -> None:
    root = config_root(load_jsonc(path))
    assert root == HOST_ROOT, (
        f"{path} declares CLAUDE_CONFIG_DIR={root}; container runs will write "
        "that root into the shared plugin registries"
    )


@each_copy
def test_config_dir_is_not_under_home_node(path: Path) -> None:
    # Stated separately from the positive assertion: a future rewrite that
    # invents a third root (say a container-local volume) must fail this too,
    # because it would again leave the host unable to read what the container
    # wrote.
    root = config_root(load_jsonc(path))
    assert root is not None
    assert not root.startswith("/home/node/")


@each_copy
def test_config_root_is_backed_by_a_bind(path: Path) -> None:
    # Without the bind at that exact target, Docker/Claude Code would create an
    # empty directory there and the container would start with a blank config.
    assert mounts_matching(load_jsonc(path), target_pattern(HOST_ROOT))


@each_copy
def test_home_node_claude_bind_stays_as_home_alias(path: Path) -> None:
    # $HOME is /home/node in the container, so anything that ignores
    # CLAUDE_CONFIG_DIR and reads ~/.claude must still land on the same bytes.
    config = load_jsonc(path)
    assert mounts_matching(config, target_pattern("/home/node/.claude"))


@each_copy
def test_config_root_comment_names_the_registry_consequence(path: Path) -> None:
    # Otherwise the host-shaped value reads as a pointless indirection of
    # /home/node/.claude and gets "simplified" back.
    comments = comment_text(path.read_text(encoding="utf-8"))
    assert "installlocation" in comments.lower(), (
        f"{path} has no comment naming installLocation"
    )


def test_live_and_template_stay_byte_identical() -> None:
    assert LIVE.read_bytes() == TEMPLATE.read_bytes()


@each_copy
def test_config_root_assertion_fails_on_pre_fix_copy(path: Path) -> None:
    # Mutation check for the devcontainer half: derive the pre-fix file by
    # putting the old container root back, and assert the detector reports it.
    text = path.read_text(encoding="utf-8")
    pre = text.replace(
        f'"CLAUDE_CONFIG_DIR": "{HOST_ROOT}"',
        '"CLAUDE_CONFIG_DIR": "/home/node/.claude"',
    )
    # The mutation actually landed and left valid JSONC behind — a green suite
    # cannot be explained away by a no-op replace or a broken scratch copy.
    root = config_root(loads_jsonc(pre))
    assert root == "/home/node/.claude"

    # ... and the detector calls it out, while the real file passes.
    assert root.startswith("/home/node/")
    real = config_root(load_jsonc(path))
    assert real is not None
    assert not real.startswith("/home/node/")


def test_registry_detector_fires_on_container_rooted_registry() -> None:
    # Mutation check for the registry half, against the shape actually observed
    # on the host on 2026-09-27 (11 of 12 marketplaces relocated in one batch).
    registry = {
        "dddpaul-ralph": {
            "source": {
                "source": "git",
                "url": "https://github.com/dddpaul/ralph.git",
            },
            "installLocation": "/home/node/.claude/plugins/marketplaces/dddpaul-ralph",
        }
    }
    assert container_rooted_paths(registry)

    # And it stays quiet on the host-shaped equivalent, so it is not matching
    # everything in sight.
    repaired = json.loads(json.dumps(registry).replace("/home/node/", "/Users/paul/"))
    assert container_rooted_paths(repaired) == []


def test_shared_plugin_registries_hold_no_container_rooted_path() -> None:
    # The live invariant, checked wherever a real config is reachable — on the
    # host after a devcontainer run, and inside the container itself. Skipped on
    # a machine whose own config root really is under /home/node (a Linux host
    # with user "node"), where those paths are local and correct.
    root = os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
    if root.startswith("/home/node/"):
        pytest.skip(f"local config root is itself under /home/node: {root}")
    plugins = Path(root) / "plugins"
    if not plugins.is_dir():
        pytest.skip(f"no plugin registry at {plugins}")

    for name in ("known_marketplaces.json", "installed_plugins.json"):
        registry = plugins / name
        if not registry.is_file():
            continue
        found = container_rooted_paths(json.loads(registry.read_text("utf-8")))
        assert not found, (
            f"{registry} records container-only paths; the host cannot resolve "
            f"them: {found}"
        )
