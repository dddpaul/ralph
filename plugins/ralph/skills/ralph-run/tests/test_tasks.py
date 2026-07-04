"""Unit tests for ``ralph/tasks.py`` (US-003 AC #2)."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from ralph import tasks


def _view_payload(
    task_id: int, *, status: str = "To Do", dependencies: Iterable[str] = ()
) -> str:
    deps_line = ""
    if dependencies:
        deps_line = f"Dependencies: {', '.join(dependencies)}\n"
    return (
        f"File: backlog/tasks/task-{task_id}.md\n\n"
        f"Task TASK-{task_id} - Some title\n"
        "=====================================\n\n"
        f"Status: {status}\n"
        "Priority: Medium\n"
        f"{deps_line}"
        "\nDescription:\n--------\n"
        f"Body for TASK-{task_id}.\n"
    )


class FakeBacklog:
    """Stand-in for the ``backlog`` CLI, driving ``_backlog_stdout``."""

    def __init__(
        self,
        todo_ids: Iterable[int],
        details: dict[int, dict[str, object]] | None = None,
    ) -> None:
        self.todo_ids = list(todo_ids)
        self.details = details or {}
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> str:
        self.calls.append(args)
        if args[:3] == ["task", "list", "-s"] and args[3] == "To Do":
            if not self.todo_ids:
                return "No tasks found\n"
            lines = ["To Do:"] + [
                f"  [MEDIUM] TASK-{i} - title" for i in self.todo_ids
            ]
            return "\n".join(lines) + "\n"
        if args[0] == "task" and len(args) >= 2 and args[-1] == "--plain":
            tid = int(args[1])
            spec = self.details.get(tid)
            if spec is None:
                return f"Task {tid} not found.\n"
            status_raw: object = spec.get("status", "To Do")
            deps_raw: object = spec.get("deps", ())
            status = status_raw if isinstance(status_raw, str) else "To Do"
            if isinstance(deps_raw, (list, tuple)):
                deps_iter = [str(d) for d in deps_raw]
            else:
                deps_iter = []
            return _view_payload(tid, status=status, dependencies=deps_iter)
        return ""


@pytest.fixture(autouse=True)
def fresh_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tasks, "_backlog_stdout", lambda args: "")


def _install_fake(monkeypatch: pytest.MonkeyPatch, fake: FakeBacklog) -> None:
    monkeypatch.setattr(tasks, "_backlog_stdout", fake)


def test_default_picks_lowest_id_with_done_deps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeBacklog(
        todo_ids=[200, 152, 153],
        details={
            150: {"status": "Done", "deps": []},
            152: {"status": "To Do", "deps": ["TASK-150"]},
            153: {"status": "To Do", "deps": ["TASK-152"]},
            200: {"status": "To Do", "deps": ["TASK-150"]},
        },
    )
    _install_fake(monkeypatch, fake)
    assert tasks.pick_next_task() == "TASK-152"


def test_default_skips_task_with_pending_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeBacklog(
        todo_ids=[152, 200],
        details={
            150: {"status": "To Do", "deps": []},
            152: {"status": "To Do", "deps": ["TASK-150"]},
            200: {"status": "To Do", "deps": []},
        },
    )
    _install_fake(monkeypatch, fake)
    assert tasks.pick_next_task() == "TASK-200"


def test_default_returns_none_when_all_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeBacklog(
        todo_ids=[152, 200],
        details={
            150: {"status": "To Do", "deps": []},
            152: {"status": "To Do", "deps": ["TASK-150"]},
            200: {"status": "To Do", "deps": ["TASK-150"]},
        },
    )
    _install_fake(monkeypatch, fake)
    assert tasks.pick_next_task() is None


def test_default_returns_none_on_no_tasks_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake(monkeypatch, FakeBacklog(todo_ids=[]))
    assert tasks.pick_next_task() is None


def test_task_with_no_dependencies_picked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeBacklog(
        todo_ids=[152, 153],
        details={
            152: {"status": "To Do", "deps": []},
            153: {"status": "To Do", "deps": []},
        },
    )
    _install_fake(monkeypatch, fake)
    assert tasks.pick_next_task() == "TASK-152"


def test_whitelist_picks_first_todo_in_user_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whitelist REPLACES the lowest-ID rule — user ordering is authoritative."""
    fake = FakeBacklog(
        todo_ids=[],
        details={
            152: {"status": "Done", "deps": []},
            200: {"status": "To Do", "deps": []},
            153: {"status": "To Do", "deps": []},
        },
    )
    _install_fake(monkeypatch, fake)
    assert tasks.pick_next_task(["200", "153"]) == "TASK-200"


def test_whitelist_skips_non_todo_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeBacklog(
        todo_ids=[],
        details={
            152: {"status": "Done"},
            153: {"status": "In Progress"},
            200: {"status": "To Do"},
        },
    )
    _install_fake(monkeypatch, fake)
    assert tasks.pick_next_task(["152", "153", "200"]) == "TASK-200"


def test_whitelist_returns_none_when_all_consumed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeBacklog(
        todo_ids=[],
        details={152: {"status": "Done"}, 153: {"status": "Done"}},
    )
    _install_fake(monkeypatch, fake)
    assert tasks.pick_next_task(["152", "153"]) is None


def test_whitelist_does_not_check_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whitelist mode skips dependency gate — user explicitly chose this task."""
    fake = FakeBacklog(
        todo_ids=[],
        details={
            150: {"status": "To Do"},
            152: {"status": "To Do", "deps": ["TASK-150"]},
        },
    )
    _install_fake(monkeypatch, fake)
    assert tasks.pick_next_task(["152"]) == "TASK-152"


def test_whitelist_accepts_task_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeBacklog(
        todo_ids=[], details={152: {"status": "To Do"}}
    )
    _install_fake(monkeypatch, fake)
    assert tasks.pick_next_task(["TASK-152"]) == "TASK-152"


def test_fetch_task_handles_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake(monkeypatch, FakeBacklog(todo_ids=[], details={}))
    assert tasks.fetch_task("999") is None


def test_fetch_task_parses_multi_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeBacklog(
        todo_ids=[],
        details={
            152: {"status": "To Do", "deps": ["TASK-150", "TASK-149"]},
        },
    )
    _install_fake(monkeypatch, fake)
    task = tasks.fetch_task("152")
    assert task is not None
    assert task.dependencies == ("TASK-150", "TASK-149")


def test_current_in_progress_task_returns_first_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TASK-200: re-derive current_task from the In Progress list (bash:849);
    the first listed TASK id wins, matching ``head -1``."""
    monkeypatch.setattr(
        tasks,
        "_backlog_stdout",
        lambda args: "In Progress:\n  [HIGH] TASK-9 - a\n  [LOW] TASK-12 - b\n",
    )
    assert tasks.current_in_progress_task() == "TASK-9"


def test_current_in_progress_task_none_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tasks, "_backlog_stdout", lambda args: "No tasks found\n")
    assert tasks.current_in_progress_task() is None
