"""task-reviewer shared infra rules bundle R-INFRA-1..7 (TASK-268).

The infrastructure rules cover files ralph-init installs in every project, so
they ship as a plugin-resident bundle beside the docs bundle. The checks pin
each rule's statement, keep project-only content out of the bundle and keep
the moved rules out of this repository's project rules file, where the
reviewer would otherwise load them twice.
"""

from __future__ import annotations

import re

import pytest
from devcontainer_config import REPO_ROOT

BUNDLE = REPO_ROOT / "plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md"
PROJECT_RULES = REPO_ROOT / ".claude/task-reviewer-rules.md"

# Rule ID -> (former project ID, title, a statement the rule must carry).
INFRA_RULES = {
    "R-INFRA-1": ("R3", "Agent files require valid YAML frontmatter", "MUST include valid YAML frontmatter"),
    "R-INFRA-2": (
        "R4",
        "Frontmatter changes do not take effect mid-session",
        "MUST be marked deferred to a fresh session in the task notes",
    ),
    "R-INFRA-3": (
        "R5",
        "Shell scripts must work on both GNU and BSD tools and parse under bash 3.2",
        "macOS system bash is GNU bash 3.2 (`/bin/bash`)",
    ),
    "R-INFRA-4": ("R6", "No over-broad shell permission rules", "`Bash(bash:*)`"),
    "R-INFRA-5": (
        "R8",
        "Hook commands reference scripts, not inline bash",
        "MUST point to a `.claude/hooks/<name>.sh` script",
    ),
    "R-INFRA-6": ("R10", "Do not bypass `master-branch-guard.sh`", "MUST reject any diff or commit"),
    "R-INFRA-7": (
        "R15",
        "PostToolUse hooks must emit JSON via hookSpecificOutput",
        '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"<text>"}}',
    ),
}


def flat(text: str) -> str:
    """Collapse whitespace, so wrapping cannot break a match."""
    return " ".join(text.split())


def bundle_rule(rule_id: str) -> str:
    """The body of one ``## <rule_id>:`` section of the bundle."""
    text = BUNDLE.read_text("utf-8")
    start = text.index(f"## {rule_id}: ")
    end = re.search(r"\n## ", text[start + 1 :])
    return flat(text[start : start + 1 + end.start() if end else None])


def project_headings() -> list[str]:
    return [line for line in PROJECT_RULES.read_text("utf-8").splitlines() if line.startswith("## ")]


@pytest.mark.parametrize("rule_id", sorted(INFRA_RULES))
def test_bundle_states_infra_rule(rule_id: str) -> None:
    _, title, statement = INFRA_RULES[rule_id]
    body = bundle_rule(rule_id)
    assert body.startswith(f"## {rule_id}: {title}")
    assert statement in body


def test_bundle_carries_exactly_seven_rules_behind_an_html_comment_header() -> None:
    text = BUNDLE.read_text("utf-8")
    assert re.findall(r"(?m)^## (R-INFRA-\d+): ", text) == sorted(INFRA_RULES)
    header = flat(text.split("\n## ", 1)[0])
    assert "<!--" in header and "-->" in header
    assert "project rules belong in .claude/task-reviewer-rules.md" in header


def test_bundle_r_infra_3_names_macos_bash_32_syntax() -> None:
    body = bundle_rule("R-INFRA-3")
    for needle in ("`date -d ...` (GNU only)", "`sed -i` without an empty-string argument", "declare -A"):
        assert needle in body


@pytest.mark.parametrize("word", ["parity", "stacks", "services", "channels", "core"])
def test_bundle_names_no_project_specific_content(word: str) -> None:
    assert word not in BUNDLE.read_text("utf-8")


def test_bundle_cites_no_task_id() -> None:
    assert not re.search(r"TASK-[0-9]", BUNDLE.read_text("utf-8"))


def test_moved_rules_are_gone_from_project_file() -> None:
    for former_id, title, _ in INFRA_RULES.values():
        assert not any(h.startswith(f"## {former_id} ") for h in project_headings()), former_id
        assert not any(title in h for h in project_headings()), title


def test_project_preamble_maps_each_moved_id() -> None:
    preamble = flat(PROJECT_RULES.read_text("utf-8").split("\n## ", 1)[0])
    for rule_id, (former_id, _, _) in INFRA_RULES.items():
        assert f"{former_id} → `{rule_id}`" in preamble
