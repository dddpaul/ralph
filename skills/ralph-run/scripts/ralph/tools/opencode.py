"""Concrete ``Tool`` for the opencode CLI.

Mirrors the bash invocation in ``ralph.sh:801``::

    timeout "$TIMEOUT_SEC" <devcontainer-prefix?> \\
        opencode run "$PROMPT" 2>&1 | tee "$OUTFILE"

The only branch-level delta from :mod:`ralph.tools.claude` is how the prompt
reaches the child: opencode takes it as a positional argv element (``opencode
run <prompt>``) rather than reading it from stdin. Everything else — tee
file, ``SIGTERM`` → grace → ``SIGKILL`` reap, devcontainer prefix as a
proper argv list (TASK-37) — is delegated to the shared executor in
:mod:`ralph.tools._subprocess`.
"""

from __future__ import annotations

from pathlib import Path

from ralph.tools import Tool, ToolResult
from ralph.tools._subprocess import execute

__all__ = ["OpencodeTool"]

_TEE_PREFIX = "ralph-opencode-"


class OpencodeTool(Tool):
    """One iteration of the ``opencode`` CLI.

    Args:
        devcontainer: When True, prepend ``devcontainer exec
            --workspace-folder <path>`` to the argv list.
        workspace_folder: Required when ``devcontainer=True``; ignored when
            ``devcontainer=False``. Passed verbatim — no shell quoting.
    """

    def __init__(
        self,
        *,
        devcontainer: bool = False,
        workspace_folder: Path | None = None,
    ) -> None:
        if devcontainer and workspace_folder is None:
            raise ValueError(
                "workspace_folder is required when devcontainer=True"
            )
        self._devcontainer = devcontainer
        self._workspace_folder = workspace_folder

    def build_argv(self, prompt: str) -> list[str]:
        """Assemble the argv list for this iteration's subprocess.

        Unlike :meth:`ClaudeTool.build_argv`, this method takes the prompt
        because opencode wires it in as a positional argv element.

        Returns:
            The fully-assembled argv as a list. When ``devcontainer=True``
            the list begins with ``["devcontainer", "exec",
            "--workspace-folder", <path>, "opencode", "run", <prompt>]`` —
            the prompt is one element, never shell-split.
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
        argv.extend(["opencode", "run", prompt])
        return argv

    def run(self, prompt: str, timeout_sec: int) -> ToolResult:
        return execute(
            self.build_argv(prompt),
            prompt="",
            timeout_sec=timeout_sec,
            tee_prefix=_TEE_PREFIX,
        )
