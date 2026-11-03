"""The devcontainer forwards CLAUDE_CODE_OAUTH_TOKEN by name only (TASK-282).

A ``containerEnv`` value becomes ``docker run ... -e NAME=value``, and that
``docker run`` process stays alive for the container's lifetime, so the token
sat in the host's ``ps -eo args``. ``--env=CLAUDE_CODE_OAUTH_TOKEN`` names the
variable without a value: docker copies it from its own environment, and the
value never reaches argv.

The forward is one runArgs element, not the pair ``"-e", "NAME"``: Upgrade U4
writes devcontainer.json through ``merge-runargs.sh``, which drops every
project element the template already has, so a template ``"-e"`` would strip a
project's own ``"-e"`` and leave its value as a stray docker run argument.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from devcontainer_config import REPO_ROOT, TEMPLATE, each_copy, load_jsonc, loads_jsonc

TOKEN = "CLAUDE_CODE_OAUTH_TOKEN"
FORWARD = f"--env={TOKEN}"
MERGE = REPO_ROOT / "plugins/ralph/skills/ralph-init/scripts/merge-runargs.sh"
SKILL_MD = REPO_ROOT / "plugins/ralph/skills/ralph-init/SKILL.md"


def runargs_line(text: str) -> str:
    """The single source line that carries ``runArgs``."""
    (line,) = [ln for ln in text.splitlines() if '"runArgs":' in ln]
    return line


@each_copy
def test_token_is_forwarded_by_name_in_run_args(path: Path) -> None:
    args = load_jsonc(path)["runArgs"]
    assert args.count(FORWARD) == 1
    assert "-e" not in args
    assert TOKEN not in args
    assert not [a for a in args if a.startswith(f"{FORWARD}=")]
    assert FORWARD in runargs_line(path.read_text(encoding="utf-8"))


@each_copy
def test_token_is_not_in_container_env(path: Path) -> None:
    assert TOKEN not in load_jsonc(path)["containerEnv"]
    assert "${localEnv:" + TOKEN + "}" not in path.read_text(encoding="utf-8")


@each_copy
def test_dropping_the_forward_is_caught(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    mutated = text.replace(f', "{FORWARD}"', "")
    assert mutated != text
    assert FORWARD not in loads_jsonc(mutated)["runArgs"]


def test_merge_keeps_the_forward_and_a_project_e_pair(tmp_path: Path) -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    line = runargs_line(text)
    project = tmp_path / "devcontainer.json"
    project.write_text(
        text.replace(line, line.replace("],", ', "-e", "FOO"],')), encoding="utf-8"
    )
    merged = subprocess.run(
        ["bash", str(MERGE), str(TEMPLATE), str(project)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    args = loads_jsonc(merged)["runArgs"]
    assert args.count(FORWARD) == 1
    i = args.index("-e")
    assert args[i + 1] == "FOO"
    assert args.count("-e") == 1


def test_skill_explains_the_name_only_forward() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    assert f"`{FORWARD}`" in text
    assert "docker run -e NAME=value" in text
    assert "`ps`" in text
    assert "${localEnv:" + TOKEN + "}" not in text
