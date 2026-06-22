"""Run summary tests (US-005 AC #7)."""

from __future__ import annotations

import io

from ralph.summary import EXIT_REASONS, RunSummary, format_duration, print_summary


def test_exit_reasons_are_the_closed_set() -> None:
    """AC #7 — exit_reason vocabulary is exactly the six allowed strings.

    ``"paused"`` mirrors bash's ``EXIT_REASON="paused"`` at ``ralph.sh:724``
    (TASK-161 — block-end pause must read as distinct from clean completion).
    ``"all specified tasks done"`` mirrors ``ralph.sh:743`` (TASK-162 — every
    ``--tasks`` whitelist entry completed must read as distinct from the
    general-queue-empty exit).
    """
    expected = {
        "all tasks done",
        "all specified tasks done",
        "max iterations reached",
        "error",
        "interrupted",
        "paused",
    }
    assert expected == EXIT_REASONS


def test_format_duration_hours_minutes_seconds() -> None:
    assert format_duration(0) == "0s"
    assert format_duration(45) == "45s"
    assert format_duration(60) == "1m 0s"
    assert format_duration(125) == "2m 5s"
    assert format_duration(3600) == "1h 0m 0s"
    assert format_duration(3725) == "1h 2m 5s"


def test_print_summary_contains_all_labels() -> None:
    summary = RunSummary(
        exit_reason="all tasks done",
        tasks_completed=3,
        tasks_remaining=0,
        iterations_used=3,
        max_iterations=10,
        failed_iterations=0,
        wall_time_sec=125,
        iter_durations_sec=[40, 42, 43],
    )
    buf = io.StringIO()
    print_summary(summary, buf)
    text = buf.getvalue()
    assert "Ralph Run Summary" in text
    assert "Exit reason:        all tasks done" in text
    assert "Tasks completed:    3" in text
    assert "Tasks remaining:    0" in text
    assert "Iterations used:    3 of 10" in text
    assert "Failed iterations:  0" in text
    assert "Total wall time:    2m 5s" in text
    assert "Per-iteration durations:" in text
    assert "Iteration 1: 40s" in text
    assert "Iteration 2: 42s" in text
    assert "Iteration 3: 43s" in text


def test_print_summary_omits_per_iteration_block_when_empty() -> None:
    summary = RunSummary(
        exit_reason="interrupted",
        tasks_completed=0,
        tasks_remaining=5,
        iterations_used=0,
        max_iterations=10,
        failed_iterations=0,
        wall_time_sec=3,
        iter_durations_sec=[],
    )
    buf = io.StringIO()
    print_summary(summary, buf)
    text = buf.getvalue()
    assert "Per-iteration durations:" not in text
    assert "interrupted" in text
