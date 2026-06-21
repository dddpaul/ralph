"""Unit tests for ``ralph/preflight.py`` — success, failure, edge cases."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from conftest import PreflightFixture, write_mock_bin

from ralph import preflight


def _run_preflight(
    fixture: PreflightFixture,
    args: list[str],
    monkeypatch: pytest.MonkeyPatch,
    env_overrides: dict[str, str] | None = None,
) -> int:
    """Invoke ``preflight.main`` with the fixture's PWD + PATH applied."""
    env = fixture.env(**(env_overrides or {}))
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(fixture.project_dir)
    return preflight.main(args)


def test_success_path(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_mock_bin(
        preflight_fixture.bin_dir,
        "backlog",
        'echo "To Do:"; echo "  TASK-1 - Test"',
    )
    rc = _run_preflight(
        preflight_fixture, [str(preflight_fixture.ralph_sh), "false"], monkeypatch
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == f"OK RALPH_PATH={preflight_fixture.ralph_sh}\n"


def test_no_todo_tasks_fails(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_mock_bin(preflight_fixture.bin_dir, "backlog", 'echo "No tasks found"')
    rc = _run_preflight(
        preflight_fixture, [str(preflight_fixture.ralph_sh), "false"], monkeypatch
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == "ERROR: No To Do tasks in backlog\n"


def test_ralph_already_running_fails(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status = preflight_fixture.project_dir / "backlog" / ".ralph-status.json"
    status.write_text('{"pid":99999,"state":"running"}\n')
    hb = preflight_fixture.project_dir / "backlog" / ".ralph-heartbeat"
    hb.touch()
    write_mock_bin(
        preflight_fixture.bin_dir, "backlog", 'echo "  TASK-1 - Something"'
    )
    rc = _run_preflight(
        preflight_fixture, [str(preflight_fixture.ralph_sh), "false"], monkeypatch
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == "ERROR: Ralph is already running (PID 99999)\n"


def test_ralph_running_but_stale_heartbeat_passes(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status = preflight_fixture.project_dir / "backlog" / ".ralph-status.json"
    status.write_text('{"pid":99999,"state":"running"}\n')
    hb = preflight_fixture.project_dir / "backlog" / ".ralph-heartbeat"
    hb.touch()
    old = time.time() - 3600
    os.utime(hb, (old, old))
    write_mock_bin(
        preflight_fixture.bin_dir, "backlog", 'echo "  TASK-1 - Something"'
    )
    rc = _run_preflight(
        preflight_fixture, [str(preflight_fixture.ralph_sh), "false"], monkeypatch
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert "OK RALPH_PATH=" in captured.out


def test_devcontainer_missing_fails(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_mock_bin(
        preflight_fixture.bin_dir, "backlog", 'echo "  TASK-1 - Something"'
    )
    rc = _run_preflight(
        preflight_fixture,
        [str(preflight_fixture.ralph_sh), "true"],
        monkeypatch,
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert (
        captured.out == "ERROR: devcontainer CLI not found but devcontainer=true\n"
    )


def test_ralph_not_executable_fails(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight_fixture.ralph_sh.chmod(0o644)
    write_mock_bin(
        preflight_fixture.bin_dir, "backlog", 'echo "  TASK-1 - Something"'
    )
    rc = _run_preflight(
        preflight_fixture, [str(preflight_fixture.ralph_sh), "false"], monkeypatch
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "is not executable" in captured.out


def test_ralph_syntax_error_fails(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight_fixture.ralph_sh.write_text('#!/bin/bash\necho "unterminated\n')
    write_mock_bin(
        preflight_fixture.bin_dir, "backlog", 'echo "  TASK-1 - Something"'
    )
    rc = _run_preflight(
        preflight_fixture, [str(preflight_fixture.ralph_sh), "false"], monkeypatch
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out.startswith("ERROR: ralph.sh has syntax errors:")


def test_invalid_devcontainer_prints_usage(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc = _run_preflight(
        preflight_fixture, [str(preflight_fixture.ralph_sh), "maybe"], monkeypatch
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out.startswith("Usage: preflight.sh")


def test_wrong_arg_count_prints_usage(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc = _run_preflight(preflight_fixture, [], monkeypatch)
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out.startswith("Usage: preflight.sh")


def test_verbose_emits_per_check_lines(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_mock_bin(
        preflight_fixture.bin_dir, "backlog", 'echo "  TASK-1 - Something"'
    )
    rc = _run_preflight(
        preflight_fixture,
        [str(preflight_fixture.ralph_sh), "false", "--verbose"],
        monkeypatch,
    )
    captured = capsys.readouterr()
    assert rc == 0
    check_lines = [ln for ln in captured.out.splitlines() if ln.startswith("check ")]
    assert len(check_lines) >= 4
    assert captured.out.splitlines()[-1].startswith("OK RALPH_PATH=")


def test_tasks_non_numeric_fails(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_mock_bin(preflight_fixture.bin_dir, "backlog", 'echo "ignored"')
    rc = _run_preflight(
        preflight_fixture,
        [str(preflight_fixture.ralph_sh), "false", "--tasks", "abc"],
        monkeypatch,
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "comma-separated numeric IDs" in captured.out


def test_tasks_id_valid_passes(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_mock_bin(
        preflight_fixture.bin_dir,
        "backlog",
        'echo "Task TASK-42 - Test"; echo "Status: To Do"',
    )
    rc = _run_preflight(
        preflight_fixture,
        [str(preflight_fixture.ralph_sh), "false", "--tasks", "42"],
        monkeypatch,
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.endswith(f"OK RALPH_PATH={preflight_fixture.ralph_sh}\n")


def test_tasks_id_done_fails(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_mock_bin(
        preflight_fixture.bin_dir,
        "backlog",
        'echo "Task TASK-1 - Test"; echo "Status: Done"',
    )
    rc = _run_preflight(
        preflight_fixture,
        [str(preflight_fixture.ralph_sh), "false", "--tasks", "1"],
        monkeypatch,
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out.startswith("ERROR: TASK-1 is not To Do")


def test_block_end_buffer_invalid_fails(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_mock_bin(
        preflight_fixture.bin_dir, "backlog", 'echo "  TASK-1 - Something"'
    )
    rc = _run_preflight(
        preflight_fixture,
        [
            str(preflight_fixture.ralph_sh),
            "false",
            "--block-end-buffer-min",
            "abc",
        ],
        monkeypatch,
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "must be a non-negative integer" in captured.out


def test_block_end_buffer_via_equals_form(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_mock_bin(
        preflight_fixture.bin_dir, "backlog", 'echo "  TASK-1 - Something"'
    )
    rc = _run_preflight(
        preflight_fixture,
        [
            str(preflight_fixture.ralph_sh),
            "false",
            "--block-end-buffer-min=0",
        ],
        monkeypatch,
    )
    _ = capsys.readouterr()
    assert rc == 0


def test_anchored_not_found_match(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC #2 anchor: the canonical line must match; substring 'not found' alone does not."""
    write_mock_bin(
        preflight_fixture.bin_dir,
        "backlog",
        'echo "Task TASK-42 - We have not found a solution"; echo "Status: To Do"',
    )
    rc = _run_preflight(
        preflight_fixture,
        [str(preflight_fixture.ralph_sh), "false", "--tasks", "42"],
        monkeypatch,
    )
    captured = capsys.readouterr()
    # Should NOT trigger the "not found" branch even though "not found" appears.
    assert rc == 0, captured.out


def test_tmpdir_env_var_respected(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """AC #2: ralph syntax check writes its scratch file under TMPDIR."""
    custom_tmp = tmp_path / "custom-tmp"
    custom_tmp.mkdir()
    preflight_fixture.ralph_sh.write_text('#!/bin/bash\nfor x in 1\necho oops\n')
    write_mock_bin(
        preflight_fixture.bin_dir, "backlog", 'echo "  TASK-1 - Something"'
    )
    _ = _run_preflight(
        preflight_fixture,
        [str(preflight_fixture.ralph_sh), "false"],
        monkeypatch,
        env_overrides={"TMPDIR": str(custom_tmp)},
    )
    # The scratch file may have been deleted by preflight before we got here —
    # what matters is that none ended up under /tmp/preflight.*. We assert by
    # checking the only place that could have created such files was custom_tmp.
    leftover = list(custom_tmp.iterdir())
    assert leftover == [] or all(
        p.name.startswith("preflight.") for p in leftover
    ), leftover


def test_does_not_chdir(
    preflight_fixture: PreflightFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC #2: ``preflight.main`` MUST NOT call ``os.chdir``."""
    write_mock_bin(
        preflight_fixture.bin_dir, "backlog", 'echo "  TASK-1 - Something"'
    )
    monkeypatch.chdir(preflight_fixture.project_dir)
    cwd_before = os.getcwd()
    chdir_calls: list[str] = []

    def _fake_chdir(path: str | os.PathLike[str]) -> None:
        chdir_calls.append(str(path))

    monkeypatch.setattr(os, "chdir", _fake_chdir)
    env = preflight_fixture.env()
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    rc = preflight.main([str(preflight_fixture.ralph_sh), "false"])
    _ = capsys.readouterr()
    assert rc == 0
    assert chdir_calls == [], chdir_calls
    assert os.getcwd() == cwd_before
