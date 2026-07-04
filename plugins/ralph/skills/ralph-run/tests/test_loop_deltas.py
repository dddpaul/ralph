"""TASK-200: parity tests for the four bash-orchestrator behaviors the Python
port had dropped, re-covering the TASK-199-retired bats specs in pytest.

Each delta is a real-gap the loop now implements:

* ``--on-error retry`` / ``--retry-count`` — the retry loop
  (``run-summary-integration.bats``: "retry that succeeds produces zero failed
  iterations and zero status errors").
* ``--log-file`` — error lines appended to the user file
  (``status-file-integration.bats``: "existing log-file flag still works
  independently").
* Task-summary block-count warning
  (``one-task-enforcement.bats``: the 0/1/2-block + timeout + COMPLETE cases).
* ``current_task`` null-clearing
  (``status-file-integration.bats``: "current_task is null after iteration if
  no In Progress task remains").
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ralph import loop as loop_module
from ralph.args import ParsedArgs
from ralph.signals import IterationSignals
from ralph.tools import OnSpawn, Tool, ToolResult
from ralph.tools._subprocess import TIMEOUT_EXIT_CODE


def _args(
    *,
    on_error: str = "stop",
    retry_count: int = 2,
    log_file: str = "",
    max_iterations: int = 3,
) -> ParsedArgs:
    return ParsedArgs(
        tool="opencode",
        model="claude-opus-4-8",
        effort="max",
        timeout="15",
        on_error=on_error,
        retry_count=retry_count,
        log_file=log_file,
        prompt_file="",
        tasks="",
        block_end_buffer_min=0,
        devcontainer=False,
        max_iterations=max_iterations,
    )


def _result(
    exit_code: int,
    *,
    complete: bool = False,
    task_summary_count: int | None = None,
    error_text: str | None = None,
) -> ToolResult:
    if task_summary_count is None:
        task_summary_count = 1 if exit_code == 0 else 0
    return ToolResult(
        stdout_path=Path("/tmp/ralph-delta-test.out"),
        exit_code=exit_code,
        signals=IterationSignals(
            task_summary_count=task_summary_count,
            complete=complete,
            error_text=error_text,
        ),
    )


class _ScriptedTool(Tool):
    """Returns pre-baked ToolResults in order; reuses the last on overflow.

    ``calls`` records how many times ``run`` was invoked so retry tests can
    assert the tool was (or was not) re-run within a single iteration.
    """

    def __init__(self, results: list[ToolResult]) -> None:
        self._results = results
        self.calls = 0

    def run(
        self,
        prompt: str,
        timeout_sec: int,
        *,
        on_spawn: OnSpawn | None = None,
    ) -> ToolResult:
        _ = (prompt, timeout_sec, on_spawn)
        idx = min(self.calls, len(self._results) - 1)
        self.calls += 1
        return self._results[idx]


@pytest.fixture
def deltas_loop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Hermetic loop harness: stub the backlog picker + zero the sleep.

    ``current_in_progress_task`` defaults to ``None`` (no In Progress task);
    individual tests re-patch it to exercise the null-clearing branch.
    """
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


def _install_tool(
    monkeypatch: pytest.MonkeyPatch, results: list[ToolResult]
) -> _ScriptedTool:
    tool = _ScriptedTool(results)
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_kw: tool)
    return tool


def _status(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Delta 1 — --on-error retry / --retry-count
# --------------------------------------------------------------------------- #


def test_retry_success_zero_failed_iterations_zero_errors(
    deltas_loop: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Bash ``run-summary-integration.bats``: a retry that later succeeds must
    not count as a failed iteration nor leave a status error."""
    tool = _install_tool(
        monkeypatch,
        [_result(1), _result(0, complete=True)],  # fail once, then succeed
    )
    rc = loop_module.run(_args(on_error="retry", retry_count=2), deltas_loop)

    assert rc == 0
    assert tool.calls == 2  # original attempt + one retry
    out = capsys.readouterr().out
    assert "Tasks completed:    1" in out
    assert "Failed iterations:  0" in out
    assert _status(deltas_loop)["errors"] == []


def test_retry_exhausted_stops_with_error(
    deltas_loop: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """When every retry fails, bash stops with the failure exit code and records
    exactly one iteration failure (ralph.sh:652)."""
    tool = _install_tool(monkeypatch, [_result(1)])  # always fails
    rc = loop_module.run(
        _args(on_error="retry", retry_count=2, max_iterations=3), deltas_loop
    )

    assert rc == 1
    assert tool.calls == 3  # original + 2 retries, then stop
    err = capsys.readouterr().err
    assert "Retrying (attempt 1 of 2)" in err
    assert "Retrying (attempt 2 of 2)" in err
    assert "AI tool failed after 2 retries. Stopping." in err
    status = _status(deltas_loop)
    assert status["state"] == "failed"
    assert len(status["errors"]) == 1


def test_retry_not_applied_to_timeout(
    deltas_loop: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A timed-out iteration (exit 124) is never retried — bash breaks straight
    out of the retry loop regardless of --on-error."""
    tool = _install_tool(monkeypatch, [_result(TIMEOUT_EXIT_CODE)])
    rc = loop_module.run(
        _args(on_error="retry", retry_count=2, max_iterations=1), deltas_loop
    )

    assert rc == 1
    assert tool.calls == 1  # NOT retried
    assert len(_status(deltas_loop)["errors"]) == 1


def test_on_error_continue_does_not_retry(
    deltas_loop: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--on-error continue runs the tool once per iteration (no retry loop)."""
    tool = _install_tool(monkeypatch, [_result(1)])
    loop_module.run(
        _args(on_error="continue", max_iterations=2), deltas_loop
    )
    assert tool.calls == 2  # one call per iteration, never re-run in place


# --------------------------------------------------------------------------- #
# Delta 2 — --log-file
# --------------------------------------------------------------------------- #


def test_log_file_receives_error_line(
    deltas_loop: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bash ``status-file-integration.bats``: --log-file captures ERROR text."""
    log_path = deltas_loop / "errors.log"
    _install_tool(monkeypatch, [_result(1)])
    loop_module.run(
        _args(on_error="stop", log_file=str(log_path)), deltas_loop
    )

    assert log_path.is_file()
    body = log_path.read_text(encoding="utf-8")
    assert "ERROR" in body
    assert "Iteration 1 failed with exit code 1" in body
    assert "(tool: opencode, retry: 0)" in body


def test_append_error_log_empty_path_is_noop(tmp_path: Path) -> None:
    """An empty --log-file writes nothing and raises nothing (bash: LOG_FILE
    unset short-circuits log_error)."""
    loop_module._append_error_log("", 1, 1, "opencode", 0)
    assert list(tmp_path.iterdir()) == []


def test_append_error_log_writes_expected_format(tmp_path: Path) -> None:
    log_path = tmp_path / "e.log"
    loop_module._append_error_log(str(log_path), 4, 2, "claude", 1)
    line = log_path.read_text(encoding="utf-8")
    assert line.startswith("[")
    assert (
        "ERROR: Iteration 4 failed with exit code 2 (tool: claude, retry: 1)"
        in line
    )


# --------------------------------------------------------------------------- #
# Delta 3 — task-summary block-count warning
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("count", "complete", "should_warn"),
    [
        (0, False, True),   # 0 blocks → warn
        (2, False, True),   # 2 blocks → warn
        (1, False, False),  # exactly 1 → no warn
        (3, False, True),   # >1 → warn
        (0, True, False),   # COMPLETE suppresses the warning even with 0 blocks
        (2, True, False),   # COMPLETE suppresses regardless of count
    ],
)
def test_warn_task_summary_count(
    count: int,
    complete: bool,
    should_warn: bool,
    capsys: pytest.CaptureFixture,
) -> None:
    signals = IterationSignals(
        task_summary_count=count, complete=complete, error_text=None
    )
    loop_module._warn_task_summary_count(7, signals)
    err = capsys.readouterr().err
    if should_warn:
        assert (
            f"WARNING: Iteration 7 produced {count} '## Task Summary' "
            "blocks (expected 1)" in err
        )
    else:
        assert "Task Summary" not in err


def test_summary_warning_fires_on_timeout(
    deltas_loop: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Bash ``one-task-enforcement.bats``: a timed-out iteration with 0 summary
    blocks still warns (the transcript is parsed from partial output)."""
    _install_tool(
        monkeypatch, [_result(TIMEOUT_EXIT_CODE, task_summary_count=0)]
    )
    loop_module.run(_args(on_error="continue", max_iterations=1), deltas_loop)
    err = capsys.readouterr().err
    assert "WARNING: Iteration 1 produced 0 '## Task Summary' blocks (expected 1)" in err


def test_no_summary_warning_on_completion(
    deltas_loop: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A COMPLETE signal with 0 blocks must NOT warn (bash suppresses it)."""
    _install_tool(
        monkeypatch, [_result(0, complete=True, task_summary_count=0)]
    )
    loop_module.run(_args(max_iterations=5), deltas_loop)
    assert "Task Summary" not in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# Delta 4 — current_task null-clearing
# --------------------------------------------------------------------------- #


def test_current_task_nulled_when_no_in_progress(
    deltas_loop: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bash ``status-file-integration.bats``: once the picked task moves to Done
    (no In Progress task remains), current_task is re-derived to null."""
    # current_in_progress_task defaults to None in the fixture.
    _install_tool(monkeypatch, [_result(0, complete=True)])
    loop_module.run(_args(max_iterations=1), deltas_loop)
    assert _status(deltas_loop)["current_task"] is None


def test_current_task_reflects_in_progress(
    deltas_loop: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When an In Progress task remains after the iteration, current_task tracks
    it rather than staying stuck at the picked task."""
    monkeypatch.setattr(
        loop_module.tasks_module, "current_in_progress_task", lambda: "TASK-9"
    )
    _install_tool(monkeypatch, [_result(0, complete=True)])
    loop_module.run(_args(max_iterations=1), deltas_loop)
    assert _status(deltas_loop)["current_task"] == "TASK-9"
