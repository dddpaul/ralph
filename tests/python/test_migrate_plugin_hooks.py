"""The tracked part of the migration to plugin-delivered hooks (TASK-299).

``migrate-plugin-hooks.sh tracked`` writes the marker first, then the
``.gitignore`` exception, then strips the managed ``settings.json`` entries, then
deletes the managed guard copies. The tests build a project the way ralph-init
Init does today (template guard copies, template ``settings.json``) plus
project-owned extras, and check what the run keeps, what it removes, that a
second run is a no-op, and — by stopping the run after every step through
``RALPH_MIGRATE_STOP_AFTER`` — that no interruption point leaves a template
registration that neither the plugin dispatcher nor a legacy copy enforces.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT

SCRIPT = REPO_ROOT / "plugins/ralph/skills/ralph-init/scripts/migrate-plugin-hooks.sh"
PLUGIN_HOOKS = REPO_ROOT / "plugins/ralph/hooks"
TEMPLATES = REPO_ROOT / "plugins/ralph/skills/ralph-init/templates"
SETTINGS = TEMPLATES / "claude/settings.json"
MANAGED = (
    "commit-msg-guard",
    "commit-prefix-guard",
    "master-branch-guard",
    "naming-guard",
    "notes-guard",
    "task-validator",
)
LEGACY_COMMAND = re.compile(r'\A"\$CLAUDE_PROJECT_DIR"/\.claude/hooks/([a-z-]+)\.sh\Z')
BASH = shutil.which("bash") or "/bin/bash"
OWN_HOOK = {
    "type": "command",
    "command": '"$CLAUDE_PROJECT_DIR"/.claude/hooks/own-check.sh',
}
STOP_POINTS = ("marker", "gitignore", "settings", *(f"hooks:{g}" for g in MANAGED))
NOTES_PAYLOAD = {
    "tool_name": "Bash",
    "tool_input": {"command": "backlog task edit 1 --notes x"},
}


def git(cwd: Path, *args: str) -> str:
    """Run git in ``cwd`` and return its stripped stdout."""
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def make_project(path: Path, *, extras: bool = True) -> Path:
    """Create a git repo bootstrapped with the legacy template guard wiring and return its canonical root.

    With ``extras`` it also carries a project-owned hook script and its
    registration, a ``permissions`` key in ``settings.json``, and an existing
    marker key.
    """
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "master")
    hooks = path / ".claude/hooks"
    hooks.mkdir(parents=True)
    for template in (TEMPLATES / "claude/hooks").iterdir():
        target = hooks / template.name
        shutil.copyfile(template, target)
        target.chmod(0o755)
    settings = json.loads(SETTINGS.read_text())
    if extras:
        (hooks / "own-check.sh").write_text("#!/bin/bash\nexit 0\n")
        (hooks / "own-check.sh").chmod(0o755)
        settings["hooks"]["PreToolUse"][0]["hooks"].append(OWN_HOOK)
        settings["hooks"]["SessionStart"] = [{"hooks": [dict(OWN_HOOK)]}]
        settings["permissions"] = {"allow": ["Bash(make:*)"]}
        (path / ".claude/ralph.json").write_text(json.dumps({"checks": "make check"}))
    (path / ".claude/settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    (path / ".gitignore").write_text(
        ".claude/*\n!.claude/settings.json\n!.claude/hooks/"
    )
    return path.resolve()


def migrate(
    root: Path, *args: str, stop_after: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``migrate-plugin-hooks.sh tracked <args> <root>`` from an unrelated cwd."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("CLAUDE_PLUGIN_ROOT", "RALPH_MIGRATE_STOP_AFTER")
    }
    if stop_after:
        env["RALPH_MIGRATE_STOP_AFTER"] = stop_after
    return subprocess.run(
        [BASH, str(SCRIPT), "tracked", *args, str(root)],
        cwd=root.parent,
        env=env,
        capture_output=True,
        text=True,
    )


def snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    """Every file under ``root`` outside ``.git``, with its bytes and mode."""
    return {
        str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mode)
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts[:1]
    }


def registrations(path: Path) -> list[tuple[str, str, str | None, str]]:
    """(event, matcher, if, command) for every hook command in a settings-shaped file."""
    if not path.exists():
        return []
    return [
        (event, group.get("matcher", ""), hook.get("if"), hook["command"])
        for event, groups in json.loads(path.read_text()).get("hooks", {}).items()
        for group in groups
        for hook in group.get("hooks", [])
    ]


def plugin_enforces(root: Path, guard: str) -> bool:
    """True when the dispatcher's gate (run.sh) is open for ``guard`` in this project."""
    marker = root / ".claude/ralph.json"
    if not marker.exists():
        return False
    data = json.loads(marker.read_text())
    return data.get("pluginHooks") is True and guard not in data.get("localGuards", [])


def legacy_enforces(
    root: Path, event: str, matcher: str, cond: str | None, guard: str
) -> bool:
    """True when the project still registers this template entry and its guard copy exists."""
    command = f'"$CLAUDE_PROJECT_DIR"/.claude/hooks/{guard}.sh'
    return (event, matcher, cond, command) in registrations(
        root / ".claude/settings.json"
    ) and (root / f".claude/hooks/{guard}.sh").is_file()


def assert_every_guard_enforced(root: Path) -> None:
    """Every template registration is covered by the plugin gate or by its legacy copy."""
    for event, matcher, cond, command in registrations(SETTINGS):
        match = LEGACY_COMMAND.match(command)
        assert match, command
        guard = match.group(1)
        assert plugin_enforces(root, guard) or legacy_enforces(
            root, event, matcher, cond, guard
        ), (
            f"{guard} ({event} {matcher} {cond}) is enforced by neither the plugin nor a legacy copy"
        )


def notes_guard_denies(root: Path) -> bool:
    """Run every wiring that would fire for a ``--notes`` edit and report whether one denies it."""
    payload = json.dumps({**NOTES_PAYLOAD, "cwd": str(root)})
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
    env.pop("RALPH_PROJECT_ROOT", None)
    commands = [f'"{PLUGIN_HOOKS}/run.sh" notes-guard']
    commands += [
        c
        for _e, _m, cond, c in registrations(root / ".claude/settings.json")
        if cond == "Bash(backlog task edit *)"
    ]
    for command in commands:
        result = subprocess.run(
            [BASH, "-c", command],
            input=payload,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
        )
        if '"deny"' in result.stdout:
            return True
    return False


# --------------------------------------------------------------------------
# A full run
# --------------------------------------------------------------------------


def test_full_run_moves_the_managed_guards_to_the_plugin(tmp_path: Path) -> None:
    root = make_project(tmp_path / "proj")
    result = migrate(root)
    assert result.returncode == 0, result.stderr
    marker = json.loads((root / ".claude/ralph.json").read_text())
    assert marker == {"checks": "make check", "pluginHooks": True}
    for guard in MANAGED:
        assert not (root / f".claude/hooks/{guard}.sh").exists()
    commands = [c for *_rest, c in registrations(root / ".claude/settings.json")]
    assert commands == [OWN_HOOK["command"], OWN_HOOK["command"]]
    settings = json.loads((root / ".claude/settings.json").read_text())
    assert settings["permissions"] == {"allow": ["Bash(make:*)"]}
    assert set(settings["hooks"]) == {"PreToolUse", "SessionStart"}
    assert [g["matcher"] for g in settings["hooks"]["PreToolUse"]] == ["Bash"]
    assert (root / ".claude/hooks/own-check.sh").read_text() == "#!/bin/bash\nexit 0\n"
    assert (root / ".claude/hooks/filename-length-guard.sh").exists()
    assert_every_guard_enforced(root)
    assert notes_guard_denies(root)


def test_gitignore_exception_makes_the_marker_committable(tmp_path: Path) -> None:
    root = make_project(tmp_path / "proj")
    assert migrate(root).returncode == 0
    lines = (root / ".gitignore").read_text().splitlines()
    assert lines == [
        ".claude/*",
        "!.claude/settings.json",
        "!.claude/hooks/",
        "!.claude/ralph.json",
    ]
    git(root, "add", "-A")
    assert (
        ".claude/ralph.json"
        in git(root, "diff", "--cached", "--name-only").splitlines()
    )


def test_gitignore_is_created_when_missing(tmp_path: Path) -> None:
    root = make_project(tmp_path / "proj")
    (root / ".gitignore").unlink()
    assert migrate(root).returncode == 0
    assert (root / ".gitignore").read_text() == "!.claude/ralph.json\n"


def test_settings_json_left_empty_is_deleted(tmp_path: Path) -> None:
    root = make_project(tmp_path / "proj", extras=False)
    result = migrate(root)
    assert result.returncode == 0, result.stderr
    assert not (root / ".claude/settings.json").exists()
    assert "removed 13 managed hook entries" in result.stdout
    assert json.loads((root / ".claude/ralph.json").read_text()) == {
        "pluginHooks": True
    }
    assert sorted(p.name for p in (root / ".claude/hooks").iterdir()) == [
        "filename-length-guard.sh"
    ]
    assert_every_guard_enforced(root)


def test_the_run_commits_nothing(tmp_path: Path) -> None:
    root = make_project(tmp_path / "proj")
    git(root, "add", "-A")
    git(
        root,
        "-c",
        "user.email=t@example.com",
        "-c",
        "user.name=T",
        "commit",
        "-q",
        "-m",
        "init",
    )
    head = git(root, "rev-parse", "HEAD")
    assert migrate(root).returncode == 0
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "diff", "--cached", "--name-only") == ""


# --------------------------------------------------------------------------
# Local guards
# --------------------------------------------------------------------------


def test_local_guards_keep_their_files_and_registrations(tmp_path: Path) -> None:
    root = make_project(tmp_path / "proj")
    result = migrate(root, "--local-guards", "notes-guard,naming-guard")
    assert result.returncode == 0, result.stderr
    marker = json.loads((root / ".claude/ralph.json").read_text())
    assert marker["localGuards"] == ["notes-guard", "naming-guard"]
    for guard in ("notes-guard", "naming-guard"):
        copy = root / f".claude/hooks/{guard}.sh"
        assert (
            copy.read_bytes() == (TEMPLATES / f"claude/hooks/{guard}.sh").read_bytes()
        )
    kept = {
        LEGACY_COMMAND.match(c).group(1)
        for *_r, c in registrations(root / ".claude/settings.json")
        if LEGACY_COMMAND.match(c)
    }
    assert kept == {"notes-guard", "naming-guard", "own-check"}
    template_rows = [
        r
        for r in registrations(SETTINGS)
        if "notes-guard" in r[3] or "naming-guard" in r[3]
    ]
    assert set(template_rows) <= set(registrations(root / ".claude/settings.json"))
    assert_every_guard_enforced(root)
    assert notes_guard_denies(root)


def test_local_guards_merge_with_the_existing_marker_list(tmp_path: Path) -> None:
    root = make_project(tmp_path / "proj")
    (root / ".claude/ralph.json").write_text(
        json.dumps(
            {
                "pluginHooks": False,
                "localGuards": ["task-validator"],
                "sharedBacklog": True,
            }
        )
    )
    assert (
        migrate(
            root, "--local-guards", "notes-guard", "--local-guards=task-validator"
        ).returncode
        == 0
    )
    marker = json.loads((root / ".claude/ralph.json").read_text())
    assert marker == {
        "pluginHooks": True,
        "localGuards": ["task-validator", "notes-guard"],
        "sharedBacklog": True,
    }
    assert (root / ".claude/hooks/task-validator.sh").exists()
    assert (root / ".claude/hooks/notes-guard.sh").exists()
    assert not (root / ".claude/hooks/naming-guard.sh").exists()


def test_a_local_guard_without_a_copy_is_reported(tmp_path: Path) -> None:
    root = make_project(tmp_path / "proj")
    (root / ".claude/hooks/notes-guard.sh").unlink()
    result = migrate(root, "--local-guards", "notes-guard")
    assert result.returncode == 0
    assert (
        "local guard notes-guard has no .claude/hooks/notes-guard.sh copy"
        in result.stderr
    )


def test_a_customised_copy_is_reported_when_deleted(tmp_path: Path) -> None:
    root = make_project(tmp_path / "proj")
    (root / ".claude/hooks/naming-guard.sh").write_text(
        "#!/bin/bash\n# project tweak\n"
    )
    result = migrate(root)
    assert result.returncode == 0
    assert (
        "deleted .claude/hooks/naming-guard.sh (it differed from the plugin's copy"
        in result.stdout
    )
    assert "deleted .claude/hooks/notes-guard.sh\n" in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["bogus"],
        ["tracked", "--local-guards"],
        ["tracked", "--local-guards", "own-check"],
        ["tracked", "--x"],
        ["clone"],
    ],
    ids=[
        "no-subcommand",
        "unknown-subcommand",
        "missing-list",
        "unmanaged-guard",
        "unknown-flag",
        "clone-not-here",
    ],
)
def test_usage_errors_exit_2_and_touch_nothing(tmp_path: Path, args: list[str]) -> None:
    root = make_project(tmp_path / "proj")
    before = snapshot(root)
    result = subprocess.run(
        [BASH, str(SCRIPT), *args], cwd=root, capture_output=True, text=True
    )
    assert result.returncode == 2
    assert snapshot(root) == before


@pytest.mark.parametrize("bad", ["marker", "marker-locals", "settings"])
def test_malformed_json_stops_before_any_write(tmp_path: Path, bad: str) -> None:
    root = make_project(tmp_path / "proj")
    if bad == "marker":
        (root / ".claude/ralph.json").write_text("{not json")
    elif bad == "marker-locals":
        (root / ".claude/ralph.json").write_text('{"localGuards": "notes-guard"}')
    else:
        (root / ".claude/settings.json").write_text("[]")
    before = snapshot(root)
    result = migrate(root)
    assert result.returncode == 2
    assert "fix it by hand" in result.stderr
    assert snapshot(root) == before


def test_not_a_git_repository_exits_2(tmp_path: Path) -> None:
    (tmp_path / "plain").mkdir()
    assert migrate(tmp_path / "plain").returncode == 2


# --------------------------------------------------------------------------
# Idempotence and interruption
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "args", [[], ["--local-guards", "notes-guard"]], ids=["plain", "local-guards"]
)
def test_a_second_run_changes_nothing(tmp_path: Path, args: list[str]) -> None:
    root = make_project(tmp_path / "proj")
    assert migrate(root, *args).returncode == 0
    after_first = snapshot(root)
    second = migrate(root, *args)
    assert second.returncode == 0
    assert second.stdout == "tracked: nothing to change\n"
    assert snapshot(root) == after_first


def test_a_compact_marker_already_migrated_is_left_byte_for_byte(
    tmp_path: Path,
) -> None:
    root = make_project(tmp_path / "proj", extras=False)
    assert migrate(root).returncode == 0
    (root / ".claude/ralph.json").write_text('{"pluginHooks":true}')
    assert migrate(root).stdout == "tracked: nothing to change\n"
    assert (root / ".claude/ralph.json").read_text() == '{"pluginHooks":true}'


@pytest.mark.parametrize("stop", STOP_POINTS)
@pytest.mark.parametrize(
    "args", [[], ["--local-guards", "notes-guard"]], ids=["plain", "local-guards"]
)
def test_every_interruption_point_still_enforces(
    tmp_path: Path, stop: str, args: list[str]
) -> None:
    if stop == "hooks:notes-guard" and args:
        pytest.skip(
            "a local guard's copy is never deleted, so this step does not exist"
        )
    root = make_project(tmp_path / "proj")
    assert_every_guard_enforced(root)
    interrupted = migrate(root, *args, stop_after=stop)
    assert interrupted.returncode == 3, interrupted.stderr
    assert f"stopped after {stop}" in interrupted.stderr
    assert_every_guard_enforced(root)
    assert notes_guard_denies(root)
    resumed = migrate(root, *args)
    assert resumed.returncode == 0, resumed.stderr
    reference = make_project(tmp_path / "reference")
    assert migrate(reference, *args).returncode == 0
    assert snapshot(root) == snapshot(reference)
