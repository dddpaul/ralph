"""ralph-refine CLI entry point.

The single wiring point the ``refine_orchestrator.py`` launcher dispatches
into (US-001 AC #2). US-001 ships the scaffold: an :class:`argparse.ArgumentParser`
that responds to ``--help`` with usage and exit 0 (AC #3). The full flag set,
validation, and refinement-loop dispatch land in US-002+ — this module is the
seam they extend.
"""

from __future__ import annotations

import argparse
import sys

_DESCRIPTION = (
    "Adversarial author-reviewer refinement loop: iterate a digital artifact "
    "(md / draw.io / PlantUML) through author and reviewer roles until a "
    "reviewer score meets a threshold."
)


def build_parser() -> argparse.ArgumentParser:
    """Construct the ``refine`` argument parser.

    US-001 scaffold: program name, description, and epilog only, so ``--help``
    prints usage. US-002 fills in the flag set (``--prompt`` / ``--draft`` /
    ``--author`` / ``--reviewer`` / ``--type`` / …) and validation.

    Returns:
        A parser configured with ``prog="refine"`` and the refine description.
    """
    return argparse.ArgumentParser(
        prog="refine",
        description=_DESCRIPTION,
        epilog="Full flag reference lands in TASK-202 (CLI argument parsing).",
    )


def main(argv: list[str] | None = None) -> int:
    """Parse args and dispatch the refinement run.

    US-001 scaffold: build the parser and hand off to argparse, which prints
    usage and raises ``SystemExit(0)`` for ``--help`` (AC #3). The parse /
    validate / loop wiring lands in US-002+.

    Args:
        argv: Argument vector to parse. Defaults to ``sys.argv[1:]`` when
            ``None`` — parity with :func:`ralph_orchestrator.main`.

    Returns:
        The process exit code (``0`` on the scaffold's successful no-op parse).
    """
    real_argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    parser.parse_args(real_argv)
    return 0
