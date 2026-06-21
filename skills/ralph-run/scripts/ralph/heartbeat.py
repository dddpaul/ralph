"""Heartbeat thread — touches ``backlog/.ralph-heartbeat`` once per interval.

Bash equivalent (``ralph.sh:597-599``):

    ( while kill -0 "$_ralph_pid"; do touch "$HEARTBEAT_FILE"; sleep 5; done ) &

The Python port runs the same loop on a ``threading.Thread`` flagged as a
daemon — so a hard ``sys.exit`` from the orchestrator never strands it —
but the normal path calls ``stop()`` for a clean ``join`` and unlinks the
file (the bash ``_ralph_cleanup`` trap does the same ``rm -f``).
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from types import TracebackType
from typing import Self

DEFAULT_INTERVAL_SEC = 5.0
DEFAULT_JOIN_TIMEOUT_SEC = 10.0


class Heartbeat:
    """Touch ``path`` every ``interval_sec`` until ``stop()``.

    Use as a context manager for guaranteed cleanup, e.g.::

        with Heartbeat(Path("backlog/.ralph-heartbeat")):
            run_iterations()

    Stop is idempotent and safe to call from signal handlers — it sets a
    ``threading.Event``, joins the thread (bounded by ``join_timeout_sec``),
    and unlinks the heartbeat file.
    """

    def __init__(
        self,
        path: Path,
        *,
        interval_sec: float = DEFAULT_INTERVAL_SEC,
        join_timeout_sec: float = DEFAULT_JOIN_TIMEOUT_SEC,
    ) -> None:
        self._path = path
        self._interval = interval_sec
        self._join_timeout = join_timeout_sec
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def path(self) -> Path:
        return self._path

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def start(self) -> None:
        """Spawn the daemon thread and immediately touch the file once.

        The eager initial touch guarantees the file exists before ``start()``
        returns — callers (e.g. the double-run guard) can check freshness on
        the very next line without racing the first tick.
        """
        if self._thread is not None:
            raise RuntimeError("Heartbeat already started")
        self._touch()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, name="ralph-heartbeat", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the loop, join (bounded), and unlink the file."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=self._join_timeout)
        self._thread = None
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.stop()

    def _touch(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            if not self._path.exists():
                self._path.touch()
                return
            now = time.time()
            os.utime(self._path, (now, now))
        except OSError:
            pass

    def _loop(self) -> None:
        while not self._stop_event.wait(self._interval):
            self._touch()
