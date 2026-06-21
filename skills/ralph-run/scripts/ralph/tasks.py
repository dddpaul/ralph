"""Backlog task picker — chooses the next iteration's target task.

Two modes, matching ``ralph.sh``:

* **Default**: query ``backlog task list -s "To Do" --plain``, then iterate
  candidates in ascending numeric ID order. Return the first candidate
  whose dependencies are all in ``Done`` status. Bash relied on the agent
  to enforce dependency order; the Python port pins it explicitly so the
  loop cannot launch a blocked task even if the agent is misbehaving.

* **Whitelist (``--tasks``)**: iterate the user-supplied IDs in the order
  they were given, return the first one still in ``To Do``. This REPLACES
  the lowest-ID rule — the user's order wins. Mirrors lines 731-744 of
  ``ralph.sh``.

Both modes return ``None`` when no candidate is available, which the
orchestrator surfaces as ``EXIT_REASON="all tasks done"``.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class BacklogTask:
    """Subset of a backlog task surfaced to the picker."""

    id: str
    status: str
    dependencies: tuple[str, ...]


_TASK_ID_RE = re.compile(r"\bTASK-(\d+)\b")
_STATUS_LINE_RE = re.compile(r"^Status:\s*(.+)$", re.MULTILINE)
_DEPENDENCIES_LINE_RE = re.compile(r"^Dependencies:\s*(.+)$", re.MULTILINE)


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
    return BacklogTask(id=f"TASK-{numeric}", status=status, dependencies=dependencies)


def _all_dependencies_done(task: BacklogTask) -> bool:
    for dep in task.dependencies:
        dep_task = fetch_task(dep)
        if dep_task is None or "Done" not in dep_task.status:
            return False
    return True


def pick_next_task(whitelist: list[str] | None = None) -> str | None:
    """Return the next task ID the orchestrator should run, or ``None``.

    Args:
        whitelist: Optional list of task IDs (``"152"`` or ``"TASK-152"``)
            in the order the user supplied via ``--tasks``. When present,
            the first whitelist entry still in ``To Do`` wins and the
            dependency rule is NOT applied — the user's hand-picked order
            is authoritative. The bash port behaves the same way at
            ``ralph.sh:731-744``.
    """
    if whitelist:
        for raw in whitelist:
            task = fetch_task(raw)
            if task is not None and "To Do" in task.status:
                return task.id
        return None

    for tid in _list_todo_ids():
        task = fetch_task(tid)
        if task is None:
            continue
        if _all_dependencies_done(task):
            return task.id
    return None
