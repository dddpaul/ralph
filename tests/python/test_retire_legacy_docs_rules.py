"""Upgrade's retirement of the legacy shared reviewer rules copy (TASK-265).

ralph-init used to write the shared ``R-DOCS-*`` rules into Documentation /
Mixed projects as ``.claude/task-reviewer-rules.docs.md``. The task-reviewer
agent now reads them from the plugin, so the copy is inert. Upgrade U1.7 reports
it through ``scripts/legacy-docs-rules.sh check`` and removes it through
``retire`` only when the operator's answer is yes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT

SKILL_DIR = REPO_ROOT / "plugins/ralph/skills/ralph-init"
SCRIPT = SKILL_DIR / "scripts/legacy-docs-rules.sh"
SKILL_MD = SKILL_DIR / "SKILL.md"
BUNDLE = SKILL_DIR / "rules/task-reviewer-rules.docs.md"
COPY = ".claude/task-reviewer-rules.docs.md"


def run(
    *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the script with CLAUDE_PLUGIN_ROOT unset unless ``env`` sets it."""
    base = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env={**base, "LC_ALL": "C", **(env or {})},
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A Mixed project still carrying a pristine legacy copy."""
    root = tmp_path / "project"
    (root / ".claude").mkdir(parents=True)
    (root / ".obsidian").mkdir()
    shutil.copyfile(BUNDLE, root / COPY)
    return root


def test_no_copy_is_silent(tmp_path: Path) -> None:
    result = run("check", str(tmp_path))
    assert (result.returncode, result.stdout) == (0, "")


def test_pristine_copy_is_reported_as_matching(project: Path) -> None:
    result = run("check", str(project))
    assert (result.returncode, result.stdout) == (
        1,
        f"{COPY}: legacy copy, matches the shipped rules\n",
    )


def test_edited_copy_is_reported_as_differing(project: Path) -> None:
    with (project / COPY).open("a") as f:
        f.write("## R-LOCAL-1: local edit\n")
    result = run("check", str(project))
    assert result.returncode == 1
    assert result.stdout.startswith(
        f"{COPY}: legacy copy, differs from the shipped rules"
    )


def test_check_never_removes(project: Path) -> None:
    run("check", str(project))
    assert (project / COPY).read_bytes() == BUNDLE.read_bytes()


@pytest.mark.parametrize("answer", ["n", "N", "no", "", "maybe", "yes please"])
def test_declined_copy_survives(project: Path, answer: str) -> None:
    with (project / COPY).open("a") as f:
        f.write("## R-LOCAL-1: local edit\n")
    before = (project / COPY).read_bytes()
    result = run("retire", str(project), answer)
    assert (result.returncode, result.stdout) == (0, "kept\n")
    assert (project / COPY).read_bytes() == before


@pytest.mark.parametrize("answer", ["y", "Y", "yes", "YES"])
def test_agreed_copy_is_removed(project: Path, answer: str) -> None:
    result = run("retire", str(project), answer)
    assert (result.returncode, result.stdout) == (0, "removed\n")
    assert not (project / COPY).exists()
    assert (project / ".claude").is_dir()
    assert run("check", str(project)).returncode == 0
    assert run("retire", str(project), answer).stdout == "absent\n"


def test_bundle_resolves_through_claude_plugin_root(
    project: Path, tmp_path: Path
) -> None:
    plugin = tmp_path / "plugin"
    shutil.copytree(SKILL_DIR, plugin / "skills/ralph-init")
    with (plugin / "skills/ralph-init/rules/task-reviewer-rules.docs.md").open(
        "a"
    ) as f:
        f.write("## R-DOCS-99: newer plugin\n")
    result = run("check", str(project), env={"CLAUDE_PLUGIN_ROOT": str(plugin)})
    assert result.stdout.startswith(f"{COPY}: legacy copy, differs")
    result = run(
        "check", str(project), env={"CLAUDE_PLUGIN_ROOT": str(tmp_path / "empty")}
    )
    assert result.returncode == 1
    assert "not compared" in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("check",),
        ("check", ".", "extra"),
        ("retire", "."),
        ("remove", ".", "y"),
        ("check", "/nonexistent"),
    ],
)
def test_usage_errors_exit_2(args: tuple[str, ...]) -> None:
    result = run(*args)
    assert (result.returncode, result.stdout) == (2, "")
    assert result.stderr


def u1_7_section() -> str:
    text = SKILL_MD.read_text("utf-8")
    return text[text.index("### U1.7:") : text.index("### U2:")]


def test_upgrade_asks_before_retiring() -> None:
    section = u1_7_section()
    assert "skills/ralph-init/scripts/legacy-docs-rules.sh check ." in section
    assert (
        "skills/ralph-init/scripts/legacy-docs-rules.sh retire . '<answer>'" in section
    )
    assert "[y/N]" in section
    assert section.index("check .") < section.index("[y/N]") < section.index("retire .")


def test_init_and_upgrade_no_longer_write_the_copy() -> None:
    text = SKILL_MD.read_text("utf-8")
    outside = text.replace(u1_7_section(), "")
    assert COPY not in outside
    gitignore = text[text.index("### 3.4 `.gitignore`") : text.index("### 3.5 Backlog")]
    assert "!.claude/task-reviewer-rules.md" in gitignore
    assert "task-reviewer-rules.docs" not in gitignore
