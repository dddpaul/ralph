"""ralph-init Init and Upgrade use the plugin-delivered files (TASK-301).

Init copies no guard scripts, no git hook bodies and no common allow rules: its
last step runs ``migrate-plugin-hooks.sh tracked`` and ``clone``, and Upgrade
runs both too, with a second host running only ``clone`` after ``git pull``.
The template copies are gone. The end-to-end test runs Init's settings and
migration steps as SKILL.md writes them on a fresh repo, against a fake plugin
registry, and shows the plugin's guards and git hooks enforce there.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT

PLUGIN = REPO_ROOT / "plugins/ralph"
INIT_DIR = PLUGIN / "skills/ralph-init"
SKILL_MD = INIT_DIR / "SKILL.md"
TEMPLATES = INIT_DIR / "templates"
SHIM = TEMPLATES / "shims/git-hook"
FENCE = re.compile(r"^```bash\n(.*?)^```", re.DOTALL | re.MULTILINE)
TRACKED = "migrate-plugin-hooks.sh tracked"
CLONE = "migrate-plugin-hooks.sh clone"

needs_jq = pytest.mark.skipif(shutil.which("jq") is None, reason="jq is not installed")


def section(start: str, end: str) -> str:
    text = SKILL_MD.read_text("utf-8")
    i = text.index(start)
    return text[i : text.index(end, i)]


def init_text() -> str:
    return section("## Step 3: Generate Files", "## Verification: zero-prompt smoke test")


def upgrade_text() -> str:
    return section("## Upgrade Mode", "### U4.5:")


def test_template_guard_and_git_hook_copies_are_deleted() -> None:
    assert not (TEMPLATES / "claude/hooks").exists()
    assert not (TEMPLATES / "git-hooks").exists()
    assert not (TEMPLATES / "claude/settings.json").exists()


@pytest.mark.parametrize("text", [init_text, upgrade_text], ids=["init", "upgrade"])
def test_no_step_copies_a_guard_a_hook_body_or_the_legacy_settings(text: Callable[[], str]) -> None:
    body = text()
    for gone in ("templates/claude/hooks", "templates/git-hooks", "templates/claude/settings.json"):
        assert gone not in body


def test_init_runs_tracked_then_clone_as_its_last_step() -> None:
    body = init_text()
    steps = re.findall(r"^### (3\.\d+[a-z]?) ", body, re.MULTILINE)
    assert steps[-1] == "3.11"
    last = body[body.index("### 3.11 ") :]
    assert TRACKED in last and CLONE in last
    assert last.index(TRACKED) < last.index(CLONE)
    assert TRACKED not in body[: body.index("### 3.11 ")]


def test_upgrade_runs_both_parts_and_a_second_host_only_clone() -> None:
    body = upgrade_text()
    assert TRACKED in body and CLONE in body
    assert re.search(r"second host needs only the clone part:\*\* after `git pull`", body)


def test_template_settings_local_holds_no_common_rule() -> None:
    template = json.loads((TEMPLATES / "claude/settings.local.json").read_text("utf-8"))
    fragment = json.loads((PLUGIN / "user-settings.json").read_text("utf-8"))
    assert not set(template["permissions"]["allow"]) & set(fragment["permissions"]["allow"])
    assert set(template) == {"permissions"}


# --------------------------------------------------------------------------
# Init, end to end
# --------------------------------------------------------------------------


def git(cwd: Path, env: dict[str, str], *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=check, capture_output=True, text=True)


def step_3_11_snippet() -> str:
    (snippet,) = FENCE.findall(init_text()[init_text().index("### 3.11 ") :])
    return snippet


@pytest.fixture
def initialized(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """A fresh repo after Init's Step 3.7a settings write and Step 3.11, as written."""
    home = tmp_path / "home"
    reg = home / ".claude/plugins/installed_plugins.json"
    reg.parent.mkdir(parents=True)
    entry = {"scope": "user", "installPath": str(PLUGIN), "version": "0.0.0"}
    reg.write_text(json.dumps({"version": 2, "plugins": {"ralph@dddpaul-ralph": [entry]}}))
    dropped = ("CLAUDE_CONFIG_DIR", "GIT_DIR", "GIT_WORK_TREE", "DEVCONTAINER")
    env = {k: v for k, v in os.environ.items() if k not in dropped}
    env |= {"HOME": str(home), "CLAUDE_PLUGIN_ROOT": str(PLUGIN), "LC_ALL": "C"}
    root = tmp_path / "proj"
    root.mkdir()
    git(root, env, "init", "-q", "-b", "master")
    git(root, env, "config", "user.email", "t@example.com")
    git(root, env, "config", "user.name", "T")
    (root / ".claude").mkdir()
    shutil.copyfile(TEMPLATES / "claude/settings.local.json", root / ".claude/settings.local.json")
    snippet = "set -e\n" + step_3_11_snippet()
    out = subprocess.run(["bash", "-c", snippet], cwd=root, env=env, capture_output=True, text=True, check=False)
    assert out.returncode == 0, out.stdout + out.stderr
    return root.resolve(), env


@needs_jq
def test_init_leaves_no_guard_copy_and_installs_the_shims(initialized: tuple[Path, dict[str, str]]) -> None:
    root, env = initialized
    assert not (root / ".claude/hooks").exists()
    assert not (root / ".claude/settings.json").exists()
    assert json.loads((root / ".claude/ralph.json").read_text()) == {"pluginHooks": True}
    assert "!.claude/ralph.json" in (root / ".gitignore").read_text().splitlines()
    for name in ("pre-commit", "commit-msg", "post-commit"):
        assert (root / ".git/hooks" / name).read_bytes() == SHIM.read_bytes()
    assert git(root, env, "config", "--bool", "ralph.pluginHooks").stdout.strip() == "true"
    assert git(root, env, "config", "ralph.projectPath").stdout.strip() == str(root)
    local = json.loads((root / ".claude/settings.local.json").read_text())
    assert local == json.loads((TEMPLATES / "claude/settings.local.json").read_text())


@needs_jq
def test_init_project_blocks_through_the_plugin(initialized: tuple[Path, dict[str, str]]) -> None:
    root, env = initialized
    git(root, env, "commit", "-q", "--allow-empty", "-m", "init")
    payload = json.dumps({"cwd": str(root), "tool_input": {"file_path": str(root / "README.md")}})
    guard = subprocess.run(
        ["bash", str(PLUGIN / "hooks/run.sh"), "master-branch-guard"],
        input=payload,
        cwd=root,
        env=env | {"CLAUDE_PROJECT_DIR": str(root)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert guard.returncode == 0, guard.stderr
    assert json.loads(guard.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    (root / "a.md").write_text("a\n")
    git(root, env, "add", "a.md")
    commit = git(root, env, "commit", "-q", "-m", "add\n\nCo-Authored-By: x <x@x>", check=False)
    assert commit.returncode == 1
    assert "forbidden trailer" in commit.stderr
