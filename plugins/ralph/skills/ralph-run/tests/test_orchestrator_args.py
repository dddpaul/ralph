"""Argparse + validation tests for ``ralph_orchestrator`` (US-005 AC #2-4, #6)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import ralph_orchestrator
from ralph.args import build_parser, parse, timeout_to_seconds, validate


def test_parser_declares_exact_bash_flag_names() -> None:
    """AC #2 — every long flag from the bash CLI is present, byte-for-byte."""
    parser = build_parser()
    flags = {act.option_strings[0] for act in parser._actions if act.option_strings}
    expected = {
        "--tool",
        "--model",
        "--effort",
        "--timeout",
        "--on-error",
        "--retry-count",
        "--log-file",
        "--prompt-file",
        "--tasks",
        "--block-end-buffer-min",
        "--devcontainer",
    }
    missing = expected - flags
    assert not missing, f"missing flags: {missing}"


def test_parser_disables_long_flag_abbreviation() -> None:
    """AC #3 — argparse must NOT accept ``--ti`` as shorthand for ``--timeout``."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--ti", "5"])


def test_parser_has_no_auto_short_flags() -> None:
    """AC #3 — no auto short-flag inference; every Action has only its long form."""
    parser = build_parser()
    for action in parser._actions:
        if not action.option_strings:
            continue
        for opt in action.option_strings:
            assert opt.startswith("--") or opt in {"-h"}, (
                f"unexpected short flag: {opt}"
            )


@pytest.mark.parametrize(
    "argv,expected_iter",
    [
        (["5"], 5),
        (["--tool", "claude", "5"], 5),
        (["5", "--tool", "claude"], 5),
        (["--tool", "claude", "--timeout", "10", "7"], 7),
        (["--timeout", "10", "7", "--tool", "opencode"], 7),
        (["7", "--devcontainer", "--effort", "high"], 7),
        (["--tasks", "62,64", "5"], 5),
        (["5", "--block-end-buffer-min", "12"], 5),
    ],
)
def test_parse_intermixed_supports_positional_anywhere(
    argv: list[str], expected_iter: int
) -> None:
    """AC #3 — ≥5 flag/positional ordering combinations covered."""
    parsed = parse(argv)
    assert parsed.max_iterations == expected_iter


def test_parse_defaults_match_bash() -> None:
    parsed = parse([])
    assert parsed.tool == "claude"
    assert parsed.model == "claude-opus-4-8"
    assert parsed.effort == "max"
    assert parsed.timeout == "15"
    assert parsed.on_error == "stop"
    assert parsed.retry_count == 2
    assert parsed.log_file == ""
    assert parsed.prompt_file == ""
    assert parsed.tasks == ""
    assert parsed.block_end_buffer_min == 0
    assert parsed.devcontainer is False
    assert parsed.max_iterations == 10


def test_validate_rejects_unknown_tool() -> None:
    parsed = parse(["--tool", "ghost"])
    err = validate(parsed)
    assert err is not None and "Invalid tool" in err


def test_validate_rejects_unknown_effort() -> None:
    parsed = parse(["--effort", "moderate"])
    err = validate(parsed)
    assert err is not None and "effort" in err.lower()


def test_validate_rejects_zero_timeout() -> None:
    parsed = parse(["--timeout", "0"])
    err = validate(parsed)
    assert err is not None and "Timeout" in err


def test_validate_rejects_negative_retry_count() -> None:
    parsed = parse(["--retry-count", "-1"])
    err = validate(parsed)
    assert err is not None and "Retry" in err


def test_validate_rejects_tasks_and_prompt_file_together(tmp_path: Path) -> None:
    prompt_file = tmp_path / "p.txt"
    prompt_file.write_text("hi")
    parsed = parse(
        ["--tasks", "62", "--prompt-file", str(prompt_file)]
    )
    err = validate(parsed)
    assert err is not None and "mutually exclusive" in err


def test_validate_rejects_missing_prompt_file(tmp_path: Path) -> None:
    parsed = parse(["--prompt-file", str(tmp_path / "ghost.txt")])
    err = validate(parsed)
    assert err is not None and "does not exist" in err


def test_validate_accepts_present_prompt_file(tmp_path: Path) -> None:
    prompt_file = tmp_path / "p.txt"
    prompt_file.write_text("hi")
    parsed = parse(["--prompt-file", str(prompt_file)])
    assert validate(parsed) is None


def test_validate_rejects_non_numeric_tasks() -> None:
    parsed = parse(["--tasks", "62,abc"])
    err = validate(parsed)
    assert err is not None and "--tasks" in err


def test_validate_accepts_well_formed_tasks() -> None:
    parsed = parse(["--tasks", "62,64,65"])
    assert validate(parsed) is None
    assert parsed.task_whitelist == ["62", "64", "65"]


def test_validate_accepts_fractional_timeout() -> None:
    parsed = parse(["--timeout", "0.5"])
    assert validate(parsed) is None
    assert timeout_to_seconds("0.5") == 30
    assert timeout_to_seconds("1") == 60
    assert timeout_to_seconds("1.25") == 75
    assert timeout_to_seconds("15") == 900


def test_resolve_project_root_honors_env_var(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC #4 — RALPH_PROJECT_ROOT wins over the file-location fallback."""
    monkeypatch.setenv("RALPH_PROJECT_ROOT", str(tmp_path))
    assert ralph_orchestrator.resolve_project_root() == tmp_path


def test_resolve_project_root_falls_back_to_script_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC #4 — fallback is ``Path(__file__).parent`` of ralph_orchestrator.py."""
    monkeypatch.delenv("RALPH_PROJECT_ROOT", raising=False)
    expected = Path(ralph_orchestrator.__file__).resolve().parent
    assert ralph_orchestrator.resolve_project_root() == expected


def test_main_returns_1_on_invalid_args(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = ralph_orchestrator.main(["--tool", "ghost"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "Invalid tool" in captured.err


def test_main_returns_1_on_missing_prompt_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = ralph_orchestrator.main(
        ["--prompt-file", str(tmp_path / "ghost.txt")]
    )
    assert rc == 1
    captured = capsys.readouterr()
    assert "does not exist" in captured.err


def test_main_returns_1_on_mutually_exclusive_tasks_and_prompt_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    prompt_file = tmp_path / "p.txt"
    prompt_file.write_text("hi")
    rc = ralph_orchestrator.main(
        ["--tasks", "62", "--prompt-file", str(prompt_file)]
    )
    assert rc == 1
    captured = capsys.readouterr()
    assert "mutually exclusive" in captured.err


def test_env_overrides_used_for_isolated_test_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RALPH_PROJECT_ROOT is documented in CLAUDE.md and the PRD as the
    test/sandbox switch; ensure it round-trips through the public resolver."""
    monkeypatch.setenv("RALPH_PROJECT_ROOT", "/tmp/ralph-sandbox")
    assert ralph_orchestrator.resolve_project_root() == Path("/tmp/ralph-sandbox")
    monkeypatch.delenv("RALPH_PROJECT_ROOT")
    assert ralph_orchestrator.resolve_project_root() != Path("/tmp/ralph-sandbox")


def test_os_environ_not_mutated_by_parser() -> None:
    """Defensive: argparse should not write to os.environ as a side effect."""
    snapshot = dict(os.environ)
    parse(["--tool", "opencode", "5"])
    assert dict(os.environ) == snapshot
