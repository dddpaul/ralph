"""Unit + golden-file tests for ``ralph/signals.py`` (US-003 AC #1, #7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph.signals import IterationSignals, parse_file, parse_text

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "signals"


@pytest.mark.parametrize(
    ("name", "summaries", "complete"),
    [
        ("complete_one_summary.txt", 1, True),
        ("incomplete_one_summary.txt", 1, False),
        ("zero_summaries.txt", 0, False),
        ("two_summaries.txt", 2, True),
        ("inline_summary_not_anchored.txt", 1, False),
    ],
)
def test_golden_signal_counts(name: str, summaries: int, complete: bool) -> None:
    fixture = FIXTURES_DIR / name
    signals = parse_file(fixture)
    assert signals.task_summary_count == summaries
    assert signals.complete is complete


def test_parse_text_returns_dataclass() -> None:
    signals = parse_text(
        "## Task Summary\n- thing\n<promise>COMPLETE</promise>\n"
    )
    assert isinstance(signals, IterationSignals)
    assert signals.task_summary_count == 1
    assert signals.complete is True


def test_summary_with_trailing_whitespace_does_not_match() -> None:
    """Bash uses ``grep -c '^## Task Summary$'`` — strict anchored equality."""
    signals = parse_text("## Task Summary \n")
    assert signals.task_summary_count == 0


def test_summary_with_extra_prefix_does_not_match() -> None:
    signals = parse_text("Note: ## Task Summary\n")
    assert signals.task_summary_count == 0


def test_complete_sentinel_anywhere_in_output() -> None:
    """The completion sentinel only needs substring presence (bash grep -q)."""
    signals = parse_text("blah blah <promise>COMPLETE</promise> blah\n")
    assert signals.complete is True


def test_complete_sentinel_case_sensitive() -> None:
    signals = parse_text("<promise>complete</promise>\n")
    assert signals.complete is False


def test_no_complete_sentinel() -> None:
    signals = parse_text("just some output\n")
    assert signals.complete is False


def test_error_text_first_match() -> None:
    signals = parse_text(
        "doing thing\nERROR: first failure\nERROR: second failure\n"
    )
    assert signals.error_text == "first failure"


def test_error_text_handles_lowercase_label() -> None:
    signals = parse_text("Error: subtly cased\n")
    assert signals.error_text == "subtly cased"


def test_error_text_none_when_absent() -> None:
    signals = parse_text("clean run\n")
    assert signals.error_text is None


def test_parse_file_handles_replacement_chars(tmp_path: Path) -> None:
    """A stray invalid byte must not derail ASCII sentinel detection."""
    transcript = tmp_path / "out.txt"
    transcript.write_bytes(b"## Task Summary\nbad byte: \xff\n<promise>COMPLETE</promise>\n")
    signals = parse_file(transcript)
    assert signals.task_summary_count == 1
    assert signals.complete is True


def test_signals_dataclass_is_frozen() -> None:
    signals = IterationSignals(task_summary_count=1, complete=True, error_text=None)
    with pytest.raises(AttributeError):
        signals.task_summary_count = 2  # type: ignore[misc]
