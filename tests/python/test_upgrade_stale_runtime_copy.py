"""Upgrade's in-place patch for the stale language-runtime copy (TASK-250).

TASK-242 fixed the python and docs fragments, but ``ralph upgrade`` never
re-assembles ``.devcontainer/Dockerfile``, so every project bootstrapped before
it still copies ``python:3.14``'s ``/usr/local`` over the bookworm base. The
upgrade flow now runs ``scripts/stale-runtime-copy.sh`` on that file: ``check``
reports the stale copy, ``patch`` prints the file with the stage and the copy
paragraph swapped for the current fragments, and SKILL.md applies it only on an
explicit yes.

The detector must apply the same suite-matching rule the fragment guard in
test_devcontainer_python_runtime.py pins, not a match on ``python:3.14``, so the
two are run side by side on the guard's own reproduction matrix.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import test_devcontainer_python_runtime as runtime_guard
from devcontainer_config import REPO_ROOT, TEMPLATE_DIR

SKILL_DIR = REPO_ROOT / "plugins/ralph/skills/ralph-init"
SCRIPT = SKILL_DIR / "scripts/stale-runtime-copy.sh"
SKILL_MD = SKILL_DIR / "SKILL.md"
LANG_DIR = TEMPLATE_DIR / "lang"
BASE = (TEMPLATE_DIR / "Dockerfile.base").read_text("utf-8")

# The pre-TASK-242 fragments, verbatim: what existing projects still carry.
OLD_STAGE = {
    "python": (
        "###\n### Stage 1: Language Runtime\n###\nFROM python:3.14 AS python-runtime"
    ),
    "docs": (
        "###\n### Stage 1: Language Runtime (Python for pptx generation)\n###\n"
        "FROM python:3.14 AS python-runtime\n"
    ),
}
OLD_COPY = (
    "# ---- Language Runtime (from multi-stage) ----\n"
    "COPY --from=python-runtime /usr/local /usr/local\n"
    "COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv"
)
OLD_INSTALL = {
    "python": OLD_COPY,
    "docs": OLD_COPY
    + "\n\n"
    + (LANG_DIR / "Dockerfile.install.docs").read_text("utf-8").split("\n\n", 1)[1],
}
FLAVOURS = ("node", "python", "go", "docs")


def assemble(stage: str, install: str, base: str = BASE) -> str:
    """Assemble a Dockerfile the way ralph-init Step 3.6 does."""
    return base.replace("{{LANGUAGE_STAGE}}", stage).replace(
        "{{LANGUAGE_INSTALL}}", install
    )


def current(flavour: str) -> str:
    """What a fresh ralph-init assembles today for ``flavour``."""
    return assemble(
        (LANG_DIR / f"Dockerfile.lang.{flavour}").read_text("utf-8"),
        (LANG_DIR / f"Dockerfile.install.{flavour}").read_text("utf-8"),
    )


def run(
    mode: str, dockerfile: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), mode, str(dockerfile)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "Dockerfile"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("flavour", ("python", "docs"))
def test_pre_242_dockerfile_is_flagged(tmp_path: Path, flavour: str) -> None:
    path = write(tmp_path, assemble(OLD_STAGE[flavour], OLD_INSTALL[flavour]))
    out = run("check", path)
    assert out.returncode == 1, out.stderr
    (line,) = out.stdout.splitlines()
    assert "COPY --from=python-runtime /usr/local" in line
    assert "'python:3.14' suite 'unpinned'" in line


def test_matching_suite_repin_is_left_alone(tmp_path: Path) -> None:
    stage = OLD_STAGE["python"].replace("python:3.14", "python:3.14-bookworm")
    base = BASE.replace("FROM node:20\n", "FROM node:20-bookworm\n")
    assert "node:20-bookworm" in base
    path = write(tmp_path, assemble(stage, OLD_INSTALL["python"], base))
    assert run("check", path).returncode == 0
    patched = run("patch", path)
    assert patched.returncode == 1
    assert patched.stdout == ""


@pytest.mark.parametrize("flavour", FLAVOURS)
def test_fresh_assembly_is_clean(tmp_path: Path, flavour: str) -> None:
    out = run("check", write(tmp_path, current(flavour)))
    assert (out.returncode, out.stdout) == (0, "")


@pytest.mark.parametrize("flavour", ("python", "docs"))
def test_patch_yields_the_current_fragments(tmp_path: Path, flavour: str) -> None:
    old = assemble(OLD_STAGE[flavour], OLD_INSTALL[flavour])
    path = write(tmp_path, old)
    out = run("patch", path)
    assert out.returncode == 0, out.stderr
    assert out.stdout == current(flavour)
    # Confirm-only: the script prints, SKILL.md writes on a yes.
    assert path.read_text("utf-8") == old


def test_patch_keeps_the_rest_of_a_customised_file(tmp_path: Path) -> None:
    extra = "\n# project addition\nRUN echo kept\n"
    old = assemble(OLD_STAGE["python"], OLD_INSTALL["python"]) + extra
    out = run("patch", write(tmp_path, old))
    assert out.returncode == 0, out.stderr
    assert out.stdout == current("python") + extra


def test_patch_refuses_a_stage_it_has_no_fragment_for(tmp_path: Path) -> None:
    stage = "FROM ruby:3.3 AS ruby-runtime\n"
    install = "COPY --from=ruby-runtime /usr/local /usr/local\n"
    path = write(tmp_path, assemble(stage, install))
    assert run("check", path).returncode == 1
    out = run("patch", path)
    assert out.returncode == 3
    assert out.stdout == ""
    assert "patch by hand" in out.stderr


def test_patch_never_swallows_a_neighbouring_instruction(tmp_path: Path) -> None:
    # No blank lines around the copy: a paragraph walk bounded only by blank
    # lines would drop the base FROM and the RUN along with the COPY.
    path = write(
        tmp_path,
        "FROM python:3.14 AS python-runtime\n"
        "FROM node:20\n"
        "COPY --from=python-runtime /usr/local /usr/local\n"
        "RUN echo important\n",
    )
    assert run("check", path).returncode == 1
    out = run("patch", path)
    assert (out.returncode, out.stdout) == (3, "")
    assert "shares a paragraph" in out.stderr


def test_patch_prints_nothing_when_a_fragment_is_unreadable(tmp_path: Path) -> None:
    path = write(tmp_path, assemble(OLD_STAGE["docs"], OLD_INSTALL["docs"]))
    env = {**os.environ, "RALPH_LANG_DIR": str(tmp_path / "missing")}
    out = run("patch", path, env)
    assert (out.returncode, out.stdout) == (2, "")


# The fragment guard's reproduction matrix: (base, stage, install).
MATRIX = (
    ("FROM node:20\n", "FROM python:3.14 AS python-runtime\n", OLD_COPY),
    ("FROM node:20-bookworm\n", "FROM python:3.14 AS python-runtime\n", OLD_COPY),
    (
        "FROM node:20-bookworm\n",
        "FROM python:3.14-bookworm AS python-runtime\n",
        OLD_COPY,
    ),
    (
        "FROM node:20-bookworm\n",
        "FROM python:3.14-trixie AS python-runtime\n",
        OLD_COPY,
    ),
    (
        "FROM node:20\n",
        "FROM golang:1.25 AS golang\n",
        "COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv\n"
        "COPY --from=golang /usr/local/go /usr/local/go\n",
    ),
    ("FROM node:20\n", "", "COPY --from=python:3.14 /usr/local/lib /usr/local/lib\n"),
)


@pytest.mark.parametrize("case", MATRIX, ids=range(len(MATRIX)))
def test_detector_agrees_with_the_fragment_guard(
    tmp_path: Path, case: tuple[str, str, str]
) -> None:
    base, stage, install = case
    guard = runtime_guard._repro(tmp_path, base, stage, install)
    dockerfile = write(tmp_path, f"{stage}\n{base}\n{install}")
    detector = run("check", dockerfile)
    assert detector.returncode in (0, 1), detector.stderr
    assert len(detector.stdout.splitlines()) == len(guard)
    assert (detector.returncode == 1) == bool(guard)


def test_detector_runs_under_mawk(tmp_path: Path) -> None:
    # mawk is the strictest awk on hand (BSD awk is not installed here); the
    # script must not lean on gawk extensions.
    mawk = shutil.which("mawk")
    if mawk is None:
        pytest.skip("mawk not installed")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "awk").symlink_to(mawk)
    env = {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"}
    path = write(tmp_path, assemble(OLD_STAGE["docs"], OLD_INSTALL["docs"]))
    assert run("check", path, env).returncode == 1
    out = run("patch", path, env)
    assert (out.returncode, out.stdout) == (0, current("docs"))


def _upgrade_section() -> str:
    text = SKILL_MD.read_text("utf-8")
    return text[text.index("## Upgrade Mode") :]


def test_skill_md_runs_the_detector_on_upgrade() -> None:
    upgrade = _upgrade_section()
    assert "stale-runtime-copy.sh check .devcontainer/Dockerfile" in upgrade
    assert "stale-runtime-copy.sh patch .devcontainer/Dockerfile" in upgrade
    assert "skipped (assembled; runtime copy patched)" in upgrade
    assert "skipped (assembled; stale runtime copy, user declined)" in upgrade


def test_dockerfile_is_not_a_mirror_pair() -> None:
    parity = (REPO_ROOT / "tests/unit/template-parity.bats").read_text("utf-8")
    rows = re.findall(r"^\w+\|([^|]+)\|", parity, re.MULTILINE)
    assert rows, "registry rows not found"
    assert ".devcontainer/Dockerfile" not in rows
