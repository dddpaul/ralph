#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["pydantic>=2.5"]
# ///
"""Ralph autonomous-loop orchestrator (Python port).

Entry point for US-005. Mirrors the bash CLI in ``ralph.sh`` byte-for-byte
on flag names (AC #2) and within-iteration ordering (AC #5).

See ``design/ralph-python-refactor-prd.md`` for the full contract.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from ralph import args as args_module
from ralph import push as push_module
from ralph.loop import run as run_loop


def resolve_project_root() -> Path:
    """Resolve the project root, honoring ``RALPH_PROJECT_ROOT`` (AC #4).

    Fallback is ``Path(__file__).parent`` — the directory containing this
    orchestrator script (parity with bash's ``SCRIPT_DIR`` fallback).
    """
    env = os.environ.get("RALPH_PROJECT_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    """Parse args, validate, dispatch into the loop. Returns the process exit code."""
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

    project_root = resolve_project_root()
    refusal = push_module.no_push_refusal(
        enforced=push_module.shared_backlog_enforced(project_root),
        enabled=push_module.push_enabled(parsed.push),
        task_whitelist=parsed.task_whitelist,
    )
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return 1
    return run_loop(parsed, project_root)


if __name__ == "__main__":
    sys.exit(main())
