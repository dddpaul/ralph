"""The language fragments' Python runtime (TASK-242).

The docs and python fragments used to declare ``FROM python:3.14 AS
python-runtime`` and then ``COPY --from=python-runtime /usr/local /usr/local``
into a ``FROM node:20`` base. The official python:3.14 image is built on a newer
Debian than node:20 (bookworm, glibc 2.36), so what landed in the image — first
in PATH, at /usr/local/bin/python3 — was an interpreter linked against a glibc
the image does not have::

    python3 -c '' -> libm.so.6: version `GLIBC_2.38' not found

Nothing in the suite noticed, because Ralph's orchestrator runs through
``uv run`` with its own interpreter. The pre-commit hook did notice: it picked
that python3 as its NFC normalizer and aborted every commit made inside a
devcontainer (see pre-commit-hook.bats for that half).

These tests pin the invariant rather than the current wording: a fragment may
not drop a foreign stage's shared-library-linked binaries into the image's own
/usr/local, /usr/local/bin or /usr/local/lib unless that stage's image and
Dockerfile.base's base image pin the SAME explicit Debian suite. A future re-pin
is therefore allowed; a bare ``FROM python:3.14`` is not. The guard is exercised
against a synthetic reproduction of the old defect so it cannot pass merely by
having nothing to look at.
"""

from __future__ import annotations

import re
from pathlib import Path

from devcontainer_config import TEMPLATE, TEMPLATE_DIR, load_jsonc

LANG_DIR = TEMPLATE_DIR / "lang"
BASE = TEMPLATE_DIR / "Dockerfile.base"
SUITES = ("buster", "bullseye", "bookworm", "trixie", "forky", "sid")


def suite_of(ref: str) -> str | None:
    """Debian codename carried by an image reference, or None when unpinned.

    A codename substring match keeps this working for node:20-bookworm,
    python:3.14-slim-bookworm and bookworm-only refs alike.
    """
    return next((s for s in SUITES if s in ref), None)


def _instructions(path: Path) -> list[list[str]]:
    return [line.split() for line in path.read_text("utf-8").splitlines()]


def base_image(base: Path) -> str:
    """The base image of the devcontainer stage (the last FROM)."""
    froms = [f[1] for f in _instructions(base) if len(f) > 1 and f[0] == "FROM"]
    return froms[-1]


def _is_guarded(src: str) -> bool:
    # /usr/local/go is deliberately not guarded: the Go toolchain is a
    # self-contained directory, not binaries dropped into the paths the base
    # image's own libraries and binaries live in.
    return src in ("/usr/local", "/usr/local/bin", "/usr/local/lib") or bool(
        re.match(r"^/usr/local/(bin|lib)/", src)
    )


def guarded_copies(lang_dir: Path) -> list[tuple[str, str, str]]:
    """``(fragment, from, src)`` for every COPY --from into interpreter paths."""
    copies: list[tuple[str, str, str]] = []
    for fragment in sorted(lang_dir.glob("Dockerfile.install.*")):
        for fields in _instructions(fragment):
            if not fields or fields[0] != "COPY":
                continue
            flags = [f for f in fields[1:] if f.startswith("--")]
            args = [f for f in fields[1:] if not f.startswith("--")]
            origin = next(
                (f.removeprefix("--from=") for f in flags if f.startswith("--from=")),
                None,
            )
            if origin and args and _is_guarded(args[0]):
                copies.append((fragment.name, origin, args[0]))
    return copies


def resolve_stage(lang_dir: Path, name: str) -> str:
    """Resolve a ``--from=`` target to an image reference.

    A stage name declared by a lang fragment resolves to that stage's image;
    anything that already looks like an image reference is returned as is.
    """
    if ":" in name or "/" in name:
        return name
    for fragment in sorted(lang_dir.glob("Dockerfile.lang.*")):
        for f in _instructions(fragment):
            is_stage = len(f) >= 4 and f[0] == "FROM" and f[2].upper() == "AS"
            if is_stage and f[3] == name:
                return f[1]
    return name


def check_copies(lang_dir: Path, base: Path) -> list[str]:
    """One message per guarded copy whose suite does not match the base's."""
    base_img = base_image(base)
    base_suite = suite_of(base_img)
    violations = []
    for fragment, origin, src in guarded_copies(lang_dir):
        img = resolve_stage(lang_dir, origin)
        suite = suite_of(img)
        if base_suite is None or suite != base_suite:
            violations.append(
                f"{fragment}: COPY --from={origin} {src} — stage image '{img}' "
                f"suite '{suite or 'unpinned'}' vs base '{base_img}' "
                f"suite '{base_suite or 'unpinned'}'"
            )
    return violations


def _repro(tmp_path: Path, base: str, lang: str, install: str) -> list[str]:
    (tmp_path / "Dockerfile.base").write_text(base, encoding="utf-8")
    (tmp_path / "Dockerfile.lang.repro").write_text(lang, encoding="utf-8")
    (tmp_path / "Dockerfile.install.repro").write_text(install, encoding="utf-8")
    return check_copies(tmp_path, tmp_path / "Dockerfile.base")


def test_no_language_fragment_declares_a_python_runtime_stage() -> None:
    offenders = [
        f"{fragment.name}: {line}"
        for fragment in sorted(LANG_DIR.glob("Dockerfile.lang.*"))
        for line in fragment.read_text("utf-8").splitlines()
        if re.match(r"^FROM\s+python:", line)
    ]
    assert not offenders, (
        f"a python:* stage is back; the base image already provides uv + "
        f"python3: {offenders}"
    )


def test_no_install_fragment_copies_a_foreign_stage_into_usr_local() -> None:
    assert check_copies(LANG_DIR, BASE) == []


def test_guard_rejects_a_stage_built_on_a_newer_debian(tmp_path: Path) -> None:
    # Verbatim reproduction of the defect, so the guard above cannot pass merely
    # because there is nothing left for it to inspect.
    install = "COPY --from=python-runtime /usr/local /usr/local\n"
    stage = "FROM python:3.14 AS python-runtime\n"
    out = _repro(tmp_path, "FROM node:20\n", stage, install)
    assert len(out) == 1
    assert "python:3.14" in out[0]
    assert "unpinned" in out[0]

    # Pinning only the base is not enough — the copied stage is still unpinned.
    assert _repro(tmp_path, "FROM node:20-bookworm\n", stage, install)

    # Both pinned to the same suite is the one shape that is allowed.
    pinned = "FROM python:3.14-bookworm AS python-runtime\n"
    assert _repro(tmp_path, "FROM node:20-bookworm\n", pinned, install) == []

    # A different suite on either side is not.
    trixie = "FROM python:3.14-trixie AS python-runtime\n"
    out = _repro(tmp_path, "FROM node:20-bookworm\n", trixie, install)
    assert len(out) == 1
    assert "trixie" in out[0]


def test_guard_ignores_uv_binary_copy_and_go_toolchain(tmp_path: Path) -> None:
    # /usr/local/go is a real copy in the shipped go fragment and must stay
    # allowed: it is a self-contained toolchain, not binaries dropped into the
    # paths the base image's own libraries and binaries live in. The uv line is the pre-TASK-251 shape,
    # kept here deliberately: uv is now copied in the base from a pinned stage
    # (no fragment carries it), but the guard must still ignore a single-file
    # /uv source wherever it appears.
    install = (
        "COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv\n"
        "COPY --from=golang /usr/local/go /usr/local/go\n"
    )
    lang = "FROM golang:1.25 AS golang\n"
    assert _repro(tmp_path, "FROM node:20\n", lang, install) == []


def test_docs_and_python_assemblies_still_provide_uv() -> None:
    # TASK-242 asserted this on the fragments, which each carried their own uv
    # copy. TASK-251 pinned uv and left a single copy in the base, so the
    # guarantee moved rather than went away: the base copies uv for every
    # flavour, and the fragments must no longer add a second, unpinned one.
    # The pin itself is covered by tests/python/test_devcontainer_uv_pin.py.
    assert "COPY --from=uv-bin /uv /usr/local/bin/uv" in BASE.read_text("utf-8")
    for name in ("Dockerfile.install.docs", "Dockerfile.install.python"):
        assert "astral-sh/uv" not in (LANG_DIR / name).read_text("utf-8")


def test_base_image_installs_the_python_the_orchestrator_needs() -> None:
    # Dropping the copied interpreter is only safe because the base image is
    # unconditionally uv-managed; if this line goes, the fragments need
    # revisiting.
    assert "uv python install" in BASE.read_text("utf-8")


def test_devcontainer_builds_the_composed_dockerfile() -> None:
    # The guard reads Dockerfile.base and the fragments; that only protects the
    # image if devcontainer.json builds the Dockerfile ralph-init composes from
    # them, rather than pulling some prebuilt image with its own /usr/local.
    config = load_jsonc(TEMPLATE)
    assert "image" not in config
    assert config["build"]["dockerfile"] == "Dockerfile"


def test_guard_fires_on_a_mutated_copy_of_the_real_fragments(tmp_path: Path) -> None:
    # Mutation check against the shipped files rather than a synthetic tree:
    # put the old python:3.14 stage and its /usr/local copy back into a copy of
    # the real python fragments and assert the guard reports exactly that.
    lang = tmp_path / "lang"
    lang.mkdir()
    for fragment in LANG_DIR.iterdir():
        (lang / fragment.name).write_bytes(fragment.read_bytes())
    with (lang / "Dockerfile.lang.python").open("a", encoding="utf-8") as f:
        f.write("\nFROM python:3.14 AS python-runtime\n")
    with (lang / "Dockerfile.install.python").open("a", encoding="utf-8") as f:
        f.write("\nCOPY --from=python-runtime /usr/local /usr/local\n")

    out = check_copies(lang, BASE)
    assert len(out) == 1
    assert out[0].startswith("Dockerfile.install.python:")
    assert "python:3.14" in out[0]
    assert check_copies(LANG_DIR, BASE) == []
