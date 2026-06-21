"""Iteration sentinel parser — surfaces the signals bash scrapes from tool output.

Bash equivalents:

* ``grep -q '<promise>COMPLETE</promise>' "$OUTFILE"`` — completion sentinel.
* ``grep -c '^## Task Summary$' "$OUTFILE"`` — agent-emitted task-summary
  block count (warned to stderr when != 1 unless ``<promise>COMPLETE</promise>``
  appeared).

The Python orchestrator parses these once per iteration and surfaces the
result as a dataclass so the main loop can branch on completion, count
summaries, and capture an error excerpt without re-reading the file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_PROMISE_COMPLETE = "<promise>COMPLETE</promise>"
_TASK_SUMMARY_RE = re.compile(r"^## Task Summary$", re.MULTILINE)
_ERROR_LINE_RE = re.compile(r"^\s*(?:ERROR|Error):\s*(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class IterationSignals:
    """Sentinels extracted from one iteration's transcript.

    Attributes:
        task_summary_count: Number of ``## Task Summary`` blocks (anchored at
            start of line) detected in the transcript.
        complete: ``True`` when ``<promise>COMPLETE</promise>`` is present —
            the agent's signal that the loop should exit cleanly.
        error_text: First ``ERROR:`` line surfaced by the tool (or ``None`` if
            no such line is present). Used to populate the structured error
            entry written to ``StatusFile.errors``.
    """

    task_summary_count: int
    complete: bool
    error_text: str | None


def parse_text(text: str) -> IterationSignals:
    """Parse signals from an in-memory transcript string."""
    return IterationSignals(
        task_summary_count=len(_TASK_SUMMARY_RE.findall(text)),
        complete=_PROMISE_COMPLETE in text,
        error_text=_first_error(text),
    )


def parse_file(path: Path) -> IterationSignals:
    """Parse signals from a transcript file on disk.

    Reads with ``errors="replace"`` so a stray non-UTF-8 byte from a tool
    that mishandles a code page does not derail the loop — sentinel
    detection is line-based ASCII and survives substitution.
    """
    return parse_text(path.read_text(encoding="utf-8", errors="replace"))


def _first_error(text: str) -> str | None:
    match = _ERROR_LINE_RE.search(text)
    if match is None:
        return None
    return match.group(1).strip() or None
