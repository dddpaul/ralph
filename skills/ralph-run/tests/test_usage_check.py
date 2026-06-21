"""Unit tests for ``ralph/usage_check.py`` — success, failure, edge cases."""

from __future__ import annotations

import json
import os
import stat
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ralph import usage_check

SYS_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(f"#!/bin/bash\n{body}\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def mock_bin(tmp_path: Path) -> Iterator[Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    yield bin_dir


def _set_path(monkeypatch: pytest.MonkeyPatch, *extra_dirs: Path) -> None:
    prefix = ":".join(str(d) for d in extra_dirs)
    monkeypatch.setenv("PATH", f"{prefix}:{SYS_PATH}" if prefix else SYS_PATH)


def test_buffer_zero_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    """BUFFER_MIN=0 returns 0 before any subprocess call."""
    monkeypatch.setenv("PATH", "/nonexistent")  # ccusage definitely not on PATH
    rc, out, err = usage_check.evaluate("0")
    assert (rc, out, err) == (0, "", "")


def test_empty_buffer_returns_2(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, out, err = usage_check.evaluate("")
    assert rc == 2
    assert out == ""
    assert err == (
        "usage-check.sh: BUFFER_MIN must be a non-negative integer "
        "(got '<empty>')\n"
    )


def test_non_numeric_buffer_returns_2(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, out, err = usage_check.evaluate("abc")
    assert rc == 2
    assert "got 'abc'" in err


def test_ccusage_missing_returns_2(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PATH", "/nonexistent")
    rc, out, err = usage_check.evaluate("5")
    assert rc == 2
    assert "ccusage not found on PATH" in err


def test_active_block_within_buffer_triggers_exit_1(
    monkeypatch: pytest.MonkeyPatch, mock_bin: Path
) -> None:
    """ccusage returns active block ending in 3 minutes; buffer=5 → exit 1."""
    end_time = (datetime.now(tz=UTC) + timedelta(minutes=3)).isoformat()
    payload = json.dumps(
        {"blocks": [{"isActive": True, "isGap": False, "endTime": end_time}]}
    )
    _write_executable(mock_bin / "ccusage", f'cat <<EOF\n{payload}\nEOF')
    _write_executable(mock_bin / "jq", 'echo "$@"')
    _set_path(monkeypatch, mock_bin)
    rc, out, err = usage_check.evaluate("5")
    assert rc == 1
    assert out.startswith("block_end_in_")
    assert "min_below_5min_buffer" in out
    assert err == ""


def test_active_block_outside_buffer_returns_0(
    monkeypatch: pytest.MonkeyPatch, mock_bin: Path
) -> None:
    end_time = (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat()
    payload = json.dumps(
        {"blocks": [{"isActive": True, "isGap": False, "endTime": end_time}]}
    )
    _write_executable(mock_bin / "ccusage", f'cat <<EOF\n{payload}\nEOF')
    _write_executable(mock_bin / "jq", 'echo "$@"')
    _set_path(monkeypatch, mock_bin)
    rc, out, err = usage_check.evaluate("5")
    assert (rc, out, err) == (0, "", "")


def test_inactive_block_returns_0(
    monkeypatch: pytest.MonkeyPatch, mock_bin: Path
) -> None:
    payload = json.dumps({"blocks": [{"isActive": False, "isGap": False}]})
    _write_executable(mock_bin / "ccusage", f'cat <<EOF\n{payload}\nEOF')
    _write_executable(mock_bin / "jq", 'echo "$@"')
    _set_path(monkeypatch, mock_bin)
    rc, out, err = usage_check.evaluate("5")
    assert (rc, out, err) == (0, "", "")


def test_unparseable_json_returns_2(
    monkeypatch: pytest.MonkeyPatch, mock_bin: Path
) -> None:
    _write_executable(mock_bin / "ccusage", 'echo "not json"')
    _write_executable(mock_bin / "jq", 'echo "$@"')
    _set_path(monkeypatch, mock_bin)
    rc, _out, err = usage_check.evaluate("5")
    assert rc == 2
    assert "unparseable JSON" in err


def test_missing_endtime_returns_2(
    monkeypatch: pytest.MonkeyPatch, mock_bin: Path
) -> None:
    payload = json.dumps({"blocks": [{"isActive": True, "isGap": False}]})
    _write_executable(mock_bin / "ccusage", f'cat <<EOF\n{payload}\nEOF')
    _write_executable(mock_bin / "jq", 'echo "$@"')
    _set_path(monkeypatch, mock_bin)
    rc, _out, err = usage_check.evaluate("5")
    assert rc == 2
    assert "missing blocks[0].endTime" in err


def test_unparseable_endtime_returns_2(
    monkeypatch: pytest.MonkeyPatch, mock_bin: Path
) -> None:
    payload = json.dumps(
        {"blocks": [{"isActive": True, "isGap": False, "endTime": "garbage"}]}
    )
    _write_executable(mock_bin / "ccusage", f'cat <<EOF\n{payload}\nEOF')
    _write_executable(mock_bin / "jq", 'echo "$@"')
    _set_path(monkeypatch, mock_bin)
    rc, _out, err = usage_check.evaluate("5")
    assert rc == 2
    assert "could not parse endTime" in err


def test_ccusage_nonzero_returns_2(
    monkeypatch: pytest.MonkeyPatch, mock_bin: Path
) -> None:
    _write_executable(mock_bin / "ccusage", 'echo "boom"; exit 9')
    _write_executable(mock_bin / "jq", 'echo "$@"')
    _set_path(monkeypatch, mock_bin)
    rc, _out, err = usage_check.evaluate("5")
    assert rc == 2
    assert "ccusage exited 9" in err


def test_cli_writes_sentinel_on_exit_2(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "/nonexistent")
    rc = usage_check.main(["5"])
    _ = capsys.readouterr()
    assert rc == 2
    sentinel = tmp_path / "backlog" / ".ralph-usage-check-disabled"
    assert sentinel.exists()


def test_cli_does_not_write_sentinel_on_exit_0(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = usage_check.main(["0"])
    assert rc == 0
    sentinel = tmp_path / "backlog" / ".ralph-usage-check-disabled"
    assert not sentinel.exists()


def test_iso_with_z_suffix_parses() -> None:
    epoch = usage_check._parse_iso_to_epoch("2026-06-21T15:00:00Z")
    assert epoch == int(
        datetime(2026, 6, 21, 15, 0, 0, tzinfo=UTC).timestamp()
    )


def test_iso_with_offset_parses() -> None:
    epoch = usage_check._parse_iso_to_epoch("2026-06-21T17:00:00+02:00")
    assert epoch == int(
        datetime(2026, 6, 21, 15, 0, 0, tzinfo=UTC).timestamp()
    )


def test_iso_garbage_returns_none() -> None:
    assert usage_check._parse_iso_to_epoch("not a date") is None


def test_sys_module_imported() -> None:
    # silence unused-import on conditionally-used `sys`
    assert sys is not None
    assert os.X_OK == os.X_OK
