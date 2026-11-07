"""Where ``shared-backlog.sh integrate`` runs its checks, and how a timeout stops them (TASK-313).

A run that used the devcontainer runs integrate's configured checks inside it:
:func:`devcontainer_env` hands the script a ``SHARED_BACKLOG_CHECKS_EXEC``
prefix of ``devcontainer exec --workspace-folder <root>`` that also tags every
process the checks start with ``RALPH_INTEGRATE_TAG=<token>``. Killing the host
``devcontainer exec`` client does not stop what it started in the container, so
the tag is how that process tree is found again: :func:`reap_command` runs a
``devcontainer exec`` that SIGKILLs every tagged process. The script runs it
(``SHARED_BACKLOG_CHECKS_KILL``) after its own deadline or a signal and before
it releases its lock; the orchestrator runs it again after its own timeout.

:func:`kill_tree` stops the host side: the script's process group and every
group under it, since the script runs each subcommand in a group of its own.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import shlex
import signal
import subprocess
import time
from pathlib import Path

TAG_VAR = "RALPH_INTEGRATE_TAG"
"""The environment variable that marks the checks' processes inside the container."""

_REAP_ROUNDS = 10

# SIGKILL every process whose environment carries the tag, until a round finds
# none; a round catches what a parent forked while the previous one ran. The
# reaper's own `devcontainer exec` does not carry the tag.
_REAP_SCRIPT = f"""\
tag=$1; n=0; round=0
while [ "$round" -lt {_REAP_ROUNDS} ]; do
  found=0
  for d in /proc/[0-9]*; do
    p=${{d#/proc/}}
    [ "$p" = "$$" ] && continue
    if tr '\\000' '\\n' <"$d/environ" 2>/dev/null | grep -qx "$tag"; then
      kill -KILL "$p" 2>/dev/null && {{ found=1; n=$((n + 1)); }}
    fi
  done
  [ "$found" = 1 ] || break
  round=$((round + 1)); sleep 1
done
echo "killed $n check process(es) left in the devcontainer"
"""


def new_tag() -> str:
    """Return a fresh ``RALPH_INTEGRATE_TAG=<token>`` assignment."""
    return f"{TAG_VAR}={secrets.token_hex(8)}"


def exec_prefix(workspace_folder: Path) -> list[str]:
    """Return the ``devcontainer exec`` argv prefix for the run's container."""
    return ["devcontainer", "exec", "--workspace-folder", str(workspace_folder)]


def reap_argv(workspace_folder: Path, tag: str) -> list[str]:
    """Return the argv that SIGKILLs every process carrying ``tag`` inside the container."""
    return [*exec_prefix(workspace_folder), "sh", "-c", _REAP_SCRIPT, "ralph-reap", tag]


def reap_command(workspace_folder: Path, tag: str) -> str:
    """Return :func:`reap_argv` as one ``sh -c`` command line."""
    return shlex.join(reap_argv(workspace_folder, tag))


def devcontainer_env(workspace_folder: Path, tag: str) -> dict[str, str]:
    """Return the environment that makes integrate run its checks in the container.

    Raises:
        ValueError: when the path holds whitespace, which the script's
            whitespace-split ``SHARED_BACKLOG_CHECKS_EXEC`` cannot carry.
    """
    folder = str(workspace_folder)
    if any(c.isspace() for c in folder):
        raise ValueError(f"cannot run integrate's checks in the devcontainer: {folder!r} contains whitespace")
    return {
        "SHARED_BACKLOG_CHECKS_EXEC": shlex.join([*exec_prefix(workspace_folder), "--remote-env", tag]),
        "SHARED_BACKLOG_CHECKS_KILL": reap_command(workspace_folder, tag),
    }


def reap(workspace_folder: Path, tag: str, timeout_sec: int = 60) -> str:
    """Run :func:`reap_argv` and return its report (or why it failed)."""
    try:
        result = subprocess.run(
            reap_argv(workspace_folder, tag),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"could not stop the checks in the devcontainer: {exc}"
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        return f"could not stop the checks in the devcontainer (exit {result.returncode}): {detail}"
    return result.stdout.strip()


def process_groups_under(pid: int) -> set[int]:
    """Return the process groups of ``pid`` and of every process descended from it."""
    try:
        listing = subprocess.run(
            ["ps", "-A", "-o", "pid=,ppid=,pgid="], check=False, capture_output=True, text=True
        ).stdout
    except OSError:
        return {pid}
    children: dict[int, list[tuple[int, int]]] = {}
    for line in listing.splitlines():
        fields = line.split()
        if len(fields) == 3 and all(f.isdigit() for f in fields):
            child, parent, group = (int(f) for f in fields)
            children.setdefault(parent, []).append((child, group))
    groups = {pid}
    todo = [pid]
    while todo:
        for child, group in children.get(todo.pop(), []):
            groups.add(group)
            todo.append(child)
    return groups


def _signal_groups(groups: set[int], sig: signal.Signals) -> None:
    for group in groups:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(group, sig)


def kill_tree(proc: subprocess.Popen[bytes], grace_sec: float) -> None:
    """Stop ``proc``, the leader of its own group, and every group under it.

    SIGTERM goes to ``proc``'s group first, so the script's traps can stop the
    checks and release the lock; whatever is left after ``grace_sec`` is
    SIGKILLed, the groups noted before the SIGTERM included.
    """
    groups = process_groups_under(proc.pid)
    _signal_groups({proc.pid}, signal.SIGTERM)
    deadline = time.monotonic() + grace_sec
    while proc.poll() is None and time.monotonic() < deadline:
        time.sleep(0.1)
    _signal_groups(groups | process_groups_under(proc.pid), signal.SIGKILL)
    proc.wait()
