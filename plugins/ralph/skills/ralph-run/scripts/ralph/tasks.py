"""Backlog task picker — chooses the next iteration's target task.

Two modes, matching ``ralph.sh``:

* **Default**: query ``backlog task list -s "To Do" --plain``, then iterate
  candidates in ascending numeric ID order. Return the first candidate
  whose dependencies are all in ``Done`` status. Bash relied on the agent
  to enforce dependency order; the Python port pins it explicitly so the
  loop cannot launch a blocked task even if the agent is misbehaving.
  Candidates held by someone else are skipped too: a task whose
  ``Assignee:`` line names anyone besides the holder and ``@claude`` is
  taken. A bare ``@claude`` counts as unassigned.

* **Whitelist (``--tasks``)**: iterate the user-supplied IDs in the order
  they were given, return the first one still in ``To Do``. This REPLACES
  the lowest-ID rule — the user's order wins. Mirrors lines 731-744 of
  ``ralph.sh``.

Both modes skip the IDs in ``exclude`` — tasks an earlier iteration of the
same run left in ``To Do`` (TASK-324).

Both modes return ``None`` when no candidate is available, which the
orchestrator surfaces as ``EXIT_REASON="all tasks done"``.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BacklogTask:
    """Subset of a backlog task surfaced to the picker."""

    id: str
    status: str
    dependencies: tuple[str, ...]
    assignees: tuple[str, ...] = ()


_TASK_ID_RE = re.compile(r"\bTASK-(\d+)\b")
_STATUS_LINE_RE = re.compile(r"^Status:\s*(.+)$", re.MULTILINE)
_DEPENDENCIES_LINE_RE = re.compile(r"^Dependencies:\s*(.+)$", re.MULTILINE)
_ASSIGNEE_LINE_RE = re.compile(r"^Assignee:\s*(.+)$", re.MULTILINE)

UNASSIGNED_ASSIGNEE = "claude"
"""A bare ``@claude`` assignee is the agent itself, so it holds nothing."""


def _backlog_stdout(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["backlog", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ""
    return result.stdout


def _parse_status(view_output: str) -> str:
    match = _STATUS_LINE_RE.search(view_output)
    if match is None:
        return ""
    tail = match.group(1).strip()
    return re.sub(r"^[^A-Za-z]*", "", tail)


def _parse_dependencies(view_output: str) -> tuple[str, ...]:
    match = _DEPENDENCIES_LINE_RE.search(view_output)
    if match is None:
        return ()
    ids = _TASK_ID_RE.findall(match.group(1))
    return tuple(f"TASK-{n}" for n in ids)


def _normalize_assignee(raw: str) -> str:
    return raw.strip().strip("'\"").lstrip("@").strip()


def _parse_assignees(view_output: str) -> tuple[str, ...]:
    """Return the ``Assignee:`` names without the leading ``@``."""
    match = _ASSIGNEE_LINE_RE.search(view_output)
    if match is None:
        return ()
    names = (_normalize_assignee(part) for part in match.group(1).split(","))
    return tuple(name for name in names if name)


def resolve_holder(cwd: Path | None = None) -> str | None:
    """Return the holder: ``SHARED_BACKLOG_HOLDER``, else ``git config ralph.holder``.

    ``cwd`` is the clone whose git config is read (default: the current
    directory). Returns ``None`` when neither is set; every real assignee then
    counts as someone else.
    """
    env_holder = _normalize_assignee(os.environ.get("SHARED_BACKLOG_HOLDER", ""))
    if env_holder:
        return env_holder
    try:
        result = subprocess.run(
            ["git", "config", "--get", "ralph.holder"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    return _normalize_assignee(result.stdout) or None


def held_by_other(task: BacklogTask, holder: str | None) -> bool:
    """Return True when ``task`` has an assignee besides ``holder`` and ``@claude``."""
    own = {UNASSIGNED_ASSIGNEE}
    if holder:
        own.add(_normalize_assignee(holder))
    return any(name not in own for name in task.assignees)


def _list_todo_ids() -> list[str]:
    """Return ``To Do`` task IDs in ascending numeric order."""
    out = _backlog_stdout(["task", "list", "-s", "To Do", "--plain"])
    if not out or "No tasks found" in out:
        return []
    ids = _TASK_ID_RE.findall(out)
    seen: set[str] = set()
    unique: list[str] = []
    for raw in ids:
        if raw in seen:
            continue
        seen.add(raw)
        unique.append(raw)
    unique.sort(key=int)
    return [f"TASK-{n}" for n in unique]


def done_task_ids() -> list[str]:
    """Return all ``Done`` task IDs in ascending numeric order.

    Used by the orchestrator's iteration loop to compute the DONE_BEFORE /
    DONE_AFTER diff that populates ``StatusFile.tasks_done``. Bash uses
    ``backlog task list -s "Done" --plain | grep -o 'TASK-[0-9]*' | sort -u``;
    the Python port does the equivalent via :data:`_TASK_ID_RE`.
    """
    out = _backlog_stdout(["task", "list", "-s", "Done", "--plain"])
    if not out or "No tasks found" in out:
        return []
    ids = _TASK_ID_RE.findall(out)
    seen: set[str] = set()
    unique: list[str] = []
    for raw in ids:
        if raw in seen:
            continue
        seen.add(raw)
        unique.append(raw)
    unique.sort(key=int)
    return [f"TASK-{n}" for n in unique]


def current_in_progress_task() -> str | None:
    """Return the first ``In Progress`` task ID, or ``None`` if none exist.

    Mirrors ``ralph.sh:849``::

        CURRENT_TASK=$(backlog task list -s 'In Progress' --plain \
            | grep -o 'TASK-[0-9]*' | head -1)

    The bash orchestrator re-derived ``current_task`` from the live In
    Progress list after every iteration, so the status file nulled it once
    the picked task moved to Done. The Python port had left ``current_task``
    stuck at the last-picked task; this restores the null-clearing contract
    the ``ralph-status`` / ``ralph-status-watch`` skills read (TASK-200).
    """
    out = _backlog_stdout(["task", "list", "-s", "In Progress", "--plain"])
    if not out or "No tasks found" in out:
        return None
    match = _TASK_ID_RE.search(out)
    return match.group(0) if match else None


def count_remaining(whitelist: list[str] | None = None) -> int:
    """Return the count of ``To Do`` tasks; honors whitelist when provided.

    Mirrors ``count_remaining_tasks()`` in ``ralph.sh:347-367``.
    """
    if whitelist:
        count = 0
        for raw in whitelist:
            task = fetch_task(raw)
            if task is not None and "To Do" in task.status:
                count += 1
        return count
    return len(_list_todo_ids())


def fetch_task(task_id: str) -> BacklogTask | None:
    """Resolve ``task_id`` to a ``BacklogTask`` via ``backlog task <id> --plain``.

    Accepts either a bare numeric ``"152"`` or a ``"TASK-152"`` form. Returns
    ``None`` when the task is missing or the CLI is unavailable.
    """
    numeric = task_id.removeprefix("TASK-")
    out = _backlog_stdout(["task", numeric, "--plain"])
    if not out:
        return None
    if re.search(rf"^Task {re.escape(numeric)} not found\.$", out, re.MULTILINE):
        return None
    status = _parse_status(out)
    dependencies = _parse_dependencies(out)
    assignees = _parse_assignees(out)
    return BacklogTask(
        id=f"TASK-{numeric}",
        status=status,
        dependencies=dependencies,
        assignees=assignees,
    )


def _all_dependencies_done(task: BacklogTask) -> bool:
    for dep in task.dependencies:
        dep_task = fetch_task(dep)
        if dep_task is None or "Done" not in dep_task.status:
            return False
    return True


def pick_next_task(
    whitelist: list[str] | None = None,
    holder: str | None = None,
    exclude: Collection[str] = (),
) -> str | None:
    """Return the next task ID the orchestrator should run, or ``None``.

    Args:
        whitelist: Optional list of task IDs (``"152"`` or ``"TASK-152"``)
            in the order the user supplied via ``--tasks``. When present,
            the first whitelist entry still in ``To Do`` wins and the
            dependency rule is NOT applied — the user's hand-picked order
            is authoritative. The bash port behaves the same way at
            ``ralph.sh:731-744``.
        holder: The run's holder (see :func:`resolve_holder`). In default
            mode a candidate assigned to anyone besides the holder and
            ``@claude`` is skipped.
        exclude: ``TASK-N`` IDs never returned, in both modes. The loop
            passes the tasks an earlier iteration of this run left in
            ``To Do`` so they are not picked again.
    """
    if whitelist:
        for raw in whitelist:
            if f"TASK-{raw.removeprefix('TASK-')}" in exclude:
                continue
            task = fetch_task(raw)
            if task is not None and "To Do" in task.status:
                return task.id
        return None

    for tid in _list_todo_ids():
        if tid in exclude:
            continue
        task = fetch_task(tid)
        if task is None or held_by_other(task, holder):
            continue
        if _all_dependencies_done(task):
            return task.id
    return None
