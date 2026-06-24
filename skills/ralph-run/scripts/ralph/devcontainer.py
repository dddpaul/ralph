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
from pathlib import Path
from typing import TextIO


def start_devcontainer(
    workspace_folder: Path,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run ``devcontainer up --workspace-folder <workspace_folder>`` once.

    Args:
        workspace_folder: Path passed verbatim to ``--workspace-folder``.
        stdout: Stream for status messages. Defaults to ``sys.stdout``.
        stderr: Stream for error messages. Defaults to ``sys.stderr``.

    Returns:
        ``0`` on success. ``1`` when the ``devcontainer`` CLI is not on
        PATH. The CLI's own exit code on ``up`` failure.
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

    print("Starting devcontainer...", file=out)
    result = subprocess.run(  # noqa: S603 — argv list, no shell.
        ["devcontainer", "up", "--workspace-folder", str(workspace_folder)],
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
