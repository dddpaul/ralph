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
— logged to stderr with its class (non-fast-forward, auth, hook, unreachable
or rejected) AND reported via a non-zero exit code — never swallowed (AC #5).

TASK-312. A clone with ``ralph.sharedBacklog`` true enforces the shared-backlog
protocol and publishes differently: the loop runs the plugin's
``shared-backlog.sh integrate --task N`` after each completed iteration that
advanced master, and once more at the end of the run unless a publish failed
(:func:`integrate`). There ``--no-push`` is allowed only for a run whose
``--tasks`` names one task (:func:`no_push_refusal`); it stops publishing the
work, not pushing the claim. Only ``shared-backlog.sh enable`` sets the switch,
and it refuses while the protocol's release gate is closed.
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

SHARED_BACKLOG_SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "shared-backlog.sh"
"""The plugin's shared-backlog script (push.py → ralph/ → scripts/ → ralph-run/ → skills/ → plugin root)."""

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
    return not env_opt_out()


def env_opt_out() -> bool:
    """Return ``True`` iff ``RALPH_NO_PUSH`` is set to a truthy value."""
    return _env_truthy(os.environ.get(PUSH_DISABLE_ENV))


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


def shared_backlog_enforced(project_root: Path) -> bool:
    """Return ``True`` iff the clone's ``ralph.sharedBacklog`` switch is true."""
    result = _git(["config", "--bool", "--get", "ralph.sharedBacklog"], project_root)
    return result.returncode == 0 and result.stdout.strip() == "true"


def no_push_refusal(*, enforced: bool, enabled: bool, task_whitelist: list[str]) -> str | None:
    """Return the preflight refusal for an opted-out run in an enforcing clone, else ``None``.

    In a clone that enforces the shared-backlog protocol a run may skip
    publishing only when ``--tasks`` names exactly one task.
    """
    if not enforced or enabled or len(task_whitelist) == 1:
        return None
    return (
        "Error: --no-push (or RALPH_NO_PUSH) in a clone that enforces the shared-backlog protocol "
        "needs --tasks naming exactly one task."
    )


def classify_push_failure(detail: str) -> str:
    """Name the class of a failed ``git push`` from its output.

    The same patterns as ``push_master`` in ``shared-backlog.sh``: auth,
    non-fast-forward, unreachable or hook, else rejected.
    """
    auth = any(
        marker in detail
        for marker in (
            "Permission denied",
            "Authentication failed",
            "could not read Username",
            "Access denied",
            "error: 403",
        )
    )
    if any(
        marker in detail
        for marker in ("[rejected]", "non-fast-forward", "fetch first", "failed to update ref", "cannot lock ref")
    ):
        return "non-fast-forward"
    if auth:
        return "auth"
    if any(marker in detail for marker in ("Could not read from remote", "unable to access", "Could not resolve")):
        return "unreachable"
    if "hook" in detail or ("[remote rejected]" not in detail and "failed to push some refs" in detail):
        return "hook"
    return "rejected"


@dataclass(frozen=True)
class PushOutcome:
    """Result of :func:`maybe_push_after_loop`.

    ``exit_code`` is ``0`` for every skip and for a successful push; it is the
    non-zero ``git push`` return code only when an attempted push failed.
    """

    action: str  # "pushed" | "skipped" | "failed"
    reason: str
    exit_code: int
    failure_class: str | None = None


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
        failure_class = classify_push_failure(detail)
        print(
            f"ERROR: git push {_ORIGIN} {ref} failed "
            f"({failure_class}, exit {result.returncode}): {detail}",
            file=err_stream,
        )
        return PushOutcome("failed", "git push failed", result.returncode, failure_class)

    if result.stdout.strip():
        out_stream.write(result.stdout)
    print(f"Published {ref} to {_ORIGIN}.", file=out_stream)
    return PushOutcome("pushed", "push succeeded", 0)


def integrate(
    *,
    project_root: Path,
    task_id: str | None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> PushOutcome:
    """Publish local master through ``shared-backlog.sh integrate [--task N]``.

    The script merges ``origin/master`` (never rebases), runs the duplicate
    check and the configured checks, and pushes under its own deadline. Its
    output is relayed to ``out`` and ``err``.

    Returns:
        ``"pushed"`` with exit code 0, or ``"failed"`` with the script's
        non-zero exit code (1 refused or check failed, 2 origin unreachable).
    """
    out_stream: TextIO = out if out is not None else sys.stdout
    err_stream: TextIO = err if err is not None else sys.stderr
    argv = ["bash", str(SHARED_BACKLOG_SCRIPT), "integrate"]
    if task_id:
        argv += ["--task", task_id.removeprefix("TASK-")]
    print(f"Publishing master through shared-backlog integrate{f' for {task_id}' if task_id else ''}...",
          file=out_stream)
    result = subprocess.run(
        argv,
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    out_stream.write(result.stdout)
    err_stream.write(result.stderr)
    if result.returncode == 0:
        return PushOutcome("pushed", "integrate succeeded", 0)
    return PushOutcome("failed", f"shared-backlog integrate failed (exit {result.returncode})", result.returncode)


def local_state(project_root: Path, ref: str = DEFAULT_MASTER_REF) -> str:
    """Describe ``ref`` against ``origin/<ref>`` and any unfinished git operation, for a failure report."""
    head = current_rev(project_root, ref)
    parts = [f"local {ref} at {head[:9] if head else 'unknown'}"]
    counts = _git(["rev-list", "--left-right", "--count", f"{ref}...{_ORIGIN}/{ref}"], project_root)
    if counts.returncode == 0 and len(counts.stdout.split()) == 2:
        ahead, behind = counts.stdout.split()
        parts.append(f"{ahead} ahead / {behind} behind {_ORIGIN}/{ref}")
    git_dir = _git(["rev-parse", "--absolute-git-dir"], project_root)
    if git_dir.returncode == 0:
        root = Path(git_dir.stdout.strip())
        for name, label in (("MERGE_HEAD", "merge"), ("rebase-merge", "rebase"), ("CHERRY_PICK_HEAD", "cherry-pick")):
            if (root / name).exists():
                parts.append(f"a {label} is in progress")
    return "; ".join(parts)
