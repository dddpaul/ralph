"""Pydantic ``StatusFile`` model — byte-identical with the bash writer.

The model declares fields in the exact order the bash writer emits them so
that ``model_dump_json()`` produces a byte-identical line. External readers
(notably ``ralph-status-watch``) depend on this contract.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ErrorEntry(BaseModel):
    """Structured error entry. Field order: ``iteration``, ``at``, ``message``."""

    model_config = ConfigDict(extra="forbid")

    iteration: int
    at: str
    message: str


class StatusFile(BaseModel):
    """Ralph autonomous-loop status file.

    Field declaration order MUST match the bash writer's key order — readers
    rely on byte-identity with the historical schema.
    """

    model_config = ConfigDict(extra="forbid")

    pid: int
    started_at: str
    state: str
    iteration: int
    max_iterations: int
    tool: str
    tasks_done: list[str] = Field(default_factory=list[str])
    tasks_remaining: int
    current_task: str | None = None
    last_iteration_duration: int | None = None
    elapsed: int
    errors: list[ErrorEntry] = Field(default_factory=list[ErrorEntry])
    completed_at: str | None = None
    exit_code: int | None = None
    iteration_started_at: str | None = None
    timeout_sec: int
    paused_reason: str | None = None
    paused_buffer_min: int | None = None
    paused_remaining_min: int | None = None
    paused_block_end_time: str | None = None
    paused_at: str | None = None

    def to_json_bytes(self) -> bytes:
        """Serialize to compact one-line JSON + trailing newline (bash parity)."""
        return self.model_dump_json().encode("utf-8") + b"\n"

    def write_atomic(self, path: Path) -> None:
        """Atomically replace ``path`` with the serialized status.

        Writes to a sibling temp file (same directory, so ``os.replace`` is a
        cheap rename) and only then renames it into place. External readers
        therefore observe either the previous file or the new one — never a
        partial write.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(self.to_json_bytes())
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, path)
