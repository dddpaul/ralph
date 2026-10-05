"""No allow-rule is seeded for the plugin helper scripts (TASK-254).

ralph-init seeds nothing for the ralph-run and ralph-status helpers. On Claude
Code 2.1.280 sandbox auto-allow approves them, and every rule shape that could
cover them was measured as either too broad (a bare ``ralph/*`` crosses ``/``,
an over-broad ``Bash(bash:*)`` in effect) or dead at the next plugin bump
(version-pinned). Older projects still carry dead helper rules, which the
upgrade flow strips.

The strip runs straight out of SKILL.md, because its escaping is easy to get
wrong in a way that reads fine and silently matches nothing: it shipped once
with doubled backslashes that jq read as a literal backslash.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from devcontainer_config import REPO_ROOT

SKILLS = REPO_ROOT / "plugins/ralph/skills"
INIT_MD = SKILLS / "ralph-init/SKILL.md"
TEMPLATE = SKILLS / "ralph-init/templates/claude/settings.local.json"
HELPER = re.compile(r"plugins/cache/|\.claude/skills/ralph")

DEAD = [
    # Pre-marketplace, $HOME and absolute forms: the files no longer exist.
    "Bash(bash $HOME/.claude/skills/ralph-run/scripts/preflight.sh:*)",
    "Bash(bash /Users/x/.claude/skills/ralph-status/scripts/utc-to-moscow.sh:*)",
    # Plugin cache pinned to a version: dead at the next plugin bump.
    "Bash(bash /Users/x/.claude/plugins/cache/dddpaul-ralph/ralph/0.1.0/skills/ralph-run/scripts/w.sh:*)",
]
KEPT = ["Bash(my-custom-tool:*)", "Bash(git add:*)", "Skill(ralph-run)"]


def init_text() -> str:
    return INIT_MD.read_text("utf-8")


def strip_snippet() -> str:
    """The Upgrade Mode dead-rule strip, dedented, exactly as written."""
    lines = init_text().splitlines()
    start = next(n for n, line in enumerate(lines) if line.lstrip().startswith("dead='"))
    end = next(n for n in range(start, len(lines)) if lines[n].strip() == "```")
    return "\n".join(line.removeprefix("  ") for line in lines[start:end])


def run_strip(tmp_path: Path, settings: dict[str, object]) -> tuple[str, dict[str, object]]:
    (tmp_path / ".claude").mkdir()
    target = tmp_path / ".claude/settings.local.json"
    target.write_text(json.dumps(settings), encoding="utf-8")
    out = subprocess.run(
        ["bash", "-c", "set -e\n" + strip_snippet()],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout, json.loads(target.read_text("utf-8"))


def test_template_seeds_no_helper_rule() -> None:
    allow = json.loads(TEMPLATE.read_text("utf-8"))["permissions"]["allow"]
    assert [r for r in allow if HELPER.search(r)] == []
    assert "{{" not in TEMPLATE.read_text("utf-8")


def test_strip_removes_both_dead_shapes_and_keeps_the_rest(tmp_path: Path) -> None:
    listed, after = run_strip(tmp_path, {"permissions": {"allow": DEAD + KEPT}})
    assert listed.splitlines() == DEAD
    assert after["permissions"] == {"allow": KEPT}


def test_strip_tolerates_a_file_without_an_allow_array(tmp_path: Path) -> None:
    listed, after = run_strip(tmp_path, {"sandbox": {"enabled": True}})
    assert listed == ""
    assert after == {"sandbox": {"enabled": True}, "permissions": {"allow": []}}


def test_every_helper_call_starts_with_bash() -> None:
    offenders = []
    for md in sorted(SKILLS.glob("*/SKILL.md")):
        for n, line in enumerate(md.read_text("utf-8").splitlines(), 1):
            if re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/[^ ]+/scripts/[^ ]+\.sh", line):
                call = line.strip().lstrip("`")
                if re.match(r"^\w+=", call):
                    offenders.append(f"{md.relative_to(REPO_ROOT)}:{n}: {call}")
    assert not offenders, offenders


def test_init_documents_why_no_helper_rule_is_seeded() -> None:
    text = init_text()
    assert "No allow-rule is seeded for the plugin helper scripts" in text
    assert "Do not add a helper rule" in text
    assert "a bare `*` crosses `/`" in text
    assert "{{CLAUDE_DIR}}" not in text


def test_no_skill_still_cites_a_seeded_helper_rule() -> None:
    # The first cut of TASK-254 seeded a rule and explained the helper call
    # shape by it; the rule was dropped and two sentences outlived it.
    stale = [
        f"{md.relative_to(REPO_ROOT)}:{n}"
        for md in sorted(SKILLS.glob("*/SKILL.md"))
        for n, line in enumerate(md.read_text("utf-8").splitlines(), 1)
        if "seeded allow-rule" in line or "seeded helper rule" in line
    ]
    assert not stale, stale
