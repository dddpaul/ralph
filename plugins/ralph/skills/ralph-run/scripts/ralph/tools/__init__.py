"""Tool abstraction — the interface ``claude`` and ``opencode`` implement.

Each iteration of the orchestrator calls ``tool.run(prompt, timeout_sec)``;
the tool is responsible for executing the underlying CLI (e.g. ``claude
--model … --print``), teeing its combined stdout/stderr to a transcript
file, and surfacing the iteration sentinels via ``IterationSignals``.

This module deliberately exposes only the abstract surface. Concrete
implementations land in US-004 (``ralph/tools/claude.py``) and US-005
(``ralph/tools/opencode.py``).
"""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ralph.signals import IterationSignals

__all__ = ["OnSpawn", "Tool", "ToolResult", "IterationSignals"]

OnSpawn = Callable[[subprocess.Popen[bytes]], None]
"""Callback invoked synchronously with the live ``Popen`` immediately after
the tool spawns its subprocess. Used by the orchestrator's signal handler to
forward SIGTERM/SIGINT to the active child's process group (TASK-160)."""


@dataclass(frozen=True)
class ToolResult:
    """The output of a single iteration of the AI tool.

    Attributes:
        stdout_path: Path to the tee'd transcript file. The orchestrator
            keeps it around through cleanup so a post-mortem grep is
            possible; bash kept the same handle via ``_ralph_cleanup_files``.
        exit_code: Exit code from the wrapped CLI. ``124`` is the bash-style
            ``timeout`` signal — concrete tools MUST translate their own
            timeout exit code (e.g. ``subprocess.TimeoutExpired``) to 124
            so the orchestrator's bash-parity branch logic keeps working.
        signals: Parsed sentinels (completion marker, summary-block count,
            first ``ERROR:`` line). See ``ralph.signals.parse_file``.
    """

    stdout_path: Path
    exit_code: int
    signals: IterationSignals


class Tool(ABC):
    """The single iteration's execution surface.

    Implementations construct the actual subprocess invocation (model
    selection, effort flags, devcontainer-exec prefix) from the
    orchestrator's CLI args at construction time; ``run()`` is invoked once
    per iteration with the iteration-specific prompt and the per-iteration
    timeout in seconds.
    """

    @abstractmethod
    def run(
        self,
        prompt: str,
        timeout_sec: int,
        *,
        on_spawn: OnSpawn | None = None,
    ) -> ToolResult:
        """Execute one iteration and return its result.

        Args:
            prompt: The full prompt text (including the
                ``MODE: autonomous (Ralph loop iteration …)`` prefix the
                orchestrator prepends). Tools forward it verbatim — they
                do NOT inject additional instructions.
            timeout_sec: Wall-clock budget for the iteration. Concrete
                tools MUST kill the subprocess (and its process group) on
                expiry and surface ``exit_code=124``.
            on_spawn: Optional callback invoked synchronously with the live
                ``Popen`` immediately after spawn. The orchestrator hands
                it ``installer.set_active_subprocess`` so a SIGTERM/SIGINT
                during ``run()`` can be forwarded to the child's process
                group (TASK-160, bash parity for ``_kill_children``).

        Returns:
            A ``ToolResult`` with the transcript path, exit code, and
            iteration signals parsed from the transcript.
        """
        raise NotImplementedError
