"""Unit tests for ``ralph/usage.py`` (US-003 AC #4).

The wrapper sits between ``ralph.usage_check`` (US-002) and the
``StatusFile`` pause-field block. Tests stub ``usage_check.evaluate`` so
the wrapper logic is exercised without real ``ccusage``.
"""

from __future__ import annotations

import pytest

from ralph import usage, usage_check
from ralph.status import StatusFile


def _fresh_status() -> StatusFile:
    return StatusFile(
        pid=4242,
        started_at="2026-06-21T15:00:00Z",
        state="running",
        iteration=2,
        max_iterations=10,
        tool="claude",
        tasks_remaining=5,
        elapsed=120,
        timeout_sec=900,
    )


def _stub_evaluate(monkeypatch: pytest.MonkeyPatch, rc: int, out: str = "") -> None:
    monkeypatch.setattr(
        usage_check, "evaluate", lambda buffer_min_raw: (rc, out, "")
    )


def _disable_block_end_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(usage, "_read_block_end_time", lambda: None)


def test_buffer_zero_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    """``buffer_min == 0`` returns False without calling usage_check."""
    sentinel: dict[str, bool] = {"called": False}

    def boom(_buffer_min_raw: str) -> tuple[int, str, str]:
        sentinel["called"] = True
        return (0, "", "")

    monkeypatch.setattr(usage_check, "evaluate", boom)
    status = _fresh_status()
    assert usage.check_and_pause(status, 0) is False
    assert sentinel["called"] is False
    assert status.paused_reason is None


def test_buffer_negative_treated_as_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defensive: a stray negative integer must NOT call usage_check."""
    sentinel: dict[str, bool] = {"called": False}

    def boom(_buffer_min_raw: str) -> tuple[int, str, str]:
        sentinel["called"] = True
        return (0, "", "")

    monkeypatch.setattr(usage_check, "evaluate", boom)
    assert usage.check_and_pause(_fresh_status(), -5) is False
    assert sentinel["called"] is False


def test_room_remaining_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_evaluate(monkeypatch, 0)
    _disable_block_end_probe(monkeypatch)
    status = _fresh_status()
    assert usage.check_and_pause(status, 5) is False
    assert status.paused_reason is None
    assert status.paused_at is None


def test_unmeasurable_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_evaluate(monkeypatch, 2)
    _disable_block_end_probe(monkeypatch)
    status = _fresh_status()
    assert usage.check_and_pause(status, 5) is False
    assert status.paused_reason is None


def test_pause_populates_all_five_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_evaluate(monkeypatch, 1, "block_end_in_3min_below_5min_buffer\n")
    monkeypatch.setattr(
        usage, "_read_block_end_time", lambda: "2026-06-21T20:00:00Z"
    )

    status = _fresh_status()
    paused = usage.check_and_pause(status, 5, now="2026-06-21T15:42:00Z")
    assert paused is True
    assert status.paused_reason == "block_end_in_3min_below_5min_buffer"
    assert status.paused_buffer_min == 5
    assert status.paused_remaining_min == 3
    assert status.paused_block_end_time == "2026-06-21T20:00:00Z"
    assert status.paused_at == "2026-06-21T15:42:00Z"


def test_pause_handles_missing_block_end_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``ccusage`` is absent, ``paused_block_end_time`` stays ``None``."""
    _stub_evaluate(monkeypatch, 1, "block_end_in_2min_below_4min_buffer\n")
    _disable_block_end_probe(monkeypatch)
    status = _fresh_status()
    paused = usage.check_and_pause(status, 4, now="2026-06-21T15:42:00Z")
    assert paused is True
    assert status.paused_block_end_time is None
    assert status.paused_remaining_min == 2


def test_pause_handles_unparseable_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the helper returns exit 1 with an unexpected string, remaining = 0."""
    _stub_evaluate(monkeypatch, 1, "unexpected_output\n")
    _disable_block_end_probe(monkeypatch)
    status = _fresh_status()
    paused = usage.check_and_pause(status, 4, now="2026-06-21T15:00:00Z")
    assert paused is True
    assert status.paused_reason == "unexpected_output"
    assert status.paused_remaining_min == 0
    assert status.paused_buffer_min == 4


def test_pause_stamps_default_paused_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_evaluate(monkeypatch, 1, "block_end_in_1min_below_5min_buffer\n")
    _disable_block_end_probe(monkeypatch)
    status = _fresh_status()
    assert usage.check_and_pause(status, 5) is True
    assert status.paused_at is not None
    assert status.paused_at.endswith("Z")
    # ISO8601 UTC timestamps from the wrapper end in 'Z' and have the
    # standard 20-character form ``YYYY-MM-DDTHH:MM:SSZ``.
    assert len(status.paused_at) == 20


def test_clear_pause_resets_all_fields() -> None:
    status = _fresh_status()
    status.paused_reason = "x"
    status.paused_buffer_min = 5
    status.paused_remaining_min = 1
    status.paused_block_end_time = "2026-06-21T20:00:00Z"
    status.paused_at = "2026-06-21T15:42:00Z"
    usage.clear_pause(status)
    assert status.paused_reason is None
    assert status.paused_buffer_min is None
    assert status.paused_remaining_min is None
    assert status.paused_block_end_time is None
    assert status.paused_at is None
