"""The seeded allow-rule for the plugin helper scripts (TASK-254).

Sandbox auto-allow does not reliably cover the ralph-run and ralph-status
helpers before Claude Code 2.1.285, so ralph-init seeds one rule for them:
``Bash(bash <claude-dir>/plugins/cache/dddpaul-ralph/ralph/*)``. Three
properties make that rule work, and each is pinned here:

- It is rendered to an absolute path. The permission matcher compares literal
  text and never expands ``$HOME`` (TASK-126), so the template carries a
  ``{{CLAUDE_DIR}}`` placeholder that init renders.
- It stops above the version directory, so it survives plugin upgrades.
- Every helper call starts with ``bash``. The rule matches by prefix, so a call
  led by ``VAR=...`` can never match it.

The render and dead-rule snippets are executed straight out of SKILL.md, the
way the upgrade flow runs them, because the escaping is easy to get wrong in
a way that reads fine and silently matches nothing.
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
HELPER_RULE = "Bash(bash {{CLAUDE_DIR}}/plugins/cache/dddpaul-ralph/ralph/*)"
VERSIONED = re.compile(r"ralph/[0-9]+\.[0-9]+\.[0-9]+")


def allow(path: Path) -> list[str]:
    return json.loads(path.read_text("utf-8"))["permissions"]["allow"]


def init_text() -> str:
    return INIT_MD.read_text("utf-8")


def render_snippet() -> str:
    """The Step 3.7a render command, as written."""
    lines = init_text().splitlines()
    i = next(n for n, line in enumerate(lines) if "gsub(" in line)
    return "\n".join(lines[i - 1 : i + 3])


def dead_pattern() -> str:
    """The U4 dead-rule regex, as the shell would hand it to jq."""
    (line,) = [line for line in init_text().splitlines() if line.lstrip().startswith("dead='")]
    out = subprocess.run(
        ["bash", "-c", f'{line.strip()}\nprintf %s "$dead"'],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def test_template_seeds_exactly_one_helper_rule() -> None:
    rules = [r for r in allow(TEMPLATE) if "plugins/cache" in r]
    assert rules == [HELPER_RULE]


def test_no_seeded_rule_names_a_plugin_version() -> None:
    assert not [r for r in allow(TEMPLATE) if VERSIONED.search(r)]


def test_render_produces_an_absolute_rule(tmp_path: Path) -> None:
    out = tmp_path / "settings.local.json"
    cmd = render_snippet().replace("${CLAUDE_PLUGIN_ROOT}", str(REPO_ROOT / "plugins/ralph"))
    cmd = cmd.replace("> .claude/settings.local.json", f'> "{out}"')
    subprocess.run(
        ["bash", "-c", cmd],
        check=True,
        env={"PATH": "/usr/bin:/bin:/opt/homebrew/bin:/usr/local/bin", "HOME": "/home/someone"},
    )
    rendered = allow(out)
    assert "Bash(bash /home/someone/.claude/plugins/cache/dddpaul-ralph/ralph/*)" in rendered
    assert "{{" not in out.read_text("utf-8")
    # Everything but the placeholder rule is carried over untouched.
    assert len(rendered) == len(allow(TEMPLATE))


def test_dead_rule_pattern_strips_both_dead_shapes() -> None:
    dead = re.compile(dead_pattern())
    removed = [
        # Pre-marketplace, $HOME and absolute forms: the files no longer exist.
        "Bash(bash $HOME/.claude/skills/ralph-run/scripts/preflight.sh:*)",
        "Bash(bash /Users/x/.claude/skills/ralph-status/scripts/utc-to-moscow.sh:*)",
        # Plugin cache pinned to a version: dead at the next plugin bump.
        "Bash(bash /Users/x/.claude/plugins/cache/dddpaul-ralph/ralph/0.1.0/skills/ralph-run/scripts/w.sh:*)",
    ]
    kept = [
        "Bash(bash /Users/x/.claude/plugins/cache/dddpaul-ralph/ralph/*)",
        "Bash(my-custom-tool:*)",
        "Skill(ralph-run)",
    ]
    assert [r for r in removed if not dead.search(r)] == []
    assert [r for r in kept if dead.search(r)] == []


def test_every_helper_call_starts_with_bash() -> None:
    offenders = []
    for md in sorted(SKILLS.glob("*/SKILL.md")):
        for n, line in enumerate(md.read_text("utf-8").splitlines(), 1):
            if re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/[^ ]+/scripts/[^ ]+\.sh", line):
                call = line.strip().lstrip("`")
                if re.match(r"^\w+=", call):
                    offenders.append(f"{md.relative_to(REPO_ROOT)}:{n}: {call}")
    assert not offenders, offenders


def test_init_no_longer_promises_no_seeded_rule() -> None:
    text = init_text()
    assert "no seeded allow-rule is required" not in text
    assert "Why zero seeded rules suffice" not in text
