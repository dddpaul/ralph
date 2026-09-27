"""The devcontainer's uv version pin (TASK-251).

``Dockerfile.base`` and the ``docs`` / ``python`` install fragments each copied
uv from ``ghcr.io/astral-sh/uv:latest``, so an assembled docs, mixed or python
image carried the instruction twice and all three copies floated. A floating tag
is resolved once, at the first build, and the layer is reused forever — the same
failure the ``CLAUDE_CODE_VERSION`` pin exists to prevent, except a stale uv
fails quietly: it runs the orchestrator, installs the interpreter and executes
every PEP 723 script, so age shows up as a confusing resolver error.

These tests pin the invariant on both copies (live ``.devcontainer/`` and the
ralph-init template): the version is a concrete ``X.Y.Z`` build arg, uv arrives
through one pinned stage, the fragments add no second copy, the image is
labelled so the version is readable without starting a container, and the build
refuses a floating tag. The guard runs for real under ``sh``, and a mutated
Dockerfile shows the checks are not vacuous.

``COPY --from`` cannot expand a build arg, which is why uv comes from a named
stage rather than a direct image reference.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import BOTH_IDS, LIVE_DIR, TEMPLATE_DIR, each_copy, load_jsonc

DOCKERFILES = (LIVE_DIR / "Dockerfile", TEMPLATE_DIR / "Dockerfile.base")
each_dockerfile = pytest.mark.parametrize("path", DOCKERFILES, ids=BOTH_IDS)
FRAGMENT_DIR = TEMPLATE_DIR / "lang"
FLAVOURS = ("docs", "go", "node", "python")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
LABEL = "dev.ralph.uv-version"
STAGE = "uv-bin"


def instructions(text: str) -> list[str]:
    """Dockerfile instructions with ``\\`` continuations joined, comments dropped."""
    joined = re.sub(r"\\\n", " ", text)
    return [
        line.strip()
        for line in joined.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def pin_problems(text: str) -> list[str]:
    """Every way a Dockerfile lets the uv version float or go stale."""
    ins = instructions(text)
    problems: list[str] = []
    args = [i for i in ins if re.match(r"ARG UV_VERSION\b", i)]
    # Two declarations: one global (for the stage FROM) and one in the
    # devcontainer stage (for the LABEL and the guard). Neither may default.
    if args != ["ARG UV_VERSION", "ARG UV_VERSION"]:
        problems.append(f"ARG must be declared twice with no default: {args}")
    # The global one must precede every FROM: `COPY --from` cannot expand a build
    # arg, so the uv stage interpolates it, and Dockerfile.lang.go contributes a
    # FROM of its own — which is why it cannot move later in the file.
    if ins and ins[0] != "ARG UV_VERSION":
        problems.append(f"the global ARG must come before the first FROM: {ins[:1]}")
    froms = [i for i in ins if i.startswith("FROM ") and STAGE in i]
    if froms != [f"FROM ghcr.io/astral-sh/uv:${{UV_VERSION}} AS {STAGE}"]:
        problems.append(f"uv stage must pin the ARG: {froms}")
    copies = [i for i in ins if "/usr/local/bin/uv" in i]
    if copies != [f"COPY --from={STAGE} /uv /usr/local/bin/uv"]:
        problems.append(f"uv must be copied exactly once, from the stage: {copies}")
    direct = [i for i in ins if "COPY" in i and "astral-sh/uv" in i]
    if direct:
        problems.append(f"COPY --from cannot expand an ARG, so it must not be used "
                        f"for uv: {direct}")
    if f'LABEL {LABEL}="${{UV_VERSION}}"' not in ins:
        problems.append(f"missing LABEL {LABEL}")
    guards = [i for i in ins if "uv --version" in i]
    if len(guards) != 1:
        problems.append(f"exactly one step must check uv against the pin: {guards}")
    elif "uv python install 3.14" not in guards[0]:
        problems.append("the checked step must also install the interpreter")
    return problems


def guard_script(text: str) -> str:
    """The semver guard of the uv ``RUN``, i.e. everything before the uv call."""
    (run,) = [i for i in instructions(text) if "uv --version" in i]
    return run.removeprefix("RUN ").split("&& uv --version", 1)[0]


@each_copy
def test_build_arg_is_a_concrete_version(path: Path) -> None:
    version = load_jsonc(path)["build"]["args"]["UV_VERSION"]
    assert SEMVER.match(version), f"{path}: UV_VERSION={version!r}"


@each_dockerfile
def test_dockerfile_cannot_float(path: Path) -> None:
    assert pin_problems(path.read_text("utf-8")) == []


@pytest.mark.parametrize("flavour", FLAVOURS)
def test_install_fragments_add_no_second_copy(flavour: str) -> None:
    """The base copies uv for every language, so a fragment must not repeat it."""
    text = (FRAGMENT_DIR / f"Dockerfile.install.{flavour}").read_text("utf-8")
    assert "astral-sh/uv" not in text
    assert "/usr/local/bin/uv" not in text


@each_dockerfile
@pytest.mark.parametrize(
    ("value", "ok"),
    [
        ("0.12.19", True),
        ("latest", False),
        ("next", False),
        ("", False),
        ("0.12.19-rc.1", False),
        ("0x.12.19", False),
        ("0.12.19.1", False),
    ],
)
def test_guard_rejects_floating_tags(path: Path, value: str, ok: bool) -> None:
    result = subprocess.run(
        ["sh", "-c", guard_script(path.read_text("utf-8"))],
        env={"UV_VERSION": value, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) is ok, result.stderr


def test_old_floating_dockerfile_is_flagged() -> None:
    """The pre-251 shape must fail every check that replaced it."""
    text = (TEMPLATE_DIR / "Dockerfile.base").read_text("utf-8")
    old = text.replace(
        f"COPY --from={STAGE} /uv /usr/local/bin/uv",
        "COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv",
    )
    old = re.sub(r"LABEL dev\.ralph\.uv-version=.*\n", "", old)
    assert old != text
    problems = pin_problems(old)
    assert any("exactly once" in p for p in problems)
    assert any("must not be used" in p for p in problems)
    assert any("LABEL" in p for p in problems)
