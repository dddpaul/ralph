"""Git hook bodies in the plugin behind one fixed per-clone shim (TASK-297).

``plugins/ralph/git-hooks/`` holds the pre-commit, commit-msg and post-commit
bodies, which also still work as legacy copies installed straight into
``.git/hooks`` (ralph-init no longer ships template copies of them).
``templates/shims/git-hook`` is the one
file installed under every hook name: it execs the plugin dispatcher
``git-hooks/run`` found through the registry resolver, which runs
``<name>.local`` first and then the plugin body (TASK-341). When the plugin
cannot be resolved the shim blocks or warns per the clone's switches, and on a
warning runs ``<name>.local`` alone (PRD US-003, FR-5). These tests drive real
``git commit`` / ``git push`` runs through the installed shim against fake ``installed_plugins.json`` registries.
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
SHIM = TEMPLATES / "shims/git-hook"
LEGACY_GUARD = PLUGIN / "hooks/filename-length-guard.sh"
HOOK_NAMES = ("pre-commit", "commit-msg", "post-commit")
# pre-push ships too, but only shared-backlog enable installs its shim (TASK-311).
BODY_NAMES = (*HOOK_NAMES, "pre-push")
DISPATCHER = BODIES / "run"
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
    return subprocess.run(
        [GIT, *args], cwd=cwd, env=env_for(cfg), input=stdin, capture_output=True, text=True, check=False
    )


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


@pytest.mark.parametrize("name", BODY_NAMES)
def test_plugin_body_is_executable(name: str) -> None:
    assert os.access(BODIES / name, os.X_OK)


def test_plugin_ships_exactly_the_shimmed_hooks_and_no_template_copies() -> None:
    assert sorted(p.name for p in BODIES.iterdir()) == sorted((*BODY_NAMES, "run"))
    assert not (TEMPLATES / "git-hooks").exists()


def test_shim_is_executable_and_names_no_hook() -> None:
    assert os.access(SHIM, os.X_OK)
    assert os.access(DISPATCHER, os.X_OK)
    text = SHIM.read_text()
    assert 'name="${0##*/}"' in text
    assert 'ralph_resolve_plugin "$PWD" git-hooks/run' in text
    for name in HOOK_NAMES:
        assert f"git-hooks/{name}" not in text


def test_shim_copies_no_stdin_through_descriptors() -> None:
    for path in (SHIM, DISPATCHER):
        text = path.read_text()
        assert "exec 3" not in text
        assert "0<&3" not in text
        assert "mktemp" not in text


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
    shutil.copy2(BODIES / "pre-commit", hooks / "pre-commit")
    if with_project_guard:
        guard = world["clone"] / ".claude/hooks/filename-length-guard.sh"
        guard.parent.mkdir(parents=True)
        shutil.copy2(LEGACY_GUARD, guard)
        guard.chmod(0o755)
    result = commit_file(world, LONG_NAME)
    assert result.returncode == (1 if with_project_guard else 0), result.stderr


def test_legacy_install_into_git_hooks_still_works(world: dict[str, Path]) -> None:
    hooks = world["clone"] / ".git/hooks"
    for name in HOOK_NAMES:
        shutil.copy2(BODIES / name, hooks / name)
    assert commit_file(world, "ok.md").returncode == 0
    blocked = commit_file(world, "two.md", "add\n\n## Test plan")
    assert blocked.returncode == 1
    assert "forbidden trailer" in blocked.stderr


# ---------------------------------------------------------------- local hooks


def recording_install(base: Path, *names: str) -> Path:
    """A fake plugin install whose bodies record their arguments and stdin."""
    install = base / "install"
    (install / "git-hooks").mkdir(parents=True, exist_ok=True)
    shutil.copy2(DISPATCHER, install / "git-hooks/run")
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


# ---------------------------------------------------------------- dispatcher

RECORD = '{ printf "%s\\n" "$@"; cat; } >"$PWD/%s.log"\n'


def dispatcher_install(base: Path, *names: str) -> Path:
    """A plugin ``git-hooks`` dir holding the real dispatcher and recording bodies."""
    hooks = base / "plugin git-hooks"
    hooks.mkdir(parents=True)
    shutil.copy2(DISPATCHER, hooks / "run")
    for name in names:
        write_hook(hooks / name, RECORD % ("%s", "body"))
    return hooks


def run_dispatcher(
    world: dict[str, Path], hooks: Path, *args: str, stdin: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(hooks / "run"), *args],
        cwd=world["clone"], env=env_for(world["cfg"]), input=stdin, capture_output=True, text=True, check=False,
    )


@pytest.mark.parametrize("stdin", ["a b c d\ne f g h\n", "no final newline", "\n\n"])
def test_dispatcher_gives_local_and_body_the_same_args_and_pre_push_stdin(world: dict[str, Path], stdin: str) -> None:
    clone = world["clone"]
    hooks = dispatcher_install(world["base"], "pre-push")
    write_hook(clone / ".git/hooks/pre-push.local", RECORD % ("%s", "local"))
    result = run_dispatcher(world, hooks, "pre-push", "origin", "a b", stdin=stdin)
    assert result.returncode == 0, result.stderr
    expected = "origin\na b\n" + stdin
    assert (clone / "local.log").read_text() == expected
    assert (clone / "body.log").read_text() == expected


def test_dispatcher_passes_git_stdin_straight_to_a_body_without_local(world: dict[str, Path]) -> None:
    hooks = dispatcher_install(world["base"], "commit-msg")
    result = run_dispatcher(world, hooks, "commit-msg", "msg", stdin="piped\n")
    assert result.returncode == 0, result.stderr
    assert (world["clone"] / "body.log").read_text() == "msg\npiped\n"


def test_dispatcher_stops_with_the_status_of_a_failing_local(world: dict[str, Path]) -> None:
    clone = world["clone"]
    hooks = dispatcher_install(world["base"], "pre-push")
    write_hook(clone / ".git/hooks/pre-push.local", "cat >/dev/null\nexit 7\n")
    result = run_dispatcher(world, hooks, "pre-push", "origin", stdin="x\n")
    assert result.returncode == 7
    assert not (clone / "body.log").exists()


def test_dispatcher_returns_the_body_status(world: dict[str, Path]) -> None:
    hooks = dispatcher_install(world["base"])
    write_hook(hooks / "pre-commit", "exit 5\n")
    assert run_dispatcher(world, hooks, "pre-commit").returncode == 5


def test_dispatcher_warns_and_exits_0_after_local_for_a_name_without_body(world: dict[str, Path]) -> None:
    clone = world["clone"]
    hooks = dispatcher_install(world["base"])
    write_hook(clone / ".git/hooks/post-rewrite.local", RECORD % ("%s", "local"))
    result = run_dispatcher(world, hooks, "post-rewrite", "amend", stdin="old new\n")
    assert result.returncode == 0
    assert "ships no post-rewrite hook; ran only post-rewrite.local" in result.stderr
    assert (clone / "local.log").read_text() == "amend\nold new\n"


# ---------------------------------------------------------------- unresolvable plugin

BLOCKING = [
    # (hook, switches set true, expected exit, bypass named)
    ("pre-commit", ("ralph.pluginHooks",), 1, "--no-verify"),
    ("commit-msg", ("ralph.pluginHooks",), 1, "--no-verify"),
    ("pre-push", ("ralph.pluginHooks",), 1, "--no-verify"),
    ("pre-push", ("ralph.sharedBacklog",), 1, "--no-verify"),
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
        [str(clone / ".git/hooks" / name), "arg"],
        cwd=clone, env=env_for(cfg), input="", capture_output=True, text=True, check=False,
    )
    assert result.returncode == code
    assert "no project- or local-scope entry" in result.stderr
    if bypass is None:
        assert "ralph: warning:" in result.stderr
        assert "--no-verify" not in result.stderr
    else:
        assert bypass in result.stderr
        assert "warning" not in result.stderr


@pytest.mark.parametrize("name", ["pre-push", "post-commit"])
def test_unresolved_plugin_warns_then_execs_local_with_git_stdin(world: dict[str, Path], name: str) -> None:
    clone, cfg = world["clone"], world["cfg"]
    write_registry(cfg, None)
    install_shim(clone / ".git/hooks", name)
    write_hook(clone / ".git/hooks" / f"{name}.local", RECORD % ("%s", "local") + "exit 4\n")
    result = subprocess.run(
        [str(clone / ".git/hooks" / name), "origin", "a b"],
        cwd=clone, env=env_for(cfg), input="refs\nmore", capture_output=True, text=True, check=False,
    )
    assert result.returncode == 4
    assert f"ralph: warning: {name} hook ran without the ralph plugin" in result.stderr
    assert (clone / "local.log").read_text() == "origin\na b\nrefs\nmore"


def test_unresolved_plugin_blocks_without_running_local(world: dict[str, Path]) -> None:
    clone, cfg = world["clone"], world["cfg"]
    write_registry(cfg, None)
    install_shim(clone / ".git/hooks", "pre-push")
    git_ok(clone, cfg, "config", "ralph.sharedBacklog", "true")
    write_hook(clone / ".git/hooks/pre-push.local", RECORD % ("%s", "local"))
    result = subprocess.run(
        [str(clone / ".git/hooks/pre-push"), "origin"],
        cwd=clone, env=env_for(cfg), input="", capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    assert not (clone / "local.log").exists()


@needs_jq
def test_shim_names_a_plugin_without_the_dispatcher_and_falls_back(world: dict[str, Path]) -> None:
    clone, cfg = world["clone"], world["cfg"]
    old_plugin = world["base"] / "old plugin"
    write_hook(old_plugin / "git-hooks/pre-commit", "exit 0\n")
    write_registry(cfg, old_plugin)
    install_shim(clone / ".git/hooks", "pre-commit")
    git_ok(clone, cfg, "config", "ralph.pluginHooks", "true")
    blocked = commit_file(world, "a.md")
    assert blocked.returncode == 1
    assert "git-hooks/run not found in the installed plugin" in blocked.stderr


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
    assert "bypass this once with --no-verify" in blocked.stderr
    assert run_git(clone, cfg, "commit", "-q", "--no-verify", "-m", "add").returncode == 0


# ---------------------------------------------------------------- merge in a linked worktree


@pytest.mark.parametrize("legacy", [False, True], ids=["plugin-body", "legacy-copy"])
def test_commit_msg_recognises_a_merge_in_a_linked_worktree(world: dict[str, Path], legacy: bool) -> None:
    clone, cfg = world["clone"], world["cfg"]
    hook = BODIES / "commit-msg"
    if legacy:
        hook = clone / ".git/hooks/commit-msg"
        shutil.copy2(BODIES / "commit-msg", hook)
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
        return subprocess.run(
            [str(hook), str(msg)], cwd=linked, env=env_for(cfg), capture_output=True, check=False
        ).returncode

    assert run_hook() == 1
    git_ok(linked, cfg, "merge", "-q", "--no-ff", "--no-commit", "side")
    assert not (clone / ".git/MERGE_MSG").exists()
    assert run_hook() == 0
