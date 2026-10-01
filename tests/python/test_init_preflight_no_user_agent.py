"""ralph-init preflight requires no user-level agent file (TASK-255).

The task-reviewer agent ships inside the ralph plugin and resolves as
``ralph:task-reviewer``; the plugin-installed check already covers it. A stale
check for ``~/.claude/agents/task-reviewer.md`` once aborted every init and
upgrade on machines without that file, so Step 1 is run here as written
against a HOME that has a plugin-cache install but no ``.claude/agents``.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from devcontainer_config import REPO_ROOT

INIT_MD = REPO_ROOT / "plugins/ralph/skills/ralph-init/SKILL.md"
PLUGIN_AGENT = REPO_ROOT / "plugins/ralph/agents/task-reviewer.md"
FENCE = re.compile(r"^```bash\n(.*?)^```", re.DOTALL | re.MULTILINE)


def step1_snippets() -> list[str]:
    """The bash blocks of Step 1, in order, exactly as written."""
    text = INIT_MD.read_text("utf-8")
    start = text.index("## Step 1: Preflight Checks")
    end = text.index("## Step 2:", start)
    return FENCE.findall(text[start:end])


def test_plugin_ships_the_task_reviewer_agent() -> None:
    assert PLUGIN_AGENT.is_file()


def test_no_bash_snippet_requires_a_user_level_agent() -> None:
    blocks = FENCE.findall(INIT_MD.read_text("utf-8"))
    assert [b for b in blocks if ".claude/agents" in b] == []


def test_step1_passes_with_plugin_and_no_user_agents(tmp_path: Path) -> None:
    home = tmp_path / "home"
    plugin = home / ".claude/plugins/cache/dddpaul-ralph/ralph/0.0.0/skills/ralph-run/scripts"
    plugin.mkdir(parents=True)
    (plugin / "ralph_orchestrator.py").write_text("", encoding="utf-8")
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    backlog = stub_bin / "backlog"
    backlog.write_text("#!/bin/sh\n", encoding="utf-8")
    backlog.chmod(0o755)
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
    env |= {"HOME": str(home), "PATH": f"{stub_bin}{os.pathsep}{env['PATH']}"}

    snippets = step1_snippets()
    assert len(snippets) == 2
    for snippet in snippets:
        out = subprocess.run(["bash", "-c", "set -e\n" + snippet], cwd=repo, env=env, capture_output=True, text=True)
        assert out.returncode == 0, out.stdout + out.stderr
    assert not (home / ".claude/agents").exists()
