"""The Claude guard hooks shipped as plugin hooks behind a marker gate (TASK-296).

``plugins/ralph/hooks/hooks.json`` carries the same entries and ``if:`` filters
as the legacy ``settings.json`` older ralph-init versions wrote (kept as
``fixtures/legacy-claude-settings.json``), but every entry calls the
dispatcher ``run.sh <guard>``. The dispatcher acts only when the tracked marker
``.claude/ralph.json`` at the session's git root has ``"pluginHooks": true`` and
does not list the guard in ``localGuards``. The behaviour tests copy ``run.sh``
next to a probe guard that records what it was given, so the gate, the input,
the cwd, ``RALPH_PROJECT_ROOT`` and the exit code are all observable. The
legacy side is pinned too: this repo's live copies stay byte-identical to the
plugin, and the plugin's guards still block when wired the old way.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from devcontainer_config import REPO_ROOT

PLUGIN_HOOKS = REPO_ROOT / "plugins/ralph/hooks"
DISPATCHER = PLUGIN_HOOKS / "run.sh"
SETTINGS = REPO_ROOT / "tests/python/fixtures/legacy-claude-settings.json"
GUARDS = (
    "commit-msg-guard",
    "commit-prefix-guard",
    "master-branch-guard",
    "naming-guard",
    "notes-guard",
    "task-validator",
    "filename-length-guard",
)
PLUGIN_COMMAND = re.compile(r'\A"\$\{CLAUDE_PLUGIN_ROOT\}"/hooks/run\.sh ([a-z-]+)\Z')
# The one guard hooks.json calls directly, outside the marker gate (TASK-316).
UNGATED = "autonomous-create-guard"
UNGATED_COMMAND = f'"${{CLAUDE_PLUGIN_ROOT}}"/hooks/{UNGATED}.sh'
LEGACY_COMMAND = re.compile(r'\A"\$CLAUDE_PROJECT_DIR"/\.claude/hooks/([a-z-]+)\.sh\Z')
# The commit guards dispatch on any git / gh command: a literal "git commit *" or
# "gh pr create *" filter never fires for git -c k=v commit / git -C dir commit or
# gh -R o/r pr create / gh pr -R o/r create, and the guards' own lexer keeps the
# other git and gh commands cheap and allowed.
WIDENED_FILTERS = {"Bash(git commit *)": "Bash(git *)", "Bash(gh pr create *)": "Bash(gh *)"}
BASH = shutil.which("bash") or "/bin/bash"
PROBE = """#!/bin/bash
out=${PROBE_OUT:?}
cat > "$out/stdin"
pwd -P > "$out/cwd"
printf '%s' "${RALPH_PROJECT_ROOT-unset}" > "$out/root"
echo "probe stderr" >&2
exit "${PROBE_EXIT:-0}"
"""


def entries(
    path: Path, pattern: re.Pattern[str]
) -> list[tuple[str, str, str | None, str]]:
    """Return (event, matcher, if, guard) for every hook command in a settings-shaped file."""
    rows = []
    for event, groups in json.loads(path.read_text())["hooks"].items():
        for group in groups:
            for hook in group["hooks"]:
                if hook["command"] == UNGATED_COMMAND:
                    continue
                match = pattern.match(hook["command"])
                assert match, f"unexpected command shape in {path}: {hook['command']}"
                rows.append(
                    (event, group.get("matcher", ""), hook.get("if"), match.group(1))
                )
    return rows


def git(cwd: Path, *args: str) -> str:
    """Run git in ``cwd`` and return its stripped stdout."""
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def make_repo(path: Path, branch: str = "master") -> Path:
    """Create a git repository with one empty commit on ``branch`` and return its canonical path."""
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", branch)
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "user.name", "Test")
    git(path, "commit", "-q", "--allow-empty", "-m", "init")
    return path.resolve()


def write_marker(root: Path, marker: Any) -> None:
    """Write ``root/.claude/ralph.json``; a str is written verbatim, anything else as JSON."""
    (root / ".claude").mkdir(exist_ok=True)
    text = marker if isinstance(marker, str) else json.dumps(marker)
    (root / ".claude/ralph.json").write_text(text)


def base_env(**extra: str) -> dict[str, str]:
    """Return the current environment without the project variables, plus ``extra``."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("RALPH_PROJECT_ROOT", "CLAUDE_PROJECT_DIR")
    }
    env.update(extra)
    return env


@pytest.fixture
def probe_hooks(tmp_path: Path) -> Path:
    """A hooks dir holding a copy of the real dispatcher and an executable ``probe`` guard."""
    hooks = tmp_path / "plugin/hooks"
    hooks.mkdir(parents=True)
    shutil.copy2(DISPATCHER, hooks / "run.sh")
    (hooks / "probe.sh").write_text(PROBE)
    (hooks / "probe.sh").chmod(0o755)
    return hooks


def dispatch(
    hooks: Path,
    guard: str,
    project_dir: Path,
    payload: str,
    run_cwd: Path,
    **extra: str,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Run ``run.sh <guard>`` with CLAUDE_PROJECT_DIR set; return the result and the probe's output dir."""
    out = run_cwd.parent / f"probe-out-{len(list(run_cwd.parent.glob('probe-out-*')))}"
    out.mkdir()
    env = base_env(CLAUDE_PROJECT_DIR=str(project_dir), PROBE_OUT=str(out), **extra)
    result = subprocess.run(
        [BASH, str(hooks / "run.sh"), guard],
        input=payload,
        cwd=run_cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, out


def payload_for(cwd: Path, **tool_input: str) -> str:
    """A hook payload with ``cwd`` and ``tool_input``, ending in a newline."""
    return json.dumps({"cwd": str(cwd), "tool_input": tool_input}) + "\n"


# --------------------------------------------------------------------------
# Layout, wiring and parity
# --------------------------------------------------------------------------


# This repo keeps copies of its six local guards only; the length guard runs from the plugin.
@pytest.mark.parametrize("guard", [g for g in GUARDS if g != "filename-length-guard"])
def test_guard_copies_are_byte_identical_to_the_plugin(guard: str) -> None:
    plugin = PLUGIN_HOOKS / f"{guard}.sh"
    assert os.access(plugin, os.X_OK), f"{plugin} is not executable"
    copy = REPO_ROOT / f".claude/hooks/{guard}.sh"
    assert copy.read_bytes() == plugin.read_bytes(), f"{copy} drifted from {plugin}"


def test_hooks_json_carries_the_legacy_entries_and_filters() -> None:
    plugin = entries(PLUGIN_HOOKS / "hooks.json", PLUGIN_COMMAND)
    legacy = [
        (event, matcher, WIDENED_FILTERS.get(cond or "", cond), guard)
        for event, matcher, cond, guard in entries(SETTINGS, LEGACY_COMMAND)
    ]
    assert len(legacy) == 13
    assert plugin[: len(legacy)] == legacy


def test_live_settings_match_hooks_json_filters() -> None:
    # The SessionStart clone-hooks check (TASK-331) is this repo's own, not a plugin guard.
    live = [
        row
        for row in entries(REPO_ROOT / ".claude/settings.json", LEGACY_COMMAND)
        if row[3] != "clone-hooks-session-check"
    ]
    plugin = entries(PLUGIN_HOOKS / "hooks.json", PLUGIN_COMMAND)
    assert live == plugin[: len(live)]
    assert ("PreToolUse", "Bash", "Bash(git *)", "commit-prefix-guard") in live
    assert ("PreToolUse", "Bash", "Bash(git *)", "commit-msg-guard") in live
    assert ("PreToolUse", "Bash", "Bash(gh *)", "commit-msg-guard") in live


def test_the_ungated_guard_is_wired_directly_for_bash_and_skill() -> None:
    groups = json.loads((PLUGIN_HOOKS / "hooks.json").read_text())["hooks"]["PreToolUse"]
    direct = [
        (group["matcher"], hook.get("if"))
        for group in groups
        for hook in group["hooks"]
        if hook["command"] == UNGATED_COMMAND
    ]
    assert direct == [("Bash|Skill", None)]
    assert os.access(PLUGIN_HOOKS / f"{UNGATED}.sh", os.X_OK)


def test_every_hooks_json_entry_names_an_existing_executable() -> None:
    rows = entries(PLUGIN_HOOKS / "hooks.json", PLUGIN_COMMAND)
    assert rows
    assert os.access(DISPATCHER, os.X_OK)
    for _event, _matcher, _if, guard in rows:
        assert os.access(PLUGIN_HOOKS / f"{guard}.sh", os.X_OK), (
            f"hooks.json names a missing guard: {guard}"
        )


# --------------------------------------------------------------------------
# The dispatcher's marker gate
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "marker",
    [
        None,
        {},
        {"pluginHooks": False},
        {"pluginHooks": "true"},
        {"sharedBacklog": True},
    ],
    ids=["absent", "empty", "false", "string-true", "other-key-only"],
)
def test_gate_closed_exits_zero_without_running_the_guard(
    probe_hooks: Path, tmp_path: Path, marker: Any
) -> None:
    root = make_repo(tmp_path / "proj")
    if marker is not None:
        write_marker(root, marker)
    result, out = dispatch(probe_hooks, "probe", root, payload_for(root), root)
    assert result.returncode == 0
    assert result.stdout == result.stderr == ""
    assert not (out / "stdin").exists()


def test_gate_open_passes_input_cwd_and_root(probe_hooks: Path, tmp_path: Path) -> None:
    root = make_repo(tmp_path / "proj")
    write_marker(root, {"pluginHooks": True})
    sub = root / "sub"
    sub.mkdir()
    payload = payload_for(sub, command="git status") + "\n"
    result, out = dispatch(
        probe_hooks, "probe", root, payload, tmp_path, RALPH_PROJECT_ROOT="/stale"
    )
    assert result.returncode == 0
    assert (out / "stdin").read_text() == payload
    assert (out / "cwd").read_text().strip() == str(sub)
    assert (out / "root").read_text() == str(root)


@pytest.mark.parametrize(
    ("local_guards", "runs"),
    [
        (["probe"], False),
        (["notes-guard", "probe"], False),
        (["notes-guard"], True),
        ([], True),
        ("probe", True),
    ],
    ids=["listed", "listed-second", "other-listed", "empty", "not-an-array"],
)
def test_local_guards_skip_only_the_listed_guard(
    probe_hooks: Path, tmp_path: Path, local_guards: Any, runs: bool
) -> None:
    root = make_repo(tmp_path / "proj")
    write_marker(root, {"pluginHooks": True, "localGuards": local_guards})
    result, out = dispatch(probe_hooks, "probe", root, payload_for(root), root)
    assert result.returncode == 0
    assert (out / "stdin").exists() is runs


def test_subdirectory_session_finds_the_root_marker(
    probe_hooks: Path, tmp_path: Path
) -> None:
    root = make_repo(tmp_path / "proj")
    write_marker(root, {"pluginHooks": True})
    sub = root / "a/b"
    sub.mkdir(parents=True)
    result, out = dispatch(probe_hooks, "probe", sub, payload_for(sub), sub)
    assert result.returncode == 0
    assert (out / "root").read_text() == str(root)


def test_nested_repository_is_not_crossed(probe_hooks: Path, tmp_path: Path) -> None:
    outer = make_repo(tmp_path / "outer")
    write_marker(outer, {"pluginHooks": True})
    inner = make_repo(outer / "vendor/inner")
    result, out = dispatch(probe_hooks, "probe", inner, payload_for(inner), inner)
    assert result.returncode == 0
    assert not (out / "stdin").exists()

    write_marker(inner, {"pluginHooks": True})
    result, out = dispatch(probe_hooks, "probe", inner, payload_for(inner), inner)
    assert result.returncode == 0
    assert (out / "root").read_text() == str(inner)


def test_non_repository_project_dir_exits_zero(
    probe_hooks: Path, tmp_path: Path
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    write_marker(plain, {"pluginHooks": True})
    result, out = dispatch(probe_hooks, "probe", plain, payload_for(plain), plain)
    assert result.returncode == 0
    assert not (out / "stdin").exists()


@pytest.mark.parametrize("code", [2, 1, 0])
def test_guard_exit_code_and_stderr_pass_through(
    probe_hooks: Path, tmp_path: Path, code: int
) -> None:
    root = make_repo(tmp_path / "proj")
    write_marker(root, {"pluginHooks": True})
    result, _out = dispatch(
        probe_hooks, "probe", root, payload_for(root), root, PROBE_EXIT=str(code)
    )
    assert result.returncode == code
    assert "probe stderr" in result.stderr


@pytest.mark.parametrize("guard", ["", "../probe", "Probe", "no-such-guard"])
def test_bad_guard_name_is_a_non_blocking_error(
    probe_hooks: Path, tmp_path: Path, guard: str
) -> None:
    root = make_repo(tmp_path / "proj")
    write_marker(root, {"pluginHooks": True})
    result, out = dispatch(probe_hooks, guard, root, payload_for(root), root)
    assert result.returncode == 1
    assert "ralph hooks:" in result.stderr
    assert not (out / "stdin").exists()


def test_unreadable_marker_is_a_non_blocking_error(
    probe_hooks: Path, tmp_path: Path
) -> None:
    root = make_repo(tmp_path / "proj")
    write_marker(root, "{not json")
    result, out = dispatch(probe_hooks, "probe", root, payload_for(root), root)
    assert result.returncode == 1
    assert "cannot read" in result.stderr
    assert not (out / "stdin").exists()


# --------------------------------------------------------------------------
# Real guards through the dispatcher
# --------------------------------------------------------------------------


def run_plugin_guard(
    guard: str, project_dir: Path, payload: str, run_cwd: Path
) -> subprocess.CompletedProcess[str]:
    """Run the shipped dispatcher for a real guard."""
    return subprocess.run(
        [BASH, str(DISPATCHER), guard],
        input=payload,
        cwd=run_cwd,
        env=base_env(CLAUDE_PROJECT_DIR=str(project_dir)),
        capture_output=True,
        text=True,
        check=False,
    )


def test_real_guard_blocks_only_behind_the_marker(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "proj")
    payload = payload_for(root, command='backlog task edit 1 --notes "x"')
    assert run_plugin_guard("notes-guard", root, payload, root).stdout == ""
    write_marker(root, {"pluginHooks": True})
    assert '"deny"' in run_plugin_guard("notes-guard", root, payload, root).stdout
    write_marker(root, {"pluginHooks": True, "localGuards": ["notes-guard"]})
    assert run_plugin_guard("notes-guard", root, payload, root).stdout == ""


def test_commit_is_interpreted_in_the_payload_cwd(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "proj", branch="task-7")
    write_marker(root, {"pluginHooks": True})
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    result = run_plugin_guard(
        "commit-prefix-guard",
        root,
        payload_for(root, command='git commit -m "bad"'),
        elsewhere,
    )
    assert "task-7: " in result.stdout


# --------------------------------------------------------------------------
# Guards run directly: RALPH_PROJECT_ROOT, else CLAUDE_PROJECT_DIR
# --------------------------------------------------------------------------


def run_guard_directly(script: Path, payload: str, run_cwd: Path, **env: str) -> str:
    """Run a guard with no dispatcher, as the legacy settings.json wiring does; return stdout."""
    result = subprocess.run(
        [BASH, str(script)],
        input=payload,
        cwd=run_cwd,
        env=base_env(**env),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


@pytest.mark.parametrize(
    ("root_env", "project_dir_env"),
    [(None, ""), ("", "elsewhere"), ("scripts/ralph", "elsewhere")],
    ids=[
        "legacy-claude-project-dir",
        "ralph-project-root",
        "ralph-project-root-below-root",
    ],
)
def test_master_branch_guard_finds_the_root(
    tmp_path: Path, root_env: str | None, project_dir_env: str
) -> None:
    root = make_repo(tmp_path / "proj")
    (root / "scripts/ralph").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    env = {
        "CLAUDE_PROJECT_DIR": str(elsewhere if project_dir_env else root / "scripts")
    }
    if root_env is not None:
        env["RALPH_PROJECT_ROOT"] = str(root / root_env)
    payload = payload_for(elsewhere, file_path=str(root / "README.md"))
    out = run_guard_directly(
        PLUGIN_HOOKS / "master-branch-guard.sh", payload, elsewhere, **env
    )
    assert '"deny"' in out


def test_master_branch_guard_ignores_paths_outside_the_root(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "proj")
    payload = payload_for(root, file_path=str(tmp_path / "other/README.md"))
    out = run_guard_directly(
        PLUGIN_HOOKS / "master-branch-guard.sh",
        payload,
        root,
        RALPH_PROJECT_ROOT=str(root),
    )
    assert out == ""


@pytest.mark.parametrize("via", ["ralph-project-root", "claude-project-dir-subdir"])
def test_task_validator_resolves_task_paths_from_the_root(
    tmp_path: Path, via: str
) -> None:
    root = make_repo(tmp_path / "proj")
    (root / "backlog/tasks").mkdir(parents=True)
    (root / "backlog/tasks/task-1 - Empty.md").write_text(
        "---\nid: TASK-1\nstatus: To Do\n---\n"
    )
    (root / "sub").mkdir()
    env = {"RALPH_AUTONOMOUS": "0"}
    if via == "ralph-project-root":
        env["RALPH_PROJECT_ROOT"] = str(root)
    else:
        env["CLAUDE_PROJECT_DIR"] = str(root / "sub")
    payload = payload_for(root / "sub", command='backlog task edit 1 -s "To Do"')
    out = run_guard_directly(
        PLUGIN_HOOKS / "task-validator.sh", payload, tmp_path, **env
    )
    assert "Description body is empty" in out


# --------------------------------------------------------------------------
# A project wired the legacy way still blocks through that wiring
# --------------------------------------------------------------------------

NON_ASCII = "Привет"
LEGACY_CASES: dict[str | None, tuple[str, str]] = {
    "Bash(git commit *)": (
        'git commit -m "x\n\nCo-Authored-By: a"',
        "forbidden trailer",
    ),
    "Bash(gh pr create *)": (
        'gh pr create --body "Generated with Claude Code"',
        "forbidden trailer",
    ),
    "Bash(backlog task edit *)": (
        'backlog task edit 1 --notes "x" --title "' + NON_ASCII + '"',
        "BLOCKED",
    ),
    "Bash(backlog task create *)": (
        f'backlog task create "{NON_ASCII}"',
        "ASCII English",
    ),
    "Bash(backlog doc create *)": (
        f'backlog doc create "{NON_ASCII}"',
        "ASCII English",
    ),
    "Bash(backlog decision create *)": (
        f'backlog decision create "{NON_ASCII}"',
        "ASCII English",
    ),
    "Bash(backlog draft create *)": (
        f'backlog draft create "{NON_ASCII}"',
        "ASCII English",
    ),
    "Bash(git checkout -b *)": (f"git checkout -b {NON_ASCII}", "ASCII English"),
}
PREFIX_CASE = ('git commit -m "no prefix"', "must start with `task-1: `")
VALIDATOR_CASES = {
    "Bash(backlog task edit *)": 'backlog task edit 1 -s "To Do"',
    "Bash(backlog task create *)": "backlog task create 1",
}


@pytest.fixture
def bootstrapped(tmp_path: Path) -> Path:
    """A project with the legacy settings.json and the guards installed the legacy way, and no marker."""
    root = make_repo(tmp_path / "proj")
    (root / ".claude/hooks").mkdir(parents=True)
    shutil.copy2(SETTINGS, root / ".claude/settings.json")
    for guard in GUARDS:
        shutil.copy2(PLUGIN_HOOKS / f"{guard}.sh", root / ".claude/hooks" / f"{guard}.sh")
        (root / ".claude/hooks" / f"{guard}.sh").chmod(0o755)
    (root / "backlog/tasks").mkdir(parents=True)
    (root / "backlog/tasks/task-1 - Empty.md").write_text(
        "---\nid: TASK-1\nstatus: To Do\n---\n"
    )
    (root / "sub").mkdir()
    return root


def legacy_hooks(root: Path) -> list[tuple[str, str | None, str]]:
    """Return (event, if, command) for every hook in the project's settings.json."""
    hooks = json.loads((root / ".claude/settings.json").read_text())["hooks"]
    return [
        (event, h.get("if"), h["command"])
        for event, groups in hooks.items()
        for g in groups
        for h in g["hooks"]
    ]


def test_legacy_wired_project_still_blocks(bootstrapped: Path) -> None:
    root = bootstrapped
    rows = legacy_hooks(root)
    assert len(rows) == 13
    for event, condition, command in rows:
        guard = LEGACY_COMMAND.match(command).group(1)  # type: ignore[union-attr]
        if guard == "commit-prefix-guard":
            git(root, "checkout", "-q", "-B", "task-1")
            tool_input, expected = {"command": PREFIX_CASE[0]}, PREFIX_CASE[1]
        elif guard == "master-branch-guard":
            git(root, "checkout", "-q", "master")
            tool_input, expected = (
                {"file_path": str(root / "README.md")},
                "no active task branch",
            )
        elif guard == "task-validator":
            tool_input, expected = {"command": VALIDATOR_CASES[condition]}, "TASK-1"
        else:
            tool_input, expected = (
                {"command": LEGACY_CASES[condition][0]},
                LEGACY_CASES[condition][1],
            )
        result = subprocess.run(
            [BASH, "-c", command],
            input=payload_for(root / "sub", **tool_input),
            cwd=root / "sub",
            env=base_env(CLAUDE_PROJECT_DIR=str(root), RALPH_AUTONOMOUS="0"),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{guard} ({condition}) failed: {result.stderr}"
        decision = "additionalContext" if event == "PostToolUse" else '"deny"'
        assert decision in result.stdout and expected in result.stdout, (
            f"{guard} ({condition}) did not act"
        )
        git(root, "checkout", "-q", "master")
