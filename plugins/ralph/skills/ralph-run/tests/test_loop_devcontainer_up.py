"""``devcontainer up`` ordering test for ``loop.run`` (TASK-175 AC #5).

Pins the bash parity invariant: when ``--devcontainer`` is set, the
orchestrator must call ``start_devcontainer`` exactly once, BEFORE the
first tool invocation, BEFORE the status file is written.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph import loop as loop_module
from ralph.args import ParsedArgs
from ralph.signals import IterationSignals
from ralph.tools import OnSpawn, Tool, ToolResult


def _args(*, devcontainer: bool) -> ParsedArgs:
    return ParsedArgs(
        tool="claude",
        model="claude-opus-4-8",
        effort="max",
        timeout="15",
        on_error="continue",
        retry_count=0,
        log_file="",
        prompt_file="",
        tasks="",
        block_end_buffer_min=0,
        devcontainer=devcontainer,
        max_iterations=1,
    )


class _CallRecordingTool(Tool):
    def __init__(self, call_log: list[str]) -> None:
        self._log = call_log

    def run(
        self,
        prompt: str,
        timeout_sec: int,
        *,
        on_spawn: OnSpawn | None = None,
    ) -> ToolResult:
        _ = (prompt, timeout_sec, on_spawn)
        self._log.append("tool.run")
        return ToolResult(
            stdout_path=Path("/tmp/ralph-test.out"),
            exit_code=0,
            signals=IterationSignals(
                task_summary_count=1, complete=True, error_text=None
            ),
        )


@pytest.fixture
def stubbed_loop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, list[str]]:
    monkeypatch.setattr(loop_module.tasks_module, "pick_next_task", lambda **_: "TASK-1")
    monkeypatch.setattr(loop_module.tasks_module, "count_remaining", lambda *_a, **_kw: 1)
    monkeypatch.setattr(loop_module.tasks_module, "done_task_ids", lambda: [])
    monkeypatch.setattr(
        loop_module.tasks_module, "current_in_progress_task", lambda: None
    )
    monkeypatch.setattr(loop_module, "ITER_SLEEP_SEC", 0)
    monkeypatch.setenv("RALPH_STATUS_FILE", str(tmp_path / "status.json"))
    monkeypatch.setenv("RALPH_HEARTBEAT_FILE", str(tmp_path / "heartbeat"))

    call_log: list[str] = []

    def fake_start(_workspace: Path, **_kw: object) -> int:
        call_log.append("start_devcontainer")
        return 0

    monkeypatch.setattr(loop_module, "start_devcontainer", fake_start)
    monkeypatch.setattr(
        loop_module, "build_tool", lambda *_a, **_kw: _CallRecordingTool(call_log)
    )
    return tmp_path, call_log


def test_up_called_once_before_tool_when_devcontainer_true(
    stubbed_loop: tuple[Path, list[str]],
) -> None:
    project_root, call_log = stubbed_loop
    rc = loop_module.run(_args(devcontainer=True), project_root)
    assert rc == 0
    assert call_log == ["start_devcontainer", "tool.run"]
    assert call_log.count("start_devcontainer") == 1


def test_up_not_called_when_devcontainer_false(
    stubbed_loop: tuple[Path, list[str]],
) -> None:
    project_root, call_log = stubbed_loop
    rc = loop_module.run(_args(devcontainer=False), project_root)
    assert rc == 0
    assert "start_devcontainer" not in call_log
    assert call_log == ["tool.run"]


def test_up_failure_returns_nonzero_and_skips_tool(
    monkeypatch: pytest.MonkeyPatch,
    stubbed_loop: tuple[Path, list[str]],
) -> None:
    project_root, call_log = stubbed_loop
    monkeypatch.setattr(loop_module, "start_devcontainer", lambda *_a, **_kw: (
        call_log.append("start_devcontainer_fail") or 2
    ))
    rc = loop_module.run(_args(devcontainer=True), project_root)
    assert rc == 2
    assert call_log == ["start_devcontainer_fail"]
