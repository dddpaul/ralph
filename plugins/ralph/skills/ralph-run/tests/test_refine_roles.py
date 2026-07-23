"""Prompt-composition tests for ``ralph.refine.roles`` (US-004 AC #1-7).

Covers the three author paths (iter-1 task / iter-1 draft / iter->1 revision),
the two reviewer paths (with and without a prior summary), the appended
output-protocol instructions, block ordering, and the guards that reject
incoherent context combinations.
"""

from __future__ import annotations

import pytest

from ralph.refine import roles
from ralph.refine.roles import ARTIFACT_INSTRUCTION, REVIEW_INSTRUCTION

# --------------------------------------------------------------------------- #
# Sample content shared across the composition paths.
# --------------------------------------------------------------------------- #
AUTHOR_ROLE = "You are a meticulous author."
REVIEWER_ROLE = "You are a demanding reviewer."
TASK = "Write a haiku about autumn."
DRAFT = "An old draft with rough edges."
PREV_ARTIFACT = "# v1\n\nSome prior content."
PREV_REVIEW = "SCORE: 6\n<summary>Tighten the middle.</summary>"
ARTIFACT = "# Draft\n\nBody paragraph."
PREV_SUMMARY = "Previously I asked to tighten the middle."

# Section headers that must be absent from the wrong path.
_SEED_HEADERS = ("## Task", "## Current draft")
_REVISION_HEADERS = ("## Previous artifact", "## Reviewer feedback")


# --------------------------------------------------------------------------- #
# AC #1 — author iteration 1 with --prompt: role + task
# --------------------------------------------------------------------------- #
def test_author_iter1_prompt_includes_role_and_task() -> None:
    """AC #1 — the task prompt is composed under a Task header with the role."""
    prompt = roles.author_prompt(AUTHOR_ROLE, task=TASK)
    assert AUTHOR_ROLE in prompt
    assert "## Task" in prompt
    assert TASK in prompt


def test_author_iter1_prompt_excludes_draft_and_revision_context() -> None:
    """AC #1 — a task-seeded prompt carries no draft or revision sections."""
    prompt = roles.author_prompt(AUTHOR_ROLE, task=TASK)
    assert "## Current draft" not in prompt
    for header in _REVISION_HEADERS:
        assert header not in prompt


# --------------------------------------------------------------------------- #
# AC #2 — author iteration 1 with --draft: role + draft
# --------------------------------------------------------------------------- #
def test_author_iter1_prompt_includes_role_and_draft() -> None:
    """AC #2 — the draft is composed under a Current draft header."""
    prompt = roles.author_prompt(AUTHOR_ROLE, draft=DRAFT)
    assert AUTHOR_ROLE in prompt
    assert "## Current draft" in prompt
    assert DRAFT in prompt


def test_author_iter1_draft_excludes_task_and_revision_context() -> None:
    """AC #2 — a draft-seeded prompt carries no task or revision sections."""
    prompt = roles.author_prompt(AUTHOR_ROLE, draft=DRAFT)
    assert "## Task" not in prompt
    for header in _REVISION_HEADERS:
        assert header not in prompt


# --------------------------------------------------------------------------- #
# AC #3 — author iteration > 1: role + previous artifact + previous full review
# --------------------------------------------------------------------------- #
def test_author_iterN_includes_prev_artifact_and_full_review() -> None:
    """AC #3 — the revision prompt carries the prior artifact and full review."""
    prompt = roles.author_prompt(
        AUTHOR_ROLE,
        previous_artifact=PREV_ARTIFACT,
        previous_review=PREV_REVIEW,
    )
    assert AUTHOR_ROLE in prompt
    assert "## Previous artifact" in prompt
    assert PREV_ARTIFACT in prompt
    assert "## Reviewer feedback" in prompt
    assert PREV_REVIEW in prompt


def test_author_iterN_excludes_seed_context() -> None:
    """AC #3 — a revision prompt carries no first-iteration seed section."""
    prompt = roles.author_prompt(
        AUTHOR_ROLE,
        previous_artifact=PREV_ARTIFACT,
        previous_review=PREV_REVIEW,
    )
    for header in _SEED_HEADERS:
        assert header not in prompt


# --------------------------------------------------------------------------- #
# AC #4 — author prompt appends the <artifact> instruction
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "kwargs",
    [
        {"task": TASK},
        {"draft": DRAFT},
        {"previous_artifact": PREV_ARTIFACT, "previous_review": PREV_REVIEW},
    ],
)
def test_author_prompt_appends_artifact_instruction(
    kwargs: dict[str, str],
) -> None:
    """AC #4 — every author path ends with the <artifact> wrap instruction."""
    prompt = roles.author_prompt(AUTHOR_ROLE, **kwargs)
    assert prompt.endswith(ARTIFACT_INSTRUCTION)
    assert "<artifact>...</artifact>" in prompt


def test_artifact_instruction_names_the_tag() -> None:
    """AC #4 — the exported instruction pins the extractor's tag protocol."""
    assert "<artifact>...</artifact>" in ARTIFACT_INSTRUCTION


# --------------------------------------------------------------------------- #
# AC #5 — reviewer prompt: role + artifact (+ previous summary when iter > 1)
# --------------------------------------------------------------------------- #
def test_reviewer_iter1_has_role_and_artifact_without_summary() -> None:
    """AC #5 — iteration 1 reviews the artifact with no prior-summary section."""
    prompt = roles.reviewer_prompt(REVIEWER_ROLE, ARTIFACT)
    assert REVIEWER_ROLE in prompt
    assert "## Artifact to review" in prompt
    assert ARTIFACT in prompt
    assert "## Your previous review summary" not in prompt
    assert PREV_SUMMARY not in prompt


def test_reviewer_iterN_includes_previous_summary() -> None:
    """AC #5 — past iteration 1 the reviewer's prior summary is included."""
    prompt = roles.reviewer_prompt(
        REVIEWER_ROLE, ARTIFACT, previous_summary=PREV_SUMMARY
    )
    assert REVIEWER_ROLE in prompt
    assert ARTIFACT in prompt
    assert "## Your previous review summary" in prompt
    assert PREV_SUMMARY in prompt


# --------------------------------------------------------------------------- #
# AC #6 — reviewer prompt appends the SCORE + <summary> instruction
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("previous_summary", [None, PREV_SUMMARY])
def test_reviewer_prompt_appends_review_instruction(
    previous_summary: str | None,
) -> None:
    """AC #6 — every reviewer path ends with the SCORE + <summary> instruction."""
    prompt = roles.reviewer_prompt(
        REVIEWER_ROLE, ARTIFACT, previous_summary=previous_summary
    )
    assert prompt.endswith(REVIEW_INSTRUCTION)
    assert "SCORE: N" in prompt
    assert "<summary>...</summary>" in prompt


def test_review_instruction_names_score_and_summary() -> None:
    """AC #6 — the exported instruction pins both reviewer output tokens."""
    assert "SCORE: N" in REVIEW_INSTRUCTION
    assert "<summary>...</summary>" in REVIEW_INSTRUCTION


# --------------------------------------------------------------------------- #
# Ordering — role leads, output-protocol instruction is the final block.
# --------------------------------------------------------------------------- #
def test_author_role_leads_and_instruction_is_last() -> None:
    """The role opens the prompt and the instruction closes it."""
    prompt = roles.author_prompt(AUTHOR_ROLE, task=TASK)
    assert prompt.startswith(AUTHOR_ROLE)
    assert prompt.endswith(ARTIFACT_INSTRUCTION)
    assert prompt.index(TASK) < prompt.index(ARTIFACT_INSTRUCTION)


def test_reviewer_role_leads_and_instruction_is_last() -> None:
    """The role opens the reviewer prompt and the instruction closes it."""
    prompt = roles.reviewer_prompt(
        REVIEWER_ROLE, ARTIFACT, previous_summary=PREV_SUMMARY
    )
    assert prompt.startswith(REVIEWER_ROLE)
    assert prompt.endswith(REVIEW_INSTRUCTION)
    assert prompt.index(PREV_SUMMARY) < prompt.index(REVIEW_INSTRUCTION)


def test_surrounding_whitespace_is_trimmed_for_clean_joins() -> None:
    """Role/body whitespace is stripped so blocks join on a single blank line."""
    prompt = roles.author_prompt("  padded role  ", task="  padded task  ")
    assert prompt.startswith("padded role")
    assert "## Task\npadded task" in prompt
    assert "\n\n\n" not in prompt


# --------------------------------------------------------------------------- #
# AC #7 — guards: reject incoherent author context combinations.
# --------------------------------------------------------------------------- #
def test_author_rejects_task_and_draft_together() -> None:
    """A first iteration takes exactly one seed, not both."""
    with pytest.raises(ValueError, match="exactly one of task or draft"):
        roles.author_prompt(AUTHOR_ROLE, task=TASK, draft=DRAFT)


def test_author_rejects_no_context() -> None:
    """With no seed and no continuation there is nothing to compose."""
    with pytest.raises(ValueError, match="exactly one of task or draft"):
        roles.author_prompt(AUTHOR_ROLE)


def test_author_rejects_seed_mixed_with_continuation() -> None:
    """A seed and a continuation cannot both be supplied."""
    with pytest.raises(ValueError, match="not both"):
        roles.author_prompt(
            AUTHOR_ROLE, task=TASK, previous_artifact=PREV_ARTIFACT
        )


def test_author_rejects_partial_continuation_missing_review() -> None:
    """A continuation needs the review as well as the artifact."""
    with pytest.raises(ValueError, match="both previous_artifact"):
        roles.author_prompt(AUTHOR_ROLE, previous_artifact=PREV_ARTIFACT)


def test_author_rejects_partial_continuation_missing_artifact() -> None:
    """A continuation needs the artifact as well as the review."""
    with pytest.raises(ValueError, match="both previous_artifact"):
        roles.author_prompt(AUTHOR_ROLE, previous_review=PREV_REVIEW)
