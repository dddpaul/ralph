"""TASK-324: a task an iteration leaves in ``To Do`` is not picked again.

Before the fix the loop re-ran :func:`tasks.pick_next_task` after every
iteration and got the same unchanged task back, so one blocked task could use
up a whole run. These tests drive the real picker over a stubbed backlog and a
stub tool that picks its task from the prompt the way the agent does, then
either finishes it (moves it to ``Done``) or leaves it in ``To Do``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ralph import loop as loop_module
from ralph import tasks as tasks_module
from ralph.args import ParsedArgs
from ralph.signals import IterationSignals
from ralph.tasks import BacklogTask
from ralph.tools import OnSpawn, Tool, ToolResult


def _args(*, tasks: str = "", max_iterations: int = 10) -> ParsedArgs:
    return ParsedArgs(
        tool="opencode",
        model="claude-opus-5",
        effort="max",
        timeout="15",
        on_error="continue",
        retry_count=0,
        log_file="",
        prompt_file="",
        tasks=tasks,
        block_end_buffer_min=0,
        devcontainer=False,
        max_iterations=max_iterations,
    )


class _Backlog:
    """In-memory task statuses behind the picker's backlog lookups."""

    def __init__(self, statuses: dict[str, str]) -> None:
        self.statuses = statuses

    def fetch(self, task_id: str) -> BacklogTask | None:
        tid = f"TASK-{task_id.removeprefix('TASK-')}"
        if tid not in self.statuses:
            return None
        return BacklogTask(id=tid, status=self.statuses[tid], dependencies=())

    def ids(self, status: str) -> list[str]:
        found = [tid for tid, st in self.statuses.items() if st == status]
        return sorted(found, key=lambda tid: int(tid.removeprefix("TASK-")))


class _StubTool(Tool):
    """Agent stand-in: moves the task it picks to ``Done`` unless it is in ``stuck``.

    Whitelist prompts name the task. Otherwise it takes the lowest ``To Do``
    task the prompt does not exclude, as CLAUDE.md tells the agent to.
    ``worked`` records each task it picked.
    """

    def __init__(self, backlog: _Backlog, stuck: set[str]) -> None:
        self._backlog = backlog
        self._stuck = stuck
        self.worked: list[str] = []

    def _choose(self, prompt: str) -> str:
        named = re.search(r"^Execute (TASK-\d+)", prompt, re.MULTILINE)
        if named:
            return named.group(1)
        excluded_line = re.search(r"^Do NOT pick these tasks.*$", prompt, re.MULTILINE)
        excluded = set(re.findall(r"TASK-\d+", excluded_line.group(0))) if excluded_line else set()
        return next(tid for tid in self._backlog.ids("To Do") if tid not in excluded)

    def run(
        self,
        prompt: str,
        timeout_sec: int,
        *,
        on_spawn: OnSpawn | None = None,
    ) -> ToolResult:
        _ = (timeout_sec, on_spawn)
        task_id = self._choose(prompt)
        self.worked.append(task_id)
        if task_id not in self._stuck:
            self._backlog.statuses[task_id] = "Done"
        return ToolResult(
            stdout_path=Path("/tmp/ralph-skip-test.out"),
            exit_code=0,
            signals=IterationSignals(task_summary_count=1, complete=False, error_text=None),
        )


@pytest.fixture
def harness(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, list[str]]:
    """Patch the backlog CLI seams; return ``(tmp_path, picked task log)``."""
    monkeypatch.setattr(loop_module, "ITER_SLEEP_SEC", 0)
    monkeypatch.setattr(loop_module, "check_and_pause", lambda *_a, **_kw: False)
    monkeypatch.setattr(tasks_module, "resolve_holder", lambda *_a: None)
    monkeypatch.setenv("RALPH_STATUS_FILE", str(tmp_path / "status.json"))
    monkeypatch.setenv("RALPH_HEARTBEAT_FILE", str(tmp_path / "heartbeat"))
    monkeypatch.setenv("RALPH_RUN_LOG", str(tmp_path / "run.log"))
    return tmp_path, []


def _install(
    monkeypatch: pytest.MonkeyPatch,
    picked: list[str],
    statuses: dict[str, str],
    stuck: set[str],
) -> _StubTool:
    backlog = _Backlog(statuses)
    monkeypatch.setattr(tasks_module, "fetch_task", backlog.fetch)
    monkeypatch.setattr(tasks_module, "_list_todo_ids", lambda: backlog.ids("To Do"))
    monkeypatch.setattr(tasks_module, "done_task_ids", lambda: backlog.ids("Done"))
    monkeypatch.setattr(tasks_module, "current_in_progress_task", lambda: None)

    real_pick = tasks_module.pick_next_task

    def recording_pick(**kwargs: object) -> str | None:
        task_id = real_pick(**kwargs)  # type: ignore[arg-type]
        if task_id is not None:
            picked.append(task_id)
        return task_id

    monkeypatch.setattr(tasks_module, "pick_next_task", recording_pick)
    tool = _StubTool(backlog, stuck)
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_kw: tool)
    return tool


def _status(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))


def test_whitelist_head_left_in_todo_lets_second_task_run(
    harness: tuple[Path, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC #1, #2, #3 — the stuck first whitelist task runs once, then the next one."""
    tmp_path, picked = harness
    statuses = {"TASK-302": "To Do", "TASK-304": "To Do", "TASK-305": "To Do"}
    tool = _install(monkeypatch, picked, statuses, stuck={"TASK-302"})

    rc = loop_module.run(_args(tasks="302,304,305"), tmp_path)

    assert rc == 0
    assert picked == ["TASK-302", "TASK-304", "TASK-305"]
    assert tool.worked == picked
    status = _status(tmp_path)
    assert status["skipped_tasks"] == [{"task": "TASK-302", "iteration": 1}]
    assert status["tasks_done"] == ["TASK-304", "TASK-305"]
    out = capsys.readouterr().out
    assert "Skipped tasks (left in To Do):" in out
    assert "  TASK-302: left in To Do by iteration 1" in out
    run_log = (tmp_path / "run.log").read_text(encoding="utf-8")
    assert "TASK-302 left in To Do by iteration 1" in run_log


def test_every_whitelist_task_left_in_todo_is_attempted_once(
    harness: tuple[Path, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC #5 — each stuck task is attempted once, then the run ends."""
    tmp_path, picked = harness
    statuses = {"TASK-1": "To Do", "TASK-2": "To Do", "TASK-3": "To Do"}
    _install(monkeypatch, picked, statuses, stuck=set(statuses))

    rc = loop_module.run(_args(tasks="1,2,3"), tmp_path)

    assert rc == 0
    assert picked == ["TASK-1", "TASK-2", "TASK-3"]
    status = _status(tmp_path)
    assert status["iteration"] == 3
    assert status["skipped_tasks"] == [
        {"task": "TASK-1", "iteration": 1},
        {"task": "TASK-2", "iteration": 2},
        {"task": "TASK-3", "iteration": 3},
    ]
    out = capsys.readouterr().out
    assert "Iterations used:    3 of 10" in out
    for n in (1, 2, 3):
        assert f"  TASK-{n}: left in To Do by iteration {n}" in out


def test_default_mode_skips_lowest_task_left_in_todo(
    harness: tuple[Path, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC #1, #5 — default mode moves past the lowest eligible task once it stays To Do."""
    tmp_path, picked = harness
    statuses = {"TASK-7": "To Do", "TASK-8": "To Do", "TASK-9": "Done"}
    tool = _install(monkeypatch, picked, statuses, stuck={"TASK-7"})

    rc = loop_module.run(_args(), tmp_path)

    assert rc == 0
    assert picked == ["TASK-7", "TASK-8"]
    assert tool.worked == picked  # the prompt steered the agent off TASK-7
    assert _status(tmp_path)["skipped_tasks"] == [{"task": "TASK-7", "iteration": 1}]
    assert "Exit reason:        all tasks done" in capsys.readouterr().out


def test_finished_tasks_are_not_reported_as_skipped(
    harness: tuple[Path, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A run where every task moves on reports no skipped tasks."""
    tmp_path, picked = harness
    _install(monkeypatch, picked, {"TASK-1": "To Do", "TASK-2": "To Do"}, stuck=set())

    loop_module.run(_args(), tmp_path)

    assert picked == ["TASK-1", "TASK-2"]
    assert _status(tmp_path)["skipped_tasks"] == []
    assert "Skipped tasks" not in capsys.readouterr().out


def test_pick_next_task_honours_exclude(monkeypatch: pytest.MonkeyPatch) -> None:
    """The picker never returns an excluded ID, in either mode."""
    backlog = _Backlog({"TASK-1": "To Do", "TASK-2": "To Do"})
    monkeypatch.setattr(tasks_module, "fetch_task", backlog.fetch)
    monkeypatch.setattr(tasks_module, "_list_todo_ids", lambda: backlog.ids("To Do"))

    assert tasks_module.pick_next_task(whitelist=["1", "2"], exclude={"TASK-1"}) == "TASK-2"
    assert tasks_module.pick_next_task(exclude={"TASK-1"}) == "TASK-2"
    assert tasks_module.pick_next_task(exclude={"TASK-1", "TASK-2"}) is None


def test_default_mode_every_task_left_in_todo_is_attempted_once(
    harness: tuple[Path, list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #5 — default mode: each stuck task is worked once, then the run ends."""
    tmp_path, picked = harness
    statuses = {"TASK-4": "To Do", "TASK-5": "To Do"}
    tool = _install(monkeypatch, picked, statuses, stuck=set(statuses))

    loop_module.run(_args(), tmp_path)

    assert picked == ["TASK-4", "TASK-5"]
    assert tool.worked == picked
    assert [e["task"] for e in _status(tmp_path)["skipped_tasks"]] == ["TASK-4", "TASK-5"]
