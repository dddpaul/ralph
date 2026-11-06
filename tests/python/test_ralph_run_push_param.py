"""ralph-run exposes a ``push`` parameter that passes ``--no-push`` through (TASK-327).

The orchestrator pushes ``master`` to ``origin`` by default; without this
parameter a launch through the skill could neither opt out nor learn that it
would push. The checks read the shipped SKILL.md text.
"""

from __future__ import annotations

from devcontainer_config import REPO_ROOT

SKILL_MD = REPO_ROOT / "plugins/ralph/skills/ralph-run/SKILL.md"


def skill_text() -> str:
    """Return the ralph-run SKILL.md text."""
    return SKILL_MD.read_text("utf-8")


def test_parameter_table_has_push_row_defaulting_true() -> None:
    assert "| push | true | --no-push (when false) |" in skill_text()


def test_push_value_is_validated() -> None:
    assert "BLOCKED: push must be true or false." in skill_text()


def test_step_4_appends_no_push_only_when_false() -> None:
    text = skill_text()
    step_4 = text[text.index("## Step 4: Launch") : text.index("## Step 5: Report")]
    assert "- push=false → `RALPH_CMD+=(--no-push)`" in step_4
    assert "push=true adds nothing" in step_4


def test_push_behaviour_is_documented() -> None:
    text = skill_text()
    for phrase in ("git push origin master", "push.followTags", "/ralph-stop", "failed run", "`pre-push` hook"):
        assert phrase in text, phrase


def test_both_launch_lines_report_push() -> None:
    step_5 = skill_text().split("## Step 5: Report", 1)[1]
    assert step_5.count("Ralph launched (PID") == 2
    assert step_5.count("push=<true|false>).") == 2
