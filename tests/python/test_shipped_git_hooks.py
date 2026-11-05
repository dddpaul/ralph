"""The list of every git hook body ralph-init has shipped (TASK-323).

``migrate-plugin-hooks.sh clone`` replaces a hook whose sha256 is listed for
its name in ``shipped-git-hooks.sha256``. The test regenerates the list from
this repo's history of the hook bodies, in every place ralph-init has kept
them, plus the bodies in the work tree, and fails when the shipped list drifts.
"""

from __future__ import annotations

import hashlib
import re
import subprocess

import pytest
from devcontainer_config import REPO_ROOT

LIST = REPO_ROOT / "plugins/ralph/skills/ralph-init/scripts/shipped-git-hooks.sha256"
BODIES = REPO_ROOT / "plugins/ralph/git-hooks"
HOOK_NAMES = ("pre-commit", "commit-msg", "post-commit")
PATHSPECS = (
    "skills/ralph-init/templates",
    "plugins/ralph/skills/ralph-init/templates/git-hooks",
    "plugins/ralph/git-hooks",
)
HOOK_PATH = re.compile(
    r"\A(?:skills/ralph-init/templates/(?:git-hooks/)?|plugins/ralph/skills/ralph-init/templates/git-hooks/"
    r"|plugins/ralph/git-hooks/)(pre-commit|commit-msg|post-commit)\Z"
)


def git(*args: str) -> bytes:
    """Run git in the repo and return its stdout."""
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True
    ).stdout


def expected_lines() -> list[str]:
    """``<name> <sha256>`` for every hook body in history and in the work tree, sorted."""
    raw = git(
        "log",
        "--format=",
        "--raw",
        "--no-abbrev",
        "--no-renames",
        "--full-history",
        "HEAD",
        "--",
        *PATHSPECS,
    )
    found: set[tuple[str, str]] = set()
    for line in raw.decode().splitlines():
        meta, _, path = line.partition("\t")
        match = HOOK_PATH.match(path)
        blob = meta.split()[3] if match else ""
        if match and blob.strip("0"):
            found.add(
                (
                    match.group(1),
                    hashlib.sha256(git("cat-file", "blob", blob)).hexdigest(),
                )
            )
    for name in HOOK_NAMES:
        found.add((name, hashlib.sha256((BODIES / name).read_bytes()).hexdigest()))
    return [f"{name} {digest}" for name, digest in sorted(found)]


def shipped_lines() -> list[str]:
    return [
        line
        for line in LIST.read_text().splitlines()
        if line and not line.startswith("#")
    ]


@pytest.mark.skipif(
    not (REPO_ROOT / ".git").exists()
    or git("rev-parse", "--is-shallow-repository").strip() == b"true",
    reason="needs the full git history",
)
def test_shipped_list_matches_git_history() -> None:
    expected = expected_lines()
    assert shipped_lines() == expected, (
        "regenerate shipped-git-hooks.sha256 with:\n" + "\n".join(expected)
    )


def test_shipped_list_names_every_hook_and_holds_sha256_digests() -> None:
    lines = shipped_lines()
    assert {line.split(" ")[0] for line in lines} == set(HOOK_NAMES)
    assert all(
        re.fullmatch(r"(pre-commit|commit-msg|post-commit) [0-9a-f]{64}", line)
        for line in lines
    )


def test_the_v0_14_14_pre_commit_and_v0_16_0_commit_msg_are_listed() -> None:
    lines = shipped_lines()
    for name, fixture in (
        ("pre-commit", "pre-commit.v0.14.14"),
        ("commit-msg", "commit-msg.v0.16.0"),
    ):
        body = (
            REPO_ROOT / "tests/python/fixtures/shipped-git-hooks" / fixture
        ).read_bytes()
        assert f"{name} {hashlib.sha256(body).hexdigest()}" in lines
