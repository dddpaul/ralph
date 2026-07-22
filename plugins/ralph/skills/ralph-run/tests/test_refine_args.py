"""Argparse + validation tests for ``ralph.refine`` (US-002 AC #1-6).

Covers the full ``refine.sh`` flag surface, the defaults, and every branch of
:func:`ralph.refine.args.validate`, plus the exit-code contract of
:func:`ralph.refine.cli.main`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph.refine import cli
from ralph.refine.args import RefineArgs, build_parser, parse, validate


def _roles(tmp_path: Path) -> tuple[Path, Path]:
    """Create readable author + reviewer role files, returning their paths."""
    author = tmp_path / "author.md"
    reviewer = tmp_path / "reviewer.md"
    author.write_text("author role")
    reviewer.write_text("reviewer role")
    return author, reviewer


def _valid_argv(tmp_path: Path, *extra: str) -> list[str]:
    """A minimally-valid argv (prompt + readable author/reviewer) plus extras."""
    author, reviewer = _roles(tmp_path)
    return [
        "--prompt",
        "make it good",
        "--author",
        str(author),
        "--reviewer",
        str(reviewer),
        *extra,
    ]


# --------------------------------------------------------------------------- #
# AC #1 — flag surface
# --------------------------------------------------------------------------- #
def test_parser_declares_exact_flag_names() -> None:
    """AC #1 — every documented long flag is present, byte-for-byte."""
    parser = build_parser()
    flags = {act.option_strings[0] for act in parser._actions if act.option_strings}
    expected = {
        "--prompt",
        "--draft",
        "--author",
        "--reviewer",
        "--type",
        "--tool",
        "--model",
        "--effort",
        "--timeout",
        "--max-iterations",
        "--threshold",
        "--output-dir",
        "--on-error",
        "--retry-count",
        "--devcontainer",
        "--resume",
        "--verbose",
        "--dry-run",
    }
    missing = expected - flags
    assert not missing, f"missing flags: {missing}"


def test_parser_disables_long_flag_abbreviation() -> None:
    """AC #1 — argparse must NOT accept ``--thr`` as shorthand for ``--threshold``."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--thr", "7"])


def test_parse_round_trips_all_flags(tmp_path: Path) -> None:
    """AC #1 — every flag flows through to the typed :class:`RefineArgs`."""
    author, reviewer = _roles(tmp_path)
    parsed = parse(
        [
            "--draft",
            "draft.md",
            "--author",
            str(author),
            "--reviewer",
            str(reviewer),
            "--type",
            "drawio",
            "--tool",
            "opencode",
            "--model",
            "claude-sonnet-4-6",
            "--effort",
            "high",
            "--timeout",
            "20",
            "--max-iterations",
            "5",
            "--threshold",
            "9",
            "--output-dir",
            "out/",
            "--on-error",
            "retry",
            "--retry-count",
            "3",
            "--devcontainer",
            "--resume",
            "--verbose",
            "--dry-run",
        ]
    )
    assert parsed == RefineArgs(
        prompt="",
        draft="draft.md",
        author=str(author),
        reviewer=str(reviewer),
        artifact_type="drawio",
        tool="opencode",
        model="claude-sonnet-4-6",
        effort="high",
        timeout=20,
        max_iterations=5,
        threshold=9,
        output_dir="out/",
        on_error="retry",
        retry_count=3,
        devcontainer=True,
        resume=True,
        verbose=True,
        dry_run=True,
    )


# --------------------------------------------------------------------------- #
# AC #2 — defaults
# --------------------------------------------------------------------------- #
def test_parse_defaults_match_refine_sh() -> None:
    """AC #2 — bare parse yields the documented ``refine.sh`` defaults."""
    parsed = parse([])
    assert parsed.prompt == ""
    assert parsed.draft == ""
    assert parsed.author == ""
    assert parsed.reviewer == ""
    assert parsed.artifact_type == "md"
    assert parsed.tool == "claude"
    assert parsed.model == "claude-opus-4-8"
    assert parsed.effort == "medium"
    assert parsed.timeout == 15
    assert parsed.max_iterations == 10
    assert parsed.threshold == 8
    assert parsed.output_dir == "iterations/"
    assert parsed.on_error == "stop"
    assert parsed.retry_count == 2
    assert parsed.devcontainer is False
    assert parsed.resume is False
    assert parsed.verbose is False
    assert parsed.dry_run is False


# --------------------------------------------------------------------------- #
# AC #3 — --prompt / --draft exclusivity + exactly-one
# --------------------------------------------------------------------------- #
def test_validate_rejects_prompt_and_draft_together(tmp_path: Path) -> None:
    author, reviewer = _roles(tmp_path)
    parsed = parse(
        [
            "--prompt",
            "p",
            "--draft",
            "d",
            "--author",
            str(author),
            "--reviewer",
            str(reviewer),
        ]
    )
    err = validate(parsed)
    assert err is not None and "mutually exclusive" in err


def test_validate_rejects_neither_prompt_nor_draft(tmp_path: Path) -> None:
    author, reviewer = _roles(tmp_path)
    parsed = parse(["--author", str(author), "--reviewer", str(reviewer)])
    err = validate(parsed)
    assert err is not None and "exactly one of --prompt or --draft" in err


def test_validate_accepts_draft_alone(tmp_path: Path) -> None:
    author, reviewer = _roles(tmp_path)
    parsed = parse(
        ["--draft", "d.md", "--author", str(author), "--reviewer", str(reviewer)]
    )
    assert validate(parsed) is None


# --------------------------------------------------------------------------- #
# AC #4 — --author / --reviewer required + readable
# --------------------------------------------------------------------------- #
def test_validate_rejects_missing_author_flag(tmp_path: Path) -> None:
    _, reviewer = _roles(tmp_path)
    parsed = parse(["--prompt", "p", "--reviewer", str(reviewer)])
    err = validate(parsed)
    assert err is not None and "--author is required" in err


def test_validate_rejects_missing_reviewer_flag(tmp_path: Path) -> None:
    author, _ = _roles(tmp_path)
    parsed = parse(["--prompt", "p", "--author", str(author)])
    err = validate(parsed)
    assert err is not None and "--reviewer is required" in err


def test_validate_rejects_unreadable_author_file(tmp_path: Path) -> None:
    _, reviewer = _roles(tmp_path)
    parsed = parse(
        [
            "--prompt",
            "p",
            "--author",
            str(tmp_path / "ghost.md"),
            "--reviewer",
            str(reviewer),
        ]
    )
    err = validate(parsed)
    assert err is not None and "Author role file" in err and "does not exist" in err


def test_validate_rejects_unreadable_reviewer_file(tmp_path: Path) -> None:
    author, _ = _roles(tmp_path)
    parsed = parse(
        [
            "--prompt",
            "p",
            "--author",
            str(author),
            "--reviewer",
            str(tmp_path / "ghost.md"),
        ]
    )
    err = validate(parsed)
    assert err is not None and "Reviewer role file" in err and "does not exist" in err


# --------------------------------------------------------------------------- #
# AC #5 — enumerated + range value checks
# --------------------------------------------------------------------------- #
def test_validate_rejects_invalid_type(tmp_path: Path) -> None:
    parsed = parse(_valid_argv(tmp_path, "--type", "pdf"))
    err = validate(parsed)
    assert err is not None and "Invalid type 'pdf'" in err


def test_validate_rejects_invalid_tool(tmp_path: Path) -> None:
    parsed = parse(_valid_argv(tmp_path, "--tool", "ghost"))
    err = validate(parsed)
    assert err is not None and "Invalid tool" in err


def test_validate_rejects_invalid_effort(tmp_path: Path) -> None:
    parsed = parse(_valid_argv(tmp_path, "--effort", "xhigh"))
    err = validate(parsed)
    assert err is not None and "Invalid effort level 'xhigh'" in err


def test_validate_rejects_invalid_on_error(tmp_path: Path) -> None:
    parsed = parse(_valid_argv(tmp_path, "--on-error", "ignore"))
    err = validate(parsed)
    assert err is not None and "Invalid on-error strategy 'ignore'" in err


@pytest.mark.parametrize("bad", ["0", "11"])
def test_validate_rejects_threshold_outside_1_10(tmp_path: Path, bad: str) -> None:
    parsed = parse(_valid_argv(tmp_path, "--threshold", bad))
    err = validate(parsed)
    assert err is not None and "Threshold must be between 1 and 10" in err


@pytest.mark.parametrize("good", ["1", "10"])
def test_validate_accepts_threshold_boundaries(tmp_path: Path, good: str) -> None:
    parsed = parse(_valid_argv(tmp_path, "--threshold", good))
    assert validate(parsed) is None


def test_validate_rejects_timeout_below_one(tmp_path: Path) -> None:
    parsed = parse(_valid_argv(tmp_path, "--timeout", "0"))
    err = validate(parsed)
    assert err is not None and "Timeout" in err


def test_validate_rejects_max_iterations_below_one(tmp_path: Path) -> None:
    parsed = parse(_valid_argv(tmp_path, "--max-iterations", "0"))
    err = validate(parsed)
    assert err is not None and "Max iterations must be at least 1" in err


def test_validate_rejects_negative_retry_count(tmp_path: Path) -> None:
    parsed = parse(_valid_argv(tmp_path, "--retry-count", "-1"))
    err = validate(parsed)
    assert err is not None and "Retry count" in err


def test_validate_accepts_fully_valid_args(tmp_path: Path) -> None:
    parsed = parse(_valid_argv(tmp_path))
    assert validate(parsed) is None


# --------------------------------------------------------------------------- #
# AC #3-5 via the CLI entry point — exit-code contract
# --------------------------------------------------------------------------- #
def test_cli_help_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """``--help`` prints usage; cli.main catches argparse's exit and returns 0."""
    rc = cli.main(["--help"])
    assert rc == 0
    assert "refine" in capsys.readouterr().out


def test_cli_main_returns_1_on_missing_prompt_and_draft(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    author, reviewer = _roles(tmp_path)
    rc = cli.main(["--author", str(author), "--reviewer", str(reviewer)])
    assert rc == 1
    assert "exactly one of --prompt or --draft" in capsys.readouterr().err


def test_cli_main_returns_1_on_invalid_effort(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(_valid_argv(tmp_path, "--effort", "turbo"))
    assert rc == 1
    assert "Invalid effort level" in capsys.readouterr().err


def test_cli_main_returns_1_on_missing_role_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, reviewer = _roles(tmp_path)
    rc = cli.main(
        [
            "--prompt",
            "p",
            "--author",
            str(tmp_path / "ghost.md"),
            "--reviewer",
            str(reviewer),
        ]
    )
    assert rc == 1
    assert "Author role file" in capsys.readouterr().err


def test_cli_main_propagates_argparse_exit_on_bad_int(tmp_path: Path) -> None:
    """A non-integer for an int flag is an argparse usage error (exit 2)."""
    rc = cli.main(_valid_argv(tmp_path, "--timeout", "abc"))
    assert rc == 2


def test_cli_main_returns_0_on_valid_args(tmp_path: Path) -> None:
    rc = cli.main(_valid_argv(tmp_path))
    assert rc == 0
