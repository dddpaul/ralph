"""The devcontainer keeps its secrets off the host's argv (TASK-282, TASK-290).

A ``containerEnv`` value becomes ``docker run ... -e NAME=value``, and that
``docker run`` process stays alive for the container's lifetime, so the token
sat in the host's ``ps -eo args``. ``--env=CLAUDE_CODE_OAUTH_TOKEN`` names the
variable without a value: docker copies it from its own environment, and the
value never reaches argv.

The forward is one runArgs element, not the pair ``"-e", "NAME"``: Upgrade U4
writes devcontainer.json through ``merge-runargs.sh``, which drops every
project element the template already has, so a template ``"-e"`` would strip a
project's own ``"-e"`` and leave its value as a stray docker run argument.
MCP_GATEWAY_TOKEN is forwarded the same way.

``userEnvProbe`` is ``none``: the default probe re-sends the container env as
``docker exec -e NAME=value`` on every ``devcontainer exec``, which put both
secrets in the host's ``ps`` for each exec's lifetime. ``remoteEnv`` supplies
the locale the probe used to supply.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT, TEMPLATE, each_copy, load_jsonc, loads_jsonc

TOKEN = "CLAUDE_CODE_OAUTH_TOKEN"
FORWARD = f"--env={TOKEN}"
GATEWAY = "MCP_GATEWAY_TOKEN"
SECRETS = (TOKEN, GATEWAY)
each_secret = pytest.mark.parametrize("name", SECRETS)
LOCALE = "C.UTF-8"
MERGE = REPO_ROOT / "plugins/ralph/skills/ralph-init/scripts/merge-runargs.sh"
SKILL_MD = REPO_ROOT / "plugins/ralph/skills/ralph-init/SKILL.md"


def runargs_line(text: str) -> str:
    """The single source line that carries ``runArgs``."""
    (line,) = [ln for ln in text.splitlines() if '"runArgs":' in ln]
    return line


@each_copy
@each_secret
def test_secret_is_forwarded_by_name_in_run_args(path: Path, name: str) -> None:
    forward = f"--env={name}"
    args = load_jsonc(path)["runArgs"]
    assert args.count(forward) == 1
    assert "-e" not in args
    assert name not in args
    assert not [a for a in args if a.startswith(f"{forward}=")]
    assert forward in runargs_line(path.read_text(encoding="utf-8"))


@each_copy
def test_secret_forwards_sit_next_to_each_other(path: Path) -> None:
    args = load_jsonc(path)["runArgs"]
    assert args.index(f"--env={GATEWAY}") == args.index(FORWARD) + 1


@each_copy
@each_secret
def test_secret_is_not_in_container_env(path: Path, name: str) -> None:
    assert name not in load_jsonc(path)["containerEnv"]
    assert "${localEnv:" + name + "}" not in path.read_text(encoding="utf-8")


@each_copy
@each_secret
def test_dropping_the_forward_is_caught(path: Path, name: str) -> None:
    text = path.read_text(encoding="utf-8")
    mutated = text.replace(f', "--env={name}"', "")
    assert mutated != text
    assert f"--env={name}" not in loads_jsonc(mutated)["runArgs"]


@each_copy
def test_exec_skips_the_user_env_probe(path: Path) -> None:
    assert load_jsonc(path)["userEnvProbe"] == "none"


@each_copy
def test_remote_env_supplies_the_locale(path: Path) -> None:
    remote = load_jsonc(path)["remoteEnv"]
    assert remote == {"LANG": LOCALE, "LC_ALL": LOCALE}
    assert not set(remote) & set(SECRETS)


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
    assert args.count(f"--env={GATEWAY}") == 1
    i = args.index("-e")
    assert args[i + 1] == "FOO"
    assert args.count("-e") == 1


def test_skill_explains_the_name_only_forward() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    assert f"`{FORWARD}`" in text
    assert "docker run -e NAME=value" in text
    assert "`ps`" in text
    assert "${localEnv:" + TOKEN + "}" not in text


def test_skill_explains_the_gateway_forward_and_the_probe() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    assert f"`--env={GATEWAY}`" in text
    assert "${localEnv:" + GATEWAY + "}" not in text
    assert '`"userEnvProbe": "none"`' in text
    assert "docker exec -e NAME=value" in text
