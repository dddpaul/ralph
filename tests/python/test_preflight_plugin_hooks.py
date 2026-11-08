"""ralph-run preflight reports the migration to plugin hooks (TASK-300).

The report-only check names "not migrated", "partially migrated" and "shims
missing in this clone", and in a project whose marker sets ``pluginHooks`` it
says that plugin guards are best effort. It never changes the exit code.
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

from ralph import preflight

PLUGIN = REPO_ROOT / "plugins/ralph"
SHIM = PLUGIN / "skills/ralph-init/templates/shims/git-hook"
LEGACY_SETTINGS = REPO_ROOT / "tests/python/fixtures/legacy-claude-settings.json"
GUARDS = (
    "commit-msg-guard",
    "commit-prefix-guard",
    "master-branch-guard",
    "naming-guard",
    "notes-guard",
    "task-validator",
)
HOOK_NAMES = ("pre-commit", "commit-msg", "post-commit")
GUARD_COMMAND = '"$CLAUDE_PROJECT_DIR"/.claude/hooks/notes-guard.sh'


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def legacy_project(root: Path) -> Path:
    """A project wired the legacy way: guard copies, the legacy settings.json, git hook bodies in .git/hooks."""
    root.mkdir()
    git(root, "init", "-q", "-b", "master")
    (root / ".claude/hooks").mkdir(parents=True)
    for guard in (*GUARDS, "filename-length-guard"):
        shutil.copy2(PLUGIN / f"hooks/{guard}.sh", root / f".claude/hooks/{guard}.sh")
    shutil.copyfile(LEGACY_SETTINGS, root / ".claude/settings.json")
    for name in HOOK_NAMES:
        shutil.copyfile(PLUGIN / "git-hooks" / name, root / ".git/hooks" / name)
    return root


def migrated_project(root: Path) -> Path:
    """A project after the tracked and the clone part."""
    root.mkdir()
    git(root, "init", "-q", "-b", "master")
    (root / ".claude").mkdir()
    (root / ".claude/ralph.json").write_text('{"pluginHooks": true}\n')
    for name in HOOK_NAMES:
        shutil.copyfile(SHIM, root / ".git/hooks" / name)
    git(root, "config", "ralph.pluginHooks", "true")
    return root


def state(root: Path, switch: bool | None = None) -> list[str]:
    if switch is None:
        out = subprocess.run(
            ["git", "config", "--bool", "ralph.pluginHooks"], cwd=root, capture_output=True, text=True, check=False
        ).stdout.strip()
        switch = out == "true"
    return preflight.migration_state(root, root / ".git/hooks", switch)


def test_legacy_project_is_not_migrated(tmp_path: Path) -> None:
    found = state(legacy_project(tmp_path / "p"))
    assert len(found) == 1
    assert found[0].startswith("not migrated")


def test_migrated_clone_reports_only_best_effort(tmp_path: Path) -> None:
    found = state(migrated_project(tmp_path / "p"))
    assert len(found) == 1
    assert found[0].startswith("plugin guards are best effort")


def test_shimmed_clone_names_the_leftover_length_guard_copy_as_removable(tmp_path: Path) -> None:
    root = migrated_project(tmp_path / "p")
    (root / ".claude/hooks").mkdir()
    shutil.copy2(PLUGIN / "hooks/filename-length-guard.sh", root / ".claude/hooks/filename-length-guard.sh")
    leftover = [f for f in state(root) if f.startswith("leftover legacy copy")]
    assert len(leftover) == 1
    assert ".claude/hooks/filename-length-guard.sh is removable" in leftover[0]
    assert "tracked --retire-legacy" in leftover[0]


def test_leftover_copy_is_not_named_while_pre_commit_is_a_legacy_copy(tmp_path: Path) -> None:
    root = migrated_project(tmp_path / "p")
    (root / ".claude/hooks").mkdir()
    shutil.copy2(PLUGIN / "hooks/filename-length-guard.sh", root / ".claude/hooks/filename-length-guard.sh")
    shutil.copyfile(PLUGIN / "git-hooks/pre-commit", root / ".git/hooks/pre-commit")
    assert not any(f.startswith("leftover legacy copy") for f in state(root))


def test_marker_with_legacy_settings_entries_is_partially_migrated(tmp_path: Path) -> None:
    root = migrated_project(tmp_path / "p")
    (root / ".claude/settings.json").write_text(
        json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": GUARD_COMMAND}]}]}})
    )
    found = state(root)
    assert found[0].startswith("partially migrated")
    assert "legacy guard copies" in found[0]
    assert any("best effort" in f for f in found)


def test_a_local_guard_entry_is_not_legacy(tmp_path: Path) -> None:
    root = migrated_project(tmp_path / "p")
    (root / ".claude/ralph.json").write_text('{"pluginHooks": true, "localGuards": ["notes-guard"]}\n')
    (root / ".claude/settings.json").write_text(
        json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": GUARD_COMMAND}]}]}})
    )
    assert not any(f.startswith("partially migrated") for f in state(root))


def test_no_marker_with_missing_guard_copies_is_partially_migrated(tmp_path: Path) -> None:
    root = legacy_project(tmp_path / "p")
    (root / ".claude/hooks/notes-guard.sh").unlink()
    found = state(root)
    assert len(found) == 1
    assert found[0].startswith("partially migrated")
    assert "notes-guard" in found[0]


@pytest.mark.parametrize("gap", ["legacy-hook", "no-switch"])
def test_marker_without_the_clone_part_reports_shims_missing(tmp_path: Path, gap: str) -> None:
    root = migrated_project(tmp_path / "p")
    if gap == "legacy-hook":
        shutil.copyfile(PLUGIN / "git-hooks/commit-msg", root / ".git/hooks/commit-msg")
    else:
        git(root, "config", "--unset", "ralph.pluginHooks")
    found = state(root)
    missing = [f for f in found if f.startswith("shims missing in this clone")]
    assert len(missing) == 1
    assert ("commit-msg not the plugin shim" in missing[0]) == (gap == "legacy-hook")
    assert ("ralph.pluginHooks is not true" in missing[0]) == (gap == "no-switch")
    assert any("best effort" in f for f in found)


def test_an_earlier_shim_is_outdated_not_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = migrated_project(tmp_path / "p")
    old = SHIM.read_bytes() + b"# an earlier shim version\n"
    shipped = tmp_path / "shipped-git-hooks.sha256"
    shipped.write_text(
        (PLUGIN / "skills/ralph-init/scripts/shipped-git-hooks.sha256").read_text()
        + f"shim {hashlib.sha256(old).hexdigest()}\n"
    )
    monkeypatch.setattr(preflight, "_SHIPPED", shipped)
    for name in ("pre-commit", "post-commit"):
        (root / ".git/hooks" / name).write_bytes(old)
    found = state(root)
    outdated = [f for f in found if f.startswith("shims outdated in this clone")]
    expected = (
        "shims outdated in this clone — an earlier plugin shim in pre-commit, post-commit "
        f"(run bash {preflight._MIGRATE_SCRIPT} clone)"
    )
    assert outdated == [expected]
    assert not any(f.startswith("shims missing") for f in found)


def test_an_unlisted_shim_like_hook_is_still_missing(tmp_path: Path) -> None:
    root = migrated_project(tmp_path / "p")
    (root / ".git/hooks/commit-msg").write_bytes(SHIM.read_bytes() + b"# edited\n")
    found = state(root)
    assert not any(f.startswith("shims outdated") for f in found)
    assert any(f.startswith("shims missing in this clone — commit-msg not the plugin shim") for f in found)


def test_check_prints_warnings_and_reads_the_git_hooks_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = migrated_project(tmp_path / "p")
    git(root, "config", "core.hooksPath", "elsewhere")
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(root)
    preflight._check_plugin_hooks(False)
    err = capsys.readouterr().err
    assert "WARNING: plugin hooks: shims missing in this clone" in err
    assert "WARNING: plugin hooks: plugin guards are best effort" in err


def test_check_is_silent_outside_a_git_work_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    preflight._check_plugin_hooks(True)
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "skipped, not a git work tree" in captured.out


@pytest.mark.parametrize("shared", [True, False], ids=["enforcing", "not-enforcing"])
def test_check_names_the_autonomous_create_guard_as_best_effort(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], shared: bool
) -> None:
    root = migrated_project(tmp_path / "p")
    if shared:
        git(root, "config", "ralph.sharedBacklog", "true")
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(root)
    preflight._check_plugin_hooks(False)
    err = capsys.readouterr().err
    line = "WARNING: plugin hooks: autonomous task creation is refused"
    assert (line in err) == shared
    if shared:
        assert "best effort, not an absolute boundary" in err
