"""Python port of ``preflight.sh`` — byte-identical output & exit codes.

Runs the five (six, when ``--block-end-buffer-min`` is non-zero) fail-fast
checks the bash helper performs, in the same order. Single-line stdout on
success ``OK RALPH_PATH=<path>`` or ``ERROR: <reason>`` on first failure;
``--verbose`` adds one ``check <name>: ...`` line per check.

A last, report-only check runs ralph-init's ``managed-file-drift.sh`` against
the project and prints one ``WARNING:`` line per managed file that is behind
the installed plugin on stderr. It never changes the exit code: a project that
missed an upgrade still runs, the operator is just told to upgrade it.

With ``devcontainer=true`` one more report-only check reads the user
``settings.json`` and prints one ``WARNING:`` line per hook command whose
executable lives outside the user Claude config dir: the container shares only
``~/.claude``, so such a hook fails there with "not found".

A last report-only check lists, in one ``WARNING:`` line, the entries of the
plugin's ``user-settings.json`` fragment the user ``settings.json`` misses. It
reads both files and changes neither.

One more report-only check reads the project's migration to plugin hooks
(``migrate-plugin-hooks.sh``): it prints "not migrated", "partially migrated",
"shims outdated in this clone" (a git hook, pre-push included, is an earlier
shim version) or "shims missing in this clone" when one applies, and in a
project whose marker sets ``pluginHooks`` it says that plugin guards are best
effort. In a clone with ``ralph.sharedBacklog`` true it also says that the
guard refusing task creation in autonomous runs is best effort. It compares the
hooks with the shim of the install the plugin registry names for the clone,
the one the git hooks run, not with its own copy.

Invariants the AC pins down explicitly:

* Runs against the invoker's PWD — this module never calls ``os.chdir``.
* Resolves tools on the invoker's PATH: ``preflight.sh`` passes it as
  ``RALPH_CALLER_PATH``, undoing the interpreter bin directory ``uv run``
  puts first.
* Honors ``TMPDIR`` for the ``bash -n`` stderr capture; falls back to
  ``/tmp`` only when ``TMPDIR`` is unset (matching bash's ``${TMPDIR:-/tmp}``).
* Anchors the backlog "not found" line on the canonical
  ``^Task <id> not found\\.$`` pattern instead of a loose substring scan.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ralph import push as _push
from ralph import usage_check as _usage_check
from ralph import user_settings as _user_settings

_TASKS_PATTERN = re.compile(r"^[0-9]+(,[0-9]+)*$")
_NON_NEG_INT = re.compile(r"^[0-9]+$")
_TASK_NOT_FOUND = re.compile(r"^Task [0-9]+ not found\.$", re.MULTILINE)
_STATE_RE = re.compile(r'"state":"([^"]*)"')
_PID_RE = re.compile(r'"pid":([0-9]+)')
# preflight.py → ralph/ → scripts/ → ralph-run/ → skills/ → the plugin root.
_PLUGIN_ROOT = Path(__file__).resolve().parents[4]
_DRIFT_SCRIPT = _PLUGIN_ROOT / "skills/ralph-init/scripts/managed-file-drift.sh"
_HOME_PREFIXES = ("$HOME/", "${HOME}/", "~/")
_MIGRATE_REL = "skills/ralph-init/scripts/migrate-plugin-hooks.sh"
_SHIM_REL = "skills/ralph-init/templates/shims/git-hook"
_SHIPPED_REL = "skills/ralph-init/scripts/shipped-git-hooks.sha256"
_MIGRATE_SCRIPT = _PLUGIN_ROOT / _MIGRATE_REL
_SHIM = _PLUGIN_ROOT / _SHIM_REL
_SHIPPED = _PLUGIN_ROOT / _SHIPPED_REL
_RESOLVER = _PLUGIN_ROOT / "skills/ralph-init/templates/shims/resolve-plugin.sh"
_LENGTH_GUARD = "filename-length-guard"
_MANAGED_GUARDS = (
    "commit-msg-guard",
    "commit-prefix-guard",
    "master-branch-guard",
    "naming-guard",
    "notes-guard",
    "task-validator",
)
_SHIMMED_HOOKS = ("pre-commit", "commit-msg", "post-commit")
_AUTONOMOUS_CREATE_NOTE = (
    "autonomous task creation is refused — this clone enforces the shared-backlog protocol, so the run records "
    "follow-ups in its task notes; the guard is best effort, not an absolute boundary (a command it does not "
    "recognise is not refused)"
)


@dataclass(frozen=True)
class _Args:
    ralph_path: str
    devcontainer: str
    verbose: bool
    tasks_raw: str
    block_end_buffer_min: str
    no_push: bool = False


def _print_usage() -> None:
    print(
        "Usage: preflight.sh <ralph_path> <devcontainer:true|false> "
        "[--verbose] [--tasks <ids>] [--block-end-buffer-min <N>] [--no-push]"
    )


def _parse_args(argv: list[str]) -> _Args | None:
    verbose = False
    no_push = False
    tasks_raw = ""
    block_end_buffer_min = "0"
    positional: list[str] = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--verbose":
            verbose = True
            i += 1
        elif arg == "--no-push":
            no_push = True
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
        no_push=no_push,
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


def _check_managed_drift(verbose: bool) -> None:
    """Warn on stderr about managed files behind the plugin; never fail."""
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(_PLUGIN_ROOT)}
    try:
        proc = subprocess.run(
            ["bash", str(_DRIFT_SCRIPT), "check", "."],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except OSError as exc:
        proc = subprocess.CompletedProcess[str]([], 2, "", str(exc))
    if proc.returncode == 0:
        _verbose(verbose, "check managed_files: ok")
        return
    if proc.returncode == 1:
        drifted = proc.stdout.splitlines()
        _verbose(verbose, f"check managed_files: WARN ({len(drifted)} behind)")
        for line in drifted:
            print(
                f"WARNING: ralph-init managed file behind the installed plugin — "
                f"{line} (run the ralph-init upgrade)",
                file=sys.stderr,
            )
        return
    reasons = [
        line
        for line in proc.stderr.splitlines()
        if line.strip() and "warning: setlocale" not in line
    ]
    reason = reasons[-1] if reasons else f"exit {proc.returncode}"
    _verbose(verbose, f"check managed_files: WARN (check exited {proc.returncode})")
    print(f"WARNING: could not check ralph-init managed files — {reason}", file=sys.stderr)


def _hook_executable_path(command: str, home: str) -> str | None:
    """Return the path a hook command runs, or ``None`` for a bare name.

    Only the first word counts: absolute paths and ``$HOME/`` / ``${HOME}/`` /
    ``~/`` paths (quoted or not, ``$HOME`` expanded to ``home``) are paths.
    A bare name such as ``jq`` or the ``[`` of a DEVCONTAINER guard is not.
    """
    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    if not words:
        return None
    first = words[0]
    for prefix in _HOME_PREFIXES:
        if first.startswith(prefix):
            return os.path.join(home, first[len(prefix):])
    return first if first.startswith("/") else None


def _hook_commands(data: object) -> list[tuple[str, str]]:
    """Flatten parsed settings into ``(event, command)``; skip malformed entries."""
    hooks = cast(dict[str, object], data).get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return []
    pairs: list[tuple[str, str]] = []
    for event, groups in cast(dict[str, object], hooks).items():
        for group in cast(list[object], groups) if isinstance(groups, list) else []:
            entries = cast(dict[str, object], group).get("hooks") if isinstance(group, dict) else None
            for entry in cast(list[object], entries) if isinstance(entries, list) else []:
                command = cast(dict[str, object], entry).get("command") if isinstance(entry, dict) else None
                if isinstance(command, str):
                    pairs.append((event, command))
    return pairs


def _host_only_hooks_from(data: object, home: str, config_dir: str) -> list[tuple[str, str]]:
    """List ``(event, command)`` for every hook in ``data`` run from outside ``config_dir``.

    ``data`` is the parsed user settings. ``$HOME/.claude`` counts as inside
    too: the container binds it as well.
    """
    roots = {os.path.normpath(config_dir), os.path.normpath(os.path.join(home, ".claude"))}
    found: list[tuple[str, str]] = []
    for event, command in _hook_commands(data):
        path = _hook_executable_path(command, home)
        if path is None:
            continue
        path = os.path.normpath(path)
        if not any(path == r or path.startswith(r + os.sep) for r in roots):
            found.append((event, command))
    return found


def _check_user_hooks(devcontainer: str, verbose: bool) -> None:
    """Warn on stderr about user hooks the devcontainer cannot run; never fail."""
    if devcontainer != "true":
        _verbose(verbose, "check user_hooks: ok (skipped, devcontainer=false)")
        return
    home = os.environ.get("HOME", "")
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    try:
        data: object = json.loads((Path(config_dir) / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = None
    found = _host_only_hooks_from(data, home, config_dir)
    if not found:
        _verbose(verbose, "check user_hooks: ok")
        return
    _verbose(verbose, f"check user_hooks: WARN ({len(found)} not reachable)")
    for event, command in found:
        print(
            f"WARNING: user hook not reachable in the devcontainer — {event}: {command} "
            "(guard the hook command with DEVCONTAINER, see ralph-init)",
            file=sys.stderr,
        )


def _check_user_settings(verbose: bool) -> None:
    """Warn on stderr, in one line, about fragment entries user settings miss; never fail."""
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.environ.get("HOME", ""), ".claude")
    settings_path = Path(config_dir) / "settings.json"
    try:
        fragment = _user_settings.load_json_object(_user_settings.FRAGMENT)
        settings = _user_settings.load_json_object(settings_path)
    except (OSError, ValueError) as exc:
        _verbose(verbose, "check user_settings: WARN (unreadable)")
        print(f"WARNING: could not check user settings for ralph entries — {exc}", file=sys.stderr)
        return
    missing = _user_settings.missing_entries(fragment, settings)
    if not missing:
        _verbose(verbose, "check user_settings: ok")
        return
    _verbose(verbose, f"check user_settings: WARN ({len(missing)} missing)")
    print(
        f"WARNING: user settings miss {len(missing)} ralph entries — {'; '.join(missing)} "
        f"(add them to {settings_path} from {_user_settings.FRAGMENT})",
        file=sys.stderr,
    )


def _git_stdout(*args: str) -> str | None:
    """Return git's stripped stdout in the current directory, or ``None`` when it fails."""
    try:
        proc = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except OSError:
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def _legacy_guard_commands(settings: Path, guards: list[str]) -> list[str]:
    """Return the ``settings.json`` hook commands that run a copy of one of ``guards``."""
    try:
        data: object = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    pattern = re.compile(
        r"(^|[^A-Za-z0-9_.-])\.claude/hooks/(" + "|".join(map(re.escape, guards)) + r")\.sh([^A-Za-z0-9_.-]|$)"
    )
    return [command for _event, command in _hook_commands(data) if guards and pattern.search(command)]


def migration_state(root: Path, hooks_dir: Path, switch: bool) -> list[str]:
    """Describe the project's migration to plugin hooks, one message per finding.

    ``root`` is the work tree, ``hooks_dir`` what ``git rev-parse --git-path
    hooks`` returns and ``switch`` the clone's ``ralph.pluginHooks``. A fully
    migrated clone yields only the best-effort note, plus the leftover-copy note
    while ``.claude/hooks/filename-length-guard.sh`` is still tracked. The shim,
    the hash list and the migrate script named in the messages come from the
    install the registry names for ``root`` (``_plugin_files``).
    """
    shim_path, shipped, migrate = _plugin_files(root)
    try:
        marker: object = json.loads((root / ".claude/ralph.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        marker = {}
    marker_dict = cast(dict[str, object], marker) if isinstance(marker, dict) else {}
    local_guards = marker_dict.get("localGuards")
    local_list = cast(list[object], local_guards) if isinstance(local_guards, list) else []
    local = [g for g in local_list if isinstance(g, str)]
    plugin_guards = [g for g in _MANAGED_GUARDS if g not in local]
    legacy = _legacy_guard_commands(root / ".claude/settings.json", plugin_guards)
    if marker_dict.get("pluginHooks") is not True:
        missing = [g for g in _MANAGED_GUARDS if not (root / f".claude/hooks/{g}.sh").is_file()]
        if missing and len(missing) < len(_MANAGED_GUARDS):
            return [
                (
                    "partially migrated — .claude/ralph.json does not set pluginHooks, but guard copies are missing "
                    f"from .claude/hooks: {', '.join(missing)} (run bash {migrate} tracked)"
                )
            ]
        return [
            f"not migrated — the project runs its own guard copies (run bash {migrate} tracked, then clone)"
        ]
    found: list[str] = []
    if legacy:
        found.append(
            f"partially migrated — .claude/ralph.json sets pluginHooks, but .claude/settings.json still runs "
            f"{len(legacy)} legacy guard copies (rerun bash {migrate} tracked)"
        )
    try:
        shim = shim_path.read_bytes()
    except OSError:
        shim = b""
    stale = [n for n in _SHIMMED_HOOKS if not _same_bytes(hooks_dir / n, shim)]
    past = _shipped_shims(shipped)
    outdated = [n for n in stale if _sha256(hooks_dir / n) in past]
    if not _same_bytes(hooks_dir / "pre-push", shim) and _sha256(hooks_dir / "pre-push") in past:
        outdated.append("pre-push")
    stale = [n for n in stale if n not in outdated]
    if outdated:
        found.append(
            f"shims outdated in this clone — an earlier plugin shim in {', '.join(outdated)} "
            f"(run bash {migrate} clone)"
        )
    if stale or not switch:
        detail = [f"{', '.join(stale)} not the plugin shim"] if stale else []
        detail += [] if switch else ["git config ralph.pluginHooks is not true"]
        found.append(f"shims missing in this clone — {'; '.join(detail)} (run bash {migrate} clone)")
    if _same_bytes(hooks_dir / "pre-commit", shim) and (root / f".claude/hooks/{_LENGTH_GUARD}.sh").exists():
        found.append(
            f"leftover legacy copy — .claude/hooks/{_LENGTH_GUARD}.sh is removable: this clone's pre-commit is the "
            f"plugin shim (once every clone has run clone, run bash {migrate} tracked --retire-legacy)"
        )
    found.append(
        "plugin guards are best effort — a plugin guard hook that cannot start does not block the command; "
        "the git hooks still block when ralph.pluginHooks is true"
    )
    return found


def _plugin_files(root: Path) -> tuple[Path, Path, Path]:
    """Return the shim, the shipped hash list and the migrate script to compare the clone at ``root`` with.

    They come from the install the plugin registry names for the clone, resolved the way the git hooks resolve
    it, so a session that has not reloaded after ``/plugin update`` still compares with the new plugin. When
    resolution fails, or that install lacks the shim or the list, they come from this module's own plugin root.
    """
    installed = _resolved_plugin_root(root)
    if installed is not None and (installed / _SHIM_REL).is_file() and (installed / _SHIPPED_REL).is_file():
        return installed / _SHIM_REL, installed / _SHIPPED_REL, installed / _MIGRATE_REL
    return _SHIM, _SHIPPED, _MIGRATE_SCRIPT


def _resolved_plugin_root(root: Path) -> Path | None:
    """Return the root of the install ``resolve-plugin.sh`` resolves for ``root``, or ``None`` when it fails."""
    script = '. "$1" && ralph_resolve_plugin "$2" "$3"'
    try:
        proc = subprocess.run(
            ["bash", "-c", script, "bash", str(_RESOLVER), str(root), _SHIM_REL],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    path = proc.stdout.strip()
    if proc.returncode != 0 or not path:
        return None
    # <install>/skills/ralph-init/templates/shims/git-hook → <install>
    return Path(path).parents[4]


def _shipped_shims(shipped: Path) -> set[str]:
    """Return the sha256 digests of every shim version the hash list ``shipped`` names."""
    try:
        lines = shipped.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    return {line[len("shim ") :] for line in lines if line.startswith("shim ")}


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _same_bytes(path: Path, data: bytes) -> bool:
    try:
        return path.read_bytes() == data
    except OSError:
        return False


def _check_no_push(no_push: bool, tasks_raw: str, verbose: bool) -> int:
    """Refuse an opted-out run in a clone that enforces the shared-backlog protocol unless it names one task."""
    enforced = _git_stdout("config", "--bool", "ralph.sharedBacklog") == "true"
    enabled = not no_push and not _push.env_opt_out()
    refusal = _push.no_push_refusal(
        enforced=enforced, enabled=enabled, task_whitelist=[t for t in tasks_raw.split(",") if t]
    )
    if refusal is not None:
        print(f"ERROR: {refusal.removeprefix('Error: ')}")
        return 1
    _verbose(verbose, "check no_push: ok")
    return 0


def _check_plugin_hooks(verbose: bool) -> None:
    """Warn on stderr about the project's migration to plugin hooks; never fail."""
    top = _git_stdout("rev-parse", "--show-toplevel")
    hooks = _git_stdout("rev-parse", "--git-path", "hooks")
    if top is None or hooks is None:
        _verbose(verbose, "check plugin_hooks: ok (skipped, not a git work tree)")
        return
    switch = _git_stdout("config", "--bool", "ralph.pluginHooks") == "true"
    found = migration_state(Path(top), Path(hooks).resolve(), switch)
    migrated = all(m.startswith(("plugin guards are best effort", "leftover legacy copy")) for m in found)
    _verbose(verbose, f"check plugin_hooks: {'ok' if migrated else 'WARN'}")
    for message in found:
        print(f"WARNING: plugin hooks: {message}", file=sys.stderr)
    if _git_stdout("config", "--bool", "ralph.sharedBacklog") == "true":
        print(f"WARNING: plugin hooks: {_AUTONOMOUS_CREATE_NOTE}", file=sys.stderr)


def _restore_caller_path() -> None:
    """Put back the PATH ``preflight.sh`` saw before ``uv run`` prepended its interpreter's bin directory."""
    caller_path = os.environ.pop("RALPH_CALLER_PATH", None)
    if caller_path is not None:
        os.environ["PATH"] = caller_path


def main(argv: list[str] | None = None) -> int:
    _restore_caller_path()
    real_argv = sys.argv[1:] if argv is None else argv
    args = _parse_args(real_argv)
    if args is None:
        _print_usage()
        return 1
    if args.devcontainer not in ("true", "false"):
        _print_usage()
        return 1

    # Check 1: To Do tasks (or whitelist when --tasks is supplied).
    rc = (
        _check_tasks_whitelist(args.tasks_raw, args.verbose)
        if args.tasks_raw
        else _check_todo_tasks(args.verbose)
    )
    if rc != 0:
        return rc

    # Check 1b: --no-push in a shared-backlog clone needs one task (TASK-312).
    rc = _check_no_push(args.no_push, args.tasks_raw, args.verbose)
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

    # Check 7: managed files behind the plugin — report only, never aborts.
    _check_managed_drift(args.verbose)

    # Check 8: user hooks unreachable in the devcontainer — report only.
    _check_user_hooks(args.devcontainer, args.verbose)

    # Check 9: user settings miss fragment entries — report only.
    _check_user_settings(args.verbose)

    # Check 10: migration to plugin hooks — report only.
    _check_plugin_hooks(args.verbose)

    print(f"OK RALPH_PATH={args.ralph_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
