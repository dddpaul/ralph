"""ralph-init's managed-file drift detector (TASK-264).

``scripts/managed-file-drift.sh check <project>`` reports every ralph-init
managed file whose content differs from the installed plugin's template, with
the stale-runtime-copy.sh exit contract: 0 clean, 1 drift, 2 usage error. The
ralph-run preflight runs it before every loop (see test_preflight.py), and
Upgrade U2 runs it to build the status table, so its file list is pinned here
against U2's.
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

PLUGIN_ROOT = REPO_ROOT / "plugins/ralph"
SKILL_DIR = PLUGIN_ROOT / "skills/ralph-init"
SCRIPT = SKILL_DIR / "scripts/managed-file-drift.sh"
SKILL_MD = SKILL_DIR / "SKILL.md"
TEMPLATES = SKILL_DIR / "templates"

# Independent oracle: managed project path → shipped template.
MANAGED = {
    "ralph.sh": TEMPLATES / "root/ralph.sh",
    "refine.sh": TEMPLATES / "root/refine.sh",
    "CLAUDE.md": TEMPLATES / "root/CLAUDE.md",
    ".git/hooks/post-commit": TEMPLATES / "git-hooks/post-commit",
    ".git/hooks/commit-msg": TEMPLATES / "git-hooks/commit-msg",
    ".git/hooks/pre-commit": TEMPLATES / "git-hooks/pre-commit",
    ".claude/settings.json": TEMPLATES / "claude/settings.json",
    ".claude/settings.local.json": TEMPLATES / "claude/settings.local.json",
    ".claude/brainstorm-rules.md": TEMPLATES / "claude/brainstorm-rules.md",
    ".devcontainer/devcontainer.json": TEMPLATES / "devcontainer/devcontainer.json",
    ".devcontainer/init-firewall.sh": TEMPLATES / "devcontainer/init-firewall.sh",
    ".devcontainer/container-settings.local.json": TEMPLATES
    / "devcontainer/container-settings.local.json",
}
HOOKS = sorted(
    [*(TEMPLATES / "claude/hooks").glob("*-guard.sh"), TEMPLATES / "claude/hooks/task-validator.sh"]
)
MANAGED.update({f".claude/hooks/{h.name}": h for h in HOOKS})


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
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
    """A Mixed project with a devcontainer, every managed file current."""
    root = tmp_path / "project"
    for path, template in MANAGED.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template, root / path)
    (root / ".obsidian").mkdir()
    return root


def test_current_project_is_clean(project: Path) -> None:
    result = run("check", str(project))
    assert (result.returncode, result.stdout) == (0, "")


@pytest.mark.parametrize(
    "path",
    [
        "ralph.sh",
        ".git/hooks/pre-commit",
        ".claude/hooks/naming-guard.sh",
        ".claude/settings.local.json",
        ".devcontainer/init-firewall.sh",
    ],
)
def test_modified_managed_file_is_named(project: Path, path: str) -> None:
    with (project / path).open("a") as f:
        f.write("# local edit\n")
    result = run("check", str(project))
    assert (result.returncode, result.stdout) == (1, f"{path}: outdated\n")


@pytest.mark.parametrize("path", ["refine.sh", ".claude/hooks/notes-guard.sh", ".claude/brainstorm-rules.md"])
def test_absent_managed_file_is_missing(project: Path, path: str) -> None:
    (project / path).unlink()
    result = run("check", str(project))
    assert (result.returncode, result.stdout) == (1, f"{path}: missing\n")


def test_every_drifted_file_gets_its_own_line(project: Path) -> None:
    (project / "ralph.sh").write_text("old\n")
    (project / ".devcontainer/devcontainer.json").unlink()
    result = run("check", str(project))
    assert result.returncode == 1
    assert result.stdout.splitlines() == ["ralph.sh: outdated", ".devcontainer/devcontainer.json: missing"]


@pytest.mark.parametrize(
    ("path", "heading"),
    [("CLAUDE.md", "## Project-Specific"), (".claude/brainstorm-rules.md", "## Project additions")],
)
def test_region_files_compare_only_above_the_heading(project: Path, path: str, heading: str) -> None:
    file = project / path
    template = file.read_text()
    assert template.count(f"\n{heading}\n") == 1
    file.write_text(template + "\nproject-owned addition below the heading\n")
    assert run("check", str(project)).returncode == 0

    file.write_text("generic edit above the heading\n" + template)
    assert run("check", str(project)).stdout == f"{path}: outdated\n"

    file.write_text(template.replace(f"\n{heading}\n", "\n## Renamed\n"))
    assert run("check", str(project)).stdout == f"{path}: outdated\n"


def test_project_owned_files_are_never_reported(project: Path) -> None:
    (project / ".claude/task-reviewer-rules.md").write_bytes(os.urandom(512))
    (project / ".claude/task-reviewer.conf").write_text("docs_rules=off\n")
    (project / ".devcontainer/Dockerfile").write_text("FROM scratch\n")
    (project / ".gitignore").write_text("anything\n")
    (project / "README.md").write_text("# project\n")
    result = run("check", str(project))
    assert (result.returncode, result.stdout) == (0, "")


def test_legacy_shared_rules_copy_is_not_managed(project: Path) -> None:
    (project / ".claude/task-reviewer-rules.docs.md").write_text("# local edit\n")
    result = run("check", str(project))
    assert (result.returncode, result.stdout) == (0, "")


def test_gated_rows_are_skipped_without_their_directory(tmp_path: Path) -> None:
    project = tmp_path / "code-only"
    for path, template in MANAGED.items():
        if path.startswith((".git/", ".devcontainer/")):
            continue
        (project / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template, project / path)
    result = run("check", str(project))
    assert (result.returncode, result.stdout) == (0, "")


def test_templates_resolve_through_claude_plugin_root(project: Path, tmp_path: Path) -> None:
    plugin = tmp_path / "plugin"
    shutil.copytree(SKILL_DIR, plugin / "skills/ralph-init")
    with (plugin / "skills/ralph-init/templates/root/ralph.sh").open("a") as f:
        f.write("# newer plugin\n")
    assert run("check", str(project)).returncode == 0
    result = run("check", str(project), env={"CLAUDE_PLUGIN_ROOT": str(plugin)})
    assert (result.returncode, result.stdout) == (1, "ralph.sh: outdated\n")


@pytest.mark.parametrize(
    "args", [(), ("patch", "."), ("check",), ("check", ".", "extra"), ("list", "extra"), ("check", "/nonexistent")]
)
def test_usage_errors_exit_2(args: tuple[str, ...]) -> None:
    result = run(*args)
    assert (result.returncode, result.stdout) == (2, "")
    assert result.stderr


def test_plugin_root_without_templates_exits_2(project: Path, tmp_path: Path) -> None:
    result = run("check", str(project), env={"CLAUDE_PLUGIN_ROOT": str(tmp_path / "empty")})
    assert (result.returncode, result.stdout) == (2, "")
    assert "no ralph-init templates" in result.stderr


def u2_section() -> str:
    text = SKILL_MD.read_text("utf-8")
    return text[text.index("### U2: Build File Status Table") : text.index("### U3:")]


def test_managed_list_matches_upgrade_status_table() -> None:
    entries = re.findall(r"^\d+\. \*\*`([^`]+)`\*\*(.*)$", u2_section(), re.MULTILINE)
    assert len(entries) >= 15
    u2 = [path for path, rest in entries if "always **skipped**" not in rest]
    script = run("list").stdout.splitlines()
    assert len(script) == len(set(script))
    assert set(script) == set(u2)
    assert ".claude/task-reviewer-rules.md" not in script
    assert ".claude/task-reviewer-rules.docs.md" not in script


def test_oracle_matches_the_script_list() -> None:
    hooks_dir = {p for p in MANAGED if p.startswith(".claude/hooks/")}
    listed = set(run("list").stdout.splitlines())
    assert listed == (set(MANAGED) - hooks_dir) | {".claude/hooks/"}


def test_upgrade_runs_the_same_script() -> None:
    assert "skills/ralph-init/scripts/managed-file-drift.sh check ." in u2_section()


MERGE = SKILL_DIR / "scripts/merge-runargs.sh"
PPTX_RULES = ["Bash(python scripts/office/soffice.py:*)", "Bash(pdftoppm:*)"]
SHM = '"--shm-size=1g"'


def jq(filter_: str, file: Path, *args: str) -> None:
    """Rewrite ``file`` in place through ``jq``, as Upgrade U4 does."""
    out = subprocess.run(["jq", *args, filter_, str(file)], capture_output=True, text=True, check=True).stdout
    file.write_text(out)


def u4_settings_local(project: Path) -> None:
    """U4 for a Documentation / Mixed project: overwrite, Step 3.7b pptx merge, dead-rule strip."""
    file = project / ".claude/settings.local.json"
    shutil.copyfile(MANAGED[".claude/settings.local.json"], file)
    p1, p2 = PPTX_RULES
    merge = ".permissions.allow = ((.permissions.allow // []) + [$p1, $p2] | unique)"
    jq(merge, file, "--arg", "p1", p1, "--arg", "p2", p2)
    dead = r"/\.claude/skills/ralph-(run|status)/|/plugins/cache/[^/]+/ralph/[0-9]+\.[0-9]+\.[0-9]+/"
    jq(".permissions.allow = ((.permissions.allow // []) | map(select(test($re) | not)))", file, "--arg", "re", dead)


def u4_devcontainer(project: Path) -> None:
    """U4's devcontainer.json overwrite: the template merged with the project's runArgs."""
    file = project / ".devcontainer/devcontainer.json"
    merged = subprocess.run(
        ["bash", str(MERGE), str(MANAGED[".devcontainer/devcontainer.json"]), str(file)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    file.write_text(merged)


def runargs_line(file: Path) -> str:
    (line,) = [ln for ln in file.read_text().splitlines() if '"runArgs":' in ln]
    return line


def add_runarg(file: Path, element: str) -> None:
    line = runargs_line(file)
    file.write_text(file.read_text().replace(line, line.replace("],", f", {element}],")))


@pytest.mark.skipif(shutil.which("jq") is None, reason="Upgrade U4 merges settings.local.json with jq")
def test_settings_local_after_u4_pptx_merge_is_current(project: Path) -> None:
    file = project / ".claude/settings.local.json"
    file.write_text('{"permissions": {"allow": ["Bash(old:*)"]}}\n')
    assert run("check", str(project)).stdout == ".claude/settings.local.json: outdated\n"
    u4_settings_local(project)
    allow = json.loads(file.read_text())["permissions"]["allow"]
    assert set(PPTX_RULES) <= set(allow)
    assert file.read_bytes() != MANAGED[".claude/settings.local.json"].read_bytes()
    result = run("check", str(project))
    assert (result.returncode, result.stdout) == (0, "")


@pytest.mark.skipif(shutil.which("jq") is None, reason="the allow rule needs jq")
@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda s: s["permissions"]["allow"].remove("Bash(git status:*)"), id="template-rule-dropped"),
        pytest.param(lambda s: s["sandbox"].update(enabled=False), id="sandbox-flipped"),
        pytest.param(lambda s: s.update(model="opus"), id="key-added"),
        pytest.param(lambda s: s["permissions"].update(deny=["Bash(rm:*)"]), id="permissions-key-added"),
        pytest.param(lambda s: s["attribution"].pop("pr"), id="key-removed"),
    ],
)
def test_settings_local_containment_still_catches_drift(project: Path, mutate: Callable[[dict], object]) -> None:
    file = project / ".claude/settings.local.json"
    settings = json.loads(file.read_text())
    settings["permissions"]["allow"] += PPTX_RULES
    file.write_text(json.dumps(settings, indent=2) + "\n")
    assert run("check", str(project)).returncode == 0
    mutate(settings)
    file.write_text(json.dumps(settings, indent=2) + "\n")
    result = run("check", str(project))
    assert (result.returncode, result.stdout) == (1, ".claude/settings.local.json: outdated\n")


def test_settings_local_without_jq_falls_back_to_exact(project: Path, tmp_path: Path) -> None:
    file = project / ".claude/settings.local.json"
    settings = json.loads(file.read_text())
    settings["permissions"]["allow"] += PPTX_RULES
    file.write_text(json.dumps(settings, indent=2) + "\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("bash", "cat", "cmp", "cut", "grep", "awk", "sed", "head", "tail", "dirname"):
        (bin_dir / tool).symlink_to(shutil.which(tool) or f"/usr/bin/{tool}")
    result = run("check", str(project), env={"PATH": str(bin_dir)})
    assert (result.returncode, result.stdout) == (1, ".claude/settings.local.json: outdated\n")


def test_u4_keeps_project_runargs_and_check_calls_it_current(project: Path) -> None:
    file = project / ".devcontainer/devcontainer.json"
    template_line = runargs_line(file)
    file.write_text(file.read_text().replace('"remoteUser": "node"', '"remoteUser": "root"'))
    add_runarg(file, SHM)
    assert run("check", str(project)).stdout == ".devcontainer/devcontainer.json: outdated\n"
    u4_devcontainer(project)
    assert SHM in runargs_line(file)
    assert runargs_line(file) == template_line.replace("],", f", {SHM}],")
    assert '"remoteUser": "node"' in file.read_text()
    result = run("check", str(project))
    assert (result.returncode, result.stdout) == (0, "")
    before = file.read_bytes()
    u4_devcontainer(project)
    assert file.read_bytes() == before


def test_u4_on_a_current_template_copy_is_a_no_op(project: Path) -> None:
    file = project / ".devcontainer/devcontainer.json"
    u4_devcontainer(project)
    assert file.read_bytes() == MANAGED[".devcontainer/devcontainer.json"].read_bytes()


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda t: t.replace('"--cap-add=NET_RAW", ', ""), id="template-element-dropped"),
        pytest.param(lambda t: t.replace('"remoteUser": "node"', '"remoteUser": "root"'), id="other-field"),
        pytest.param(lambda t: t.replace('"waitFor": "postStartCommand"', '"waitFor": "x"'), id="last-field"),
        pytest.param(lambda t: t.replace('"runArgs": [', '"runArgs": [\n    '), id="multi-line-runargs"),
    ],
)
def test_runargs_containment_still_catches_drift(project: Path, mutate: Callable[[str], str]) -> None:
    file = project / ".devcontainer/devcontainer.json"
    add_runarg(file, SHM)
    assert run("check", str(project)).returncode == 0
    text = file.read_text()
    assert mutate(text) != text
    file.write_text(mutate(text))
    result = run("check", str(project))
    assert (result.returncode, result.stdout) == (1, ".devcontainer/devcontainer.json: outdated\n")


def test_reordered_template_runargs_are_outdated(project: Path) -> None:
    file = project / ".devcontainer/devcontainer.json"
    admin, raw = '"--cap-add=NET_ADMIN"', '"--cap-add=NET_RAW"'
    file.write_text(file.read_text().replace(f"{admin}, {raw}", f"{raw}, {admin}"))
    assert run("check", str(project)).stdout == ".devcontainer/devcontainer.json: outdated\n"


def test_skill_documents_project_runargs_and_the_merged_overwrite() -> None:
    text = SKILL_MD.read_text("utf-8")
    u4 = text[text.index("### U4: Apply Updates") : text.index("### U5")]
    assert "**Project `runArgs` in `devcontainer.json`:**" in u4
    assert "skills/ralph-init/scripts/merge-runargs.sh" in u4
    assert "overwrite from `templates/devcontainer/devcontainer.json`." not in u4
    u2 = u2_section()
    assert "exact content match against `templates/claude/settings.local.json`" not in u2
    assert "merge-runargs.sh" in u2
