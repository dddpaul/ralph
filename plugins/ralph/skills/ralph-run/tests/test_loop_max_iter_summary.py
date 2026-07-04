"""Summary-text parity for the max-iterations exit path (TASK-163).

Bash equivalent at ``ralph.sh:890``::

    EXIT_REASON="max iterations reached ($TASKS_COMPLETED task(s) completed)"

The Python orchestrator keeps :data:`ralph.summary.EXIT_REASONS` as a flat
closed set (``"max iterations reached"`` verbatim) and interpolates the count
at the presentation boundary in :func:`ralph.summary.print_summary`. These
tests drive :func:`ralph.loop.run` through a synthetic max-iterations exit
and pin the templated summary line for ``tasks_completed`` ∈ {0, 2}.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph import loop as loop_module
from ralph.args import ParsedArgs
from ralph.signals import IterationSignals
from ralph.tools import OnSpawn, Tool, ToolResult


def _args(max_iterations: int = 2) -> ParsedArgs:
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
        devcontainer=False,
        max_iterations=max_iterations,
    )


class _ScriptedTool(Tool):
    """Returns pre-baked ToolResults in order; reuses the last entry on overflow."""

    def __init__(self, results: list[ToolResult]) -> None:
        self._results = results
        self._calls = 0

    def run(
        self,
        prompt: str,
        timeout_sec: int,
        *,
        on_spawn: OnSpawn | None = None,
    ) -> ToolResult:
        _ = (prompt, timeout_sec, on_spawn)
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
    monkeypatch.setattr(
        loop_module.tasks_module, "current_in_progress_task", lambda: None
    )
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


def test_max_iter_summary_with_zero_completions(
    stubbed_loop: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC #3 — tasks_completed=0 exit summary contains the templated suffix."""
    # Every iteration fails so tasks_completed stays at 0; with on_error
    # "continue" we fall through max_iterations.
    _patch_tool(monkeypatch, [_result(exit_code=1)])
    rc = loop_module.run(_args(max_iterations=2), stubbed_loop)
    assert rc == 1

    out = capsys.readouterr().out
    assert (
        "Exit reason:        max iterations reached (0 task(s) completed)" in out
    )


def test_max_iter_summary_with_two_completions(
    stubbed_loop: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC #4 — tasks_completed=2 exit summary interpolates the count."""
    # Two non-completing successes (complete=False) increment tasks_completed
    # twice without triggering the "all tasks done" short-circuit, then the
    # loop falls through max_iterations.
    _patch_tool(monkeypatch, [_result(exit_code=0, complete=False)])
    rc = loop_module.run(_args(max_iterations=2), stubbed_loop)
    assert rc == 0

    out = capsys.readouterr().out
    assert (
        "Exit reason:        max iterations reached (2 task(s) completed)" in out
    )
