#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["pydantic>=2.5"]
# ///
"""ralph-refine adversarial author-reviewer loop orchestrator (Python port).

Entry point for US-001. Mirrors ``ralph_orchestrator.py``: a thin PEP-723
launcher that pins the shared ``ralph`` package root onto ``sys.path`` (so the
``ralph.*`` reused layer and the ``ralph.refine`` sub-package import cleanly)
and dispatches into :func:`ralph.refine.cli.main`.

See ``design/ralph-refine-prd.md`` (US-001) and backlog ``doc-4`` (ralph-refine
Overview) for the full contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from ralph.refine.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
