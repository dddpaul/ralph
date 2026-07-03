"""Python port of ``wait-heartbeat.sh`` — exit codes & stdout parity.

Polls ``backlog/.ralph-heartbeat`` once per second for up to ten seconds.
Returns:

* ``0`` — a heartbeat younger than 15 seconds was observed. This module is
  read-only; the caller (ralph-run Step 4) removes the launch log.
* ``1`` — no fresh heartbeat after ten polls; the last 20 lines of
  ``backlog/.ralph-launch.log`` and ``backlog/.ralph-run.log`` are emitted.
* ``2`` — invocation directory has no ``backlog/`` child.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


def _tail_or(path: Path, fallback: str) -> None:
    """Emit ``tail -20 path`` (stderr suppressed), or ``fallback`` on failure."""
    try:
        result = subprocess.run(
            ["tail", "-20", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        print(fallback)
        return
    if result.returncode != 0:
        print(fallback)
        return
    sys.stdout.flush()
    sys.stdout.buffer.write(result.stdout)
    sys.stdout.buffer.flush()


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Args are ignored (parity with bash helper)."""
    _ = argv
    if not Path("backlog").is_dir():
        print("ERROR: must be invoked from project root (no backlog/ here)")
        return 2

    hb = Path("backlog/.ralph-heartbeat")
    for i in range(1, 11):
        time.sleep(1)
        if not hb.is_file():
            continue
        try:
            hb_mtime = int(hb.stat().st_mtime)
        except OSError:
            continue
        now = int(time.time())
        age = now - hb_mtime
        if age < 15:
            print(f"OK heartbeat age={age}s after {i}s")
            return 0

    print("FAIL no fresh heartbeat after 10s")
    print("--- launch log (last 20 lines) ---")
    _tail_or(Path("backlog/.ralph-launch.log"), "(launch log not created)")
    print("--- run log (last 20 lines) ---")
    _tail_or(Path("backlog/.ralph-run.log"), "(run log not created)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
