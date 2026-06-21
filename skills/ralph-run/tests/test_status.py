"""Golden-file round-trip tests for ``StatusFile`` (US-001 contract).

For each captured bash-writer output, parse via pydantic and re-serialize.
The re-serialized bytes MUST equal the original byte-for-byte — that is the
schema-parity contract on which ``ralph-status-watch`` and other external
readers depend.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph.status import StatusFile

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE_NAMES = [
    "status_running.json",
    "status_completed.json",
    "status_paused.json",
    "status_with_errors.json",
]


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_golden_roundtrip_byte_identical(fixture_name: str) -> None:
    fixture = FIXTURES_DIR / fixture_name
    original = fixture.read_bytes()

    model = StatusFile.model_validate_json(original)
    rendered = model.to_json_bytes()

    assert rendered == original, (
        f"Fixture {fixture_name} did not round-trip byte-identically.\n"
        f"Original: {original!r}\n"
        f"Rendered: {rendered!r}"
    )


def test_write_atomic_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "subdir" / ".ralph-status.json"
    model = StatusFile.model_validate_json(
        (FIXTURES_DIR / "status_completed.json").read_bytes()
    )

    model.write_atomic(target)

    assert target.exists()
    assert target.read_bytes() == model.to_json_bytes()


def test_write_atomic_leaves_no_temp_files(tmp_path: Path) -> None:
    target = tmp_path / ".ralph-status.json"
    model = StatusFile.model_validate_json(
        (FIXTURES_DIR / "status_running.json").read_bytes()
    )

    model.write_atomic(target)

    leftover = [p for p in tmp_path.iterdir() if p != target]
    assert leftover == [], f"Expected no temp leftovers, found: {leftover}"


def test_write_atomic_overwrites_existing(tmp_path: Path) -> None:
    target = tmp_path / ".ralph-status.json"
    target.write_bytes(b"stale content\n")

    model = StatusFile.model_validate_json(
        (FIXTURES_DIR / "status_paused.json").read_bytes()
    )
    model.write_atomic(target)

    assert target.read_bytes() == model.to_json_bytes()


def test_extra_field_rejected() -> None:
    payload = (
        b'{"pid":1,"started_at":"2026-01-01T00:00:00Z","state":"running",'
        b'"iteration":0,"max_iterations":1,"tool":"claude","tasks_done":[],'
        b'"tasks_remaining":0,"current_task":null,"last_iteration_duration":null,'
        b'"elapsed":0,"errors":[],"completed_at":null,"exit_code":null,'
        b'"iteration_started_at":null,"timeout_sec":60,"paused_reason":null,'
        b'"paused_buffer_min":null,"paused_remaining_min":null,'
        b'"paused_block_end_time":null,"paused_at":null,"unexpected":"x"}'
    )
    with pytest.raises(ValueError):
        StatusFile.model_validate_json(payload)
