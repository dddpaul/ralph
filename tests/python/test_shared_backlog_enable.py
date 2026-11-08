"""The shared-backlog project shim and the clone switch's enable and disable (TASK-310).

``shared-backlog.sh enable`` needs ``"sharedBacklog": true`` in
``.claude/ralph.json``, saves the host's default holder as
``ralph.holder`` (asked once), installs the plugin shim as pre-push and sets
``ralph.sharedBacklog true``. ``disable`` clears the switch; neither the clone
migration nor a commit that drops the marker changes it afterwards. The project
shim ``templates/shims/shared-backlog.sh`` resolves the plugin through the
registry and execs its script.
"""

from __future__ import annotations

import hashlib
import json
import os
import pty
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT

PLUGIN = REPO_ROOT / "plugins/ralph"
SCRIPT = PLUGIN / "scripts/shared-backlog.sh"
SHIMS = PLUGIN / "skills/ralph-init/templates/shims"
HOOK_SHIM = SHIMS / "git-hook"
PROJECT_SHIM = SHIMS / "shared-backlog.sh"
MIGRATE = PLUGIN / "skills/ralph-init/scripts/migrate-plugin-hooks.sh"
BASH = shutil.which("bash") or "/bin/bash"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None, reason="jq is not installed"
)


def git(cwd: Path, *args: str, check: bool = True) -> str:
    """Run git in ``cwd`` and return its stripped stdout."""
    return subprocess.run(
        ["git", *args], cwd=cwd, check=check, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    """An environment isolated from the host's git config, holder and plugin registry."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    out = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("GIT_", "SHARED_BACKLOG_", "CLAUDE_"))
        and k
        not in ("RALPH_RUN_LOCK_TOKEN", "RALPH_MIGRATE_STOP_AFTER", "DEVCONTAINER")
    }
    out.update(
        HOME=str(home), GIT_CONFIG_NOSYSTEM="1", CLAUDE_CONFIG_DIR=str(home / ".claude")
    )
    for key, value in (("user.name", "tester"), ("user.email", "t@example.invalid")):
        subprocess.run(["git", "config", "--global", key, value], env=out, check=True)
    return out


@pytest.fixture
def repo(tmp_path: Path, env: dict[str, str]) -> Path:
    """A clone whose marker opts in to the shared backlog."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "master"], cwd=root, env=env, check=True)
    (root / ".claude").mkdir()
    (root / ".claude/ralph.json").write_text(
        '{"pluginHooks": true, "sharedBacklog": true}\n'
    )
    return root.resolve()


def run(
    repo: Path,
    env: dict[str, str],
    *args: str,
    script: Path = SCRIPT,
    **kw: object,
) -> subprocess.CompletedProcess[str]:
    """Run ``script`` in ``repo``."""
    kw.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.run(
        [BASH, str(script), *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        **kw,
    )  # type: ignore[call-overload]


def config(repo: Path, key: str) -> str:
    return git(repo, "config", "--get", key, check=False)


def pre_push(repo: Path) -> Path:
    return repo / ".git/hooks/pre-push"


# --------------------------------------------------------------------------
# Release and opt-in
# --------------------------------------------------------------------------


def test_the_shipped_script_has_no_release_gate() -> None:
    text = SCRIPT.read_text()
    assert "RELEASED" not in text
    assert "not released yet" not in text


@pytest.mark.parametrize(
    "marker", [None, "{}", '{"sharedBacklog": false}', '{"sharedBacklog": "true"}']
)
def test_enable_requires_shared_backlog_true_in_the_marker(
    repo: Path, env: dict[str, str], marker: str | None
) -> None:
    path = repo / ".claude/ralph.json"
    if marker is None:
        path.unlink()
    else:
        path.write_text(marker)
    result = run(repo, env, "enable", "--holder", "@host-a")
    assert result.returncode == 1
    assert "not opted in" in result.stderr
    assert config(repo, "ralph.sharedBacklog") == ""
    assert config(repo, "ralph.holder") == ""
    assert not pre_push(repo).exists()


# --------------------------------------------------------------------------
# enable
# --------------------------------------------------------------------------


def test_enable_sets_the_switch_installs_the_pre_push_shim_and_saves_the_holder(
    repo: Path, env: dict[str, str]
) -> None:
    result = run(repo, env, "enable", "--holder", "host-a")
    assert result.returncode == 0, result.stderr
    assert config(repo, "ralph.sharedBacklog") == "true"
    assert config(repo, "ralph.holder") == "@host-a"
    assert pre_push(repo).read_bytes() == HOOK_SHIM.read_bytes()
    assert os.access(pre_push(repo), os.X_OK)
    assert git(repo, "status", "--porcelain") == "?? .claude/"


def test_enable_twice_changes_nothing(repo: Path, env: dict[str, str]) -> None:
    assert run(repo, env, "enable", "--holder", "@host-a").returncode == 0
    result = run(repo, env, "enable")
    assert result.returncode == 0, result.stderr
    assert (
        "installed" not in result.stdout
        and "set git config ralph.holder" not in result.stdout
    )
    assert not (repo / ".git/hooks/pre-push.local").exists()


def test_enable_keeps_an_existing_holder_without_asking(
    repo: Path, env: dict[str, str]
) -> None:
    git(repo, "config", "ralph.holder", "@host-b")
    result = run(repo, env, "enable")
    assert result.returncode == 0, result.stderr
    assert config(repo, "ralph.holder") == "@host-b"
    assert "Default holder" not in result.stderr


def test_enable_without_a_holder_and_no_terminal_refuses_and_writes_nothing(
    repo: Path, env: dict[str, str]
) -> None:
    result = run(repo, env, "enable")
    assert result.returncode == 1
    assert "no holder" in result.stderr
    assert config(repo, "ralph.sharedBacklog") == ""
    assert not pre_push(repo).exists()


@pytest.mark.parametrize("holder", ["@claude", "claude", "@a b"])
def test_enable_refuses_a_holder_that_names_no_host(
    repo: Path, env: dict[str, str], holder: str
) -> None:
    result = run(repo, env, "enable", "--holder", holder)
    assert result.returncode == 1
    assert config(repo, "ralph.sharedBacklog") == ""


def test_enable_asks_once_for_the_holder_on_a_terminal(
    repo: Path, env: dict[str, str]
) -> None:
    master, slave = pty.openpty()
    try:
        os.write(master, b"host-c\n")
        result = run(repo, env, "enable", stdin=slave)
    finally:
        os.close(slave)
        os.close(master)
    assert result.returncode == 0, result.stderr
    assert "Default holder for this host" in result.stderr
    assert config(repo, "ralph.holder") == "@host-c"
    again = run(repo, env, "enable")
    assert again.returncode == 0 and "Default holder" not in again.stderr


def test_enable_keeps_an_existing_pre_push_as_pre_push_local(
    repo: Path, env: dict[str, str]
) -> None:
    own = b"#!/bin/sh\necho own pre-push\n"
    pre_push(repo).write_bytes(own)
    result = run(repo, env, "enable", "--holder", "@host-a")
    assert result.returncode == 0, result.stderr
    assert (repo / ".git/hooks/pre-push.local").read_bytes() == own
    assert pre_push(repo).read_bytes() == HOOK_SHIM.read_bytes()


def test_enable_refuses_when_pre_push_local_differs_and_writes_nothing(
    repo: Path, env: dict[str, str]
) -> None:
    pre_push(repo).write_bytes(b"#!/bin/sh\necho one\n")
    (repo / ".git/hooks/pre-push.local").write_bytes(b"#!/bin/sh\necho two\n")
    result = run(repo, env, "enable", "--holder", "@host-a")
    assert result.returncode == 1
    assert "pre-push.local already exists" in result.stderr
    assert pre_push(repo).read_bytes() == b"#!/bin/sh\necho one\n"
    assert (
        config(repo, "ralph.holder") == "" and config(repo, "ralph.sharedBacklog") == ""
    )


def plugin_with_old_shim(tmp_path: Path) -> tuple[Path, bytes]:
    """A copy of the plugin whose hash list also lists a fabricated earlier shim; return it and that shim."""
    plugin = tmp_path / "plugin"
    shutil.copytree(PLUGIN, plugin, ignore=shutil.ignore_patterns("__pycache__"))
    old = HOOK_SHIM.read_bytes() + b"# an earlier shim version\n"
    with (plugin / "skills/ralph-init/scripts/shipped-git-hooks.sha256").open("a") as f:
        f.write(f"shim {hashlib.sha256(old).hexdigest()}\n")
    return plugin, old


def test_enable_replaces_an_earlier_pre_push_shim_in_place(
    tmp_path: Path, repo: Path, env: dict[str, str]
) -> None:
    plugin, old = plugin_with_old_shim(tmp_path)
    pre_push(repo).write_bytes(old)
    result = run(
        repo, env, "enable", "--holder", "@host-a", script=plugin / "scripts/shared-backlog.sh"
    )
    assert result.returncode == 0, result.stderr
    assert pre_push(repo).read_bytes() == HOOK_SHIM.read_bytes()
    assert not (repo / ".git/hooks/pre-push.local").exists()
    assert "pre-push.local" not in result.stdout


def test_enable_replaces_the_real_pre_dispatcher_shim(repo: Path, env: dict[str, str]) -> None:
    pre_push(repo).write_bytes(
        (REPO_ROOT / "tests/python/fixtures/shipped-git-hooks/git-hook-shim.v0.25.10").read_bytes()
    )
    result = run(repo, env, "enable", "--holder", "@host-a")
    assert result.returncode == 0, result.stderr
    assert pre_push(repo).read_bytes() == HOOK_SHIM.read_bytes()
    assert not (repo / ".git/hooks/pre-push.local").exists()


def test_enable_replaces_an_earlier_shim_and_keeps_its_pre_push_local(
    tmp_path: Path, repo: Path, env: dict[str, str]
) -> None:
    plugin, old = plugin_with_old_shim(tmp_path)
    own = b"#!/bin/sh\necho own pre-push\n"
    pre_push(repo).write_bytes(old)
    (repo / ".git/hooks/pre-push.local").write_bytes(own)
    result = run(
        repo, env, "enable", "--holder", "@host-a", script=plugin / "scripts/shared-backlog.sh"
    )
    assert result.returncode == 0, result.stderr
    assert pre_push(repo).read_bytes() == HOOK_SHIM.read_bytes()
    assert (repo / ".git/hooks/pre-push.local").read_bytes() == own


def test_enable_keeps_an_unlisted_shim_like_pre_push_as_pre_push_local(
    repo: Path, env: dict[str, str]
) -> None:
    edited = HOOK_SHIM.read_bytes() + b"# edited\n"
    pre_push(repo).write_bytes(edited)
    result = run(repo, env, "enable", "--holder", "@host-a")
    assert result.returncode == 0, result.stderr
    assert (repo / ".git/hooks/pre-push.local").read_bytes() == edited
    assert pre_push(repo).read_bytes() == HOOK_SHIM.read_bytes()


# --------------------------------------------------------------------------
# disable, the migration and the marker
# --------------------------------------------------------------------------


def test_disable_clears_the_switch_and_the_clone_migration_does_not_turn_it_back_on(
    repo: Path, env: dict[str, str]
) -> None:
    assert run(repo, env, "enable", "--holder", "@host-a").returncode == 0
    result = run(repo, env, "disable")
    assert result.returncode == 0, result.stderr
    assert config(repo, "ralph.sharedBacklog") == ""
    migrated = subprocess.run(
        [BASH, str(MIGRATE), "clone", str(repo)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert migrated.returncode == 0, migrated.stderr
    assert config(repo, "ralph.pluginHooks") == "true"
    assert config(repo, "ralph.sharedBacklog") == ""
    assert "nothing to change" in run(repo, env, "disable").stdout


def test_a_commit_that_removes_the_marker_does_not_change_the_switch(
    repo: Path, env: dict[str, str]
) -> None:
    assert run(repo, env, "enable", "--holder", "@host-a").returncode == 0
    subprocess.run(["git", "add", "-A"], cwd=repo, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-q", "--no-verify", "-m", "marker"],
        cwd=repo,
        env=env,
        check=True,
    )
    subprocess.run(
        ["git", "rm", "-q", ".claude/ralph.json"], cwd=repo, env=env, check=True
    )
    subprocess.run(
        ["git", "commit", "-q", "--no-verify", "-m", "drop marker"],
        cwd=repo,
        env=env,
        check=True,
    )
    assert config(repo, "ralph.sharedBacklog") == "true"
    assert config(repo, "ralph.holder") == "@host-a"


# --------------------------------------------------------------------------
# The project shim
# --------------------------------------------------------------------------


def write_registry(env: dict[str, str], install: Path) -> None:
    reg = Path(env["CLAUDE_CONFIG_DIR"]) / "plugins/installed_plugins.json"
    reg.parent.mkdir(parents=True, exist_ok=True)
    entry = {"scope": "user", "installPath": str(install), "version": "test"}
    reg.write_text(
        json.dumps({"version": 2, "plugins": {"ralph@dddpaul-ralph": [entry]}})
    )


def test_project_shim_execs_the_registered_plugin_script(
    repo: Path, env: dict[str, str]
) -> None:
    write_registry(env, PLUGIN)
    (repo / "scripts").mkdir()
    shim = repo / "scripts/shared-backlog.sh"
    shutil.copy2(PROJECT_SHIM, shim)
    helped = run(repo, env, "--help", script=shim)
    assert helped.returncode == 0, helped.stderr
    assert "enable [--holder @who]" in helped.stdout
    enabled = run(repo, env, "enable", "--holder", "@host-a", script=shim)
    assert enabled.returncode == 0, enabled.stderr
    assert config(repo, "ralph.sharedBacklog") == "true"


def test_project_shim_fails_when_the_plugin_cannot_be_resolved(
    repo: Path, env: dict[str, str]
) -> None:
    result = run(repo, env, "--help", script=PROJECT_SHIM)
    assert result.returncode == 1
    assert "plugin lookup" in result.stderr
    assert "cannot be resolved" in result.stderr


# --------------------------------------------------------------------------
# ralph-init Init and Upgrade
# --------------------------------------------------------------------------

SKILL_MD = PLUGIN / "skills/ralph-init/SKILL.md"
SH_FENCE = re.compile(r"^```sh\n(.*?)^```", re.DOTALL | re.MULTILINE)


def skill_section(start: str, end: str) -> str:
    text = SKILL_MD.read_text("utf-8")
    i = text.index(start)
    return text[i : text.index(end, i)]


def test_init_asks_for_the_opt_in_and_upgrade_offers_it() -> None:
    questions = skill_section("## Step 2: Clarifying Questions", "## Step 3:")
    assert "shared-backlog protocol" in questions
    upgrade = skill_section("### U4: Apply Updates", "### U4.5:")
    assert "Shared backlog (opt-in)" in upgrade
    assert "shared-backlog.sh enable" in upgrade
    assert "never enables it unasked" in upgrade


@pytest.mark.parametrize("checks", ["", "uv run pytest"])
def test_init_snippet_writes_the_marker_installs_the_shim_and_enables(
    repo: Path, env: dict[str, str], checks: str
) -> None:
    (snippet,) = SH_FENCE.findall(skill_section("### 3.11 ", "## Step 4:"))
    snippet = snippet.replace("<checks>", checks).replace("<holder>", "@host-a")
    write_registry(env, PLUGIN)
    (repo / ".claude/ralph.json").write_text('{"pluginHooks": true}\n')
    e = dict(env, CLAUDE_PLUGIN_ROOT=str(PLUGIN))
    result = subprocess.run(
        [BASH, "-c", "set -e\n" + snippet],
        cwd=repo,
        env=e,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    marker = json.loads((repo / ".claude/ralph.json").read_text())
    assert marker == {
        "pluginHooks": True,
        "sharedBacklog": True,
        **({"checks": checks} if checks else {}),
    }
    assert (
        repo / "scripts/shared-backlog.sh"
    ).read_bytes() == PROJECT_SHIM.read_bytes()
    assert config(repo, "ralph.sharedBacklog") == "true"
    assert config(repo, "ralph.holder") == "@host-a"
    assert pre_push(repo).read_bytes() == HOOK_SHIM.read_bytes()
