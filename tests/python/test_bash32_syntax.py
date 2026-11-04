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

``bash -n`` cannot see run-time-only bash 4 builtins: ``declare -A`` parses fine
and only fails when executed (TASK-294). A static scan therefore rejects
associative-array declarations, ``mapfile`` and ``readarray`` outside comments
on every host. ``|&`` and ``&>>`` are left out: the commit guards' jq lexer
program carries those characters as data.
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
BASH4_BUILTIN = re.compile(
    r"\b(?:declare|local|typeset)\s+(?:-\w+\s+)*-\w*A\b|\b(?:mapfile|readarray)\b"
)
COMMENT = re.compile(r"(?:^|\s)#.*$")


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


def bash4_builtin_lines(text: str) -> list[str]:
    """Return the lines of ``text`` that use a bash 4 builtin outside a ``#`` comment."""
    return [
        line
        for line in text.splitlines()
        if BASH4_BUILTIN.search(COMMENT.sub("", line))
    ]


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
    """The scan reaches the extensionless plugin git hooks, the shim template and the live hooks."""
    found = {p.relative_to(REPO_ROOT).as_posix() for p in tracked_shell_scripts()}
    assert {f"plugins/ralph/git-hooks/{h}" for h in ("commit-msg", "post-commit", "pre-commit")} <= found
    assert "plugins/ralph/skills/ralph-init/templates/shims/git-hook" in found
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


@pytest.mark.parametrize(
    "line",
    [
        "declare -A head_by_nfc",
        "  local -A seen=()",
        "typeset -A map",
        "declare -gA cache",
        "declare -r -A frozen",
        "mapfile -t lines < file",
        'n=${#x[@]}; readarray -t rows <<< "$out"',
    ],
)
def test_bash4_builtin_scan_flags_usage(line: str) -> None:
    """The static scan flags each bash 4 builtin form."""
    assert bash4_builtin_lines(f"#!/usr/bin/env bash\n{line}\n") == [line]


@pytest.mark.parametrize(
    "line",
    [
        "# bash 3.2 has no associative arrays: no declare -A here",
        "x=1  # avoid mapfile / readarray",
        "declare -a list",
        "local -r name=value",
        "echo ${#arr[@]}",
    ],
)
def test_bash4_builtin_scan_ignores_comments_and_bash32_forms(line: str) -> None:
    """Comments, indexed arrays and other bash 3.2 declarations pass the scan."""
    assert bash4_builtin_lines(f"{line}\n") == []


def test_tracked_shell_scripts_avoid_bash4_builtins() -> None:
    """No tracked script uses associative arrays, ``mapfile`` or ``readarray`` (TASK-294)."""
    failures = [
        f"{script.relative_to(REPO_ROOT)}: {line.strip()}"
        for script in tracked_shell_scripts()
        for line in bash4_builtin_lines(script.read_text(errors="replace"))
    ]
    assert not failures, "bash 4-only builtins (macOS /bin/bash is 3.2):\n" + "\n".join(
        failures
    )
