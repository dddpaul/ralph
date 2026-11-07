"""The plugin registry resolver shared by ralph.sh, refine.sh and the shims (TASK-295, TASK-321).

``templates/shims/resolve-plugin.sh`` holds one marker-delimited block that
defines ``ralph_resolve_plugin <dir> <relpath>``. Every embedding file carries a
byte-identical copy, so the parity test below is the only thing keeping the
copies in step. The behaviour tests source the block from the source of truth
and run it against fake ``installed_plugins.json`` registries and real git
clones, including a linked worktree and a clone "mounted" at another path.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from devcontainer_config import REPO_ROOT

TEMPLATES = REPO_ROOT / "plugins/ralph/skills/ralph-init/templates"
SHIMS = TEMPLATES / "shims"
SOURCE = SHIMS / "resolve-plugin.sh"
BEGIN = "# >>> ralph-resolve-plugin >>>\n"
END = "# <<< ralph-resolve-plugin <<<\n"
KEY = "ralph@dddpaul-ralph"
REL = "skills/ralph-run/scripts/ralph_orchestrator.py"
BASH = shutil.which("bash") or "/bin/bash"
GIT = shutil.which("git") or "/usr/bin/git"
JQ = shutil.which("jq")


def extract_block(text: str) -> str | None:
    """Return the resolver block (markers included) from ``text``, or None if absent."""
    start = text.find(BEGIN)
    end = text.find(END, start)
    if start < 0 or end < 0:
        return None
    return text[start : end + len(END)]


def embedding_files() -> list[Path]:
    """Every file that must embed the resolver: shim templates and both orchestrator shims."""
    shims = sorted(p for p in SHIMS.iterdir() if p.is_file() and p != SOURCE)
    roots = [REPO_ROOT / "ralph.sh", REPO_ROOT / "refine.sh"]
    roots += [TEMPLATES / "root/ralph.sh", TEMPLATES / "root/refine.sh"]
    return shims + roots


def block_drift(path: Path, source_block: str) -> str | None:
    """Describe how ``path`` fails to embed ``source_block``, or None when it matches."""
    text = path.read_text()
    block = extract_block(text)
    if block is None:
        return f"{path}: no resolver block"
    if block != source_block:
        return f"{path}: resolver block differs from {SOURCE.name}"
    if text.count(BEGIN) != 1:
        return f"{path}: more than one resolver block"
    return None


SOURCE_BLOCK = extract_block(SOURCE.read_text())


def test_source_holds_one_block() -> None:
    assert SOURCE_BLOCK is not None
    assert SOURCE.read_text().count(BEGIN) == 1


@pytest.mark.parametrize("path", embedding_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_embedded_copy_matches_source(path: Path) -> None:
    assert SOURCE_BLOCK is not None
    assert block_drift(path, SOURCE_BLOCK) is None


def test_parity_check_catches_a_drifted_copy(tmp_path: Path) -> None:
    assert SOURCE_BLOCK is not None
    drifted = tmp_path / "ralph.sh"
    drifted.write_text((REPO_ROOT / "ralph.sh").read_text().replace("expected 2", "expected 3"))
    assert block_drift(drifted, SOURCE_BLOCK) == f"{drifted}: resolver block differs from {SOURCE.name}"
    missing = tmp_path / "git-hook"
    missing.write_text("#!/usr/bin/env bash\n")
    assert block_drift(missing, SOURCE_BLOCK) == f"{missing}: no resolver block"


@pytest.mark.parametrize("name", ["ralph.sh", "refine.sh"])
def test_no_cache_sort_remains(name: str) -> None:
    for path in (REPO_ROOT / name, TEMPLATES / "root" / name):
        text = path.read_text()
        assert "sort -V" not in text
        assert "plugins/cache/" not in text
        assert "ralph_resolve_plugin \"$RALPH_PROJECT_ROOT\" skills/ralph-run/scripts/" in text


# ---------------------------------------------------------------- behaviour


def git(cwd: Path, *args: str) -> str:
    """Run git in ``cwd`` with a throwaway identity and return stdout."""
    cmd = [GIT, "-c", "user.name=t", "-c", "user.email=t@t", *args]
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout


def make_clone(path: Path) -> Path:
    """Create a git clone with one commit at ``path`` and return its canonical root."""
    path.mkdir(parents=True)
    git(path, "init", "-q")
    git(path, "commit", "-q", "--allow-empty", "-m", "init")
    return path.resolve()


def make_install(cache: Path, marketplace: str, version: str) -> Path:
    """Lay down a plugin cache install holding the orchestrator; return its installPath."""
    install = cache / marketplace / "ralph" / version
    (install / REL).parent.mkdir(parents=True)
    (install / REL).touch()
    return install


def write_registry(cfg: Path, entries: list[dict[str, Any]], version: int = 2) -> None:
    """Write ``<cfg>/plugins/installed_plugins.json`` with ``entries`` under the ralph key."""
    reg = cfg / "plugins/installed_plugins.json"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(json.dumps({"version": version, "plugins": {KEY: entries, "other@x": []}}))


def user(install: Path) -> dict[str, Any]:
    return {"scope": "user", "installPath": str(install), "version": install.name}


def project(install: Path, project_path: Path | str, scope: str = "project") -> dict[str, Any]:
    return {
        "scope": scope,
        "projectPath": str(project_path),
        "installPath": str(install),
        "version": install.name,
    }


def tool_path(tmp: Path, *tools: str) -> str:
    """Return a PATH dir holding only symlinks to ``tools`` (always git)."""
    bindir = tmp / "only-bin"
    bindir.mkdir(exist_ok=True)
    for tool in ("git", *tools):
        found = shutil.which(tool)
        assert found, tool
        link = bindir / tool
        if not link.exists():
            link.symlink_to(found)
    return str(bindir)


def resolve(
    start: Path,
    cfg: Path | None,
    *,
    path: str | None = None,
    home: Path | None = None,
    rel: str = REL,
    extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Source the resolver block and run it from ``start``."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.pop("CLAUDE_CONFIG_DIR", None)
    if cfg is not None:
        env["CLAUDE_CONFIG_DIR"] = str(cfg)
    if path is not None:
        env["PATH"] = path
    env["HOME"] = str(home) if home is not None else env.get("HOME", "/nonexistent")
    env.update(extra or {})
    script = f'. "{SOURCE}" && ralph_resolve_plugin "$1" "$2"'
    return subprocess.run(
        [BASH, "-c", script, "resolve", str(start), rel],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def ok(result: subprocess.CompletedProcess[str], install: Path) -> None:
    assert (result.returncode, result.stderr) == (0, "")
    assert result.stdout == f"{install / REL}\n"


# One reason phrase per failure; each failing run must name exactly its own.
REASONS = (
    "is not inside a git work tree",
    "separate git dir layout is not supported",
    "jq is not on PATH",
    "installed_plugins.json not found",
    "is not valid JSON",
    "has version",
    "no project- or local-scope entry for",
    "has no installPath",
    "does not exist",
    "not found in the installed plugin",
)


def fails(result: subprocess.CompletedProcess[str], reason: str) -> None:
    assert result.returncode == 1
    assert result.stdout == ""
    assert reason in result.stderr
    named = [r for r in REASONS if r in result.stderr]
    assert named == [next(r for r in REASONS if r in reason)], result.stderr


needs_jq = pytest.mark.skipif(JQ is None, reason="jq is not installed")


@pytest.fixture
def world(tmp_path: Path) -> dict[str, Path]:
    """A clone, a config dir and a plugin cache, all under paths with spaces."""
    base = tmp_path / "with spaces"
    cfg = base / "claude cfg"
    cache = cfg / "plugins/cache"
    return {
        "base": base,
        "clone": make_clone(base / "my project"),
        "cfg": cfg,
        "user": make_install(cache, "dddpaul-ralph", "0.14.15"),
        "proj": make_install(cache, "dddpaul-ralph", "0.15.0"),
        "fork": make_install(cache, "zz-fork", "0.1.0"),
    }


@needs_jq
def test_user_scope_entry_resolves_despite_a_zz_fork_cache(world: dict[str, Path]) -> None:
    write_registry(world["cfg"], [user(world["user"])])
    ok(resolve(world["clone"], world["cfg"]), world["user"])


@needs_jq
def test_user_then_project_resolves_the_user_entry(world: dict[str, Path]) -> None:
    # Claude Code 2.1.309 loads the first applicable entry in registry order, and
    # appends new installs: a user install made first wins inside the project too.
    write_registry(world["cfg"], [user(world["user"]), project(world["proj"], world["clone"])])
    ok(resolve(world["clone"], world["cfg"]), world["user"])
    ok(resolve(world["clone"] / ".git", world["cfg"]), world["user"])


@needs_jq
def test_project_then_user_resolves_by_location(world: dict[str, Path]) -> None:
    unrelated = make_clone(world["base"] / "unrelated")
    write_registry(world["cfg"], [project(world["proj"], world["clone"]), user(world["user"])])
    ok(resolve(world["clone"], world["cfg"]), world["proj"])
    ok(resolve(world["clone"] / ".git", world["cfg"]), world["proj"])
    ok(resolve(unrelated, world["cfg"]), world["user"])


@needs_jq
def test_local_scope_entry_behaves_like_project_scope(world: dict[str, Path]) -> None:
    unrelated = make_clone(world["base"] / "unrelated")
    write_registry(world["cfg"], [project(world["proj"], world["clone"], "local"), user(world["user"])])
    ok(resolve(world["clone"], world["cfg"]), world["proj"])
    ok(resolve(unrelated, world["cfg"]), world["user"])
    write_registry(world["cfg"], [user(world["user"]), project(world["proj"], world["clone"], "local")])
    ok(resolve(world["clone"], world["cfg"]), world["user"])
    write_registry(world["cfg"], [project(world["proj"], world["clone"], "local")])
    ok(resolve(world["clone"], world["cfg"]), world["proj"])
    fails(resolve(unrelated, world["cfg"]), "no project- or local-scope entry for")


@needs_jq
def test_project_scope_entry_for_another_clone_is_ignored(world: dict[str, Path]) -> None:
    other = world["base"] / "elsewhere"
    write_registry(world["cfg"], [project(world["proj"], other), user(world["user"])])
    ok(resolve(world["clone"], world["cfg"]), world["user"])


@needs_jq
def test_project_only_install_from_the_host_path(world: dict[str, Path]) -> None:
    write_registry(world["cfg"], [project(world["proj"], world["clone"])])
    sub = world["clone"] / "sub dir"
    sub.mkdir()
    ok(resolve(sub, world["cfg"]), world["proj"])


@needs_jq
def test_exported_cdpath_does_not_change_the_identity(world: dict[str, Path]) -> None:
    # A relative `cd .git` consults CDPATH and echoes the target; a CDPATH entry
    # holding another repo's .git must not hijack the lookup either.
    decoy = make_clone(world["base"] / "decoy")
    write_registry(world["cfg"], [project(world["proj"], world["clone"])])
    for cdpath in (".:/nonexistent", str(decoy)):
        ok(resolve(world["clone"], world["cfg"], extra={"CDPATH": cdpath}), world["proj"])


@needs_jq
def test_project_only_install_from_a_workspace_mount(world: dict[str, Path]) -> None:
    # The devcontainer sees the host clone at /workspace; the identity saved in
    # the clone's git config is what matches the host-path registry entry.
    host_path = "/Users/someone/Projects/my project"
    mount = make_clone(world["base"] / "workspace")
    write_registry(world["cfg"], [project(world["proj"], host_path)])
    fails(resolve(mount, world["cfg"]), "no project- or local-scope entry for")
    git(mount, "config", "ralph.projectPath", host_path)
    ok(resolve(mount, world["cfg"]), world["proj"])


@needs_jq
def test_project_only_install_from_a_linked_worktree(world: dict[str, Path]) -> None:
    linked = world["base"] / "linked tree"
    git(world["clone"], "worktree", "add", "-q", "-b", "side", str(linked))
    write_registry(world["cfg"], [project(world["proj"], world["clone"])])
    ok(resolve(linked, world["cfg"]), world["proj"])


@needs_jq
def test_separate_git_dir_is_rejected(world: dict[str, Path]) -> None:
    clone = world["base"] / "split"
    git(world["base"], "init", "-q", f"--separate-git-dir={world['base'] / 'store.git'}", str(clone))
    write_registry(world["cfg"], [user(world["user"])])
    fails(resolve(clone, world["cfg"]), "separate git dir layout is not supported")


@needs_jq
def test_config_dir_precedence(world: dict[str, Path]) -> None:
    home = world["base"] / "home"
    write_registry(home / ".claude", [user(world["fork"])])
    git_cfg = world["base"] / "git cfg"
    write_registry(git_cfg, [user(world["proj"])])
    write_registry(world["cfg"], [user(world["user"])])
    ok(resolve(world["clone"], None, home=home), world["fork"])
    git(world["clone"], "config", "ralph.claudeConfigDir", str(git_cfg))
    ok(resolve(world["clone"], None, home=home), world["proj"])
    ok(resolve(world["clone"], world["cfg"], home=home), world["user"])


@needs_jq
def test_jq_falls_back_to_git_config(world: dict[str, Path], tmp_path: Path) -> None:
    write_registry(world["cfg"], [user(world["user"])])
    no_jq = tool_path(tmp_path)
    git(world["clone"], "config", "ralph.jq", str(JQ))
    ok(resolve(world["clone"], world["cfg"], path=no_jq), world["user"])


@needs_jq
def test_missing_jq(world: dict[str, Path], tmp_path: Path) -> None:
    write_registry(world["cfg"], [user(world["user"])])
    no_jq = tool_path(tmp_path)
    fails(resolve(world["clone"], world["cfg"], path=no_jq), "jq is not on PATH")
    git(world["clone"], "config", "ralph.jq", str(tmp_path / "missing-jq"))
    fails(resolve(world["clone"], world["cfg"], path=no_jq), "jq is not on PATH")


@needs_jq
def test_wrong_registry_version(world: dict[str, Path]) -> None:
    write_registry(world["cfg"], [user(world["user"])], version=1)
    fails(resolve(world["clone"], world["cfg"]), "has version 1, expected 2")


@needs_jq
def test_missing_registry(world: dict[str, Path]) -> None:
    fails(resolve(world["clone"], world["cfg"]), "installed_plugins.json not found")


@needs_jq
def test_not_installed(world: dict[str, Path]) -> None:
    write_registry(world["cfg"], [])
    fails(resolve(world["clone"], world["cfg"]), "no project- or local-scope entry for")


@needs_jq
def test_no_applicable_entry(world: dict[str, Path]) -> None:
    other = world["base"] / "elsewhere"
    entries = [project(world["proj"], other), project(world["user"], other, "local"), {"scope": "managed"}]
    write_registry(world["cfg"], entries)
    result = resolve(world["clone"], world["cfg"])
    fails(result, f"has no user-scope entry and no project- or local-scope entry for {world['clone']}")


@needs_jq
@pytest.mark.parametrize("scope", ["user", "project"])
def test_several_applicable_entries_take_the_first(world: dict[str, Path], scope: str) -> None:
    if scope == "user":
        entries = [user(world["user"]), user(world["proj"])]
    else:
        entries = [project(world["proj"], world["clone"]), project(world["user"], world["clone"]), user(world["fork"])]
    write_registry(world["cfg"], entries)
    ok(resolve(world["clone"], world["cfg"]), world["user"] if scope == "user" else world["proj"])


@needs_jq
def test_missing_install_path(world: dict[str, Path]) -> None:
    write_registry(world["cfg"], [{"scope": "user", "version": "0.14.15"}])
    fails(resolve(world["clone"], world["cfg"]), "has no installPath")


@needs_jq
def test_install_path_directory_gone(world: dict[str, Path]) -> None:
    write_registry(world["cfg"], [user(world["base"] / "gone")])
    fails(resolve(world["clone"], world["cfg"]), "does not exist")


@needs_jq
def test_missing_target_file(world: dict[str, Path]) -> None:
    write_registry(world["cfg"], [user(world["user"])])
    result = resolve(world["clone"], world["cfg"], rel="git-hooks/pre-commit")
    fails(result, "git-hooks/pre-commit not found in the installed plugin")


@needs_jq
def test_invalid_registry_json(world: dict[str, Path]) -> None:
    reg = world["cfg"] / "plugins/installed_plugins.json"
    reg.write_text("{not json")
    fails(resolve(world["clone"], world["cfg"]), "is not valid JSON")


def test_outside_a_git_work_tree(tmp_path: Path) -> None:
    fails(resolve(tmp_path, tmp_path), "is not inside a git work tree")


def test_reasons_are_distinct() -> None:
    for reason in REASONS:
        assert [r for r in REASONS if r in reason] == [reason]
