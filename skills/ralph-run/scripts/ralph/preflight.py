"""Python port of ``preflight.sh`` — byte-identical output & exit codes.

Runs the five (six, when ``--block-end-buffer-min`` is non-zero) fail-fast
checks the bash helper performs, in the same order. Single-line stdout on
success ``OK RALPH_PATH=<path>`` or ``ERROR: <reason>`` on first failure;
``--verbose`` adds one ``check <name>: ...`` line per check.

Invariants the AC pins down explicitly:

* Runs against the invoker's PWD — this module never calls ``os.chdir``.
* Honors ``TMPDIR`` for the ``bash -n`` stderr capture; falls back to
  ``/tmp`` only when ``TMPDIR`` is unset (matching bash's ``${TMPDIR:-/tmp}``).
* Anchors the backlog "not found" line on the canonical
  ``^Task <id> not found\\.$`` pattern instead of a loose substring scan.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from ralph import usage_check as _usage_check

_TASKS_PATTERN = re.compile(r"^[0-9]+(,[0-9]+)*$")
_NON_NEG_INT = re.compile(r"^[0-9]+$")
_TASK_NOT_FOUND = re.compile(r"^Task [0-9]+ not found\.$", re.MULTILINE)
_STATE_RE = re.compile(r'"state":"([^"]*)"')
_PID_RE = re.compile(r'"pid":([0-9]+)')


@dataclass(frozen=True)
class _Args:
    ralph_path: str
    devcontainer: str
    verbose: bool
    tasks_raw: str
    block_end_buffer_min: str


def _print_usage() -> None:
    print(
        "Usage: preflight.sh <ralph_path> <devcontainer:true|false> "
        "[--verbose] [--tasks <ids>] [--block-end-buffer-min <N>]"
    )


def _parse_args(argv: list[str]) -> _Args | None:
    verbose = False
    tasks_raw = ""
    block_end_buffer_min = "0"
    positional: list[str] = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--verbose":
            verbose = True
            i += 1
        elif arg == "--tasks":
            if i + 1 >= len(argv):
                return None
            tasks_raw = argv[i + 1]
            i += 2
        elif arg.startswith("--tasks="):
            tasks_raw = arg.split("=", 1)[1]
            i += 1
        elif arg == "--block-end-buffer-min":
            if i + 1 >= len(argv):
                return None
            block_end_buffer_min = argv[i + 1]
            i += 2
        elif arg.startswith("--block-end-buffer-min="):
            block_end_buffer_min = arg.split("=", 1)[1]
            i += 1
        else:
            positional.append(arg)
            i += 1

    if len(positional) != 2:
        return None
    return _Args(
        ralph_path=positional[0],
        devcontainer=positional[1],
        verbose=verbose,
        tasks_raw=tasks_raw,
        block_end_buffer_min=block_end_buffer_min,
    )


def _verbose(enabled: bool, message: str) -> None:
    if enabled:
        print(message)


def _backlog_stdout(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["backlog", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ""
    return result.stdout


def _parse_status_line(backlog_output: str) -> str:
    for line in backlog_output.splitlines():
        if line.startswith("Status:"):
            tail = line[len("Status:"):]
            return re.sub(r"^[^A-Za-z]*", "", tail)
    return ""


def _check_tasks_whitelist(tasks_raw: str, verbose: bool) -> int:
    if not _TASKS_PATTERN.fullmatch(tasks_raw):
        _verbose(verbose, "check tasks_whitelist: FAIL (non-numeric)")
        print(
            "ERROR: --tasks must be comma-separated numeric IDs. "
            f"Got: '{tasks_raw}'"
        )
        return 1
    ids = tasks_raw.split(",")
    for wid in ids:
        out = _backlog_stdout(["task", wid, "--plain"])
        if not out or _TASK_NOT_FOUND.search(out):
            _verbose(
                verbose, f"check tasks_whitelist: FAIL (TASK-{wid} not found)"
            )
            print(f"ERROR: TASK-{wid} not found in backlog")
            return 1
        status = _parse_status_line(out)
        if "To Do" not in status:
            _verbose(
                verbose,
                f"check tasks_whitelist: FAIL (TASK-{wid} status: {status})",
            )
            print(f"ERROR: TASK-{wid} is not To Do (status: {status})")
            return 1
    _verbose(verbose, f"check tasks_whitelist: ok ({len(ids)} tasks)")
    return 0


def _check_todo_tasks(verbose: bool) -> int:
    out = _backlog_stdout(["task", "list", "-s", "To Do", "--plain"])
    if "No tasks found" in out or "TASK-" not in out:
        _verbose(verbose, "check todo_tasks: FAIL (no To Do tasks)")
        print("ERROR: No To Do tasks in backlog")
        return 1
    count = sum(1 for line in out.splitlines() if "TASK-" in line)
    _verbose(verbose, f"check todo_tasks: ok ({count} tasks)")
    return 0


def _check_ralph_running(verbose: bool) -> int:
    status_file = Path("backlog/.ralph-status.json")
    if status_file.is_file():
        try:
            content = status_file.read_text()
        except OSError:
            content = ""
        state_match = _STATE_RE.search(content)
        state = state_match.group(1) if state_match else ""
        if state == "running":
            hb = Path("backlog/.ralph-heartbeat")
            if hb.is_file():
                try:
                    hb_mtime = int(hb.stat().st_mtime)
                except OSError:
                    hb_mtime = 0
                now = int(time.time())
                if now - hb_mtime < 15:
                    pid_match = _PID_RE.search(content)
                    pid = pid_match.group(1) if pid_match else "unknown"
                    _verbose(
                        verbose, f"check ralph_running: FAIL (PID {pid} active)"
                    )
                    print(f"ERROR: Ralph is already running (PID {pid})")
                    return 1
    _verbose(verbose, "check ralph_running: ok (no fresh heartbeat)")
    return 0


def _check_devcontainer(devcontainer: str, verbose: bool) -> int:
    if devcontainer == "true":
        if shutil.which("devcontainer") is None:
            _verbose(verbose, "check devcontainer_cli: FAIL (not found)")
            print("ERROR: devcontainer CLI not found but devcontainer=true")
            return 1
        _verbose(verbose, "check devcontainer_cli: ok")
    else:
        _verbose(
            verbose, "check devcontainer_cli: ok (skipped, devcontainer=false)"
        )
    return 0


def _check_ralph_executable(ralph_path: str, verbose: bool) -> int:
    if not os.access(ralph_path, os.X_OK):
        _verbose(verbose, f"check ralph_executable: FAIL ({ralph_path})")
        print(f"ERROR: ralph.sh is not executable at {ralph_path}")
        return 1
    _verbose(verbose, "check ralph_executable: ok")
    return 0


def _check_ralph_syntax(ralph_path: str, verbose: bool) -> int:
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    fd, syntax_err_path = tempfile.mkstemp(prefix="preflight.", dir=tmpdir)
    os.close(fd)
    try:
        with open(syntax_err_path, "wb") as stderr_sink:
            proc = subprocess.run(
                ["bash", "-n", ralph_path],
                stderr=stderr_sink,
                stdout=subprocess.DEVNULL,
                check=False,
            )
        if proc.returncode != 0:
            msg = ""
            with open(syntax_err_path) as f:
                for line in f:
                    if "warning: setlocale" not in line:
                        msg = line.rstrip("\n")
                        break
            _verbose(verbose, "check ralph_syntax: FAIL")
            print(f"ERROR: ralph.sh has syntax errors: {msg}")
            return 1
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(syntax_err_path)
    _verbose(verbose, "check ralph_syntax: ok")
    return 0


def _run_usage_helper(buffer_min_raw: str) -> tuple[int, str]:
    """Run usage_check; return ``(exit_code, captured_stdout)``.

    If ``RALPH_USAGE_CHECK_SCRIPT`` is set, exec that path as a subprocess
    (matches bash's env-override hook). Otherwise call the in-process Python
    helper. Stderr from the helper is discarded — bash drops it too via
    ``2>/dev/null`` on the capture.
    """
    script = os.environ.get("RALPH_USAGE_CHECK_SCRIPT")
    if script:
        try:
            proc = subprocess.run(
                [script, buffer_min_raw],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return 2, ""
        return proc.returncode, proc.stdout
    rc, out, _err = _usage_check.evaluate(buffer_min_raw)
    return rc, out


def _check_usage(block_end_buffer_min: str, verbose: bool) -> int:
    if not _NON_NEG_INT.fullmatch(block_end_buffer_min):
        _verbose(
            verbose,
            f"check block_end_buffer: FAIL (non-integer: {block_end_buffer_min})",
        )
        print(
            "ERROR: --block-end-buffer-min must be a non-negative integer. "
            f"Got: '{block_end_buffer_min}'"
        )
        return 1
    buffer_min = int(block_end_buffer_min)
    if buffer_min == 0:
        _verbose(verbose, "check usage: ok (skipped, buffer=0)")
        return 0

    flag_path = Path(
        os.environ.get(
            "RALPH_USAGE_DISABLED_FLAG", "backlog/.ralph-usage-check-disabled"
        )
    )

    uc_rc, uc_out = _run_usage_helper(block_end_buffer_min)
    stripped = uc_out.strip()

    if uc_rc == 0:
        _verbose(
            verbose,
            f"check usage: ok (block boundary outside {buffer_min}m buffer)",
        )
        return 0
    if uc_rc == 1:
        _verbose(verbose, f"check usage: FAIL ({stripped})")
        print(f"ERROR: usage cap tripped — {stripped}")
        return 1
    if uc_rc == 2:
        _verbose(
            verbose,
            "check usage: WARN (cannot measure — block-end check disabled this run)",
        )
        print(
            "WARNING: usage-check.sh cannot measure block boundary — "
            "continuing without block-end protection",
            file=sys.stderr,
        )
        try:
            flag_path.parent.mkdir(parents=True, exist_ok=True)
            flag_path.touch()
        except OSError:
            pass
        return 0
    _verbose(
        verbose, f"check usage: WARN (unexpected exit {uc_rc} — continuing)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    real_argv = sys.argv[1:] if argv is None else argv
    args = _parse_args(real_argv)
    if args is None:
        _print_usage()
        return 1
    if args.devcontainer not in ("true", "false"):
        _print_usage()
        return 1

    # Check 1: To Do tasks (or whitelist when --tasks is supplied).
    if args.tasks_raw:
        rc = _check_tasks_whitelist(args.tasks_raw, args.verbose)
    else:
        rc = _check_todo_tasks(args.verbose)
    if rc != 0:
        return rc

    # Check 2: Ralph not already running.
    rc = _check_ralph_running(args.verbose)
    if rc != 0:
        return rc

    # Check 3: devcontainer CLI present when devcontainer=true.
    rc = _check_devcontainer(args.devcontainer, args.verbose)
    if rc != 0:
        return rc

    # Check 4: ralph.sh is executable.
    rc = _check_ralph_executable(args.ralph_path, args.verbose)
    if rc != 0:
        return rc

    # Check 5: ralph.sh parses.
    rc = _check_ralph_syntax(args.ralph_path, args.verbose)
    if rc != 0:
        return rc

    # Check 6: usage cap (only when buffer > 0).
    rc = _check_usage(args.block_end_buffer_min, args.verbose)
    if rc != 0:
        return rc

    print(f"OK RALPH_PATH={args.ralph_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
