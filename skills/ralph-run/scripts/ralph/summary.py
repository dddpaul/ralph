"""Run summary printer — bash-parity output for every exit path.

Mirrors ``print_summary()`` in ``ralph.sh:304-334``. The exit-reason vocabulary
is the closed set ``{"all tasks done", "all specified tasks done",
"max iterations reached", "error", "interrupted", "paused"}``. The
``"paused"`` entry mirrors bash's ``EXIT_REASON="paused"`` at ``ralph.sh:724``
(block-end usage-cap pause). The ``"all specified tasks done"`` entry mirrors
bash's ``EXIT_REASON="all specified tasks done"`` at ``ralph.sh:743`` (every
``--tasks`` whitelist entry completed) so the summary distinguishes a
whitelist-exhausted run from a general-queue-empty run.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import IO

EXIT_REASONS: frozenset[str] = frozenset(
    {
        "all tasks done",
        "all specified tasks done",
        "max iterations reached",
        "error",
        "interrupted",
        "paused",
    }
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

    The ``"max iterations reached"`` exit_reason is rendered with a
    ``" (N task(s) completed)"`` suffix templated from
    ``summary.tasks_completed``. Bash equivalent at ``ralph.sh:890``
    interpolates the count directly into ``EXIT_REASON``; Python keeps
    :data:`EXIT_REASONS` as a flat closed set (exit-classification state)
    and templates the count at the presentation boundary. The literal
    ``"task(s)"`` is intentional — bash does not pluralize.
    """
    exit_reason_text = summary.exit_reason
    if summary.exit_reason == "max iterations reached":
        exit_reason_text = (
            f"max iterations reached ({summary.tasks_completed} task(s) completed)"
        )
    print("", file=out)
    print("===============================", file=out)
    print("  Ralph Run Summary", file=out)
    print("===============================", file=out)
    print(f"Exit reason:        {exit_reason_text}", file=out)
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
