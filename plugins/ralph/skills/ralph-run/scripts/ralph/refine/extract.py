"""Artifact / summary / score extraction from LLM transcripts (US-003).

The refine loop chains iterations by pulling three things out of each LLM
call's tee'd transcript (:attr:`ralph.tools.ToolResult.stdout_path`):

* the author's artifact — the text between ``<artifact>`` and ``</artifact>``;
* the reviewer's summary — the text between ``<summary>`` and ``</summary>``;
* the reviewer's score — a line-anchored ``SCORE: N`` (integer 1-10).

Parity notes carried over from the bash ``refine``:

* single-line tags (open + content + close on one line) are accepted
  (refine TASK-10);
* leading blank lines inside a tag are stripped (refine TASK-12);
* on any extraction failure the tee'd transcript is surfaced for post-mortem
  (refine TASK-16) — :class:`ExtractionError` carries it verbatim.

Because the shared tool layer tees stdout and stderr into a single file, each
extractor keys on the tag block (non-greedy) and a line-anchored ``^SCORE:``
and ignores any noise outside them.
"""

from __future__ import annotations

import re
from pathlib import Path

from ralph.tools import ToolResult

__all__ = ["ExtractionError", "Source", "artifact", "score", "summary"]

Source = ToolResult | Path | str
"""Anything an extractor can read a transcript from.

* :class:`ralph.tools.ToolResult` — reads its ``stdout_path`` tee file (the
  loop's primary path; AC #7).
* :class:`pathlib.Path` — reads that file directly (e.g. a saved review file
  on ``--resume``).
* :class:`str` — used verbatim as the transcript text.
"""

_ARTIFACT_TAG = "artifact"
_SUMMARY_TAG = "summary"

_SCORE_MIN = 1
_SCORE_MAX = 10

_SCORE_RE = re.compile(r"^SCORE:\s*(\d+)", re.MULTILINE)
_TAG_RES = {
    tag: re.compile(rf"<{tag}>(.*?)</{tag}>", re.DOTALL)
    for tag in (_ARTIFACT_TAG, _SUMMARY_TAG)
}

_POST_MORTEM_TAIL = 4000
"""Chars of transcript tail embedded in :class:`ExtractionError`'s message so a
post-mortem log line is self-contained; the full transcript stays on the
``transcript`` attribute."""


class ExtractionError(Exception):
    """A required tag or score was missing or invalid in an LLM transcript.

    Signalled to the caller (the refine loop) so its ``--on-error`` strategy
    can decide whether to stop / continue / retry. Carries the tee'd
    transcript so the loop can surface it for post-mortem (refine TASK-16
    parity).

    Attributes:
        transcript: The full tee'd transcript the extraction ran against.
        source: The file the transcript was read from, or ``None`` when the
            extractor was handed a raw ``str``.
    """

    def __init__(
        self,
        message: str,
        *,
        transcript: str,
        source: Path | None = None,
    ) -> None:
        self.transcript = transcript
        self.source = source
        super().__init__(self._compose(message))

    def _compose(self, message: str) -> str:
        where = f" (source: {self.source})" if self.source is not None else ""
        tail = self.transcript[-_POST_MORTEM_TAIL:]
        return f"{message}{where}\n--- LLM transcript (post-mortem) ---\n{tail}"


def artifact(source: Source) -> str:
    """Return the author artifact between ``<artifact>`` and ``</artifact>``.

    Args:
        source: The author call's transcript (see :data:`Source`).

    Returns:
        The artifact body, with leading blank lines and trailing whitespace
        stripped.

    Raises:
        ExtractionError: When no ``<artifact>...</artifact>`` block is present.
    """
    transcript, origin = _coerce(source)
    return _require_tag(transcript, _ARTIFACT_TAG, origin)


def summary(source: Source) -> str:
    """Return the reviewer summary between ``<summary>`` and ``</summary>``.

    Args:
        source: The reviewer call's transcript (see :data:`Source`).

    Returns:
        The summary body, with leading blank lines and trailing whitespace
        stripped.

    Raises:
        ExtractionError: When no ``<summary>...</summary>`` block is present.
    """
    transcript, origin = _coerce(source)
    return _require_tag(transcript, _SUMMARY_TAG, origin)


def score(source: Source) -> int:
    """Return the reviewer's line-anchored ``SCORE: N`` value.

    The last line-anchored ``^SCORE:`` line wins, so a reviewer that restates
    a prior score before emitting its own verdict still resolves to the
    verdict. Non-anchored mentions (``the SCORE: was 3``) are ignored.

    Args:
        source: The reviewer call's transcript (see :data:`Source`).

    Returns:
        The parsed score.

    Raises:
        ExtractionError: When no line-anchored ``SCORE: N`` is present, or the
            parsed value falls outside ``1-10``.
    """
    transcript, origin = _coerce(source)
    matches = _SCORE_RE.findall(transcript)
    if not matches:
        raise ExtractionError(
            "No line-anchored 'SCORE: N' line found in reviewer output",
            transcript=transcript,
            source=origin,
        )
    value = int(matches[-1])
    if not _SCORE_MIN <= value <= _SCORE_MAX:
        raise ExtractionError(
            f"SCORE {value} is out of range {_SCORE_MIN}-{_SCORE_MAX}",
            transcript=transcript,
            source=origin,
        )
    return value


def _coerce(source: Source) -> tuple[str, Path | None]:
    """Resolve a :data:`Source` to ``(transcript_text, origin_path_or_None)``.

    File reads use ``errors="replace"`` so a stray non-UTF-8 byte from a tool
    that mishandles a code page cannot derail extraction — the tag protocol
    and ``SCORE:`` line are ASCII and survive substitution (parity with
    :func:`ralph.signals.parse_file`).
    """
    if isinstance(source, ToolResult):
        path = source.stdout_path
        return path.read_text(encoding="utf-8", errors="replace"), path
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8", errors="replace"), source
    return source, None


def _require_tag(transcript: str, tag: str, origin: Path | None) -> str:
    body = _find_tag(transcript, tag)
    if body is None:
        raise ExtractionError(
            f"Missing <{tag}>...</{tag}> block in LLM output",
            transcript=transcript,
            source=origin,
        )
    return body


def _find_tag(transcript: str, tag: str) -> str | None:
    match = _TAG_RES[tag].search(transcript)
    if match is None:
        return None
    return _strip_leading_blank_lines(match.group(1))


def _strip_leading_blank_lines(raw: str) -> str:
    """Drop leading whitespace-only lines (refine TASK-12), rstrip the tail.

    Single-line tag bodies (refine TASK-10) survive untouched: there are no
    leading blank lines to drop and no meaningful trailing whitespace.
    """
    lines = raw.splitlines()
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    return "\n".join(lines[start:]).rstrip()
