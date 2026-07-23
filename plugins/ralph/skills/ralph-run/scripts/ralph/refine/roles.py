"""Author & reviewer prompt composition (US-004).

The refine loop makes two LLM calls per iteration — an *author* that produces
the artifact and a *reviewer* that scores it. This module assembles the prompt
for each call from a role file plus the prior-iteration context, and appends the
output-format instruction that pins the tag protocol :mod:`ralph.refine.extract`
keys on.

Like :mod:`ralph.prompts`, these are **pure** string builders: they take
already-loaded content (role text, the seed task/draft, the previous artifact /
review / summary) and return a prompt string. File I/O stays in the loop
(US-005); keeping composition side-effect-free is what makes every path directly
unit-testable (AC #7).

Composition shape (parity with the bash ``refine`` author↔reviewer wiring):

* **Author, iteration 1** — role + the seed: a task prompt (``--prompt``) *or* a
  draft to revise (``--draft``).
* **Author, iteration > 1** — role + the previous artifact + the previous *full*
  review, so the author revises against concrete feedback.
* **Reviewer** — role + the artifact under review, plus the reviewer's own
  previous ``<summary>`` once past iteration 1 (continuity of critique).

The two output-protocol instructions are exported as
:data:`ARTIFACT_INSTRUCTION` / :data:`REVIEW_INSTRUCTION` so the loop's
``--dry-run`` / ``--verbose`` output, the bundled example roles (US-007), and the
e2e fake-claude stub (US-009) all reference the one contract.
"""

from __future__ import annotations

__all__ = [
    "ARTIFACT_INSTRUCTION",
    "REVIEW_INSTRUCTION",
    "author_prompt",
    "reviewer_prompt",
]

ARTIFACT_INSTRUCTION = (
    "Output your complete, final artifact wrapped in <artifact>...</artifact> "
    "tags. Put nothing else inside those tags — only the text between "
    "<artifact> and </artifact> is saved as this iteration's artifact."
)
"""Author output protocol, appended to every author prompt (AC #4).

Names the ``<artifact>...</artifact>`` block :func:`ralph.refine.extract.artifact`
pulls out."""

REVIEW_INSTRUCTION = (
    "End your review with a single line 'SCORE: N', where N is an integer from "
    "1 to 10, and wrap your feedback in <summary>...</summary> tags."
)
"""Reviewer output protocol, appended to every reviewer prompt (AC #6).

Names the line-anchored ``SCORE: N`` and ``<summary>...</summary>`` block that
:func:`ralph.refine.extract.score` / :func:`ralph.refine.extract.summary` read."""


def author_prompt(
    role: str,
    *,
    task: str | None = None,
    draft: str | None = None,
    previous_artifact: str | None = None,
    previous_review: str | None = None,
) -> str:
    """Compose the author prompt for one iteration.

    Exactly one of two context shapes must be supplied:

    * **First iteration** — exactly one of ``task`` (``--prompt``) or ``draft``
      (``--draft``); the artifact is created from scratch or from the draft.
    * **Later iterations** — both ``previous_artifact`` and ``previous_review``;
      the author revises against the full prior review.

    Args:
        role: The author role file's text (the persona and instructions).
        task: The task prompt for a first iteration created from scratch.
        draft: An existing draft to revise, for a first iteration.
        previous_artifact: The artifact produced by the previous iteration.
        previous_review: The previous iteration's full reviewer output.

    Returns:
        The composed prompt: role, then the context section(s), then
        :data:`ARTIFACT_INSTRUCTION` as the final block.

    Raises:
        ValueError: If the first-iteration seed and the continuation context are
            mixed, if neither is given, or if only one half of the continuation
            context is supplied.
    """
    is_continuation = previous_artifact is not None or previous_review is not None

    if is_continuation:
        if task is not None or draft is not None:
            raise ValueError(
                "author_prompt: pass either a first-iteration seed "
                "(task/draft) or a continuation (previous_artifact + "
                "previous_review), not both"
            )
        if previous_artifact is None or previous_review is None:
            raise ValueError(
                "author_prompt: a continuation needs both previous_artifact "
                "and previous_review"
            )
        sections = [
            _section("Previous artifact", previous_artifact),
            _section("Reviewer feedback", previous_review),
        ]
    elif task is not None and draft is None:
        sections = [_section("Task", task)]
    elif draft is not None and task is None:
        sections = [_section("Current draft", draft)]
    else:
        raise ValueError(
            "author_prompt: the first iteration needs exactly one of task or "
            "draft"
        )

    return _compose(role, sections, ARTIFACT_INSTRUCTION)


def reviewer_prompt(
    role: str,
    artifact: str,
    *,
    previous_summary: str | None = None,
) -> str:
    """Compose the reviewer prompt for one iteration.

    Args:
        role: The reviewer role file's text.
        artifact: The current iteration's artifact, to be reviewed.
        previous_summary: The reviewer's own ``<summary>`` from the previous
            iteration; supplied only past iteration 1 (AC #5).

    Returns:
        The composed prompt: role, the artifact section, the optional prior
        summary section, then :data:`REVIEW_INSTRUCTION` as the final block.
    """
    sections = [_section("Artifact to review", artifact)]
    if previous_summary is not None:
        sections.append(_section("Your previous review summary", previous_summary))
    return _compose(role, sections, REVIEW_INSTRUCTION)


def _section(header: str, body: str) -> str:
    """Render a labelled ``## Header`` block with its (stripped) body."""
    return f"## {header}\n{body.strip()}"


def _compose(role: str, sections: list[str], instruction: str) -> str:
    """Join role, context sections, and the trailing instruction.

    Blocks are separated by a blank line; the role leads and the output-protocol
    instruction is always last, so it is the most recent thing the model reads.
    """
    return "\n\n".join([role.strip(), *sections, instruction])
