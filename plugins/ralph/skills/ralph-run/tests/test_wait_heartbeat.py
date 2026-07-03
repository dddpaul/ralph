"""Unit tests for ``ralph/wait_heartbeat.py`` — success, failure, edge cases."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from ralph import wait_heartbeat


def test_no_backlog_dir_returns_2(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = wait_heartbeat.main()
    captured = capsys.readouterr()
    assert rc == 2
    assert (
        captured.out == "ERROR: must be invoked from project root (no backlog/ here)\n"
    )


def test_fresh_heartbeat_returns_0(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "backlog").mkdir()
    hb = tmp_path / "backlog" / ".ralph-heartbeat"
    hb.touch()
    rc = wait_heartbeat.main()
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.startswith("OK heartbeat age=")
    assert captured.out.endswith("\n")


def test_fresh_heartbeat_leaves_launch_log(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """wait_heartbeat is read-only: a successful poll must NOT touch the launch log.

    Launch-log cleanup was relocated to the ralph-run skill's Step 4
    (``… && rm -f backlog/.ralph-launch.log``); the module only reads.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "backlog").mkdir()
    hb = tmp_path / "backlog" / ".ralph-heartbeat"
    hb.touch()
    launch_log = tmp_path / "backlog" / ".ralph-launch.log"
    launch_log.write_text("noise\n")
    rc = wait_heartbeat.main()
    _ = capsys.readouterr()
    assert rc == 0
    assert launch_log.exists()
    assert launch_log.read_text() == "noise\n"


def test_stale_heartbeat_returns_1(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Heartbeat older than 15s after 10 polls → exit 1."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "backlog").mkdir()
    hb = tmp_path / "backlog" / ".ralph-heartbeat"
    hb.touch()
    old = time.time() - 3600
    os.utime(hb, (old, old))

    # Avoid real 10-second wall-clock wait — patch ``time.sleep``.
    monkeypatch.setattr(wait_heartbeat.time, "sleep", lambda _s: None)

    launch_log = tmp_path / "backlog" / ".ralph-launch.log"
    launch_log.write_text("line1\nline2\n")
    run_log = tmp_path / "backlog" / ".ralph-run.log"
    run_log.write_text("alpha\nbeta\n")

    rc = wait_heartbeat.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert "FAIL no fresh heartbeat after 10s" in captured.out
    assert "--- launch log (last 20 lines) ---" in captured.out
    assert "line1" in captured.out
    assert "alpha" in captured.out


def test_missing_logs_show_fallback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "backlog").mkdir()
    monkeypatch.setattr(wait_heartbeat.time, "sleep", lambda _s: None)
    rc = wait_heartbeat.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert "(launch log not created)" in captured.out
    assert "(run log not created)" in captured.out
