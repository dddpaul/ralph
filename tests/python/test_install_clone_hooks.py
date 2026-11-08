"""This repo's per-clone git hook installer and its SessionStart check (TASK-331).

``.claude/hooks/install-clone-hooks.sh`` installs the TASK-214 version-bump
wrapper (as ``pre-push.local`` behind the plugin shim, or as ``pre-push`` in a
clone without one) and the TASK-217 bump nudge (as ``post-commit.local`` behind
the shim). ``--check`` changes nothing and reports. The SessionStart hook
``clone-hooks-session-check.sh`` turns a failed check into one line of
``hookSpecificOutput.additionalContext``. The tests run both against temporary
clones whose hooks dir starts out the way ``migrate-plugin-hooks.sh clone``
leaves it.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT

INSTALLER = REPO_ROOT / ".claude/hooks/install-clone-hooks.sh"
SESSION_CHECK = REPO_ROOT / ".claude/hooks/clone-hooks-session-check.sh"
SHIM = REPO_ROOT / "plugins/ralph/skills/ralph-init/templates/shims/git-hook"
OLD_SHIM = REPO_ROOT / "tests/python/fixtures/shipped-git-hooks/git-hook-shim.v0.25.10"
WRAPPER = """#!/bin/bash
# pre-push wrapper (TASK-214). Standard hook location, so any other pre-push
# tooling keeps working. Delegates to the tracked, reviewable guard — nothing
# under .git/ is committable, so the guard SOURCE lives in .claude/hooks/ and
# this wrapper is installed once.
exec "$(git rev-parse --show-toplevel)/.claude/hooks/version-bump-guard.sh" "$@"
"""


def make_clone(
    tmp_path: Path, *, pre_push_shim: bool = True, post_commit_shim: bool = True
) -> Path:
    """A git repo with the plugin shim installed under the chosen hook names; return its root."""
    root = tmp_path / "clone"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "master"], cwd=root, check=True)
    hooks = root / ".git/hooks"
    for name, wanted in (
        ("pre-push", pre_push_shim),
        ("post-commit", post_commit_shim),
    ):
        if wanted:
            (hooks / name).write_bytes(SHIM.read_bytes())
            (hooks / name).chmod(0o755)
    return root


def run(
    script: Path, cwd: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``script`` in ``cwd`` and capture its output."""
    return subprocess.run(
        [str(script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def snapshot(hooks: Path) -> dict[str, tuple[bytes, int]]:
    """Content and mode of every non-sample file in ``hooks``."""
    return {
        p.name: (p.read_bytes(), p.stat().st_mode)
        for p in sorted(hooks.iterdir())
        if not p.name.endswith(".sample")
    }


def test_installs_behind_the_shims(tmp_path: Path) -> None:
    root = make_clone(tmp_path)
    result = run(INSTALLER, root)
    assert result.returncode == 0, result.stderr
    hooks = root / ".git/hooks"
    assert (hooks / "pre-push.local").read_text() == WRAPPER
    assert (hooks / "pre-push").read_bytes() == SHIM.read_bytes()
    assert (hooks / "pre-push.local").stat().st_mode & 0o777 == 0o755
    nudge = (hooks / "post-commit.local").read_text()
    assert '"$BUMP_HELPER" --nudge || true' in nudge
    assert '[ -x "$BUMP_HELPER" ]' in nudge
    assert nudge.rstrip().endswith("exit 0")
    assert (hooks / "post-commit.local").stat().st_mode & 0o777 == 0o755


def test_installs_wrapper_as_pre_push_when_absent(tmp_path: Path) -> None:
    root = make_clone(tmp_path, pre_push_shim=False)
    result = run(INSTALLER, root)
    assert result.returncode == 0, result.stderr
    hooks = root / ".git/hooks"
    assert (hooks / "pre-push").read_text() == WRAPPER
    assert not (hooks / "pre-push.local").exists()
    assert run(INSTALLER, root, "--check").returncode == 0


def test_nudge_matches_this_clone(tmp_path: Path) -> None:
    """The nudge is byte for byte the hand-installed one, where this clone has it."""
    local = REPO_ROOT / ".git/hooks/post-commit.local"
    if not local.is_file():
        pytest.skip("this clone has no post-commit.local")
    root = make_clone(tmp_path)
    run(INSTALLER, root)
    assert (root / ".git/hooks/post-commit.local").read_bytes() == local.read_bytes()


def test_installed_wrapper_runs_the_guard(tmp_path: Path) -> None:
    root = make_clone(tmp_path, pre_push_shim=False)
    run(INSTALLER, root)
    guard = root / ".claude/hooks/version-bump-guard.sh"
    guard.parent.mkdir(parents=True)
    guard.write_text('#!/bin/bash\necho "guard $*"\nexit 7\n')
    guard.chmod(0o755)
    result = subprocess.run(
        [str(root / ".git/hooks/pre-push"), "origin", "url"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode, result.stdout) == (7, "guard origin url\n")


def test_second_run_changes_nothing(tmp_path: Path) -> None:
    root = make_clone(tmp_path)
    assert run(INSTALLER, root).returncode == 0
    before = snapshot(root / ".git/hooks")
    result = run(INSTALLER, root)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "" and result.stderr == ""
    assert snapshot(root / ".git/hooks") == before


@pytest.mark.parametrize("name", ["pre-push.local", "post-commit.local"])
def test_differing_local_hook_left_untouched(tmp_path: Path, name: str) -> None:
    root = make_clone(tmp_path)
    hooks = root / ".git/hooks"
    (hooks / name).write_text("#!/bin/sh\necho mine\n")
    (hooks / name).chmod(0o700)
    before = (hooks / name).read_bytes(), (hooks / name).stat().st_mode
    result = run(INSTALLER, root)
    assert result.returncode != 0
    assert name in result.stderr and "differs" in result.stderr
    assert ((hooks / name).read_bytes(), (hooks / name).stat().st_mode) == before
    other = "post-commit.local" if name == "pre-push.local" else "pre-push.local"
    assert (hooks / other).is_file(), "the other hook is still installed"


def test_foreign_pre_push_left_untouched(tmp_path: Path) -> None:
    root = make_clone(tmp_path, pre_push_shim=False)
    hook = root / ".git/hooks/pre-push"
    hook.write_text("#!/bin/sh\nexit 0\n")
    hook.chmod(0o755)
    result = run(INSTALLER, root)
    assert result.returncode != 0
    assert str(Path(".git/hooks/pre-push")) + ":" in result.stderr
    assert hook.read_text() == "#!/bin/sh\nexit 0\n"
    assert not (root / ".git/hooks/pre-push.local").exists()


def test_post_commit_not_shim_is_refused(tmp_path: Path) -> None:
    root = make_clone(tmp_path, post_commit_shim=False)
    result = run(INSTALLER, root)
    assert result.returncode != 0
    assert (
        "post-commit" in result.stderr
        and "migrate-plugin-hooks.sh clone" in result.stderr
    )
    assert not (root / ".git/hooks/post-commit.local").exists()
    assert not (root / ".git/hooks/post-commit").exists()


def test_check_passes_when_in_place(tmp_path: Path) -> None:
    root = make_clone(tmp_path)
    run(INSTALLER, root)
    before = snapshot(root / ".git/hooks")
    result = run(INSTALLER, root, "--check")
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
    assert snapshot(root / ".git/hooks") == before


def test_check_accepts_an_earlier_recorded_shim(tmp_path: Path) -> None:
    root = make_clone(tmp_path)
    run(INSTALLER, root)
    hooks = root / ".git/hooks"
    for name in ("pre-push", "post-commit"):
        (hooks / name).write_bytes(OLD_SHIM.read_bytes())
    result = run(INSTALLER, root, "--check")
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def test_check_refuses_an_unrecorded_shim_like_pre_push(tmp_path: Path) -> None:
    root = make_clone(tmp_path)
    run(INSTALLER, root)
    hooks = root / ".git/hooks"
    (hooks / "pre-push").write_bytes(SHIM.read_bytes() + b"# edited\n")
    result = run(INSTALLER, root, "--check")
    assert result.returncode != 0
    assert "pre-push: differs" in result.stderr


def test_check_names_each_missing_hook_and_changes_nothing(tmp_path: Path) -> None:
    root = make_clone(tmp_path)
    before = snapshot(root / ".git/hooks")
    result = run(INSTALLER, root, "--check")
    assert result.returncode != 0
    lines = result.stderr.splitlines()
    assert len(lines) == 2
    assert any("pre-push.local: missing" in line for line in lines)
    assert any("post-commit.local: missing" in line for line in lines)
    assert snapshot(root / ".git/hooks") == before


def test_check_names_differing_and_non_executable_hooks(tmp_path: Path) -> None:
    root = make_clone(tmp_path)
    run(INSTALLER, root)
    hooks = root / ".git/hooks"
    (hooks / "pre-push.local").write_text(WRAPPER + "# edited\n")
    (hooks / "post-commit.local").chmod(0o644)
    result = run(INSTALLER, root, "--check")
    assert result.returncode != 0
    assert "pre-push.local: differs" in result.stderr
    assert "post-commit.local: is not executable" in result.stderr


def session_env(root: Path) -> dict[str, str]:
    """Environment for the SessionStart hook, as Claude Code sets it."""
    return {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}


def test_session_check_silent_when_in_place(tmp_path: Path) -> None:
    root = make_clone(tmp_path)
    run(INSTALLER, root)
    result = run(SESSION_CHECK, tmp_path, env=session_env(root))
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def test_session_check_reports_missing_hooks(tmp_path: Path) -> None:
    root = make_clone(tmp_path)
    before = snapshot(root / ".git/hooks")
    result = run(SESSION_CHECK, tmp_path, env=session_env(root))
    assert result.returncode == 0
    assert result.stdout.count("\n") == 1
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    context = out["additionalContext"]
    assert "\n" not in context
    assert (
        "pre-push.local: missing" in context and "post-commit.local: missing" in context
    )
    assert ".claude/hooks/install-clone-hooks.sh" in context
    assert snapshot(root / ".git/hooks") == before


def test_session_check_escapes_json(tmp_path: Path) -> None:
    root = make_clone(tmp_path)
    hooks = tmp_path / 'odd"dir\\name'
    hooks.mkdir()
    (hooks / "pre-push").write_bytes(SHIM.read_bytes())
    (hooks / "post-commit").write_bytes(SHIM.read_bytes())
    subprocess.run(
        ["git", "config", "core.hooksPath", str(hooks)], cwd=root, check=True
    )
    result = run(SESSION_CHECK, tmp_path, env=session_env(root))
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert f"{hooks}/pre-push.local: missing" in context


def test_settings_registers_session_check() -> None:
    settings = json.loads((REPO_ROOT / ".claude/settings.json").read_text())
    commands = [
        h["command"]
        for entry in settings["hooks"]["SessionStart"]
        for h in entry["hooks"]
    ]
    assert (
        '"$CLAUDE_PROJECT_DIR"/.claude/hooks/clone-hooks-session-check.sh' in commands
    )
