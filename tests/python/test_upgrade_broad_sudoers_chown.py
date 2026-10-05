"""Upgrade's in-place patch for the broad devcontainer sudoers grant (TASK-273).

TASK-271 narrowed the ``node-firewall`` sudoers rule in ``Dockerfile.base`` from
a bare ``/bin/chown`` (any arguments, so ``node`` can take over the root-run
firewall script) to the one chown ``postCreateCommand`` runs. ``ralph upgrade``
never re-assembles ``.devcontainer/Dockerfile``, so older projects keep the
broad grant. ``scripts/broad-sudoers-chown.sh`` finds it (``check``) and prints
the file with the grant narrowed (``patch``); SKILL.md writes it only on a yes.

The patched file is fed to the same ``rule_problems()`` that guards the
templates in test_devcontainer_sudoers.py, so the patch cannot drift from it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import test_devcontainer_sudoers as sudoers_guard
from devcontainer_config import LIVE_DIR, REPO_ROOT, TEMPLATE_DIR

SKILL_DIR = REPO_ROOT / "plugins/ralph/skills/ralph-init"
SCRIPT = SKILL_DIR / "scripts/broad-sudoers-chown.sh"
SKILL_MD = SKILL_DIR / "SKILL.md"
BASE = (TEMPLATE_DIR / "Dockerfile.base").read_text("utf-8")
CONFIG = TEMPLATE_DIR / "devcontainer.json"
SUDOERS = sudoers_guard.SUDOERS
CURRENT_STEP = (
    f" && {sudoers_guard.NARROW_ECHO} > {SUDOERS} \\\n"
    f" && chmod 0440 {SUDOERS} \\\n"
    f" && visudo -cf {SUDOERS}\n"
)
# The pre-TASK-271 step, verbatim: what existing projects still carry.
OLD_STEP = f" && {sudoers_guard.BARE_ECHO} > {SUDOERS} \\\n && chmod 0440 {SUDOERS}\n"
OLD = BASE.replace(CURRENT_STEP, OLD_STEP)


def run(
    mode: str, *paths: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), mode, *map(str, paths)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def write(tmp_path: Path, text: str, name: str = "Dockerfile") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def config_with(tmp_path: Path, post_create: object) -> Path:
    return write(
        tmp_path, json.dumps({"postCreateCommand": post_create}), "devcontainer.json"
    )


def test_fixture_is_the_old_step() -> None:
    assert OLD != BASE
    assert any("exactly" in p for p in sudoers_guard.rule_problems(OLD))


def test_bare_chown_is_flagged(tmp_path: Path) -> None:
    out = run("check", write(tmp_path, OLD))
    assert out.returncode == 1, out.stderr
    (line,) = out.stdout.splitlines()
    assert "allows /bin/chown with any arguments" in line
    assert line.startswith(
        f"line {OLD.splitlines().index(OLD_STEP.splitlines()[0]) + 1}:"
    )


@pytest.mark.parametrize(
    "path",
    (TEMPLATE_DIR / "Dockerfile.base", LIVE_DIR / "Dockerfile"),
    ids=("template", "live"),
)
def test_current_dockerfiles_are_clean(path: Path) -> None:
    out = run("check", path)
    assert (out.returncode, out.stdout) == (0, ""), out.stderr


def test_bare_chown_last_in_a_continued_grant_is_flagged(tmp_path: Path) -> None:
    text = (
        "FROM node:20\n"
        "RUN true \\\n"
        "# a comment inside the continuation\n"
        f' && echo "node ALL=(root) NOPASSWD: /bin/chown, {sudoers_guard.FIREWALL}" > {SUDOERS}\n'
    )
    assert run("check", write(tmp_path, text)).returncode == 1


def test_patch_narrows_the_grant_and_adds_visudo(tmp_path: Path) -> None:
    path = write(tmp_path, OLD)
    out = run("patch", path, CONFIG)
    assert out.returncode == 0, out.stderr
    assert out.stdout == BASE
    assert sudoers_guard.rule_problems(out.stdout) == []
    # Confirm-only: the script prints, SKILL.md writes on a yes.
    assert path.read_text("utf-8") == OLD


def test_patch_keeps_an_existing_visudo(tmp_path: Path) -> None:
    text = BASE.replace(sudoers_guard.NARROW_ECHO, sudoers_guard.BARE_ECHO)
    out = run("patch", write(tmp_path, text), CONFIG)
    assert (out.returncode, out.stdout) == (0, BASE), out.stderr


def test_patch_keeps_the_rest_of_a_customised_file(tmp_path: Path) -> None:
    extra = "\n# project addition\nRUN echo kept\n"
    out = run("patch", write(tmp_path, OLD + extra), CONFIG)
    assert (out.returncode, out.stdout) == (0, BASE + extra), out.stderr


def test_nothing_to_patch_on_a_current_file(tmp_path: Path) -> None:
    out = run("patch", write(tmp_path, BASE), CONFIG)
    assert (out.returncode, out.stdout) == (1, "")


def test_patch_refuses_a_grant_with_another_command(tmp_path: Path) -> None:
    text = OLD.replace('/bin/chown"', '/bin/chown, /usr/bin/apt-get"')
    assert text != OLD
    path = write(tmp_path, text)
    assert run("check", path).returncode == 1
    out = run("patch", path, CONFIG)
    assert (out.returncode, out.stdout) == (3, "")
    assert "/usr/bin/apt-get" in out.stderr and "patch by hand" in out.stderr


@pytest.mark.parametrize(
    ("post_create", "code"),
    [
        (
            "sudo chown node:node /workspace/.venv && git config --global --add safe.directory /workspace",
            0,
        ),
        ("git config --global --add safe.directory /workspace", 0),
        ("sudo chown -R node:node /workspace && uv sync", 3),
        ("sudo chown node:node /workspace/.venv; sudo apt-get install -y jq", 3),
        (["sudo", "chown", "node:node", "/workspace/.venv"], 3),
    ],
    ids=("template", "no-sudo", "other-chown", "second-sudo", "array-form"),
)
def test_patch_checks_post_create_command(
    tmp_path: Path, post_create: object, code: int
) -> None:
    out = run("patch", write(tmp_path, OLD), config_with(tmp_path, post_create))
    assert out.returncode == code, out.stderr
    assert out.stdout == (BASE if code == 0 else "")


def test_patch_accepts_a_config_without_post_create(tmp_path: Path) -> None:
    config = write(tmp_path, "{\n  // no hooks\n}\n", "devcontainer.json")
    assert run("patch", write(tmp_path, OLD), config).returncode == 0


def test_patch_refuses_a_grant_split_over_lines(tmp_path: Path) -> None:
    text = OLD.replace(f'/bin/chown" > {SUDOERS}', f'/bin/chown" \\\n   > {SUDOERS}')
    assert text != OLD
    path = write(tmp_path, text)
    assert run("check", path).returncode == 1
    out = run("patch", path, CONFIG)
    assert (out.returncode, out.stdout) == (3, "")
    assert "spans several lines" in out.stderr


@pytest.mark.parametrize(
    "args", (("check",), ("patch", "x"), ("check", "x", "y"), ("fix", "x")), ids=str
)
def test_usage_errors(args: tuple[str, ...]) -> None:
    out = subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, check=False
    )
    assert (out.returncode, out.stdout) == (2, "")


def test_unreadable_config_prints_nothing(tmp_path: Path) -> None:
    out = run("patch", write(tmp_path, OLD), tmp_path / "missing.json")
    assert (out.returncode, out.stdout) == (2, "")


def test_detector_runs_under_mawk(tmp_path: Path) -> None:
    mawk = shutil.which("mawk")
    if mawk is None:
        pytest.skip("mawk not installed")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "awk").symlink_to(mawk)
    env = {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"}
    path = write(tmp_path, OLD)
    assert run("check", path, env=env).returncode == 1
    out = run("patch", path, CONFIG, env=env)
    assert (out.returncode, out.stdout) == (0, BASE)


def _upgrade_section() -> str:
    text = SKILL_MD.read_text("utf-8")
    return text[text.index("## Upgrade Mode") :]


def test_skill_md_runs_the_detector_on_upgrade() -> None:
    upgrade = _upgrade_section()
    assert "broad-sudoers-chown.sh check .devcontainer/Dockerfile" in upgrade
    assert (
        "broad-sudoers-chown.sh patch .devcontainer/Dockerfile .devcontainer/devcontainer.json"
        in upgrade
    )
    for label in (
        "skipped (assembled; broad sudoers chown)",
        "sudoers narrowed",
        "broad sudoers chown, user declined",
        "broad sudoers chown, patch by hand",
    ):
        assert label in upgrade, label
