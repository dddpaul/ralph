"""Summary-text parity for whitelist-exhausted vs. queue-empty exits (TASK-162).

Bash equivalent at ``ralph.sh:743`` (whitelist branch) and ``ralph.sh:751``
(general branch)::

    EXIT_REASON="all specified tasks done"   # every --tasks ID completed
    EXIT_REASON="all tasks done"             # general To Do queue empty

Python previously collapsed both to ``"all tasks done"`` at ``loop.py:203``.
These tests pin the bash-parity contract: a whitelist-exhausted run's summary
reads ``all specified tasks done``; a general-queue-empty run still reads
``all tasks done``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph import loop as loop_module
from ralph.args import ParsedArgs


def _args(*, tasks: str = "") -> ParsedArgs:
    return ParsedArgs(
        tool="claude",
        model="claude-opus-4-7",
        effort="max",
        timeout="15",
        on_error="continue",
        retry_count=0,
        log_file="",
        prompt_file="",
        tasks=tasks,
        block_end_buffer_min=0,
        devcontainer=False,
        max_iterations=2,
    )


@pytest.fixture
def stubbed_loop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    # pick_next_task returns None immediately → loop hits the exhausted branch
    # on iteration 1 before ever touching the tool. This keeps the test focused
    # on the exit_reason split.
    monkeypatch.setattr(loop_module.tasks_module, "pick_next_task", lambda **_: None)
    monkeypatch.setattr(loop_module.tasks_module, "count_remaining", lambda *_a, **_kw: 0)
    monkeypatch.setattr(loop_module.tasks_module, "done_task_ids", lambda: [])
    monkeypatch.setattr(loop_module, "check_and_pause", lambda *_a, **_kw: False)
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_kw: None)
    monkeypatch.setattr(loop_module, "ITER_SLEEP_SEC", 0)
    monkeypatch.setenv("RALPH_STATUS_FILE", str(tmp_path / "status.json"))
    monkeypatch.setenv("RALPH_HEARTBEAT_FILE", str(tmp_path / "heartbeat"))
    return tmp_path


def test_whitelist_exhausted_says_all_specified_tasks_done(
    stubbed_loop: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC #2, AC #4, AC #5 — whitelist set and exhausted must yield the
    distinct ``"all specified tasks done"`` reason and summary line."""
    rc = loop_module.run(_args(tasks="1,2,3"), stubbed_loop)
    assert rc == 0

    out = capsys.readouterr().out
    assert "Exit reason:        all specified tasks done" in out
    # The line must NOT be the bare "all tasks done" — guard with the full
    # label so the substring "all tasks done" appearing inside the longer
    # whitelist string doesn't false-pass.
    assert "Exit reason:        all tasks done" not in out


def test_no_whitelist_queue_empty_still_says_all_tasks_done(
    stubbed_loop: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC #3, AC #6 — no whitelist and queue empty still reads as the
    original ``"all tasks done"`` (no regression from the whitelist split)."""
    rc = loop_module.run(_args(tasks=""), stubbed_loop)
    assert rc == 0

    out = capsys.readouterr().out
    assert "Exit reason:        all tasks done" in out
    assert "all specified tasks done" not in out
