"""Usage-cap wrapper — bridges ``usage_check`` to ``StatusFile.paused_*``.

The bash version (``ralph.sh:_check_usage_or_pause``) calls ``usage-check.sh``
and, on exit code 1, populates five ``PAUSED_*`` shell variables that feed
the next ``_update_status`` write. The Python wrapper does the same:

* exit 0 → no pause; status untouched
* exit 1 → fill ``paused_reason``, ``paused_buffer_min``,
  ``paused_remaining_min``, ``paused_block_end_time``, ``paused_at`` on the
  caller's ``StatusFile`` and return ``True``
* exit 2 → unmeasurable; the disabled-flag sentinel is written by
  ``usage_check.main`` (US-002 carve-out — see ``usage_check.py``); the
  wrapper returns ``False`` so the loop continues

The wrapper deliberately mutates the ``StatusFile`` in place: the caller
flips ``state="paused"`` and writes the status file in one atomic step,
matching bash's single-line JSON write.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any, cast

from ralph import usage_check
from ralph.status import StatusFile

_REASON_REMAINING_RE = re.compile(r"block_end_in_(\d+)min_below_")


def _now_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_block_end_time() -> str | None:
    """Best-effort re-read of the active block's ``endTime`` for the status field.

    Bash uses ``ccusage blocks --active --token-limit max --json | jq ...``;
    if either tool is missing, the field stays ``None``. Errors are swallowed —
    a missing ``paused_block_end_time`` is annoying for the user but never a
    reason to crash the orchestrator.
    """
    if shutil.which("ccusage") is None:
        return None
    try:
        proc = subprocess.run(
            ["ccusage", "blocks", "--active", "--token-limit", "max", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None
    if proc.returncode != 0:
        return None
    try:
        payload: Any = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    data = cast(dict[str, Any], payload)
    blocks_any: Any = data.get("blocks")
    if not isinstance(blocks_any, list) or not blocks_any:
        return None
    blocks = cast(list[Any], blocks_any)
    first_any: Any = blocks[0]
    if not isinstance(first_any, dict):
        return None
    first = cast(dict[str, Any], first_any)
    end_time = first.get("endTime")
    return end_time if isinstance(end_time, str) and end_time else None


def check_and_pause(
    status: StatusFile, buffer_min: int, *, now: str | None = None
) -> bool:
    """Run usage-check; mutate ``status`` and return ``True`` if pause tripped.

    Args:
        status: The current ``StatusFile`` to update in place when paused.
            Callers typically flip ``status.state = "paused"`` after this
            returns ``True``; that final write is the caller's job because
            the bash flow batches the state flip with ``completed_at`` and
            ``exit_code`` in a single status write.
        buffer_min: ``--block-end-buffer-min`` (non-negative). ``0`` short-
            circuits to ``False`` without invoking ``usage_check``.
        now: Optional override for ``paused_at`` (testing hook). Production
            callers omit it and let the wrapper stamp the current UTC time.

    Returns:
        ``True`` when usage-check exited 1 (block-end imminent); ``False``
        when usage-check exited 0 (room remains) or 2 (unmeasurable).
    """
    if buffer_min <= 0:
        return False

    rc, out, _err = usage_check.evaluate(str(buffer_min))
    if rc != 1:
        return False

    reason = out.strip() or f"block_end_in_unknown_below_{buffer_min}min_buffer"
    match = _REASON_REMAINING_RE.search(reason)
    remaining = int(match.group(1)) if match else 0

    status.paused_reason = reason
    status.paused_buffer_min = buffer_min
    status.paused_remaining_min = remaining
    status.paused_block_end_time = _read_block_end_time()
    status.paused_at = now if now is not None else _now_iso()
    return True


def clear_pause(status: StatusFile) -> None:
    """Reset all five ``paused_*`` fields to ``None`` on ``status`` in place."""
    status.paused_reason = None
    status.paused_buffer_min = None
    status.paused_remaining_min = None
    status.paused_block_end_time = None
    status.paused_at = None
