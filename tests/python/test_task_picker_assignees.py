"""The Ralph task picker skips To Do tasks held by someone else (TASK-314).

``BacklogTask`` parses ``Assignee:`` from ``backlog task view --plain``,
including several assignees. Default mode skips a candidate assigned to anyone
besides the holder; a bare ``@claude`` counts as unassigned. The holder comes
from ``SHARED_BACKLOG_HOLDER``, else ``git config ralph.holder``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ralph import tasks


def view(
    numeric: str,
    *,
    assignee: str | None = None,
    status: str = "○ To Do",
    deps: str | None = None,
) -> str:
    lines = [
        f"File: /x/backlog/tasks/task-{numeric} - t.md",
        "",
        f"Task TASK-{numeric} - t",
        "=" * 50,
        "",
        f"Status: {status}",
    ]
    if assignee is not None:
        lines.append(f"Assignee: {assignee}")
    if deps is not None:
        lines.append(f"Dependencies: {deps}")
    lines += ["Created: 2026-11-04 14:54 (UTC)", "", "Description:", "-" * 50, "d"]
    return "\n".join(lines) + "\n"


def fake_backlog(monkeypatch: pytest.MonkeyPatch, views: dict[str, str]) -> None:
    todo = "\n".join(f"  TASK-{n} - t" for n, v in views.items() if "To Do" in v)

    def stdout(args: list[str]) -> str:
        if args[:2] == ["task", "list"]:
            return f"To Do:\n{todo}\n" if todo else "No tasks found."
        return views.get(args[1], f"Task {args[1]} not found.\n")

    monkeypatch.setattr(tasks, "_backlog_stdout", stdout)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (None, ()),
        ("@paul", ("paul",)),
        ("@paul, @claude", ("paul", "claude")),
        ("@a, @b, @c", ("a", "b", "c")),
        ("bob", ("bob",)),
    ],
)
def test_fetch_task_parses_assignees(
    monkeypatch: pytest.MonkeyPatch, line: str | None, expected: tuple
) -> None:
    fake_backlog(monkeypatch, {"7": view("7", assignee=line)})
    task = tasks.fetch_task("7")
    assert task is not None
    assert task.assignees == expected


def test_parses_assignees_from_real_backlog_output(tmp_path: Path) -> None:
    """The regex matches what the installed backlog CLI actually prints."""
    if subprocess.run(["which", "backlog"], capture_output=True, check=False).returncode != 0:
        pytest.skip("backlog CLI not installed")

    def run(*args: str) -> str:
        return subprocess.run(
            ["backlog", *args], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    run("init", "picker", "--defaults")
    run("task", "create", "a", "-a", "@paul", "-a", "@claude")
    assert tasks._parse_assignees(run("task", "view", "1", "--plain")) == (
        "paul",
        "claude",
    )


@pytest.mark.parametrize(
    ("assignees", "holder", "held"),
    [
        ((), None, False),
        (("claude",), None, False),
        (("claude",), "paul", False),
        (("paul",), "paul", False),
        (("paul", "claude"), "paul", False),
        (("paul",), None, True),
        (("bob",), "paul", True),
        (("paul", "bob"), "paul", True),
        (("claude", "bob"), "@paul", True),
        (("paul",), "@paul", False),
    ],
)
def test_held_by_other(
    assignees: tuple[str, ...], holder: str | None, held: bool
) -> None:
    task = tasks.BacklogTask(
        id="TASK-1", status="To Do", dependencies=(), assignees=assignees
    )
    assert tasks.held_by_other(task, holder) is held


def test_default_mode_skips_tasks_held_by_someone_else(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_backlog(
        monkeypatch,
        {
            "1": view("1", assignee="@bob"),
            "2": view("2", assignee="@paul, @bob"),
            "3": view("3", assignee="@claude"),
        },
    )
    assert tasks.pick_next_task(holder="paul") == "TASK-3"


def test_default_mode_takes_the_holders_own_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_backlog(
        monkeypatch,
        {"1": view("1", assignee="@bob"), "2": view("2", assignee="@paul, @claude")},
    )
    assert tasks.pick_next_task(holder="paul") == "TASK-2"


def test_default_mode_without_holder_skips_every_real_assignee(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_backlog(monkeypatch, {"1": view("1", assignee="@paul"), "2": view("2")})
    assert tasks.pick_next_task() == "TASK-2"


def test_default_mode_returns_none_when_every_task_is_held(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_backlog(monkeypatch, {"1": view("1", assignee="@bob")})
    assert tasks.pick_next_task(holder="paul") is None


def test_bare_claude_task_with_done_dependencies_is_picked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_backlog(
        monkeypatch,
        {
            "1": view("1", assignee="@claude", deps="TASK-9"),
            "2": view("2"),
            "9": view("9", status="✔ Done"),
        },
    )
    assert tasks.pick_next_task(holder="paul") == "TASK-1"


def test_resolve_holder_prefers_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "ralph.holder", "@cfg"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SHARED_BACKLOG_HOLDER", "@env")
    assert tasks.resolve_holder() == "env"
    monkeypatch.delenv("SHARED_BACKLOG_HOLDER")
    assert tasks.resolve_holder() == "cfg"


def test_resolve_holder_missing_is_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SHARED_BACKLOG_HOLDER", raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    assert tasks.resolve_holder() is None
