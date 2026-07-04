"""Between-iteration ``tasks_remaining`` honors ``--tasks`` whitelist (TASK-164).

Bash parity: ``ralph.sh`` calls ``count_remaining_tasks`` with the whitelist
on every write (start, between, and final). The Python port matched this at
start-of-iteration (``loop.py:215``) and in the run summary (``loop.py:352``)
but the between-iteration write at ``loop.py:321`` previously called
``count_remaining()`` with no whitelist — inflating ``tasks_remaining`` in
the JSON snapshot any external reader saw between iterations.

These tests pin the contract: every JSON write during a whitelisted run uses
the whitelisted count; non-whitelist runs remain unaffected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ralph import loop as loop_module
from ralph.args import ParsedArgs
from ralph.signals import IterationSignals
from ralph.status import StatusFile
from ralph.tools import OnSpawn, Tool, ToolResult

_TOTAL_TODO = 99
_WHITELIST_REMAINING = 2


def _args(*, tasks: str, max_iterations: int = 2) -> ParsedArgs:
    return ParsedArgs(
        tool="claude",
        model="claude-opus-4-8",
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


class _ScriptedTool(Tool):
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
                task_summary_count=1, complete=False, error_text=None
            ),
        )


def _stub_count_remaining(whitelist: list[str] | None) -> int:
    """Return a distinct value depending on whether whitelist was supplied.

    The two return values (``_WHITELIST_REMAINING`` vs ``_TOTAL_TODO``) let the
    test prove WHICH branch the loop took when writing the JSON snapshot —
    a `tasks_remaining=99` between iterations would be the pre-fix bug.
    """
    return _WHITELIST_REMAINING if whitelist else _TOTAL_TODO


@pytest.fixture
def stubbed_loop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, list[int]]:
    """Stub backlog calls; capture every ``tasks_remaining`` written to disk.

    Returns ``(status_path, writes)`` where ``writes`` accumulates the
    ``tasks_remaining`` field on each ``write_atomic`` call, in order. The
    test asserts both the per-write values AND the final file content.
    """
    monkeypatch.setattr(
        loop_module.tasks_module, "pick_next_task", lambda **_: "TASK-1"
    )
    monkeypatch.setattr(
        loop_module.tasks_module,
        "count_remaining",
        lambda whitelist=None: _stub_count_remaining(whitelist),
    )
    monkeypatch.setattr(loop_module.tasks_module, "done_task_ids", lambda: [])
    monkeypatch.setattr(
        loop_module.tasks_module, "current_in_progress_task", lambda: None
    )
    monkeypatch.setattr(loop_module, "check_and_pause", lambda *_a, **_kw: False)
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_kw: _ScriptedTool())
    monkeypatch.setattr(loop_module, "ITER_SLEEP_SEC", 0)

    status_path = tmp_path / "status.json"
    monkeypatch.setenv("RALPH_STATUS_FILE", str(status_path))
    monkeypatch.setenv("RALPH_HEARTBEAT_FILE", str(tmp_path / "heartbeat"))

    writes: list[int] = []
    real_write = StatusFile.write_atomic

    def _spy_write(self: StatusFile, path: Path) -> None:
        writes.append(self.tasks_remaining)
        real_write(self, path)

    monkeypatch.setattr(StatusFile, "write_atomic", _spy_write)
    return status_path, writes


def test_whitelist_between_iteration_uses_whitelisted_count(
    stubbed_loop: tuple[Path, list[int]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC #1, #2, #4 — every JSON write during a whitelisted run reports the
    whitelisted ``tasks_remaining`` (here: 2), never the inflated 99 count.

    The 99-vs-2 split is the load-bearing assertion: a regression where
    ``_update_after_iteration`` drops the whitelist would surface as a 99
    landing in ``writes`` between iterations.
    """
    status_path, writes = stubbed_loop
    rc = loop_module.run(_args(tasks="1,2,3", max_iterations=2), status_path.parent)
    assert rc == 0

    assert writes, "expected at least one status write"
    assert all(n == _WHITELIST_REMAINING for n in writes), (
        f"all writes must report the whitelisted count, got {writes!r}"
    )

    final = json.loads(status_path.read_text())
    assert final["tasks_remaining"] == _WHITELIST_REMAINING

    summary = capsys.readouterr().out
    assert f"Tasks remaining:    {_WHITELIST_REMAINING}" in summary


def test_no_whitelist_run_unaffected(
    stubbed_loop: tuple[Path, list[int]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC #3 — no whitelist → every write still reflects the full To Do
    queue count (99), confirming the fix didn't regress the bash-parity
    behavior of non-whitelisted runs.
    """
    status_path, writes = stubbed_loop
    rc = loop_module.run(_args(tasks="", max_iterations=2), status_path.parent)
    assert rc == 0

    assert writes
    assert all(n == _TOTAL_TODO for n in writes), (
        f"non-whitelist run must report full To Do count, got {writes!r}"
    )

    final = json.loads(status_path.read_text())
    assert final["tasks_remaining"] == _TOTAL_TODO

    summary = capsys.readouterr().out
    assert f"Tasks remaining:    {_TOTAL_TODO}" in summary
