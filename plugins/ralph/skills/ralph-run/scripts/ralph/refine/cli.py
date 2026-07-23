"""ralph-refine CLI entry point.

The single wiring point the ``refine_orchestrator.py`` launcher dispatches into
(US-001 AC #2). US-002 fills in the flag set and validation: :func:`main`
parses the full ``refine.sh`` flag surface via :mod:`ralph.refine.args`,
surfaces any validation error on stderr, and exits 1 — mirroring
:func:`ralph_orchestrator.main`. US-005 wires the refinement loop:
:func:`main` dispatches validated args into :func:`ralph.refine.loop.run` and
returns its exit code.
"""

from __future__ import annotations

import argparse
import sys

from ralph.refine import args as args_module
from ralph.refine import loop as loop_module


def main(argv: list[str] | None = None) -> int:
    """Parse args, validate, and (US-005) dispatch the refinement run.

    Args:
        argv: Argument vector to parse. Defaults to ``sys.argv[1:]`` when
            ``None`` — parity with :func:`ralph_orchestrator.main`.

    Returns:
        The process exit code: argparse's own code for ``--help`` / usage
        errors, ``1`` when :func:`ralph.refine.args.validate` rejects the
        parsed args, else the exit code of :func:`ralph.refine.loop.run`
        (``0`` at threshold / ``1`` at max iterations or a stopped call /
        ``130`` on interrupt).
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

    return loop_module.run(parsed)
