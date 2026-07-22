"""ralph-refine CLI entry point.

The single wiring point the ``refine_orchestrator.py`` launcher dispatches into
(US-001 AC #2). US-002 fills in the flag set and validation: :func:`main`
parses the full ``refine.sh`` flag surface via :mod:`ralph.refine.args`,
surfaces any validation error on stderr, and exits 1 — mirroring
:func:`ralph_orchestrator.main`. The refinement-loop dispatch lands in US-005;
this module is the seam it extends.
"""

from __future__ import annotations

import argparse
import sys

from ralph.refine import args as args_module


def main(argv: list[str] | None = None) -> int:
    """Parse args, validate, and (US-005) dispatch the refinement run.

    Args:
        argv: Argument vector to parse. Defaults to ``sys.argv[1:]`` when
            ``None`` — parity with :func:`ralph_orchestrator.main`.

    Returns:
        The process exit code: argparse's own code for ``--help`` / usage
        errors, ``1`` when :func:`ralph.refine.args.validate` rejects the
        parsed args, else ``0`` (the loop dispatch, and its own exit code,
        land in US-005).
    """
    real_argv = sys.argv[1:] if argv is None else argv

    try:
        parsed = args_module.parse(real_argv)
    except (argparse.ArgumentError, SystemExit) as exc:
        # argparse already printed its own usage/error; propagate the code.
        if isinstance(exc, SystemExit):
            return int(exc.code) if isinstance(exc.code, int) else 1
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    error = args_module.validate(parsed)
    if error is not None:
        print(error, file=sys.stderr)
        return 1

    # US-005: dispatch into the author-reviewer refinement loop here.
    return 0
