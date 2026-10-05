"""Every git-tracked shell script parses under macOS system bash 3.2 (TASK-267).

macOS ships GNU bash 3.2 as ``/bin/bash``, and ralph-run's preflight and
ralph-init Upgrade resolve ``bash`` through PATH, so on a default Mac every
shipped script runs under 3.2. Its parser rejects constructs bash 4+ accepts —
e.g. a case pattern's unbalanced ``)`` inside ``$( ... )`` ends the substitution
early — and the Linux devcontainer's bash 5 cannot see that. This guard runs
``bash -n`` over every tracked script when the syntax shell reports major
version 3, and skips with the reason otherwise.

``BASH32_SYNTAX_SHELL`` overrides the ``/bin/bash`` default so a locally built
bash 3.2 can drive the guard on Linux.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT

SYNTAX_SHELL = os.environ.get("BASH32_SYNTAX_SHELL", "/bin/bash")
SHEBANG = re.compile(rb"^#!.*\b(ba)?sh\b")


def tracked_shell_scripts() -> list[Path]:
    """Git-tracked ``*.sh`` / ``*.bash`` files plus extensionless sh/bash-shebang files."""
    listing = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
        capture_output=True,
        check=True,
    ).stdout.decode()
    scripts = []
    for name in filter(None, listing.split("\0")):
        path = REPO_ROOT / name
        if path.suffix in (".sh", ".bash"):
            scripts.append(path)
        elif not path.suffix and path.is_file():
            with path.open("rb") as fh:
                if SHEBANG.match(fh.readline()):
                    scripts.append(path)
    return scripts


def shell_major_version(shell: str) -> int | None:
    """Return ``BASH_VERSINFO[0]`` of ``shell``, or None if it cannot run."""
    try:
        out = subprocess.run(
            [shell, "-c", "echo ${BASH_VERSINFO[0]}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return int(out) if out.isdigit() else None


def test_scan_covers_hooks_and_hook_templates() -> None:
    """The scan reaches the extensionless git-hook templates and the live hooks."""
    found = {p.relative_to(REPO_ROOT).as_posix() for p in tracked_shell_scripts()}
    git_hooks = "plugins/ralph/skills/ralph-init/templates/git-hooks/"
    assert {f"{git_hooks}{h}" for h in ("commit-msg", "post-commit", "pre-commit")} <= found
    assert ".claude/hooks/task-validator.sh" in found
    assert "plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh" in found


def test_tracked_shell_scripts_parse_under_bash32() -> None:
    """``bash -n`` succeeds for every tracked script under bash 3.2."""
    major = shell_major_version(SYNTAX_SHELL)
    if major != 3:
        pytest.skip(f"{SYNTAX_SHELL} reports bash major version {major}, not 3 (macOS system bash)")
    failures = []
    for script in tracked_shell_scripts():
        result = subprocess.run([SYNTAX_SHELL, "-n", str(script)], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            failures.append(f"{script.relative_to(REPO_ROOT)}:\n{result.stderr}")
    assert not failures, f"{SYNTAX_SHELL} -n failed:\n" + "\n".join(failures)
