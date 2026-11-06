"""The autonomous-create guard: no task IDs from an autonomous run in an opted-in clone (TASK-316).

``plugins/ralph/hooks/autonomous-create-guard.sh`` refuses ``backlog task
create``, ``shared-backlog.sh create`` and the ``ralph:ralph-handoff`` skill when
``RALPH_AUTONOMOUS=1`` and the session's clone has ``ralph.sharedBacklog`` true.
hooks.json calls it directly, so the tests run that exact command line with
``CLAUDE_PLUGIN_ROOT`` set: the ``pluginHooks`` marker, ``localGuards`` and the
marker's presence must not change the outcome.
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

PLUGIN_ROOT = REPO_ROOT / "plugins/ralph"
HOOK_COMMAND = next(
    hook["command"]
    for group in json.loads((PLUGIN_ROOT / "hooks/hooks.json").read_text())["hooks"]["PreToolUse"]
    for hook in group["hooks"]
    if "autonomous-create-guard" in hook["command"]
)
BASH = shutil.which("bash") or "/bin/bash"

REFUSED = [
    'backlog task create "Follow up"',
    'cd ../other && backlog task create "Follow up" -d "x"',
    'cd /tmp; backlog tasks create "Follow up"',
    'git pull && \\\n  backlog task create "Follow up"',
    'FOO=1 npx backlog task create "Follow up"',
    '/usr/local/bin/backlog task create "Follow up"',
    'bash scripts/shared-backlog.sh create "Follow up"',
    '"${CLAUDE_PLUGIN_ROOT}"/scripts/shared-backlog.sh create "Follow up" -l x',
    "x=$(backlog task create 'Follow up' --plain)",
]
ALLOWED = [
    "backlog task list -s 'To Do' --plain",
    'backlog task edit 7 --append-notes "Follow-up: create a task for X"',
    'grep -n "backlog task create" README.md',
    "echo backlog task create",
    "bash scripts/shared-backlog.sh claim 7",
    "git status",
]


def git(cwd: Path, *args: str) -> None:
    """Run git in ``cwd``."""
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def make_clone(path: Path, *, shared: str | None, marker: Any = None) -> Path:
    """Create a repository with ``ralph.sharedBacklog`` set to ``shared`` and an optional marker."""
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "master")
    if shared is not None:
        git(path, "config", "ralph.sharedBacklog", shared)
    if marker is not None:
        (path / ".claude").mkdir()
        (path / ".claude/ralph.json").write_text(json.dumps(marker))
    return path.resolve()


def run_guard(
    project: Path, tool_input: dict[str, str], *, tool: str = "Bash", cwd: Path | None = None, **env: str
) -> subprocess.CompletedProcess[str]:
    """Run the hooks.json command line for a ``tool`` call made in session ``project``."""
    full_env = {k: v for k, v in os.environ.items() if k not in ("RALPH_AUTONOMOUS", "RALPH_PROJECT_ROOT")}
    full_env.update(CLAUDE_PLUGIN_ROOT=str(PLUGIN_ROOT), CLAUDE_PROJECT_DIR=str(project), **env)
    payload = {"cwd": str(cwd or project), "tool_name": tool, "tool_input": tool_input}
    return subprocess.run(
        [BASH, "-c", HOOK_COMMAND],
        input=json.dumps(payload) + "\n",
        cwd=cwd or project,
        env=full_env,
        capture_output=True,
        text=True,
        check=False,
    )


def assert_refused(result: subprocess.CompletedProcess[str], what: str) -> None:
    assert result.returncode == 2, result.stderr
    assert f"BLOCKED: {what} during an autonomous run" in result.stderr
    assert "--append-notes" in result.stderr


@pytest.fixture
def opted_in(tmp_path: Path) -> Path:
    """A clone that enforces the protocol, with no ownership marker at all."""
    return make_clone(tmp_path / "proj", shared="true")


@pytest.mark.parametrize("command", REFUSED)
def test_autonomous_run_refuses_task_creation(opted_in: Path, command: str) -> None:
    what = "shared-backlog.sh create" if "shared-backlog.sh" in command else "backlog task create"
    assert_refused(run_guard(opted_in, {"command": command}, RALPH_AUTONOMOUS="1"), what)


@pytest.mark.parametrize("skill", ["ralph:ralph-handoff", "ralph-handoff"])
def test_autonomous_run_refuses_the_handoff_skill(opted_in: Path, skill: str) -> None:
    result = run_guard(opted_in, {"skill": skill}, tool="Skill", RALPH_AUTONOMOUS="1")
    assert_refused(result, "the ralph:ralph-handoff skill")


@pytest.mark.parametrize(
    "marker",
    [
        None,
        {},
        {"pluginHooks": False},
        {"pluginHooks": True},
        {"pluginHooks": True, "localGuards": ["autonomous-create-guard"]},
    ],
    ids=["no-marker", "pluginHooks-absent", "pluginHooks-false", "pluginHooks-true", "local-guard"],
)
def test_refusal_ignores_the_marker_gate(tmp_path: Path, marker: Any) -> None:
    clone = make_clone(tmp_path / "proj", shared="true", marker=marker)
    result = run_guard(clone, {"command": 'backlog task create "x"'}, RALPH_AUTONOMOUS="1")
    assert_refused(result, "backlog task create")


def test_refusal_keys_on_the_session_clone_not_the_cwd(tmp_path: Path) -> None:
    clone = make_clone(tmp_path / "proj", shared="true")
    other = make_clone(tmp_path / "other", shared=None)
    command = f'cd {other} && backlog task create "x"'
    result = run_guard(clone, {"command": command}, cwd=other, RALPH_AUTONOMOUS="1")
    assert_refused(result, "backlog task create")
    # The reverse: a session in a clone that does not enforce may cd into one that does.
    result = run_guard(other, {"command": f'cd {clone} && backlog task create "x"'}, RALPH_AUTONOMOUS="1")
    assert (result.returncode, result.stderr) == (0, "")


@pytest.mark.parametrize("command", ALLOWED)
def test_autonomous_run_allows_other_commands(opted_in: Path, command: str) -> None:
    result = run_guard(opted_in, {"command": command}, RALPH_AUTONOMOUS="1")
    assert (result.returncode, result.stderr) == (0, "")


def test_autonomous_run_allows_other_skills(opted_in: Path) -> None:
    result = run_guard(opted_in, {"skill": "ralph:ralph-task"}, tool="Skill", RALPH_AUTONOMOUS="1")
    assert (result.returncode, result.stderr) == (0, "")


@pytest.mark.parametrize("autonomous", [None, "", "0", "true"], ids=["unset", "empty", "zero", "word"])
def test_interactive_session_is_allowed(opted_in: Path, autonomous: str | None) -> None:
    env = {} if autonomous is None else {"RALPH_AUTONOMOUS": autonomous}
    for tool_input, tool in (
        ({"command": 'backlog task create "x"'}, "Bash"),
        ({"command": 'scripts/shared-backlog.sh create "x"'}, "Bash"),
        ({"skill": "ralph:ralph-handoff"}, "Skill"),
    ):
        result = run_guard(opted_in, tool_input, tool=tool, **env)
        assert (result.returncode, result.stderr) == (0, "")


@pytest.mark.parametrize("shared", [None, "false"], ids=["unset", "false"])
def test_clone_that_does_not_enforce_is_allowed(tmp_path: Path, shared: str | None) -> None:
    # The tracked marker may opt the project in; only the clone switch decides.
    clone = make_clone(tmp_path / "proj", shared=shared, marker={"pluginHooks": True, "sharedBacklog": True})
    for tool_input, tool in (
        ({"command": 'backlog task create "x"'}, "Bash"),
        ({"command": 'scripts/shared-backlog.sh create "x"'}, "Bash"),
        ({"skill": "ralph:ralph-handoff"}, "Skill"),
    ):
        result = run_guard(clone, tool_input, tool=tool, RALPH_AUTONOMOUS="1")
        assert (result.returncode, result.stderr) == (0, "")


def test_session_outside_a_repository_is_allowed(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    result = run_guard(plain, {"command": 'backlog task create "x"'}, RALPH_AUTONOMOUS="1")
    assert (result.returncode, result.stderr) == (0, "")
