"""Refine run summary — the score/delta table written to ``summary.md`` (US-005).

The loop records one reviewer score per completed iteration. When the run
terminates (threshold met, or max iterations reached) it writes a Markdown
``summary.md`` next to the artifacts so a human can see the score trajectory at
a glance: the per-iteration table with the round-over-round *delta*, plus the
final score, the threshold, and how many iterations ran (AC #5).

Like :mod:`ralph.refine.roles`, this module is a **pure** renderer: it takes the
already-collected scores and returns a Markdown string. The file write stays in
:mod:`ralph.refine.loop`, which keeps every rendering path directly unit-testable.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["RefineSummary", "render_summary"]

_BASELINE_DELTA = "—"
"""First-iteration delta placeholder: there is no prior score to diff against."""


@dataclass(frozen=True)
class RefineSummary:
    """Inputs to :func:`render_summary`.

    Attributes:
        scores: Reviewer scores in iteration order (``scores[0]`` is
            iteration 1). May be empty only on degenerate error paths — the
            renderer tolerates it.
        threshold: The ``--threshold`` the run targeted.
        reached_threshold: ``True`` when the final score met the threshold
            (exit 0 path); ``False`` for the max-iterations fall-through
            (exit 1 path). Drives the rendered "Result" line.
    """

    scores: Sequence[int]
    threshold: int
    reached_threshold: bool

    @property
    def iterations(self) -> int:
        """Number of scored iterations (table rows)."""
        return len(self.scores)

    @property
    def final_score(self) -> int | None:
        """The last reviewer score, or ``None`` when no iteration completed."""
        return self.scores[-1] if self.scores else None


def _delta(scores: Sequence[int], index: int) -> str:
    """Render the score delta for ``scores[index]`` versus the prior score.

    Iteration 1 (``index == 0``) has no predecessor and renders as the
    baseline placeholder. Later iterations render a signed delta
    (``"+2"`` / ``"-1"`` / ``"0"``) so the trend reads at a glance.
    """
    if index == 0:
        return _BASELINE_DELTA
    change = scores[index] - scores[index - 1]
    return f"+{change}" if change > 0 else str(change)


def render_summary(summary: RefineSummary) -> str:
    """Render ``summary`` as the Markdown body of ``summary.md``.

    Args:
        summary: The collected scores plus threshold / outcome context.

    Returns:
        A Markdown document: an ``| Iteration | Score | Delta |`` table
        followed by a final-score / threshold / iteration-count / result
        block. Always ends with a trailing newline.
    """
    lines = [
        "# Refine Summary",
        "",
        "| Iteration | Score | Delta |",
        "| --- | --- | --- |",
    ]
    for i, score in enumerate(summary.scores):
        lines.append(f"| {i + 1} | {score} | {_delta(summary.scores, i)} |")

    final = summary.final_score
    final_text = f"{final} / 10" if final is not None else "n/a"
    result = (
        "threshold reached"
        if summary.reached_threshold
        else "max iterations reached without meeting threshold"
    )
    lines.extend(
        [
            "",
            f"- **Final score:** {final_text}",
            f"- **Threshold:** {summary.threshold}",
            f"- **Iterations:** {summary.iterations}",
            f"- **Result:** {result}",
            "",
        ]
    )
    return "\n".join(lines)
