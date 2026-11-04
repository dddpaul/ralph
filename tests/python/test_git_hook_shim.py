"""Git hook bodies in the plugin behind one fixed per-clone shim (TASK-297).

``plugins/ralph/git-hooks/`` holds the pre-commit, commit-msg and post-commit
bodies; ``templates/git-hooks/`` keeps byte-identical copies for legacy
installs straight into ``.git/hooks``. ``templates/shims/git-hook`` is the one
file installed under every hook name: it runs ``<name>.local`` first, then
execs the plugin body found through the registry resolver, and when the plugin
cannot be resolved it blocks or warns per the clone's switches (PRD US-003,
FR-5). These tests drive real ``git commit`` / ``git push`` runs through the
installed shim against fake ``installed_plugins.json`` registries.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT

PLUGIN = REPO_ROOT / "plugins/ralph"
BODIES = PLUGIN / "git-hooks"
TEMPLATES = REPO_ROOT / "plugins/ralph/skills/ralph-init/templates"
TEMPLATE_HOOKS = TEMPLATES / "git-hooks"
SHIM = TEMPLATES / "shims/git-hook"
LEGACY_GUARD = TEMPLATES / "claude/hooks/filename-length-guard.sh"
HOOK_NAMES = ("pre-commit", "commit-msg", "post-commit")
GIT = shutil.which("git") or "/usr/bin/git"
LONG_NAME = "x" * 130 + ".md"

needs_jq = pytest.mark.skipif(shutil.which("jq") is None, reason="jq is not installed")


def env_for(cfg: Path) -> dict[str, str]:
    """A git-clean environment whose Claude config dir is ``cfg``."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["CLAUDE_CONFIG_DIR"] = str(cfg)
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "t"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "t@t"
    return env


def run_git(cwd: Path, cfg: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run git in ``cwd`` with ``cfg`` as the Claude config dir; never raises."""
    return subprocess.run([GIT, *args], cwd=cwd, env=env_for(cfg), input=stdin, capture_output=True, text=True)


def git_ok(cwd: Path, cfg: Path, *args: str) -> str:
    result = run_git(cwd, cfg, *args)
    assert result.returncode == 0, result.stderr
    return result.stdout


def write_registry(cfg: Path, install: Path | None) -> None:
    """Register ``install`` as the user-scope ralph plugin, or no install when None."""
    entries = [] if install is None else [{"scope": "user", "installPath": str(install), "version": "9.9.9"}]
    reg = cfg / "plugins/installed_plugins.json"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(json.dumps({"version": 2, "plugins": {"ralph@dddpaul-ralph": entries}}))


def make_clone(path: Path, cfg: Path) -> Path:
    path.mkdir(parents=True)
    git_ok(path, cfg, "init", "-q", "-b", "master")
    git_ok(path, cfg, "commit", "-q", "--allow-empty", "-m", "init")
    return path.resolve()


def install_shim(hooks_dir: Path, *names: str) -> None:
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copy2(SHIM, hooks_dir / name)


def write_hook(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)


@pytest.fixture
def world(tmp_path: Path) -> dict[str, Path]:
    """A clone and a Claude config dir, under paths with spaces."""
    base = tmp_path / "with spaces"
    cfg = base / "claude cfg"
    return {"base": base, "cfg": cfg, "clone": make_clone(base / "my project", cfg)}


def commit_file(world: dict[str, Path], name: str, message: str = "add") -> subprocess.CompletedProcess[str]:
    clone, cfg = world["clone"], world["cfg"]
    (clone / name).write_text("x\n")
    git_ok(clone, cfg, "add", "--", name)
    return run_git(clone, cfg, "commit", "-q", "-m", message)


# ---------------------------------------------------------------- parity


@pytest.mark.parametrize("name", HOOK_NAMES)
def test_template_copy_is_byte_identical_to_the_plugin_body(name: str) -> None:
    body, copy = BODIES / name, TEMPLATE_HOOKS / name
    assert body.read_bytes() == copy.read_bytes()
    assert os.access(body, os.X_OK) and os.access(copy, os.X_OK)


def test_plugin_ships_exactly_the_template_hooks() -> None:
    assert sorted(p.name for p in BODIES.iterdir()) == sorted(p.name for p in TEMPLATE_HOOKS.iterdir())


def test_shim_is_executable_and_names_no_hook() -> None:
    assert os.access(SHIM, os.X_OK)
    text = SHIM.read_text()
    assert 'name="${0##*/}"' in text
    for name in HOOK_NAMES:
        assert f"git-hooks/{name}" not in text


# ---------------------------------------------------------------- shim → plugin body


@needs_jq
def test_shim_runs_the_plugin_bodies_on_a_real_commit(world: dict[str, Path]) -> None:
    write_registry(world["cfg"], PLUGIN)
    install_shim(world["clone"] / ".git/hooks", *HOOK_NAMES)
    assert commit_file(world, "ok.md").returncode == 0
    blocked = commit_file(world, "two.md", "add\n\nCo-Authored-By: x <x@x>")
    assert blocked.returncode == 1
    assert "forbidden trailer" in blocked.stderr


@needs_jq
def test_plugin_pre_commit_uses_the_bundled_length_guard(world: dict[str, Path]) -> None:
    # No .claude/hooks copy in the project: only the plugin's own guard can block.
    write_registry(world["cfg"], PLUGIN)
    install_shim(world["clone"] / ".git/hooks", "pre-commit")
    result = commit_file(world, LONG_NAME)
    assert result.returncode == 1
    assert LONG_NAME in result.stderr


@pytest.mark.parametrize("with_project_guard", [True, False])
def test_legacy_pre_commit_falls_back_to_the_project_guard(world: dict[str, Path], with_project_guard: bool) -> None:
    hooks = world["clone"] / ".git/hooks"
    hooks.mkdir(exist_ok=True)
    shutil.copy2(TEMPLATE_HOOKS / "pre-commit", hooks / "pre-commit")
    if with_project_guard:
        guard = world["clone"] / ".claude/hooks/filename-length-guard.sh"
        guard.parent.mkdir(parents=True)
        shutil.copy2(LEGACY_GUARD, guard)
        guard.chmod(0o755)  # tracked 100644 in the templates; ralph-init installs it executable
    result = commit_file(world, LONG_NAME)
    assert result.returncode == (1 if with_project_guard else 0), result.stderr


def test_legacy_install_into_git_hooks_still_works(world: dict[str, Path]) -> None:
    hooks = world["clone"] / ".git/hooks"
    for name in HOOK_NAMES:
        shutil.copy2(TEMPLATE_HOOKS / name, hooks / name)
    assert commit_file(world, "ok.md").returncode == 0
    blocked = commit_file(world, "two.md", "add\n\n## Test plan")
    assert blocked.returncode == 1
    assert "forbidden trailer" in blocked.stderr


# ---------------------------------------------------------------- local hooks


def recording_install(base: Path, *names: str) -> Path:
    """A fake plugin install whose bodies record their arguments and stdin."""
    install = base / "install"
    for name in names:
        write_hook(
            install / "git-hooks" / name,
            f'{{ printf "%s\\n" "$@"; cat; }} >"$(git rev-parse --git-path hooks)/../{name}.body.log"\n',
        )
    return install


@needs_jq
def test_local_pre_push_and_body_get_the_same_args_and_stdin_with_core_hooks_path(world: dict[str, Path]) -> None:
    clone, cfg = world["clone"], world["cfg"]
    remote = world["base"] / "remote.git"
    git_ok(world["base"], cfg, "init", "-q", "--bare", str(remote))
    git_ok(clone, cfg, "remote", "add", "origin", str(remote))
    git_ok(clone, cfg, "config", "core.hooksPath", "custom hooks")
    hooks_dir = Path(git_ok(clone, cfg, "rev-parse", "--git-path", "hooks").strip())
    assert hooks_dir == Path("custom hooks")
    write_registry(cfg, recording_install(world["base"], "pre-push"))
    install_shim(clone / hooks_dir, "pre-push")
    write_hook(clone / hooks_dir / "pre-push.local", '{ printf "%s\\n" "$@"; cat; } >"$PWD/local.log"\n')
    head = git_ok(clone, cfg, "rev-parse", "HEAD").strip()
    git_ok(clone, cfg, "push", "-q", "origin", "master")
    local_log = (clone / "local.log").read_text()
    body_log = (clone / hooks_dir / ".." / "pre-push.body.log").read_text()
    assert local_log == body_log
    assert local_log.startswith(f"origin\n{remote}\n")
    assert f"refs/heads/master {head} refs/heads/master " in local_log


@needs_jq
def test_failing_local_hook_stops_the_hook(world: dict[str, Path]) -> None:
    clone, cfg = world["clone"], world["cfg"]
    write_registry(cfg, recording_install(world["base"], "commit-msg"))
    install_shim(clone / ".git/hooks", "commit-msg")
    write_hook(clone / ".git/hooks/commit-msg.local", 'printf "%s\\n" "$@" >"$PWD/local.log"\nexit 3\n')
    result = commit_file(world, "a.md")
    assert result.returncode == 1
    assert (clone / "local.log").read_text() == ".git/COMMIT_EDITMSG\n"
    assert not (clone / ".git/commit-msg.body.log").exists()
    (clone / ".git/hooks/commit-msg.local").write_text("#!/usr/bin/env bash\nexit 0\n")
    assert run_git(clone, cfg, "commit", "-q", "-m", "add").returncode == 0
    assert (clone / ".git/commit-msg.body.log").read_text().startswith(".git/COMMIT_EDITMSG\n")


# ---------------------------------------------------------------- unresolvable plugin

BLOCKING = [
    # (hook, switches set true, expected exit, bypass named)
    ("pre-commit", ("ralph.pluginHooks",), 1, "git commit --no-verify"),
    ("commit-msg", ("ralph.pluginHooks",), 1, "git commit --no-verify"),
    ("pre-push", ("ralph.pluginHooks",), 1, "git push --no-verify"),
    ("pre-push", ("ralph.sharedBacklog",), 1, "git push --no-verify"),
    ("pre-commit", ("ralph.sharedBacklog",), 0, None),
    ("commit-msg", ("ralph.sharedBacklog",), 0, None),
    ("post-commit", ("ralph.pluginHooks", "ralph.sharedBacklog"), 0, None),
    ("pre-commit", (), 0, None),
    ("commit-msg", (), 0, None),
    ("pre-push", (), 0, None),
    ("post-commit", (), 0, None),
]


@pytest.mark.parametrize(("name", "switches", "code", "bypass"), BLOCKING)
def test_unresolved_plugin_blocks_only_per_switch(
    world: dict[str, Path], name: str, switches: tuple[str, ...], code: int, bypass: str | None
) -> None:
    clone, cfg = world["clone"], world["cfg"]
    write_registry(cfg, None)
    install_shim(clone / ".git/hooks", name)
    for switch in switches:
        git_ok(clone, cfg, "config", switch, "true")
    result = subprocess.run(
        [str(clone / ".git/hooks" / name), "arg"], cwd=clone, env=env_for(cfg), input="", capture_output=True, text=True
    )
    assert result.returncode == code
    assert "no project- or local-scope entry" in result.stderr
    if bypass is None:
        assert "ralph: warning:" in result.stderr
        assert "--no-verify" not in result.stderr
    else:
        assert bypass in result.stderr
        assert "warning" not in result.stderr


def test_unresolved_plugin_with_a_switch_false_only_warns(world: dict[str, Path]) -> None:
    clone, cfg = world["clone"], world["cfg"]
    install_shim(clone / ".git/hooks", "pre-commit")
    git_ok(clone, cfg, "config", "ralph.pluginHooks", "false")
    assert commit_file(world, "a.md").returncode == 0


def test_unresolved_plugin_blocks_a_real_commit_until_no_verify(world: dict[str, Path]) -> None:
    clone, cfg = world["clone"], world["cfg"]
    install_shim(clone / ".git/hooks", "pre-commit", "commit-msg")
    git_ok(clone, cfg, "config", "ralph.pluginHooks", "true")
    blocked = commit_file(world, "a.md")
    assert blocked.returncode == 1
    assert "git commit --no-verify" in blocked.stderr
    assert run_git(clone, cfg, "commit", "-q", "--no-verify", "-m", "add").returncode == 0


# ---------------------------------------------------------------- merge in a linked worktree


@pytest.mark.parametrize("hook", [BODIES / "commit-msg", TEMPLATE_HOOKS / "commit-msg"])
def test_commit_msg_recognises_a_merge_in_a_linked_worktree(world: dict[str, Path], hook: Path) -> None:
    clone, cfg = world["clone"], world["cfg"]
    linked = world["base"] / "linked tree"
    git_ok(clone, cfg, "branch", "side")
    git_ok(clone, cfg, "worktree", "add", "-q", "-b", "work", str(linked))
    assert (linked / ".git").is_file()
    (clone / "side.md").write_text("s\n")
    git_ok(clone, cfg, "checkout", "-q", "side")
    git_ok(clone, cfg, "add", "side.md")
    git_ok(clone, cfg, "commit", "-q", "--no-verify", "-m", "side")
    msg = linked / "msg.txt"
    msg.write_text("Merge\n\nCo-Authored-By: x <x@x>\n")

    def run_hook() -> int:
        return subprocess.run([str(hook), str(msg)], cwd=linked, env=env_for(cfg), capture_output=True).returncode

    assert run_hook() == 1
    git_ok(linked, cfg, "merge", "-q", "--no-ff", "--no-commit", "side")
    assert not (clone / ".git/MERGE_MSG").exists()
    assert run_hook() == 0
