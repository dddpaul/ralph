"""Every seeded git allow-rule is a named, vetted subcommand prefix (TASK-257).

The template pre-approves the narrow write rules the merge flow needs plus a
handful of read-only queries. ``git tag`` and ``git branch`` look like queries
but are not: ``git tag -d`` deletes a release tag and ``git branch -D`` deletes
an unmerged branch, so both must keep prompting. A blanket ``Bash(git:*)`` is
forbidden by reviewer rule R6.

Caveat: ``git log``, ``git diff`` and ``git show`` accept ``--output=<file>``,
which writes a file. A prefix rule cannot exclude a flag; the sandbox's write
boundary is what bounds it.
"""

from __future__ import annotations

import json
import re

from devcontainer_config import REPO_ROOT

TEMPLATE = (
    REPO_ROOT / "plugins/ralph/skills/ralph-init/templates/claude/settings.local.json"
)
GIT_RULE = re.compile(r"Bash\(git(?P<rest>[ :].*)?\)")
NAMED = re.compile(r" (?P<sub>[a-z][a-z-]*):\*")

WRITES = {"add", "commit", "config", "checkout", "merge", "mv", "rm"}
READS = {"log", "status", "diff", "show", "rev-parse", "ls-files"}


def git_rules() -> list[str]:
    allow = json.loads(TEMPLATE.read_text("utf-8"))["permissions"]["allow"]
    return [rule for rule in allow if GIT_RULE.fullmatch(rule)]


def test_every_git_rule_is_a_named_vetted_subcommand() -> None:
    for rule in git_rules():
        named = NAMED.fullmatch(GIT_RULE.fullmatch(rule)["rest"] or "")
        assert named, f"{rule} is not a named git subcommand prefix"
        assert named["sub"] in WRITES | READS, f"{rule} is not a vetted git subcommand"


def test_read_only_queries_are_allowed() -> None:
    assert {f"Bash(git {sub}:*)" for sub in READS} <= set(git_rules())


def test_destructive_lookalikes_and_blanket_rule_are_absent() -> None:
    rules = set(git_rules())
    for forbidden in (
        "Bash(git:*)",
        "Bash(git *)",
        "Bash(git)",
        "Bash(git tag:*)",
        "Bash(git branch:*)",
    ):
        assert forbidden not in rules
