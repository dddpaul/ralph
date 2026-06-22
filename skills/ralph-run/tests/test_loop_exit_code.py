"""Exit-code parity tests for max-iterations fall-through (TASK-159).

Bash equivalent at ``ralph.sh:889-894``::

    if [[ "$TASKS_COMPLETED" -gt 0 && "$FAILED_ITERATIONS" -eq 0 ]]; then
        cleanup_and_exit 0
    else
        cleanup_and_exit 1
    fi

The Python orchestrator previously always returned 0 on the max-iterations
exit path. These tests pin the bash-parity contract: exit 1 when zero tasks
completed OR any iteration failed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph import loop as loop_module
from ralph.args import ParsedArgs
from ralph.signals import IterationSignals
from ralph.tools import Tool, ToolResult


def _args(max_iterations: int = 2) -> ParsedArgs:
    return ParsedArgs(
        tool="claude",
        model="claude-opus-4-7",
        effort="max",
        timeout="15",
        on_error="continue",
        retry_count=0,
        log_file="",
        prompt_file="",
        tasks="",
        block_end_buffer_min=0,
        devcontainer=False,
        max_iterations=max_iterations,
    )


class _ScriptedTool(Tool):
    """Returns pre-baked ToolResults in order; reuses the last entry on overflow."""

    def __init__(self, results: list[ToolResult]) -> None:
        self._results = results
        self._calls = 0

    def run(self, prompt: str, timeout_sec: int) -> ToolResult:
        _ = (prompt, timeout_sec)
        idx = min(self._calls, len(self._results) - 1)
        self._calls += 1
        return self._results[idx]


def _result(exit_code: int, *, complete: bool = False) -> ToolResult:
    return ToolResult(
        stdout_path=Path("/tmp/ralph-test.out"),
        exit_code=exit_code,
        signals=IterationSignals(
            task_summary_count=1 if exit_code == 0 else 0,
            complete=complete,
            error_text=None,
        ),
    )


@pytest.fixture
def stubbed_loop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    """Stub backlog interaction + speed up the inter-iteration sleep."""
    monkeypatch.setattr(loop_module.tasks_module, "pick_next_task", lambda **_: "TASK-1")
    monkeypatch.setattr(loop_module.tasks_module, "count_remaining", lambda *_a, **_kw: 1)
    monkeypatch.setattr(loop_module.tasks_module, "done_task_ids", lambda: [])
    monkeypatch.setattr(loop_module, "ITER_SLEEP_SEC", 0)
    monkeypatch.setenv("RALPH_STATUS_FILE", str(tmp_path / "status.json"))
    monkeypatch.setenv("RALPH_HEARTBEAT_FILE", str(tmp_path / "heartbeat"))
    return tmp_path


def _patch_tool(
    monkeypatch: pytest.MonkeyPatch, results: list[ToolResult]
) -> _ScriptedTool:
    scripted = _ScriptedTool(results)
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_kw: scripted)
    return scripted


def test_max_iterations_zero_completions_returns_1(
    stubbed_loop: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #3 — 0 completions → exit 1 (bash returns 1 here too)."""
    # Every iteration fails (exit_code != 0). With on_error="continue" we
    # keep iterating until the for loop falls through max_iterations.
    _patch_tool(monkeypatch, [_result(exit_code=1)])
    rc = loop_module.run(_args(max_iterations=2), stubbed_loop)
    assert rc == 1


def test_max_iterations_completion_plus_failure_returns_1(
    stubbed_loop: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #4 — 1 completion + 1 failure → exit 1."""
    _patch_tool(
        monkeypatch,
        [_result(exit_code=0), _result(exit_code=1)],
    )
    rc = loop_module.run(_args(max_iterations=2), stubbed_loop)
    assert rc == 1


def test_max_iterations_completion_no_failure_returns_0(
    stubbed_loop: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #5 — 1+ completions, 0 failures → exit 0 (bash's success path)."""
    # Non-completing successes: exit_code=0 but signals.complete=False so the
    # loop does NOT short-circuit to "all tasks done"; it must fall through
    # max_iterations and hit our new branch.
    _patch_tool(monkeypatch, [_result(exit_code=0, complete=False)])
    rc = loop_module.run(_args(max_iterations=2), stubbed_loop)
    assert rc == 0
