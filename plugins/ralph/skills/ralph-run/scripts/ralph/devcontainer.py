"""Pre-loop devcontainer setup.

Mirrors bash ``ralph.sh:602-611`` — bring the container up before the
iteration loop starts so the first ``devcontainer exec`` finds a running
container. Without this step, every default-python + ``--devcontainer``
launch fails immediately with ``Error: Dev container not found.``
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

# Files read only when the container is CREATED — an edit after that is
# silently ignored by a reused container (TASK-258).
_CREATION_INPUTS = (
    Path(".devcontainer") / "devcontainer.json",
    Path(".devcontainer") / "Dockerfile",
)
_DOCKER_TIMEOUT_SEC = 10
STALE_CONTAINER_EXIT = 1
# A tuple constant, not ``except (A, B)``: ruff's py314 formatter strips those
# parentheses into syntax older host Pythons reject.
_PROBE_ERRORS = (OSError, subprocess.SubprocessError)


def _docker(*args: str) -> str | None:
    """Run ``docker <args>`` and return stripped stdout, or ``None`` on any failure."""
    try:
        result = subprocess.run(  # noqa: S603 — argv list, no shell.
            ["docker", *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=_DOCKER_TIMEOUT_SEC,
        )
    except _PROBE_ERRORS:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def container_created_at(workspace_folder: Path) -> datetime | None:
    """Creation time of the devcontainer bound to ``workspace_folder``.

    The devcontainer CLI labels its container with
    ``devcontainer.local_folder=<abs workspace path>``. Returns ``None`` when
    the answer is unknowable — no ``docker`` on PATH, no matching container,
    a failing ``ps``/``inspect``, or an unparseable timestamp.
    """
    if shutil.which("docker") is None:
        return None
    label = f"label=devcontainer.local_folder={workspace_folder.absolute()}"
    ids = _docker("ps", "-aq", "--filter", label)
    if not ids:
        return None
    # ``ps`` lists newest first; that is the container ``up`` would reuse.
    created = _docker("inspect", ids.split()[0], "--format", "{{.Created}}")
    if not created:
        return None
    try:
        parsed = datetime.fromisoformat(created)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def stale_inputs(
    workspace_folder: Path, created: datetime
) -> list[tuple[Path, datetime]]:
    """Creation inputs whose mtime is later than ``created``, with that mtime."""
    stale: list[tuple[Path, datetime]] = []
    for rel in _CREATION_INPUTS:
        try:
            mtime = (workspace_folder / rel).stat().st_mtime
        except OSError:
            continue
        changed = datetime.fromtimestamp(mtime, tz=UTC)
        if changed > created:
            stale.append((rel, changed))
    return stale


def _report_stale(
    workspace_folder: Path,
    created: datetime,
    stale: list[tuple[Path, datetime]],
    err: TextIO,
) -> None:
    bar = "!" * 72
    rows = [("container created", created.astimezone(UTC))]
    rows += [(f"{rel} changed", changed) for rel, changed in stale]
    width = max(len(label) for label, _ in rows) + 2
    lines = [bar, "STALE DEVCONTAINER — refusing to reuse it."]
    lines += [
        f"  {label + ':':<{width}}{ts.isoformat(timespec='seconds')}"
        for label, ts in rows
    ]
    lines += [
        "Container config applies only at creation, so the existing container",
        "would silently ignore these changes. Recreate it:",
        "  /ralph-run rebuild=true   (CLI: --devcontainer --rebuild)",
        "or by hand:",
        f"  devcontainer up --workspace-folder {workspace_folder}"
        " --remove-existing-container",
        bar,
    ]
    print("\n".join(lines), file=err)


def start_devcontainer(
    workspace_folder: Path,
    *,
    rebuild: bool = False,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run ``devcontainer up --workspace-folder <workspace_folder>`` once.

    A bare ``up`` REUSES any existing container, and ``devcontainer.json``
    mount/config changes take effect only at container CREATION — so a
    reused container silently ignores them (TASK-237). ``rebuild=True``
    appends ``--remove-existing-container`` to force a fresh one.

    Without ``rebuild``, an existing container created before the last change
    to ``.devcontainer/devcontainer.json`` or ``.devcontainer/Dockerfile`` is
    REFUSED with a banner naming both timestamps and the ``rebuild=true``
    remedy (TASK-258). The check is advisory: when docker, the container, or
    its creation time is unavailable, the launch proceeds as before.

    Args:
        workspace_folder: Path passed verbatim to ``--workspace-folder``.
        rebuild: When ``True``, discard any existing container first so
            ``devcontainer.json`` mount changes apply. Off by default —
            a rebuild is expensive, so normal runs keep reusing.
        stdout: Stream for status messages. Defaults to ``sys.stdout``.
        stderr: Stream for error messages. Defaults to ``sys.stderr``.

    Returns:
        ``0`` on success. ``1`` when the ``devcontainer`` CLI is not on
        PATH. ``STALE_CONTAINER_EXIT`` when the existing container predates
        its config. The CLI's own exit code on ``up`` failure.
    """
    out = stdout or sys.stdout
    err = stderr or sys.stderr

    if shutil.which("devcontainer") is None:
        print(
            "Error: 'devcontainer' CLI not found. Install with: "
            "npm install -g @devcontainers/cli",
            file=err,
        )
        return 1

    if not rebuild:
        created = container_created_at(workspace_folder)
        stale = stale_inputs(workspace_folder, created) if created else []
        if created and stale:
            _report_stale(workspace_folder, created, stale, err)
            return STALE_CONTAINER_EXIT

    argv = ["devcontainer", "up", "--workspace-folder", str(workspace_folder)]
    if rebuild:
        argv.append("--remove-existing-container")
        print("Rebuilding devcontainer (removing existing container)...", file=out)
    else:
        print("Starting devcontainer...", file=out)
    result = subprocess.run(  # noqa: S603 — argv list, no shell.
        argv,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        out.write(result.stdout)
    if result.returncode != 0:
        if result.stderr:
            err.write(result.stderr)
        return result.returncode
    print("Devcontainer is ready.", file=out)
    return 0
