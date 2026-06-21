"""Run summary printer — bash-parity output for every exit path.

Mirrors ``print_summary()`` in ``ralph.sh:304-334``. The exit-reason vocabulary
is the closed set ``{"all tasks done", "max iterations reached", "error",
"interrupted"}`` (PRD §6 + TASK-5 historical-context appendix).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import IO

EXIT_REASONS: frozenset[str] = frozenset(
    {"all tasks done", "max iterations reached", "error", "interrupted"}
)


@dataclass(frozen=True)
class RunSummary:
    """Inputs to :func:`print_summary` — one dataclass keeps argument shape stable."""

    exit_reason: str
    tasks_completed: int
    tasks_remaining: int
    iterations_used: int
    max_iterations: int
    failed_iterations: int
    wall_time_sec: int
    iter_durations_sec: Sequence[int]


def format_duration(seconds: int) -> str:
    """Format ``seconds`` as ``"1h 2m 3s"`` / ``"2m 3s"`` / ``"5s"`` (bash parity)."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def print_summary(summary: RunSummary, out: IO[str]) -> None:
    """Emit the bash-style summary block to ``out``.

    Output is byte-identical (modulo trailing newlines) to the bash
    ``print_summary`` function so log scrapers keyed on these labels keep
    working.
    """
    print("", file=out)
    print("===============================", file=out)
    print("  Ralph Run Summary", file=out)
    print("===============================", file=out)
    print(f"Exit reason:        {summary.exit_reason}", file=out)
    print(f"Tasks completed:    {summary.tasks_completed}", file=out)
    print(f"Tasks remaining:    {summary.tasks_remaining}", file=out)
    print(
        f"Iterations used:    {summary.iterations_used} of "
        f"{summary.max_iterations}",
        file=out,
    )
    print(f"Failed iterations:  {summary.failed_iterations}", file=out)
    print(f"Total wall time:    {format_duration(summary.wall_time_sec)}", file=out)
    if summary.iter_durations_sec:
        print("", file=out)
        print("Per-iteration durations:", file=out)
        for idx, dur in enumerate(summary.iter_durations_sec, start=1):
            print(f"  Iteration {idx}: {format_duration(dur)}", file=out)
    print("===============================", file=out)
