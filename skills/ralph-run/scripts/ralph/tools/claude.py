"""Concrete ``Tool`` for the claude-code CLI.

Mirrors the bash invocation in ``ralph.sh:804``::

    timeout "$TIMEOUT_SEC" <devcontainer-prefix?> \\
        claude --model "$MODEL" --effort "$EFFORT" \\
        --dangerously-skip-permissions --print <<< "$PROMPT" \\
        2>&1 | tee "$OUTFILE"

with the timeout wrapper rolled into ``Popen.wait()`` and the
``_kill_children`` tree-cleanup folded into an ``SIGTERM`` → 5s grace →
``SIGKILL`` reap of the child's process group on timeout.

The child is launched with ``start_new_session=True`` so the orchestrator's
top-level signal handler (US-005) can target its whole process group via
``os.killpg`` — bash relied on ``pgrep -P $$`` to find the direct children
and walked their pgids; the Python port front-loads the isolation at spawn
time, which is the recipe historical-context entry "Subprocess management /
process cleanup" (TASK-23, TASK-37) calls out as the cleanly portable shape.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ralph.tools import OnSpawn, Tool, ToolResult
from ralph.tools._subprocess import (
    READER_JOIN_SEC,
    TERMINATE_GRACE_SEC,
    TIMEOUT_EXIT_CODE,
    execute,
    terminate_tree,
)

__all__ = [
    "READER_JOIN_SEC",
    "TERMINATE_GRACE_SEC",
    "TIMEOUT_EXIT_CODE",
    "ClaudeTool",
    "_execute",
    "_terminate_tree",
]

_TEE_PREFIX = "ralph-claude-"


class ClaudeTool(Tool):
    """One iteration of the ``claude-code`` CLI.

    Construction binds the invariant flags (model, effort, optional
    devcontainer prefix); :meth:`run` is called per-iteration with the
    iteration-specific prompt body and the per-iteration timeout in seconds.

    The devcontainer prefix is assembled as an argv list (never a joined
    string) so workspace paths containing spaces survive — TASK-37's
    invariant from the bash port.

    Args:
        model: Value for ``claude --model`` (e.g. ``"claude-opus-4-7"``).
        effort: Value for ``claude --effort`` (e.g. ``"max"``).
        devcontainer: When True, prepend ``devcontainer exec
            --workspace-folder <path>`` to the argv list.
        workspace_folder: Required when ``devcontainer=True``; ignored when
            ``devcontainer=False``. Passed verbatim — no shell quoting.
    """

    def __init__(
        self,
        *,
        model: str,
        effort: str,
        devcontainer: bool = False,
        workspace_folder: Path | None = None,
    ) -> None:
        if devcontainer and workspace_folder is None:
            raise ValueError(
                "workspace_folder is required when devcontainer=True"
            )
        self._model = model
        self._effort = effort
        self._devcontainer = devcontainer
        self._workspace_folder = workspace_folder

    def build_argv(self) -> list[str]:
        """Assemble the argv list for this iteration's subprocess.

        Returns:
            The fully-assembled argv as a list. When ``devcontainer=True``
            the list begins with ``["devcontainer", "exec",
            "--workspace-folder", <path>, ...]`` — never a single joined
            string.
        """
        argv: list[str] = []
        if self._devcontainer and self._workspace_folder is not None:
            argv.extend(
                [
                    "devcontainer",
                    "exec",
                    "--workspace-folder",
                    str(self._workspace_folder),
                ]
            )
        argv.extend(
            [
                "claude",
                "--model",
                self._model,
                "--effort",
                self._effort,
                "--dangerously-skip-permissions",
                "--print",
            ]
        )
        return argv

    def run(
        self,
        prompt: str,
        timeout_sec: int,
        *,
        on_spawn: OnSpawn | None = None,
    ) -> ToolResult:
        return _execute(self.build_argv(), prompt, timeout_sec, on_spawn=on_spawn)


def _execute(
    argv: list[str],
    prompt: str,
    timeout_sec: int,
    *,
    on_spawn: OnSpawn | None = None,
) -> ToolResult:
    """Compatibility wrapper around ``_subprocess.execute`` for claude.

    Preserves the original ``_execute(argv, prompt, timeout_sec)`` signature
    so existing unit tests keep working; new callers (opencode) use
    :func:`ralph.tools._subprocess.execute` directly.
    """
    return execute(
        argv,
        prompt,
        timeout_sec,
        tee_prefix=_TEE_PREFIX,
        on_spawn=on_spawn,
    )


def _terminate_tree(proc: subprocess.Popen[bytes]) -> None:
    """Re-export of ``_subprocess.terminate_tree`` for backward-compatible tests."""
    terminate_tree(proc)
