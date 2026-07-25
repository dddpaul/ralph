"""Post-loop publish: push the master ref to ``origin`` after an advancing run.

TASK-211. The Ralph loop merges each task branch to LOCAL master (the agent
runs ``git checkout master && git merge <branch>`` per the CLAUDE.md Task
Lifecycle; ``loop.py`` itself never merges). For this repo — the upstream
producer of the control-gateway orchestration mesh — a merge only becomes
"canon" once it reaches ``origin/master`` on GitHub, where downstream mesh
members read it. This module publishes that canon automatically at the end of
a run.

Publish is ENABLED BY DEFAULT and gated on three independent conditions, ALL
of which must hold before a push is attempted:

1. Not opted out — neither ``--no-push`` nor a truthy ``RALPH_NO_PUSH`` env
   variable was given (AC #1, #6).
2. An ``origin`` remote is registered (AC #3).
3. The loop actually advanced master — the ``git rev-parse master`` SHA
   snapshotted before the loop differs from the SHA after it (AC #4).

When any gate fails the run skips cleanly: no push, no error, exit code
untouched. When a push IS attempted and fails, the failure is surfaced loudly
— logged to stderr AND reported via a non-zero exit code — never swallowed
(AC #5).
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

DEFAULT_MASTER_REF = "master"
"""The ref this repo publishes as mesh canon (task body: 'Master ref: master')."""

PUSH_DISABLE_ENV = "RALPH_NO_PUSH"
"""Env opt-out. A truthy value disables push regardless of the CLI default."""

_ORIGIN = "origin"
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _env_truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in _TRUTHY


def push_enabled(cli_push: bool) -> bool:
    """Resolve whether push-on-complete is enabled (AC #1, #6).

    Push is on by default. It is disabled if EITHER the CLI opt-out was given
    (``cli_push`` is ``False`` — i.e. ``--no-push``) OR ``RALPH_NO_PUSH`` is
    set to a truthy value. Either opt-out alone is sufficient.
    """
    if not cli_push:
        return False
    return not _env_truthy(os.environ.get(PUSH_DISABLE_ENV))


def _git(args: list[str], project_root: Path) -> subprocess.CompletedProcess[str]:
    """Run ``git <args>`` anchored at ``project_root`` (argv list, no shell)."""
    return subprocess.run(  # noqa: S603 — argv list, no shell.
        ["git", *args],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )


def current_rev(project_root: Path, ref: str = DEFAULT_MASTER_REF) -> str | None:
    """Return the SHA ``ref`` resolves to, or ``None`` if it can't be resolved.

    A ``None`` here (ref missing, or ``project_root`` is not a git repo) makes
    the advancement check conservative: an unresolved before/after pair is
    treated as "did not advance", so nothing is pushed.
    """
    result = _git(["rev-parse", "--verify", "--quiet", ref], project_root)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def has_origin_remote(project_root: Path) -> bool:
    """Return ``True`` iff an ``origin`` remote is registered (AC #3)."""
    result = _git(["remote"], project_root)
    if result.returncode != 0:
        return False
    return _ORIGIN in result.stdout.split()


@dataclass(frozen=True)
class PushOutcome:
    """Result of :func:`maybe_push_after_loop`.

    ``exit_code`` is ``0`` for every skip and for a successful push; it is the
    non-zero ``git push`` return code only when an attempted push failed.
    """

    action: str  # "pushed" | "skipped" | "failed"
    reason: str
    exit_code: int


def maybe_push_after_loop(
    *,
    project_root: Path,
    enabled: bool,
    rev_before: str | None,
    ref: str = DEFAULT_MASTER_REF,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> PushOutcome:
    """Push ``ref`` to ``origin`` when all gates pass; otherwise skip cleanly.

    Args:
        project_root: Repo root; every git command runs with this ``cwd``.
        enabled: Result of :func:`push_enabled` — the resolved opt-out gate.
        rev_before: ``ref``'s SHA snapshotted BEFORE the loop (``None`` if it
            could not be resolved then).
        ref: The branch to publish (default ``master``).
        out: Info stream. Defaults to ``sys.stdout``.
        err: Error stream. Defaults to ``sys.stderr``.

    Returns:
        A :class:`PushOutcome`. ``exit_code`` is non-zero ONLY when a push was
        attempted and failed (AC #5); every skip returns ``exit_code == 0``.
    """
    out_stream: TextIO = out if out is not None else sys.stdout
    err_stream: TextIO = err if err is not None else sys.stderr

    if not enabled:
        return PushOutcome("skipped", "push disabled (opt-out)", 0)

    if not has_origin_remote(project_root):
        return PushOutcome("skipped", f"no '{_ORIGIN}' remote registered", 0)

    rev_after = current_rev(project_root, ref)
    if rev_before is None or rev_after is None or rev_before == rev_after:
        return PushOutcome("skipped", f"{ref} did not advance", 0)

    print(
        f"Publishing {ref} to {_ORIGIN} "
        f"({rev_before[:9]} -> {rev_after[:9]})...",
        file=out_stream,
    )
    result = _git(["push", _ORIGIN, ref], project_root)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        print(
            f"ERROR: git push {_ORIGIN} {ref} failed "
            f"(exit {result.returncode}): {detail}",
            file=err_stream,
        )
        return PushOutcome("failed", "git push failed", result.returncode)

    if result.stdout.strip():
        out_stream.write(result.stdout)
    print(f"Published {ref} to {_ORIGIN}.", file=out_stream)
    return PushOutcome("pushed", "push succeeded", 0)
