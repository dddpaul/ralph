"""The per-clone part of the migration to plugin-delivered hooks (TASK-300).

``migrate-plugin-hooks.sh clone`` checks every git hook before it writes, then
saves ``ralph.jq`` / ``ralph.projectPath`` (and ``ralph.claudeConfigDir`` off
the default), installs the plugin shim as pre-commit, commit-msg and
post-commit in ``git rev-parse --git-path hooks``, sets ``ralph.pluginHooks``
and trims the common allow rules from ``.claude/settings.local.json`` that the
user settings already hold. The tests build a clone the way older ralph-init
versions did (legacy copies of the hook bodies, the legacy
``settings.local.json`` kept as ``fixtures/legacy-settings.local.json``) and
check what it installs, keeps and refuses, that it never commits or sets
``ralph.sharedBacklog``, and that a second run changes nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT

SCRIPT = REPO_ROOT / "plugins/ralph/skills/ralph-init/scripts/migrate-plugin-hooks.sh"
TEMPLATES = REPO_ROOT / "plugins/ralph/skills/ralph-init/templates"
SHIM = TEMPLATES / "shims/git-hook"
FRAGMENT = REPO_ROOT / "plugins/ralph/user-settings.json"
LOCAL_TEMPLATE = REPO_ROOT / "tests/python/fixtures/legacy-settings.local.json"
BODIES = REPO_ROOT / "plugins/ralph/git-hooks"
OLD_HOOKS = REPO_ROOT / "tests/python/fixtures/shipped-git-hooks"
HOOK_NAMES = ("pre-commit", "commit-msg", "post-commit")
STOP_POINTS = ("config", *(f"shim:{n}" for n in HOOK_NAMES), "switch")
BASH = shutil.which("bash") or "/bin/bash"
JQ = shutil.which("jq")

pytestmark = pytest.mark.skipif(JQ is None, reason="jq is not installed")


def git(cwd: Path, *args: str, check: bool = True) -> str:
    """Run git in ``cwd`` and return its stripped stdout."""
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True).stdout.strip()


def make_clone(path: Path) -> Path:
    """A git repo with legacy git hook copies and the legacy settings.local.json; return its canonical root."""
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "master")
    for name in HOOK_NAMES:
        hook = path / ".git/hooks" / name
        shutil.copyfile(BODIES / name, hook)
        hook.chmod(0o755)
    (path / ".claude").mkdir()
    shutil.copyfile(LOCAL_TEMPLATE, path / ".claude/settings.local.json")
    (path / ".claude/ralph.json").write_text('{"pluginHooks": true}\n')
    return path.resolve()


def env_for(home: Path, config_dir: Path | None = None) -> dict[str, str]:
    """An environment with ``home`` as HOME and, when given, ``config_dir`` as CLAUDE_CONFIG_DIR."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("CLAUDE_PLUGIN_ROOT", "RALPH_MIGRATE_STOP_AFTER", "CLAUDE_CONFIG_DIR", "DEVCONTAINER")
        and not k.startswith("GIT_")
    }
    env["HOME"] = str(home)
    if config_dir is not None:
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    return env


def clone(
    root: Path,
    home: Path,
    *,
    config_dir: Path | None = None,
    stop_after: str | None = None,
    cwd: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run ``migrate-plugin-hooks.sh clone <root>``."""
    env = env_for(home, config_dir)
    if stop_after:
        env["RALPH_MIGRATE_STOP_AFTER"] = stop_after
    env.update(extra_env or {})
    return subprocess.run(
        [BASH, str(SCRIPT), "clone", str(root)],
        cwd=cwd or root.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def write_user_settings(config_dir: Path, allow: list[str], **extra: object) -> Path:
    """Write ``<config_dir>/settings.json`` holding ``allow`` and ``extra`` keys."""
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "settings.json"
    path.write_text(json.dumps({"permissions": {"allow": allow}, **extra}, indent=2) + "\n")
    return path


def snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    """Every file under ``root``, ``.git`` included, with its bytes and mode."""
    return {
        str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mode) for p in sorted(root.rglob("*")) if p.is_file()
    }


def ralph_config(root: Path) -> dict[str, str]:
    """The clone's ``ralph.*`` git config, keys lower-cased as git prints them."""
    out = git(root, "config", "--get-regexp", r"^ralph\.", check=False)
    return dict(line.split(" ", 1) for line in out.splitlines())


def accept(root: Path, name: str) -> None:
    """Append the accept-file line managed-file-drift.sh prints for ``.git/hooks/<name>``."""
    template = hashlib.sha256((BODIES / name).read_bytes()).hexdigest()
    project = hashlib.sha256((root / ".git/hooks" / name).read_bytes()).hexdigest()
    with (root / ".claude/managed-file-drift.accept").open("a") as f:
        f.write(f".git/hooks/{name} template={template} project={project}\n")


@pytest.fixture
def home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    return home


# --------------------------------------------------------------------------
# Shims, switches and no commit
# --------------------------------------------------------------------------


def test_installs_the_shim_sets_the_switches_and_commits_nothing(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    result = clone(root, home)
    assert result.returncode == 0, result.stderr
    for name in HOOK_NAMES:
        hook = root / ".git/hooks" / name
        assert hook.read_bytes() == SHIM.read_bytes()
        assert os.access(hook, os.X_OK)
        assert not (root / f".git/hooks/{name}.local").exists()
    config = ralph_config(root)
    assert config["ralph.pluginhooks"] == "true"
    assert config["ralph.jq"] == JQ
    assert config["ralph.projectpath"] == str(root)
    assert "ralph.claudeconfigdir" not in config
    assert "ralph.sharedbacklog" not in config
    assert git(root, "rev-list", "--all") == ""
    assert "best effort" in result.stdout
    assert "nothing was committed" in result.stdout


def test_second_run_changes_nothing(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    write_user_settings(home / ".claude", ["Bash(git add:*)"])
    assert clone(root, home).returncode == 0
    before = snapshot(root)
    second = clone(root, home)
    assert second.returncode == 0, second.stderr
    assert snapshot(root) == before
    assert "clone: nothing to change" in second.stdout


def test_never_sets_shared_backlog_even_when_the_marker_declares_it(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    (root / ".claude/ralph.json").write_text('{"pluginHooks": true, "sharedBacklog": true}\n')
    assert clone(root, home).returncode == 0
    assert "ralph.sharedbacklog" not in ralph_config(root)


def test_shims_go_where_git_path_hooks_points(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    git(root, "config", "core.hooksPath", "custom-hooks")
    assert clone(root, home).returncode == 0
    for name in HOOK_NAMES:
        assert (root / "custom-hooks" / name).read_bytes() == SHIM.read_bytes()
        assert (root / ".git/hooks" / name).read_bytes() == (BODIES / name).read_bytes()


def test_linked_worktree_saves_the_main_worktree_root(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    (root / "f").write_text("x")
    git(root, "add", "f")
    git(root, "-c", "core.hooksPath=/dev/null", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    worktree = tmp_path / "wt"
    git(root, "worktree", "add", "-q", str(worktree), "-b", "task-1")
    shutil.copytree(root / ".claude", worktree / ".claude")
    result = clone(worktree.resolve(), home)
    assert result.returncode == 0, result.stderr
    assert ralph_config(root)["ralph.projectpath"] == str(root)
    for name in HOOK_NAMES:
        assert (root / ".git/hooks" / name).read_bytes() == SHIM.read_bytes()


@pytest.mark.parametrize("where", ["default", "other"])
def test_claude_config_dir_is_saved_only_off_the_default(tmp_path: Path, home: Path, where: str) -> None:
    root = make_clone(tmp_path / "proj")
    config_dir = home / ".claude" if where == "default" else tmp_path / "cfg"
    config_dir.mkdir(exist_ok=True)
    assert clone(root, home, config_dir=config_dir).returncode == 0
    saved = ralph_config(root).get("ralph.claudeconfigdir")
    assert saved == (None if where == "default" else str(config_dir.resolve()))


# --------------------------------------------------------------------------
# Differing hooks and .local
# --------------------------------------------------------------------------


def customise(root: Path, name: str) -> bytes:
    """Append a line to the clone's ``name`` hook and return its new bytes."""
    hook = root / ".git/hooks" / name
    hook.write_text(hook.read_text() + "echo project-own\n")
    return hook.read_bytes()


def test_accepted_differing_hook_becomes_local(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    own = customise(root, "post-commit")
    accept(root, "post-commit")
    result = clone(root, home)
    assert result.returncode == 0, result.stderr
    local = root / ".git/hooks/post-commit.local"
    assert local.read_bytes() == own
    assert os.access(local, os.X_OK)
    assert (root / ".git/hooks/post-commit").read_bytes() == SHIM.read_bytes()
    before = snapshot(root)
    assert clone(root, home).returncode == 0
    assert snapshot(root) == before


def test_accepted_modified_copy_of_the_body_warns_and_still_becomes_local(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    hook = root / ".git/hooks/pre-commit"
    lines = hook.read_text().splitlines(keepends=True)
    hook.write_text(lines[0] + "# project tweak\necho project-first\n" + "".join(lines[1:]) + "\n  echo project-own\n")
    own = hook.read_bytes()
    accept(root, "pre-commit")
    result = clone(root, home)
    assert result.returncode == 0, result.stderr
    assert "the accepted pre-commit hook repeats the plugin body" in result.stderr
    assert "git-hooks/pre-commit" in result.stderr
    assert "commit-msg" not in result.stderr
    assert (root / ".git/hooks/pre-commit.local").read_bytes() == own
    assert (root / ".git/hooks/pre-commit").read_bytes() == SHIM.read_bytes()


@pytest.mark.parametrize("own", ["#!/bin/sh\necho mine\n", "drop-one-line"])
def test_accepted_hook_without_the_body_lines_gets_no_warning(tmp_path: Path, home: Path, own: str) -> None:
    root = make_clone(tmp_path / "proj")
    hook = root / ".git/hooks/post-commit"
    if own == "drop-one-line":
        body = hook.read_text().splitlines(keepends=True)
        last = max(i for i, line in enumerate(body) if line.strip() and not line.lstrip().startswith("#"))
        own = "".join(body[:last] + body[last + 1 :])
    hook.write_text(own)
    accept(root, "post-commit")
    result = clone(root, home)
    assert result.returncode == 0, result.stderr
    assert "repeats the plugin body" not in result.stderr
    assert (root / ".git/hooks/post-commit.local").read_text() == own


def test_existing_local_is_never_overwritten(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    customise(root, "post-commit")
    accept(root, "post-commit")
    local = root / ".git/hooks/post-commit.local"
    local.write_text("#!/bin/sh\necho mine\n")
    before = snapshot(root)
    result = clone(root, home)
    assert result.returncode == 1
    assert "post-commit.local already exists" in result.stderr
    assert "never overwritten" in result.stderr
    assert snapshot(root) == before
    assert ralph_config(root) == {}


def test_existing_local_equal_to_the_accepted_hook_completes_an_interrupted_run(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    own = customise(root, "post-commit")
    accept(root, "post-commit")
    (root / ".git/hooks/post-commit.local").write_bytes(own)
    assert clone(root, home).returncode == 0
    assert (root / ".git/hooks/post-commit.local").read_bytes() == own
    assert (root / ".git/hooks/post-commit").read_bytes() == SHIM.read_bytes()


def test_existing_local_beside_a_legacy_hook_is_kept(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    local = root / ".git/hooks/pre-commit.local"
    local.write_text("#!/bin/sh\necho mine\n")
    assert clone(root, home).returncode == 0
    assert local.read_text() == "#!/bin/sh\necho mine\n"
    assert (root / ".git/hooks/pre-commit").read_bytes() == SHIM.read_bytes()


def test_unaccepted_differing_hook_stops_before_any_write(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    customise(root, "commit-msg")
    before = snapshot(root)
    result = clone(root, home)
    assert result.returncode == 1
    assert "commit-msg differs from every commit-msg hook body ralph-init has shipped" in result.stderr
    assert snapshot(root) == before
    assert ralph_config(root) == {}


def test_old_shipped_hook_copies_are_replaced_by_the_shim(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    shutil.copyfile(OLD_HOOKS / "pre-commit.v0.14.14", root / ".git/hooks/pre-commit")
    shutil.copyfile(OLD_HOOKS / "commit-msg.v0.16.0", root / ".git/hooks/commit-msg")
    result = clone(root, home)
    assert result.returncode == 0, result.stderr
    for name in HOOK_NAMES:
        assert (root / ".git/hooks" / name).read_bytes() == SHIM.read_bytes()
        assert not (root / f".git/hooks/{name}.local").exists()


def plugin_with_old_shim(tmp_path: Path, list_it: bool = True) -> tuple[Path, bytes]:
    """A copy of the plugin and a fabricated earlier shim, which its hash list lists when ``list_it``."""
    plugin = tmp_path / "plugin"
    shutil.copytree(REPO_ROOT / "plugins/ralph", plugin, ignore=shutil.ignore_patterns("__pycache__"))
    old = SHIM.read_bytes() + b"# an earlier shim version\n"
    if list_it:
        with (plugin / "skills/ralph-init/scripts/shipped-git-hooks.sha256").open("a") as f:
            f.write(f"shim {hashlib.sha256(old).hexdigest()}\n")
    return plugin, old


def test_an_earlier_shim_is_replaced_by_the_current_shim(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    plugin, old = plugin_with_old_shim(tmp_path)
    for name in HOOK_NAMES:
        (root / ".git/hooks" / name).write_bytes(old)
    result = clone(root, home, extra_env={"CLAUDE_PLUGIN_ROOT": str(plugin)})
    assert result.returncode == 0, result.stderr
    for name in HOOK_NAMES:
        assert (root / ".git/hooks" / name).read_bytes() == SHIM.read_bytes()
        assert not (root / f".git/hooks/{name}.local").exists()
    assert "installed the plugin shim as pre-commit" in result.stdout


def test_the_real_pre_dispatcher_shim_is_replaced_in_place(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    old = OLD_HOOKS / "git-hook-shim.v0.25.10"
    for name in HOOK_NAMES:
        shutil.copyfile(old, root / ".git/hooks" / name)
    result = clone(root, home)
    assert result.returncode == 0, result.stderr
    for name in HOOK_NAMES:
        assert (root / ".git/hooks" / name).read_bytes() == SHIM.read_bytes()
        assert not (root / f".git/hooks/{name}.local").exists()


def test_an_unlisted_shim_like_hook_is_refused(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    plugin, old = plugin_with_old_shim(tmp_path, list_it=False)
    (root / ".git/hooks/pre-commit").write_bytes(old)
    before = snapshot(root)
    result = clone(root, home, extra_env={"CLAUDE_PLUGIN_ROOT": str(plugin)})
    assert result.returncode == 1
    assert "pre-commit differs from every pre-commit hook body ralph-init has shipped" in result.stderr
    assert snapshot(root) == before


def test_a_shipped_body_of_another_hook_name_is_refused(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    shutil.copyfile(BODIES / "pre-commit", root / ".git/hooks/commit-msg")
    before = snapshot(root)
    assert clone(root, home).returncode == 1
    assert snapshot(root) == before


def test_refuses_inside_the_devcontainer_and_writes_nothing(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    before = snapshot(root)
    result = clone(root, home, extra_env={"DEVCONTAINER": "true"})
    assert result.returncode == 1
    assert "run it on the host" in result.stderr
    assert snapshot(root) == before
    assert ralph_config(root) == {}


def test_missing_hooks_get_the_shim(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    for name in HOOK_NAMES:
        (root / ".git/hooks" / name).unlink()
    assert clone(root, home).returncode == 0
    for name in HOOK_NAMES:
        assert (root / ".git/hooks" / name).read_bytes() == SHIM.read_bytes()


@pytest.mark.parametrize("stop", STOP_POINTS)
def test_an_interrupted_run_completes_on_rerun(tmp_path: Path, home: Path, stop: str) -> None:
    root = make_clone(tmp_path / "proj")
    customise(root, "post-commit")
    accept(root, "post-commit")
    assert clone(root, home, stop_after=stop).returncode == 3
    assert clone(root, home).returncode == 0
    reference = make_clone(tmp_path / "ref")
    customise(reference, "post-commit")
    accept(reference, "post-commit")
    assert clone(reference, home).returncode == 0
    for name in (*HOOK_NAMES, "post-commit.local"):
        assert (root / ".git/hooks" / name).read_bytes() == (reference / ".git/hooks" / name).read_bytes()
    assert ralph_config(root)["ralph.pluginhooks"] == "true"


# --------------------------------------------------------------------------
# Allow rules in settings.local.json
# --------------------------------------------------------------------------


def test_only_entries_user_settings_hold_are_removed_and_the_rest_reported(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    fragment = json.loads(FRAGMENT.read_text())
    held = fragment["permissions"]["allow"][:3]
    write_user_settings(home / ".claude", held, attribution={"commit": "", "pr": ""})
    result = clone(root, home)
    assert result.returncode == 0, result.stderr
    local = json.loads((root / ".claude/settings.local.json").read_text())
    template = json.loads(LOCAL_TEMPLATE.read_text())
    assert local["permissions"]["allow"] == [r for r in template["permissions"]["allow"] if r not in held]
    assert "attribution" not in local
    assert local["sandbox"] == template["sandbox"]
    not_held = [r for r in fragment["permissions"]["allow"] if r not in held]
    for rule in not_held:
        assert f"not yet in {home}/.claude/settings.json: permissions.allow: {rule}\n" in result.stdout
    assert "sandbox.enabled=true" in result.stdout
    for rule in held:
        assert f"permissions.allow: {rule}\n" not in result.stdout
    assert "Skill(ralph-run)" in local["permissions"]["allow"]


def test_permissions_missing_from_user_settings_are_kept(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    before = (root / ".claude/settings.local.json").read_bytes()
    result = clone(root, home)
    assert result.returncode == 0, result.stderr
    assert (root / ".claude/settings.local.json").read_bytes() == before
    assert "kept in .claude/settings.local.json" in result.stdout


def test_a_differing_value_is_neither_removed_nor_reported(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    path = root / ".claude/settings.local.json"
    data = json.loads(path.read_text())
    data["sandbox"]["enabled"] = False
    path.write_text(json.dumps(data))
    write_user_settings(home / ".claude", [], sandbox={"enabled": False, "autoAllowBashIfSandboxed": True})
    result = clone(root, home)
    assert result.returncode == 0, result.stderr
    assert json.loads(path.read_text())["sandbox"] == {"enabled": False}
    assert "sandbox.enabled" not in result.stdout


def test_settings_local_is_deleted_when_nothing_is_left(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    shutil.copyfile(FRAGMENT, root / ".claude/settings.local.json")
    shutil.copyfile(FRAGMENT, home / ".claude/settings.json")
    result = clone(root, home)
    assert result.returncode == 0, result.stderr
    assert not (root / ".claude/settings.local.json").exists()
    assert "kept in" not in result.stdout


@pytest.mark.parametrize("bad", ["local", "user"])
def test_malformed_settings_stop_before_any_write(tmp_path: Path, home: Path, bad: str) -> None:
    root = make_clone(tmp_path / "proj")
    target = root / ".claude/settings.local.json" if bad == "local" else home / ".claude/settings.json"
    target.write_text("[]")
    before = snapshot(root)
    result = clone(root, home)
    assert result.returncode == 2
    assert "is not a JSON object" in result.stderr
    assert snapshot(root) == before
    assert ralph_config(root) == {}


def test_warns_when_the_tracked_part_has_not_run(tmp_path: Path, home: Path) -> None:
    root = make_clone(tmp_path / "proj")
    (root / ".claude/ralph.json").unlink()
    result = clone(root, home)
    assert result.returncode == 0
    assert "run the tracked part" in result.stderr
