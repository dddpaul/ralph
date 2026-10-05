"""task-reviewer built-in review-conduct rules R-CORE-1..6 (TASK-262).

These rules ship inside the plugin-bundled agent, so they reach every project
on a plugin update; a downstream project has no rules file to fall back on.
The checks pin each rule's statement, keep project-only rules out of the agent
and keep the moved rules out of this repository's project rules file, where
the reviewer would otherwise load them twice.
"""

from __future__ import annotations

import re

import pytest
from devcontainer_config import REPO_ROOT

AGENT = REPO_ROOT / "plugins/ralph/agents/task-reviewer.md"
PROJECT_RULES = REPO_ROOT / ".claude/task-reviewer-rules.md"
PLUGINS = REPO_ROOT / "plugins"

CORE_RULES = {
    "R-CORE-1": (
        "Review the diff, not the working tree; git is the truth",
        "The source of truth for review is `git diff master..HEAD`.",
    ),
    "R-CORE-2": (
        "Every AC must be checked or explicitly deferred",
        "A silent unchecked AC is a blocking finding.",
    ),
    "R-CORE-3": (
        "Rationalization is not exemption",
        "Apply the rules first and read the narrative second.",
    ),
    "R-CORE-4": (
        "Content preservation during moves",
        "A rename diff with unauthorized content drift is rejected.",
    ),
    "R-CORE-5": (
        "Task descriptions must not reference brainstorm files",
        "A task whose description body contains a path matching `design/.*-brainstorm\\.md` is rejected.",
    ),
    "R-CORE-6": (
        "A changed external-tool default needs an invocation AC",
        "**invokes that program with the new value and records the observed result**",
    ),
}

# Project headings (and the retired IDs) whose rules now live in the agent.
MOVED_TITLES = [
    "Review the diff, not the working tree",
    "Git is the truth, not the working tree",
    "Every AC must be checked or explicitly deferred",
    "Rationalization is not exemption",
    "Content preservation during moves",
    "Task descriptions must not reference brainstorm files",
    "A changed external-tool default needs an invocation AC",
]
RETIRED_IDS = ["R1", "R2", "R9", "R13", "R14", "R16", "R17"]
KEPT_IDS = ["R3", "R4", "R5", "R6", "R7", "R8", "R10", "R11", "R12", "R15"]


def flat(text: str) -> str:
    """Collapse whitespace, so wrapping cannot break a match."""
    return " ".join(text.split())


def core_rule(rule_id: str) -> str:
    """The body of one ``### <rule_id>`` subsection of the agent file."""
    text = AGENT.read_text("utf-8")
    start = text.index(f"### {rule_id} — ")
    end = re.search(r"\n#{2,3} ", text[start + 1 :])
    return flat(text[start : start + 1 + end.start() if end else None])


@pytest.mark.parametrize("rule_id", sorted(CORE_RULES))
def test_agent_states_core_rule(rule_id: str) -> None:
    title, statement = CORE_RULES[rule_id]
    body = core_rule(rule_id)
    assert body.startswith(f"### {rule_id} — {title}")
    assert statement in body


def test_core_rules_are_blocking_and_named_by_id() -> None:
    text = flat(AGENT.read_text("utf-8"))
    assert "a violation is a blocking finding named by its `R-CORE-*` ID" in text
    assert (
        "a violation of a built-in rule or of a rule from a loaded rules file" in text
    )


def test_core_rule_r5_scan_names_its_rule() -> None:
    assert (
        'echo "R-CORE-5 violation: $f references a brainstorm file in its description"'
        in core_rule("R-CORE-5")
    )


def test_agent_ships_no_project_only_rule() -> None:
    text = AGENT.read_text("utf-8")
    assert not re.search(r"(?i)template[ -]parity", text)
    assert not re.search(r"(?i)co-authored-by|trailer|attribution", text)


def test_moved_rules_are_gone_from_project_file() -> None:
    headings = [
        line
        for line in PROJECT_RULES.read_text("utf-8").splitlines()
        if line.startswith("## ")
    ]
    for title in MOVED_TITLES:
        assert not any(title in h for h in headings), title
    for rule_id in RETIRED_IDS:
        assert not any(h.startswith(f"## {rule_id} ") for h in headings), rule_id


def test_project_file_keeps_project_and_infrastructure_rules() -> None:
    headings = [
        line
        for line in PROJECT_RULES.read_text("utf-8").splitlines()
        if line.startswith("## ")
    ]
    assert [h.split()[1] for h in headings] == KEPT_IDS
    preamble = flat(PROJECT_RULES.read_text("utf-8").split("\n## ", 1)[0])
    assert "Their numbers are retired, not reused" in preamble
    for rule_id in RETIRED_IDS:
        assert rule_id in preamble


def test_no_shipped_file_cites_a_project_rule_id() -> None:
    offenders = []
    for path in sorted(PLUGINS.rglob("*")):
        if path.is_file() and path.suffix in {".md", ".sh", ".py", ".json"}:
            for n, line in enumerate(path.read_text("utf-8").splitlines(), 1):
                if re.search(r"\bR(6|11|16)\b", line):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{n}")
    assert not offenders, offenders
