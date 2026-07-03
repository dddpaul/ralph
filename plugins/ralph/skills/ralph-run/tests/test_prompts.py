"""Prompt builder tests — bash-parity formatting (US-005 AC #5, #6)."""

from __future__ import annotations

from ralph.prompts import MODE_PREFIX_TEMPLATE, build_prompt


def test_mode_prefix_format_matches_bash() -> None:
    """The exact prefix string is part of CLAUDE.md's autonomous-mode contract."""
    prefix = MODE_PREFIX_TEMPLATE.format(i=3, max_i=10)
    assert prefix == "MODE: autonomous (Ralph loop iteration 3 of 10)"


def test_default_body_is_used_when_no_overrides() -> None:
    prompt = build_prompt(iteration=1, max_iterations=10)
    assert prompt.startswith("MODE: autonomous (Ralph loop iteration 1 of 10)\n\n")
    assert "Pick the next To Do task" in prompt
    assert "## Task Summary block" in prompt


def test_prompt_file_body_replaces_default() -> None:
    """AC #6 — --prompt-file REPLACES inner body; MODE prefix still prepended."""
    prompt = build_prompt(
        iteration=2,
        max_iterations=5,
        prompt_file_body="CUSTOM PROMPT BODY",
    )
    assert prompt.startswith("MODE: autonomous (Ralph loop iteration 2 of 5)\n\n")
    assert prompt.endswith("CUSTOM PROMPT BODY")
    assert "Pick the next To Do task" not in prompt


def test_whitelist_task_id_takes_priority_over_prompt_file_body() -> None:
    """Whitelist wins over prompt-file (bash precedence at ralph.sh:783-788)."""
    prompt = build_prompt(
        iteration=1,
        max_iterations=10,
        whitelist_task_id="62",
        prompt_file_body="SHOULD BE IGNORED",
    )
    assert "Execute TASK-62" in prompt
    assert "SHOULD BE IGNORED" not in prompt


def test_whitelist_strips_TASK_prefix() -> None:
    prompt = build_prompt(
        iteration=1,
        max_iterations=10,
        whitelist_task_id="TASK-154",
    )
    assert "Execute TASK-154" in prompt
    assert "TASK-TASK-" not in prompt


def test_prefix_and_body_separated_by_blank_line() -> None:
    prompt = build_prompt(iteration=1, max_iterations=2)
    first, rest = prompt.split("\n\n", 1)
    assert first == "MODE: autonomous (Ralph loop iteration 1 of 2)"
    assert rest.startswith("Pick the next To Do task")
