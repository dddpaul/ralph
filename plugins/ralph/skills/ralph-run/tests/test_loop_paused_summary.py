"""Summary-text parity for the paused vs. completed exit paths (TASK-161).

Bash equivalent at ``ralph.sh:724-728``::

    EXIT_REASON="paused"
    _update_status "paused" ...
    show_summary "paused"

The Python orchestrator previously rewrote ``state.exit_reason`` to
``"all tasks done"`` on the paused branch to satisfy a closed-set assertion,
which made the summary line indistinguishable from a clean completion. These
tests pin the bash-parity contract: a paused run's summary contains ``paused``
and does NOT contain ``all tasks done``; a clean completion still does.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph import loop as loop_module
from ralph.args import ParsedArgs
from ralph.signals import IterationSignals
from ralph.status import StatusFile
from ralph.tools import OnSpawn, Tool, ToolResult


def _args() -> ParsedArgs:
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
        # Non-zero buffer so the patched check_and_pause is actually consulted;
        # the production gate at usage.py:99 short-circuits to False when 0.
        block_end_buffer_min=5,
        devcontainer=False,
        max_iterations=2,
    )


class _CompletingTool(Tool):
    """Returns a single completion signal on first call."""

    def run(
        self,
        prompt: str,
        timeout_sec: int,
        *,
        on_spawn: OnSpawn | None = None,
    ) -> ToolResult:
        _ = (prompt, timeout_sec, on_spawn)
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
) -> Path:
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


def test_paused_run_summary_says_paused_not_all_tasks_done(
    stubbed_loop: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC #1, AC #3 — paused branch must produce a summary text that reads as
    a pause, not as a clean completion."""

    def _force_pause(status: StatusFile, _buffer_min: int) -> bool:
        # Mirror the real wrapper's status mutations so downstream writes look
        # the same as a production pause; the only thing that matters for the
        # summary text is the return value.
        status.paused_reason = "block_end_in_3min_below_5min_buffer"
        status.paused_buffer_min = 5
        status.paused_remaining_min = 3
        return True

    monkeypatch.setattr(loop_module, "check_and_pause", _force_pause)
    # build_tool would still try to construct a real ClaudeTool; stub it to a
    # no-op since the pause branch returns before ever invoking the tool.
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_kw: _CompletingTool())

    rc = loop_module.run(_args(), stubbed_loop)
    assert rc == 0

    out = capsys.readouterr().out
    assert "Exit reason:        paused" in out
    assert "all tasks done" not in out


def test_completed_run_summary_still_says_all_tasks_done(
    stubbed_loop: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC #4 — clean-completion path still emits the original 'all tasks done'
    summary line (no regression from the paused-branch split)."""
    monkeypatch.setattr(loop_module, "check_and_pause", lambda *_a, **_kw: False)
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_kw: _CompletingTool())

    rc = loop_module.run(_args(), stubbed_loop)
    assert rc == 0

    out = capsys.readouterr().out
    assert "Exit reason:        all tasks done" in out
    assert "paused" not in out
