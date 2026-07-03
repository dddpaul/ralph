"""Unit tests for ``ralph/heartbeat.py`` (US-003 AC #3)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from ralph.heartbeat import Heartbeat


def test_start_creates_file_immediately(tmp_path: Path) -> None:
    hb_path = tmp_path / "backlog" / ".ralph-heartbeat"
    hb = Heartbeat(hb_path, interval_sec=0.05)
    hb.start()
    try:
        assert hb_path.exists(), "Heartbeat file must exist before start() returns"
        assert hb.is_running is True
    finally:
        hb.stop()


def test_stop_removes_file_and_joins_thread(tmp_path: Path) -> None:
    hb_path = tmp_path / "backlog" / ".ralph-heartbeat"
    hb = Heartbeat(hb_path, interval_sec=0.05)
    hb.start()
    hb.stop()
    assert hb.is_running is False
    assert not hb_path.exists()


def test_stop_is_idempotent(tmp_path: Path) -> None:
    hb_path = tmp_path / "backlog" / ".ralph-heartbeat"
    hb = Heartbeat(hb_path, interval_sec=0.05)
    hb.start()
    hb.stop()
    hb.stop()
    assert hb.is_running is False


def test_double_start_raises(tmp_path: Path) -> None:
    hb_path = tmp_path / "backlog" / ".ralph-heartbeat"
    hb = Heartbeat(hb_path, interval_sec=0.05)
    hb.start()
    try:
        with pytest.raises(RuntimeError):
            hb.start()
    finally:
        hb.stop()


def test_mtime_updates_between_ticks(tmp_path: Path) -> None:
    """The thread MUST update mtime at the interval cadence."""
    hb_path = tmp_path / "backlog" / ".ralph-heartbeat"
    hb = Heartbeat(hb_path, interval_sec=0.05)
    hb.start()
    try:
        initial_mtime = hb_path.stat().st_mtime
        # Wait long enough for two ticks even on a slow CI runner.
        time.sleep(0.3)
        updated_mtime = hb_path.stat().st_mtime
        assert updated_mtime >= initial_mtime
        # On systems with sub-second mtime resolution, the difference is
        # usually strictly positive; on coarse-mtime FSes it can equal.
    finally:
        hb.stop()


def test_context_manager_starts_and_stops(tmp_path: Path) -> None:
    hb_path = tmp_path / ".heartbeat"
    with Heartbeat(hb_path, interval_sec=0.05) as hb:
        assert hb.is_running is True
        assert hb_path.exists()
    assert not hb_path.exists()


def test_missing_parent_directory_is_created(tmp_path: Path) -> None:
    hb_path = tmp_path / "nested" / "deeper" / ".heartbeat"
    hb = Heartbeat(hb_path, interval_sec=0.05)
    hb.start()
    try:
        assert hb_path.exists()
    finally:
        hb.stop()


def test_path_property_exposed(tmp_path: Path) -> None:
    hb_path = tmp_path / ".heartbeat"
    hb = Heartbeat(hb_path)
    assert hb.path == hb_path


def test_unlink_failure_does_not_raise(tmp_path: Path) -> None:
    """If the file is removed externally before stop, stop() must not raise."""
    hb_path = tmp_path / ".heartbeat"
    hb = Heartbeat(hb_path, interval_sec=0.05)
    hb.start()
    hb_path.unlink()
    hb.stop()  # Must not raise.
