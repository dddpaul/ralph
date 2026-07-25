"""CLI argument parsing & validation — bash-flag parity for ``ralph.sh``.

The :func:`build_parser` factory returns an ``argparse.ArgumentParser`` whose
flag names match the bash entry point byte-for-byte. Two argparse knobs are
load-bearing:

* ``allow_abbrev=False`` — argparse otherwise accepts any unambiguous prefix
  of a long flag (e.g. ``--ti`` for ``--timeout``); the bash entry point did
  not, so we turn it off.
* :meth:`ArgumentParser.parse_intermixed_args` — allows the positional
  ``max_iterations`` to appear anywhere on the command line (before, between,
  or after flags), matching how the bash ``while [[ $# -gt 0 ]]; case`` loop
  consumed flags in any order around the positional.

:func:`validate` performs the post-parse value checks bash performed in
``validate_args()`` (lines 166-213 of ``ralph.sh``). Returning ``None`` means
"valid"; a non-empty string is the error message to surface verbatim before
exiting with code 1.
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedArgs:
    """Strongly-typed view of the parser's namespace.

    Field names are normalized to snake_case (argparse's ``dest=`` defaults
    do this already, but we restate them here so the dataclass is the single
    source of truth for downstream code).
    """

    tool: str
    model: str
    effort: str
    timeout: str
    on_error: str
    retry_count: int
    log_file: str
    prompt_file: str
    tasks: str
    block_end_buffer_min: int
    devcontainer: bool
    max_iterations: int
    push: bool = True

    @property
    def task_whitelist(self) -> list[str]:
        """Normalize ``--tasks`` into a list of bare numeric IDs."""
        if not self.tasks:
            return []
        return [t for t in self.tasks.split(",") if t]


_EFFORT_CHOICES = ("low", "medium", "high", "xhigh", "max")
_TOOL_CHOICES = ("claude", "opencode")
_ON_ERROR_CHOICES = ("stop", "continue", "retry")
_TIMEOUT_RE = re.compile(r"^[0-9]*\.?[0-9]+$")
_TASKS_RE = re.compile(r"^[0-9]+(,[0-9]+)*$")


def build_parser() -> argparse.ArgumentParser:
    """Return a parser that mirrors the bash CLI's flag surface exactly.

    Choices are NOT enforced by argparse for ``--tool`` / ``--effort`` /
    ``--on-error`` because the bash version surfaces a custom error
    message ("Error: Invalid effort level 'xyz'. Must be ...") rather than
    argparse's stock ``invalid choice`` output. :func:`validate` produces
    the bash-compatible message instead.
    """
    parser = argparse.ArgumentParser(
        prog="ralph_orchestrator.py",
        description="Ralph Wiggum - Long-running AI agent loop (Python port).",
        allow_abbrev=False,
    )
    parser.add_argument("--tool", default="claude")
    parser.add_argument("--model", default="claude-opus-4-8")
    parser.add_argument("--effort", default="max")
    parser.add_argument("--timeout", default="15")
    parser.add_argument("--on-error", dest="on_error", default="stop")
    parser.add_argument("--retry-count", dest="retry_count", type=int, default=2)
    parser.add_argument("--log-file", dest="log_file", default="")
    parser.add_argument("--prompt-file", dest="prompt_file", default="")
    parser.add_argument("--tasks", default="")
    parser.add_argument(
        "--block-end-buffer-min", dest="block_end_buffer_min", type=int, default=0
    )
    parser.add_argument("--devcontainer", action="store_true", default=False)
    # Push-on-complete is ENABLED BY DEFAULT (TASK-211); --no-push opts out.
    # A truthy RALPH_NO_PUSH env is the equivalent env opt-out, resolved at
    # push time by ralph.push.push_enabled (kept out of validation so the env
    # can override per-run without re-parsing).
    parser.add_argument("--no-push", dest="push", action="store_false", default=True)
    parser.add_argument("max_iterations", type=int, nargs="?", default=10)
    return parser


def parse(argv: list[str]) -> ParsedArgs:
    """Parse ``argv`` (no leading program name) into a typed ParsedArgs.

    Uses :meth:`parse_intermixed_args` so the positional ``max_iterations``
    can appear anywhere on the command line, matching bash.
    """
    parser = build_parser()
    ns = parser.parse_intermixed_args(argv)
    return ParsedArgs(
        tool=ns.tool,
        model=ns.model,
        effort=ns.effort,
        timeout=ns.timeout,
        on_error=ns.on_error,
        retry_count=ns.retry_count,
        log_file=ns.log_file,
        prompt_file=ns.prompt_file,
        tasks=ns.tasks,
        block_end_buffer_min=ns.block_end_buffer_min,
        devcontainer=ns.devcontainer,
        max_iterations=ns.max_iterations,
        push=ns.push,
    )


def validate(args: ParsedArgs) -> str | None:
    """Return ``None`` if valid, else a bash-parity error message.

    Mirrors ``validate_args()`` in ``ralph.sh:166-213``. Order of checks
    matches the bash order — the first failure wins.
    """
    if args.tool not in _TOOL_CHOICES:
        return f"Error: Invalid tool '{args.tool}'. Must be 'claude' or 'opencode'."

    if not _TIMEOUT_RE.fullmatch(args.timeout) or float(args.timeout) <= 0:
        return "Error: Timeout must be a positive number of minutes."

    if args.effort not in _EFFORT_CHOICES:
        return (
            f"Error: Invalid effort level '{args.effort}'. "
            "Must be 'low', 'medium', 'high', 'xhigh', or 'max'."
        )

    if args.on_error not in _ON_ERROR_CHOICES:
        return (
            f"Error: Invalid on-error strategy '{args.on_error}'. "
            "Must be 'stop', 'continue', or 'retry'."
        )

    if args.retry_count < 0:
        return "Error: Retry count must be a non-negative integer."

    if args.prompt_file and not os.access(args.prompt_file, os.R_OK):
        return (
            f"Error: Prompt file '{args.prompt_file}' does not exist or "
            "is not readable."
        )

    if args.tasks:
        if not _TASKS_RE.fullmatch(args.tasks):
            return (
                "Error: --tasks must be comma-separated numeric IDs "
                f"(e.g. 62,64,65). Got: '{args.tasks}'"
            )
        if args.prompt_file:
            return "Error: --tasks and --prompt-file are mutually exclusive"

    if args.block_end_buffer_min < 0:
        return (
            "Error: --block-end-buffer-min must be a non-negative integer. "
            f"Got: '{args.block_end_buffer_min}'"
        )

    return None


def timeout_to_seconds(timeout_min: str) -> int:
    """Convert a ``--timeout`` value (minutes, possibly fractional) to seconds.

    Mirrors the bash arithmetic in ``ralph.sh:702-711`` — integer math on
    minutes plus millisecond-precision fraction, no rounding above
    millisecond resolution.
    """
    if "." not in timeout_min:
        return int(timeout_min) * 60
    int_part, frac_part = timeout_min.split(".", 1)
    base = int(int_part or "0") * 60
    frac_part = (frac_part + "000")[:3]
    return base + int(frac_part) * 60 // 1000
