"""CLI argument parsing & validation for ``ralph-refine`` (US-002).

The refine sibling of :mod:`ralph.args`. Where ``ralph.args`` mirrors
``ralph.sh``, this module mirrors ``refine.sh``: the same long-flag surface and
the same defaults, so existing ``refine.sh`` invocations keep working once the
Python entry point replaces the bash one.

Two conventions carry over from :mod:`ralph.args`:

* ``allow_abbrev=False`` — argparse otherwise accepts any unambiguous prefix of
  a long flag (e.g. ``--thr`` for ``--threshold``); the bash entry point did
  not, so we turn it off.
* :func:`validate` performs the post-parse value checks. Returning ``None``
  means "valid"; a non-empty string is the error message to surface verbatim
  before exiting with code 1. Order of checks is first-failure-wins.

``argparse`` choice enforcement is deliberately *not* used for the enumerated
flags (``--type`` / ``--effort`` / ``--on-error`` / ``--tool``): the bash
version surfaces a custom ``Error: ...`` message and exits 1, whereas argparse
would print its stock ``invalid choice`` usage and exit 2. :func:`validate`
produces the parity message instead.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RefineArgs:
    """Strongly-typed view of the refine parser's namespace.

    Field names are snake_case (argparse ``dest=`` handles the mapping for the
    hyphenated flags). ``artifact_type`` backs ``--type`` because ``type`` is a
    Python builtin.
    """

    prompt: str
    draft: str
    author: str
    reviewer: str
    artifact_type: str
    tool: str
    model: str
    effort: str
    timeout: int
    max_iterations: int
    threshold: int
    output_dir: str
    on_error: str
    retry_count: int
    devcontainer: bool
    resume: bool
    verbose: bool
    dry_run: bool


_TYPE_CHOICES = ("md", "drawio", "puml")
_EFFORT_CHOICES = ("low", "medium", "high", "max")
_TOOL_CHOICES = ("claude", "opencode")
_ON_ERROR_CHOICES = ("stop", "continue", "retry")


def build_parser() -> argparse.ArgumentParser:
    """Return a parser that mirrors the ``refine.sh`` flag surface exactly.

    Choices are validated in :func:`validate` (not by argparse) so the custom
    ``Error: ...`` messages and exit-code-1 semantics match the bash entry
    point. Integer-typed flags (``--timeout`` / ``--max-iterations`` /
    ``--threshold`` / ``--retry-count``) use ``type=int`` so non-numeric input
    is rejected by argparse; the range checks live in :func:`validate`.
    """
    parser = argparse.ArgumentParser(
        prog="refine",
        description=(
            "Adversarial author-reviewer refinement loop: iterate a digital "
            "artifact (md / draw.io / PlantUML) through author and reviewer "
            "roles until a reviewer score meets a threshold."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--prompt", default="")
    parser.add_argument("--draft", default="")
    parser.add_argument("--author", default="")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--type", dest="artifact_type", default="md")
    parser.add_argument("--tool", default="claude")
    parser.add_argument("--model", default="claude-opus-4-8")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument(
        "--max-iterations", dest="max_iterations", type=int, default=10
    )
    parser.add_argument("--threshold", type=int, default=8)
    parser.add_argument(
        "--output-dir", dest="output_dir", default="iterations/"
    )
    parser.add_argument("--on-error", dest="on_error", default="stop")
    parser.add_argument("--retry-count", dest="retry_count", type=int, default=2)
    parser.add_argument("--devcontainer", action="store_true", default=False)
    parser.add_argument("--resume", action="store_true", default=False)
    parser.add_argument("--verbose", action="store_true", default=False)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)
    return parser


def parse(argv: list[str]) -> RefineArgs:
    """Parse ``argv`` (no leading program name) into a typed :class:`RefineArgs`.

    Raises ``SystemExit`` (via argparse) on unknown flags, ``--help``, or a
    non-integer value for an integer-typed flag — the caller propagates the
    argparse exit code. Value-range and combination checks are deferred to
    :func:`validate`.
    """
    parser = build_parser()
    ns = parser.parse_args(argv)
    return RefineArgs(
        prompt=ns.prompt,
        draft=ns.draft,
        author=ns.author,
        reviewer=ns.reviewer,
        artifact_type=ns.artifact_type,
        tool=ns.tool,
        model=ns.model,
        effort=ns.effort,
        timeout=ns.timeout,
        max_iterations=ns.max_iterations,
        threshold=ns.threshold,
        output_dir=ns.output_dir,
        on_error=ns.on_error,
        retry_count=ns.retry_count,
        devcontainer=ns.devcontainer,
        resume=ns.resume,
        verbose=ns.verbose,
        dry_run=ns.dry_run,
    )


def validate(args: RefineArgs) -> str | None:
    """Return ``None`` if valid, else a ``refine.sh``-parity error message.

    First-failure-wins. The checks cover the four combination/requirement rules
    (``--prompt``/``--draft`` exclusivity + exactly-one, ``--author`` and
    ``--reviewer`` required and readable) and the enumerated/range value checks
    (``--type``, ``--tool``, ``--effort``, ``--on-error``, ``--threshold``,
    ``--timeout``, ``--max-iterations``, ``--retry-count``).
    """
    if args.prompt and args.draft:
        return "Error: --prompt and --draft are mutually exclusive."
    if not args.prompt and not args.draft:
        return "Error: exactly one of --prompt or --draft is required."

    if not args.author:
        return "Error: --author is required."
    if not os.access(args.author, os.R_OK):
        return (
            f"Error: Author role file '{args.author}' does not exist or "
            "is not readable."
        )

    if not args.reviewer:
        return "Error: --reviewer is required."
    if not os.access(args.reviewer, os.R_OK):
        return (
            f"Error: Reviewer role file '{args.reviewer}' does not exist or "
            "is not readable."
        )

    if args.artifact_type not in _TYPE_CHOICES:
        return (
            f"Error: Invalid type '{args.artifact_type}'. "
            "Must be 'md', 'drawio', or 'puml'."
        )

    if args.tool not in _TOOL_CHOICES:
        return f"Error: Invalid tool '{args.tool}'. Must be 'claude' or 'opencode'."

    if args.effort not in _EFFORT_CHOICES:
        return (
            f"Error: Invalid effort level '{args.effort}'. "
            "Must be 'low', 'medium', 'high', or 'max'."
        )

    if args.on_error not in _ON_ERROR_CHOICES:
        return (
            f"Error: Invalid on-error strategy '{args.on_error}'. "
            "Must be 'stop', 'continue', or 'retry'."
        )

    if not 1 <= args.threshold <= 10:
        return "Error: Threshold must be between 1 and 10."

    if args.timeout < 1:
        return "Error: Timeout must be a positive number of minutes."

    if args.max_iterations < 1:
        return "Error: Max iterations must be at least 1."

    if args.retry_count < 0:
        return "Error: Retry count must be a non-negative integer."

    return None
