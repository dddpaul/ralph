"""task-reviewer report contract: evidence per AC, findings rubric, SCORE line (TASK-260).

The reviewer's verdict is the only machine check before merge, so the agent
file must demand proof per AC and derive the verdict and score from classified
findings instead of an overall impression. These checks pin that wording.
"""

from __future__ import annotations

import re

from devcontainer_config import REPO_ROOT

AGENT = REPO_ROOT / "plugins/ralph/agents/task-reviewer.md"
EXAMPLE = re.compile(r"(\d+) blocking(?: and (\d+) minor)? → (APPROVED|CHANGES REQUESTED), SCORE: (\d+)")


def agent_text() -> str:
    """The agent file with whitespace collapsed, so wrapping cannot break a match."""
    return " ".join(AGENT.read_text("utf-8").split())


def section(name: str) -> str:
    """The body of one ``## <name>`` section of the agent file."""
    text = AGENT.read_text("utf-8")
    start = text.index(f"## {name}\n")
    end = text.find("\n## ", start + 1)
    return " ".join(text[start : end if end != -1 else None].split())


def rubric(blocking: int, minor: int) -> tuple[str, int]:
    """Reference implementation of the rubric the agent file states."""
    if blocking == 0:
        return "APPROVED", max(7, 10 - minor)
    return "CHANGES REQUESTED", max(1, 5 - (blocking - 1))


def test_every_met_ac_needs_one_of_three_evidence_kinds() -> None:
    body = section("Evidence per AC")
    assert "Every AC you count as met MUST carry evidence of one of three kinds" in body
    assert "a command you ran plus the relevant output lines" in body
    assert "a `file:line` quote" in body
    assert "the path of a rendered image or crop" in body
    assert "An AC without evidence is reported as NOT met" in body


def test_reviewer_runs_checks_and_author_claims_are_not_evidence() -> None:
    body = section("Evidence per AC")
    assert "Run the checks yourself where you can" in body
    assert "Quoting the task's own notes or the author's summary is not evidence" in body


def test_unverifiable_ac_counts_only_with_explicit_deferral() -> None:
    body = section("Evidence per AC")
    assert "is reported as **not verifiable here** with the reason" in body
    assert "counts as met only if the task notes defer it explicitly with a reason" in body


def test_checklist_and_instructions_point_at_the_evidence_rule() -> None:
    text = agent_text()
    assert "an AC without evidence is NOT met" in section("Checklist")
    assert "last line `SCORE: N`" in section("Instructions")
    assert text.count("## Evidence per AC") == 1


def test_findings_are_blocking_or_minor_and_rules_named_by_id() -> None:
    body = section("Findings Classification")
    assert "Classify every finding as **blocking** or **minor**" in body
    assert "a violation of a rule from a loaded rules file" in body
    assert "**Minor:** style remarks not backed by a rule" in body
    assert "Name every violated rule from a loaded rules file by its rule ID" in body


def test_rubric_is_stated_as_fixed_formulas() -> None:
    body = section("Verdict and Score Rubric")
    assert "never from overall impression" in body
    assert "**APPROVED** if and only if there are zero blocking findings" in body
    assert "SCORE = 10 minus the number of minor findings, floor 7" in body
    assert "**CHANGES REQUESTED** on any blocking finding" in body
    assert "SCORE = 5 minus (blocking findings - 1), floor 1" in body


def test_rubric_examples_agree_with_the_formulas() -> None:
    examples = EXAMPLE.findall(section("Verdict and Score Rubric"))
    assert len(examples) >= 4
    for blocking, minor, verdict, score in examples:
        assert rubric(int(blocking), int(minor or 0)) == (verdict, int(score))


def test_report_ends_with_a_score_line_refine_can_parse() -> None:
    body = section("Report Format")
    assert "the report's last line is `SCORE: N`, with nothing after it" in body
    assert "`^SCORE:\\s*(\\d+)`" in body
