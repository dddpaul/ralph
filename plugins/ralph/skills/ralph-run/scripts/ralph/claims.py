"""Claim lifecycle for Ralph runs in enforcing clones (TASK-315).

In a clone with ``ralph.sharedBacklog`` true a run works only on a task whose
claim it has pushed:

* :class:`RunSession` resolves the holder once and refuses the run without
  one. It takes the shared-backlog run lock for the whole run, so a second run
  and an unrelated ``sync`` or ``claim`` in the clone refuse. For the run it
  exports ``SHARED_BACKLOG_HOLDER`` and ``RALPH_RUN_LOCK_TOKEN``: the run's own
  protocol calls carry the token, and the devcontainer prefix forwards both
  into the container.
* :func:`claim_next` runs before each iteration. It syncs, picks the next
  task, claims it and pushes the claim through ``shared-backlog.sh claim``,
  then syncs again and checks the claim. A claim that loses moves on to the
  next candidate. With ``--tasks`` a task another holder holds is refused
  unless ``--force-claim`` is given.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Collection
from pathlib import Path

from ralph import tasks as tasks_module
from ralph.push import SHARED_BACKLOG_SCRIPT

HOLDER_ENV = "SHARED_BACKLOG_HOLDER"
RUN_LOCK_TOKEN_ENV = "RALPH_RUN_LOCK_TOKEN"
DELEGATED_ENV = (HOLDER_ENV, RUN_LOCK_TOKEN_ENV)
"""Variables the run hands to every tool subprocess, the devcontainer included."""


class ClaimError(Exception):
    """A refusal or failure that stops the run; ``exit_code`` is the run's exit code."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _script(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run ``shared-backlog.sh <args>`` at ``project_root`` and relay its stderr."""
    proc = subprocess.run(
        ["bash", str(SHARED_BACKLOG_SCRIPT), *args],
        cwd=project_root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(proc.stderr)
    return proc


def run_holder(holder: str | None) -> str:
    """Return ``@holder`` for an enforcing run.

    Raises:
        ClaimError: when there is no holder, or it is the generic ``@claude``.
    """
    if not holder or holder == tasks_module.UNASSIGNED_ASSIGNEE:
        raise ClaimError(
            "this clone enforces the shared-backlog protocol and the run has no holder: "
            "set SHARED_BACKLOG_HOLDER or git config ralph.holder to a per-host @name (not @claude)"
        )
    return f"@{holder}"


class RunSession:
    """The run lock and the holder of one run in an enforcing clone."""

    def __init__(self, project_root: Path, holder: str, token: str, saved_env: dict[str, str | None]) -> None:
        self.project_root = project_root
        self.holder = holder
        self.token = token
        self._saved_env = saved_env

    @classmethod
    def open(cls, project_root: Path, holder: str | None) -> RunSession:
        """Check the holder, take the run lock and export the delegated variables.

        Raises:
            ClaimError: when the holder is missing or the run lock is not taken.
        """
        at = run_holder(holder)
        proc = _script(project_root, "run-lock", "--pid", str(os.getpid()))
        token = proc.stdout.strip()
        if proc.returncode != 0 or not token:
            raise ClaimError(
                "the shared-backlog run lock is not taken: another Ralph run or protocol operation "
                "holds this clone",
                proc.returncode or 1,
            )
        saved = {name: os.environ.get(name) for name in DELEGATED_ENV}
        os.environ[HOLDER_ENV] = at
        os.environ[RUN_LOCK_TOKEN_ENV] = token
        print(f"Ralph: holding the shared-backlog run lock as {at}", flush=True)
        return cls(project_root, at, token, saved)

    def close(self) -> None:
        """Release the run lock and restore the delegated variables."""
        _script(self.project_root, "run-unlock", self.token)
        for name, value in self._saved_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _sync(project_root: Path, purpose: str) -> None:
    proc = _script(project_root, "sync")
    if proc.returncode != 0:
        raise ClaimError(f"shared-backlog sync {purpose} failed (exit {proc.returncode})", proc.returncode)


def _holds(task_id: str, holder: str) -> bool:
    """True when ``task_id`` is To Do and held by ``holder`` alone (``@claude`` aside)."""
    task = tasks_module.fetch_task(task_id)
    if task is None or "To Do" not in task.status:
        return False
    return holder.lstrip("@") in task.assignees and not tasks_module.held_by_other(task, holder)


def _lost(task_id: str, holder: str) -> bool:
    """True when a refused claim lost to someone: the task is taken or no longer To Do."""
    task = tasks_module.fetch_task(task_id)
    if task is None:
        return False
    return "To Do" not in task.status or tasks_module.held_by_other(task, holder)


def claim(project_root: Path, task_id: str, holder: str, *, force: bool = False) -> bool:
    """Claim ``task_id`` for ``holder``, push the claim and check it again.

    Returns:
        ``True`` when the claim holds on origin, ``False`` when it lost.

    Raises:
        ClaimError: on any other refusal or failure (origin unreachable, local
            master ahead, unfinished dependencies, the task missing).
    """
    argv = ["claim", task_id.removeprefix("TASK-"), "--as", holder]
    if force:
        argv.append("--force")
    proc = _script(project_root, *argv)
    if proc.returncode == 0:
        sys.stdout.write(proc.stdout)
        _sync(project_root, f"to re-check the claim of {task_id}")
        return _holds(task_id, holder)
    if proc.returncode == 1 and _lost(task_id, holder):
        return False
    raise ClaimError(f"claiming {task_id} failed (exit {proc.returncode})", proc.returncode)


def claim_next(
    project_root: Path,
    *,
    holder: str,
    whitelist: list[str] | None,
    exclude: Collection[str] = (),
    force: bool = False,
) -> str | None:
    """Sync, then pick and claim the next task; ``None`` when no candidate is left.

    Args:
        project_root: The clone; the picker reads the backlog of the current
            directory, like the rest of the loop.
        holder: The run's holder, ``@name``.
        whitelist: ``--tasks`` IDs, or ``None`` for default mode.
        exclude: ``TASK-N`` IDs never picked.
        force: ``--force-claim``: take over a ``--tasks`` task another holder holds.

    Raises:
        ClaimError: when a ``--tasks`` task is held by another holder without
            ``force``, or a sync or claim fails for a reason other than losing.
    """
    _sync(project_root, "before picking a task")
    lost: set[str] = set()
    while True:
        task_id = tasks_module.pick_next_task(
            whitelist=whitelist, holder=holder.lstrip("@"), exclude={*exclude, *lost}
        )
        if task_id is None:
            return None
        if whitelist and not force:
            task = tasks_module.fetch_task(task_id)
            if task is not None and tasks_module.held_by_other(task, holder):
                own = (holder.lstrip("@"), tasks_module.UNASSIGNED_ASSIGNEE)
                others = ", ".join(f"@{name}" for name in task.assignees if name not in own)
                raise ClaimError(f"{task_id} is held by {others}, not {holder}; --force-claim takes it over")
        if claim(project_root, task_id, holder, force=force):
            return task_id
        print(f"Ralph: the claim of {task_id} lost; trying the next candidate", flush=True)
        lost.add(task_id)
