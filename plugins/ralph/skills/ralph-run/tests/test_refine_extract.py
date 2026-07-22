"""Extraction tests for ``ralph.refine.extract`` (US-003 AC #1-8).

Covers artifact / summary / score extraction, the single-line-tag and
leading-blank-line parity cases (refine TASK-10 / TASK-12), the post-mortem
transcript surfacing on failure (refine TASK-16), and reading from a real
``ToolResult.stdout_path`` tee file while ignoring noise outside the tag block.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph.refine import extract
from ralph.refine.extract import ExtractionError
from ralph.signals import parse_text
from ralph.tools import ToolResult


def _result(tmp_path: Path, text: str) -> ToolResult:
    """Build a ``ToolResult`` whose ``stdout_path`` tee holds ``text``."""
    tee = tmp_path / "transcript.out"
    tee.write_text(text, encoding="utf-8")
    return ToolResult(stdout_path=tee, exit_code=0, signals=parse_text(text))


# --------------------------------------------------------------------------- #
# AC #1 — artifact()
# --------------------------------------------------------------------------- #
def test_artifact_returns_content_between_tags() -> None:
    """AC #1 — the body between the tags is returned verbatim."""
    text = "chatter\n<artifact>\n# Title\n\nBody line\n</artifact>\ntrailer"
    assert extract.artifact(text) == "# Title\n\nBody line"


def test_artifact_preserves_internal_blank_lines() -> None:
    """AC #1 — only *leading* blanks are dropped; internal ones stay."""
    text = "<artifact>\npara one\n\npara two\n</artifact>"
    assert extract.artifact(text) == "para one\n\npara two"


def test_artifact_missing_tags_raises(tmp_path: Path) -> None:
    """AC #1 — absent tags signal an error to the caller."""
    with pytest.raises(ExtractionError):
        extract.artifact(_result(tmp_path, "no tags at all here"))


def test_artifact_missing_close_tag_raises() -> None:
    """AC #1 — an unterminated block is not a match."""
    with pytest.raises(ExtractionError):
        extract.artifact("<artifact>\nunterminated body\n")


# --------------------------------------------------------------------------- #
# AC #2 — summary()
# --------------------------------------------------------------------------- #
def test_summary_returns_content_between_tags() -> None:
    """AC #2 — the reviewer summary body is returned."""
    text = "SCORE: 7\n<summary>\nTighten the intro.\n</summary>\n"
    assert extract.summary(text) == "Tighten the intro."


def test_summary_missing_tags_raises(tmp_path: Path) -> None:
    """AC #2 — absent tags signal an error to the caller."""
    with pytest.raises(ExtractionError):
        extract.summary(_result(tmp_path, "SCORE: 7\nno summary block"))


# --------------------------------------------------------------------------- #
# AC #3 — score()
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("value", range(1, 11))
def test_score_parses_full_valid_range(value: int) -> None:
    """AC #3 — every integer 1-10 on an anchored SCORE line parses."""
    assert extract.score(f"verdict\nSCORE: {value}\n") == value


def test_score_allows_missing_space_after_colon() -> None:
    """AC #3 — ``\\s*`` permits ``SCORE:8`` with no space."""
    assert extract.score("SCORE:8\n") == 8


def test_score_missing_raises(tmp_path: Path) -> None:
    """AC #3 — no anchored SCORE line signals an error."""
    with pytest.raises(ExtractionError):
        extract.score(_result(tmp_path, "the review has no score line"))


def test_score_requires_line_anchor() -> None:
    """AC #3 — a mid-line ``SCORE:`` mention is not a match."""
    with pytest.raises(ExtractionError):
        extract.score("the final SCORE: 9 was fair, but ...")


@pytest.mark.parametrize("value", [0, 11, 42, 100])
def test_score_out_of_range_raises(value: int) -> None:
    """AC #3 — a parsed value outside 1-10 signals an error."""
    with pytest.raises(ExtractionError):
        extract.score(f"SCORE: {value}\n")


def test_score_last_anchored_line_wins() -> None:
    """AC #3 — a restated earlier score is overridden by the final verdict."""
    text = "Last round was\nSCORE: 5\nNow improved:\nSCORE: 9\n"
    assert extract.score(text) == 9


# --------------------------------------------------------------------------- #
# AC #4 — single-line tags (refine TASK-10 parity)
# --------------------------------------------------------------------------- #
def test_artifact_single_line_tag() -> None:
    """AC #4 — open + content + close on one line is handled."""
    assert extract.artifact("<artifact>one liner</artifact>") == "one liner"


def test_summary_single_line_tag() -> None:
    """AC #4 — the same single-line handling for summary."""
    assert extract.summary("<summary>looks good</summary>") == "looks good"


def test_single_line_tag_with_surrounding_noise() -> None:
    """AC #4 + #7 — a single-line tag is found amid other output."""
    text = "log: starting\n<artifact>inline</artifact>\nlog: done"
    assert extract.artifact(text) == "inline"


# --------------------------------------------------------------------------- #
# AC #5 — leading blank lines stripped (refine TASK-12 parity)
# --------------------------------------------------------------------------- #
def test_artifact_strips_leading_blank_lines() -> None:
    """AC #5 — blank lines right after ``<artifact>`` are dropped."""
    text = "<artifact>\n\n\n   \nfirst real line\n</artifact>"
    assert extract.artifact(text) == "first real line"


def test_summary_strips_leading_blank_lines() -> None:
    """AC #5 — same leading-blank stripping for summary."""
    assert extract.summary("<summary>\n\nfeedback\n</summary>") == "feedback"


# --------------------------------------------------------------------------- #
# AC #6 — post-mortem transcript surfaced on failure (refine TASK-16 parity)
# --------------------------------------------------------------------------- #
def test_extraction_error_carries_full_transcript(tmp_path: Path) -> None:
    """AC #6 — the tee'd transcript is attached to the error verbatim."""
    tee_text = "reviewer said things\nbut emitted no score line\n"
    with pytest.raises(ExtractionError) as exc_info:
        extract.score(_result(tmp_path, tee_text))
    assert exc_info.value.transcript == tee_text


def test_extraction_error_message_includes_transcript_and_source(
    tmp_path: Path,
) -> None:
    """AC #6 — the error message embeds the transcript tail and source path."""
    result = _result(tmp_path, "garbage output with no artifact tag")
    with pytest.raises(ExtractionError) as exc_info:
        extract.artifact(result)
    message = str(exc_info.value)
    assert "garbage output with no artifact tag" in message
    assert str(result.stdout_path) in message
    assert exc_info.value.source == result.stdout_path


def test_extraction_error_from_str_has_no_source() -> None:
    """AC #6 — a raw-``str`` source leaves ``source`` unset but keeps text."""
    with pytest.raises(ExtractionError) as exc_info:
        extract.summary("no tags")
    assert exc_info.value.source is None
    assert exc_info.value.transcript == "no tags"


# --------------------------------------------------------------------------- #
# AC #7 — reads from ToolResult.stdout_path tee, ignores outside-block noise
# --------------------------------------------------------------------------- #
def test_reads_from_toolresult_stdout_path(tmp_path: Path) -> None:
    """AC #7 — extraction reads the tee file named by ``stdout_path``."""
    result = _result(tmp_path, "<artifact>\nfrom the tee file\n</artifact>")
    assert extract.artifact(result) == "from the tee file"


def test_reads_from_plain_path(tmp_path: Path) -> None:
    """AC #7 — a bare ``Path`` (e.g. a saved review file) is read too."""
    review = tmp_path / "review-v1.md"
    review.write_text("SCORE: 6\n<summary>ok</summary>\n", encoding="utf-8")
    assert extract.score(review) == 6
    assert extract.summary(review) == "ok"


def test_ignores_noise_outside_tag_block(tmp_path: Path) -> None:
    """AC #7 — combined stdout/stderr noise around the block is ignored."""
    text = (
        "warning: some tool chatter on stderr\n"
        "[stream] token token token\n"
        "<artifact>\n"
        "the real content\n"
        "</artifact>\n"
        "info: wrote 1 file\n"
    )
    assert extract.artifact(_result(tmp_path, text)) == "the real content"


def test_score_ignores_noise_and_unanchored_mentions(tmp_path: Path) -> None:
    """AC #7 — surrounding noise + non-anchored SCORE text is ignored."""
    text = (
        "note: the previous SCORE: 2 was low\n"
        "here is my review with lots of detail\n"
        "SCORE: 8\n"
        "trailing stderr line\n"
    )
    assert extract.score(_result(tmp_path, text)) == 8
