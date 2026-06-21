"""Python port of ``usage-check.sh`` — exit-code + stdout/stderr parity.

Exit codes mirror the bash helper:

* ``0`` — buffer disabled, no active block, or remaining > buffer.
* ``1`` — block is about to end (``remainingMinutes <= buffer``); stdout has
  ``block_end_in_<rem>min_below_<buffer>min_buffer``.
* ``2`` — cannot measure (missing tool, malformed JSON, unparseable
  ``endTime``); stderr carries a one-line warning prefixed with
  ``usage-check.sh:``.

One CLI-only deviation from the bash helper: when ``main()`` returns exit
code ``2`` it also touches ``backlog/.ralph-usage-check-disabled`` (US-002
AC #4 consolidates that responsibility into the helper itself; in bash the
sentinel is written by ``preflight.sh``).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

SENTINEL_FLAG = Path("backlog/.ralph-usage-check-disabled")
_NON_NEG_INT = re.compile(r"^[0-9]+$")


def _parse_iso_to_epoch(value: str) -> int | None:
    """Parse an ISO 8601 timestamp to epoch seconds; ``None`` on failure."""
    normalized = value
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp())


def evaluate(buffer_min_raw: str) -> tuple[int, str, str]:
    """Run the block-end check; return ``(exit_code, stdout, stderr)``.

    The returned strings already include trailing newlines on every line —
    the CLI writes them verbatim to ``sys.stdout`` / ``sys.stderr``.
    """
    if not _NON_NEG_INT.fullmatch(buffer_min_raw or ""):
        display = buffer_min_raw if buffer_min_raw else "<empty>"
        return (
            2,
            "",
            "usage-check.sh: BUFFER_MIN must be a non-negative integer "
            f"(got '{display}')\n",
        )

    buffer_min = int(buffer_min_raw)
    if buffer_min == 0:
        return (0, "", "")

    if shutil.which("ccusage") is None:
        return (
            2,
            "",
            "usage-check.sh: ccusage not found on PATH — block-end check skipped\n",
        )
    if shutil.which("jq") is None:
        return (
            2,
            "",
            "usage-check.sh: jq not found on PATH — block-end check skipped\n",
        )
    if shutil.which("date") is None:
        return (
            2,
            "",
            "usage-check.sh: date not found on PATH — block-end check skipped\n",
        )

    proc = subprocess.run(
        ["ccusage", "blocks", "--active", "--token-limit", "max", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return (
            2,
            "",
            f"usage-check.sh: ccusage exited {proc.returncode} — "
            "block-end check skipped\n",
        )

    try:
        data: Any = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return (
            2,
            "",
            "usage-check.sh: ccusage produced unparseable JSON — "
            "block-end check skipped\n",
        )

    if not isinstance(data, dict):
        return (0, "", "")
    payload = cast(dict[str, Any], data)
    blocks_any: Any = payload.get("blocks")
    if not isinstance(blocks_any, list) or not blocks_any:
        return (0, "", "")
    blocks = cast(list[Any], blocks_any)
    first_any: Any = blocks[0]
    if not isinstance(first_any, dict):
        return (0, "", "")
    first = cast(dict[str, Any], first_any)
    is_active = first.get("isActive", False) is True
    is_gap = first.get("isGap", False) is True
    if not is_active or is_gap:
        return (0, "", "")
    end_time_any: Any = first.get("endTime")
    if not isinstance(end_time_any, str) or not end_time_any:
        return (
            2,
            "",
            "usage-check.sh: ccusage JSON missing blocks[0].endTime — "
            "block-end check skipped\n",
        )
    end_time: str = end_time_any

    end_epoch = _parse_iso_to_epoch(end_time)
    if end_epoch is None:
        return (
            2,
            "",
            f"usage-check.sh: could not parse endTime '{end_time}' — "
            "block-end check skipped\n",
        )

    now_epoch = int(datetime.now(tz=UTC).timestamp())
    remaining_sec = end_epoch - now_epoch
    remaining_min = 0 if remaining_sec <= 0 else remaining_sec // 60

    if remaining_min <= buffer_min:
        return (
            1,
            f"block_end_in_{remaining_min}min_below_{buffer_min}min_buffer\n",
            "",
        )
    return (0, "", "")


def _write_sentinel() -> None:
    try:
        SENTINEL_FLAG.parent.mkdir(parents=True, exist_ok=True)
        SENTINEL_FLAG.touch()
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Returns exit code; writes sentinel on exit 2."""
    real_argv = sys.argv[1:] if argv is None else argv
    buffer_min_raw = real_argv[0] if real_argv else ""
    rc, out, err = evaluate(buffer_min_raw)
    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err)
    if rc == 2:
        _write_sentinel()
    return rc


if __name__ == "__main__":
    sys.exit(main())
