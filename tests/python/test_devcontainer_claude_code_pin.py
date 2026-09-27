"""The devcontainer's Claude Code version pin (TASK-248).

The image used to install ``@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}``
with ``CLAUDE_CODE_VERSION=latest``. That ``RUN`` line never changed, so Docker
reused the cached layer forever: ``latest`` was resolved once, at the first
build, and the container's CLI silently fell 24 releases behind npm until a
Ralph run died on ``Claude Code 2.1.259 does not support this model``.

These tests pin the invariant on both copies (live ``.devcontainer/`` and the
ralph-init template): the version is a concrete ``X.Y.Z`` build arg, the
Dockerfile has no floating default to fall back on, the npm layer's cache key
carries the version, and the build refuses a floating tag. The guard is run for
real under ``sh`` rather than matched as text, and a mutated Dockerfile shows
the checks are not vacuous.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import BOTH_IDS, LIVE_DIR, TEMPLATE_DIR, each_copy, load_jsonc

DOCKERFILES = (LIVE_DIR / "Dockerfile", TEMPLATE_DIR / "Dockerfile.base")
each_dockerfile = pytest.mark.parametrize("path", DOCKERFILES, ids=BOTH_IDS)
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
LABEL = "dev.ralph.claude-code-version"


def instructions(text: str) -> list[str]:
    """Dockerfile instructions with ``\\`` continuations joined, comments dropped."""
    joined = re.sub(r"\\\n", " ", text)
    return [
        line.strip()
        for line in joined.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def pin_problems(text: str) -> list[str]:
    """Every way a Dockerfile lets the Claude Code version float or go stale."""
    ins = instructions(text)
    problems: list[str] = []
    args = [i for i in ins if re.match(r"ARG CLAUDE_CODE_VERSION\b", i)]
    if args != ["ARG CLAUDE_CODE_VERSION"]:
        problems.append(f"ARG must be declared once with no default: {args}")
    npm = [i for i in ins if "@anthropic-ai/claude-code@" in i]
    if (
        len(npm) != 1
        or "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" not in npm[0]
    ):
        problems.append(f"npm install must use the ARG (cache key): {npm}")
    elif "claude --version" not in npm[0]:
        problems.append("npm step must check the installed CLI against the pin")
    if f'LABEL {LABEL}="${{CLAUDE_CODE_VERSION}}"' not in ins:
        problems.append(f"missing LABEL {LABEL}")
    return problems


def guard_script(text: str) -> str:
    """The version guard of the npm ``RUN``, i.e. everything before the install."""
    (npm,) = [i for i in instructions(text) if "@anthropic-ai/claude-code@" in i]
    return npm.removeprefix("RUN ").split("&& npm install", 1)[0]


@each_copy
def test_build_arg_is_a_concrete_version(path: Path) -> None:
    version = load_jsonc(path)["build"]["args"]["CLAUDE_CODE_VERSION"]
    assert SEMVER.match(version), f"{path}: CLAUDE_CODE_VERSION={version!r}"


@each_dockerfile
def test_dockerfile_cannot_float(path: Path) -> None:
    assert pin_problems(path.read_text("utf-8")) == []


@each_dockerfile
@pytest.mark.parametrize(
    ("value", "ok"),
    [("2.1.283", True), ("latest", False), ("next", False), ("", False)],
)
def test_guard_rejects_floating_tags(path: Path, value: str, ok: bool) -> None:
    result = subprocess.run(
        ["sh", "-c", guard_script(path.read_text("utf-8"))],
        env={"CLAUDE_CODE_VERSION": value, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) is ok, result.stderr


def test_old_floating_dockerfile_is_flagged() -> None:
    text = (TEMPLATE_DIR / "Dockerfile.base").read_text("utf-8")
    old = re.sub(r"ARG CLAUDE_CODE_VERSION\n", "ARG CLAUDE_CODE_VERSION=latest\n", text)
    old = re.sub(r"LABEL dev\.ralph\.claude-code-version=.*\n", "", old)
    assert old != text
    problems = pin_problems(old)
    assert any("no default" in p for p in problems)
    assert any("LABEL" in p for p in problems)
