#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Fake ``claude`` CLI for the refine end-to-end test (US-009).

Stands in for a real LLM the way ``fake_claude.py`` does for the coder loop, but
speaks the *refine* author/reviewer protocol instead of the backlog one. The
refine loop's ``ClaudeTool`` spawns ``claude ... --print`` and feeds the composed
prompt on stdin (``ralph.tools._subprocess.execute``); this shim reads that
prompt, tells an author call from a reviewer call by the trailing output-protocol
instruction (:data:`ralph.refine.roles.REVIEW_INSTRUCTION` — the one contract the
roles module exports for exactly this stub), and emits the matching tag block:

* **author** → an ``<artifact>...</artifact>`` block; the body carries the
  author-call index so successive ``artifact-vN`` files differ;
* **reviewer** → a converging ``SCORE: N`` line plus a ``<summary>...</summary>``
  block. The score sequence is supplied via ``FAKE_REFINE_SCORES`` (comma-
  separated) and indexed by a per-run counter file derived from
  ``FAKE_REFINE_STATE`` so the score climbs across iterations until it meets the
  threshold.

No real model is ever contacted: the loop, extractor, tool subprocess layer, and
summary writer all run for real against this deterministic stand-in. Flags
(``--model``, ``--effort``, ``--print``, ``--dangerously-skip-permissions``) are
accepted and ignored — the prompt arrives on stdin, exactly as with real
``claude``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Reach the pinned ``ralph`` package root so the stub keys on the *same*
# REVIEW_INSTRUCTION the loop appends, rather than a drifting copy of the text.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from ralph.refine.roles import REVIEW_INSTRUCTION  # noqa: E402


def _bump_counter(state_path: Path) -> int:
    """Return the current 0-based call index and persist the increment.

    Each ``claude`` invocation is a fresh process, so the climbing score
    sequence (and the per-iteration artifact body) is threaded through a file
    rather than in-memory state.
    """
    count = int(state_path.read_text()) if state_path.exists() else 0
    state_path.write_text(str(count + 1))
    return count


def _author_output(index: int) -> str:
    """An ``<artifact>`` block whose body varies per author call."""
    return (
        f"Here is the artifact.\n"
        f"<artifact>\n# Fake artifact v{index + 1}\nRefined body {index + 1}.\n"
        f"</artifact>\n"
    )


def _reviewer_output(index: int) -> str:
    """A ``SCORE:`` line (from ``FAKE_REFINE_SCORES``) plus a ``<summary>`` block."""
    scores = [int(s) for s in os.environ["FAKE_REFINE_SCORES"].split(",")]
    score = scores[index] if index < len(scores) else scores[-1]
    return (
        f"Reasonable draft.\nSCORE: {score}\n"
        f"<summary>fake review {index + 1}</summary>\n"
    )


def main() -> int:
    prompt = sys.stdin.read()
    state = Path(os.environ["FAKE_REFINE_STATE"])
    if prompt.rstrip().endswith(REVIEW_INSTRUCTION):
        index = _bump_counter(state.with_name(f"{state.name}.reviewer"))
        sys.stdout.write(_reviewer_output(index))
    else:
        index = _bump_counter(state.with_name(f"{state.name}.author"))
        sys.stdout.write(_author_output(index))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
