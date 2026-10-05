"""Upgrade's in-place patch for the early ``ARG CLAUDE_CODE_VERSION`` (TASK-273).

TASK-272 moved the ``ARG`` in ``Dockerfile.base`` from the top of the final
stage to just before ``LABEL dev.ralph.claude-code-version``: a changed ``ARG``
value misses the cache for every ``RUN`` after its declaration, so the early
``ARG`` rebuilt the whole image on every Claude Code bump. ``ralph upgrade``
never re-assembles ``.devcontainer/Dockerfile``, so older projects keep the
early ``ARG``. ``scripts/early-claude-arg.sh`` finds it (``check``) and prints
the file with the ``ARG`` moved (``patch``), refreshing the pre-TASK-272 Claude
block comment from the shipped template (TASK-274); SKILL.md writes it only on
a yes.

The detector is run against ``placement_problems()`` from
test_devcontainer_claude_code_pin.py, and the pre-TASK-271 template is put
through both upgrade patches and the template guards.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import test_devcontainer_claude_code_pin as pin_guard
import test_devcontainer_sudoers as sudoers_guard
from devcontainer_config import LIVE_DIR, REPO_ROOT, TEMPLATE_DIR

SKILL_DIR = REPO_ROOT / "plugins/ralph/skills/ralph-init"
SCRIPT = SKILL_DIR / "scripts/early-claude-arg.sh"
SUDOERS_SCRIPT = SKILL_DIR / "scripts/broad-sudoers-chown.sh"
SKILL_MD = SKILL_DIR / "SKILL.md"
LANG_DIR = TEMPLATE_DIR / "lang"
BASE = (TEMPLATE_DIR / "Dockerfile.base").read_text("utf-8")
ARG = "ARG CLAUDE_CODE_VERSION\n"
LABEL = 'LABEL dev.ralph.claude-code-version="${CLAUDE_CODE_VERSION}"\n'
# The pre-TASK-272 comment paragraph and its place, verbatim.
OLD_COMMENT = (
    "# No default on purpose: the version comes from devcontainer.json build.args,\n"
    "# a concrete X.Y.Z. A floating tag like `latest` is resolved once and then\n"
    "# frozen in the layer cache, so the image silently ages; the npm step below\n"
    "# refuses one.\n"
)
EARLY_SLOT = 'ARG TZ\nENV TZ="$TZ"\n\n'
# The template before TASK-271 and TASK-272: broad sudoers chown and early ARG.
PRE_271_REV = "39adcb5"
PRE_271_PATH = "plugins/ralph/skills/ralph-init/templates/devcontainer/Dockerfile.base"


def early(text: str) -> str:
    """``text`` with its ARG moved to the top of the final stage, comment and all."""
    late = text.replace(ARG, "", 1)
    moved = late.replace(EARLY_SLOT, EARLY_SLOT + OLD_COMMENT + ARG + "\n", 1)
    assert late != text and moved != late
    return moved


def assemble_node(base: str) -> str:
    """Assemble ``base`` as the node flavour, the way ralph-init Step 3.6 does."""
    return base.replace(
        "{{LANGUAGE_STAGE}}", (LANG_DIR / "Dockerfile.lang.node").read_text("utf-8")
    ).replace(
        "{{LANGUAGE_INSTALL}}",
        (LANG_DIR / "Dockerfile.install.node").read_text("utf-8"),
    )


def run(
    mode: str,
    dockerfile: Path,
    env: dict[str, str] | None = None,
    script: Path = SCRIPT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script), mode, str(dockerfile)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def write(tmp_path: Path, text: str, name: str = "Dockerfile") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def placement(text: str) -> list[str]:
    return pin_guard.placement_problems(pin_guard.instructions(text))


def test_early_arg_is_flagged(tmp_path: Path) -> None:
    old = early(BASE)
    assert placement(old)
    out = run("check", write(tmp_path, old))
    assert out.returncode == 1, out.stderr
    (line,) = out.stdout.splitlines()
    arg_line = old.splitlines().index(ARG.strip()) + 1
    assert line.startswith(
        f"line {arg_line}: ARG CLAUDE_CODE_VERSION is declared 5 RUN step(s)"
    )


@pytest.mark.parametrize(
    "path",
    (TEMPLATE_DIR / "Dockerfile.base", LIVE_DIR / "Dockerfile"),
    ids=("template", "live"),
)
def test_current_dockerfiles_are_clean(path: Path) -> None:
    out = run("check", path)
    assert (out.returncode, out.stdout) == (0, ""), out.stderr


@pytest.mark.parametrize(
    "mutation",
    [
        lambda t: t.replace(ARG, ARG + "RUN true\n", 1),
        early,
        lambda t: t.replace(ARG, "", 1).replace(LABEL, LABEL + ARG, 1),
        lambda t: ARG + t.replace(ARG, "", 1),
    ],
    ids=("run-after-arg", "early", "arg-after-label", "global-arg"),
)
def test_detector_agrees_with_placement_problems(
    tmp_path: Path, mutation: object
) -> None:
    text = mutation(BASE)  # type: ignore[operator]
    out = run("check", write(tmp_path, text))
    assert out.returncode in (0, 1), out.stderr
    assert (out.returncode == 1) == any("RUN between" in p for p in placement(text))


def test_patch_moves_the_arg_and_its_comment(tmp_path: Path) -> None:
    old = early(BASE)
    path = write(tmp_path, old)
    out = run("patch", path)
    assert out.returncode == 0, out.stderr
    # The rest of the file is unchanged: putting the moved lines back gives `old`.
    assert out.stdout == BASE.replace(ARG + LABEL, OLD_COMMENT + ARG + LABEL, 1)
    assert placement(out.stdout) == []
    # Confirm-only: the script prints, SKILL.md writes on a yes.
    assert path.read_text("utf-8") == old


def test_patch_without_label_moves_before_the_npm_run(tmp_path: Path) -> None:
    old = early(BASE).replace(LABEL, "", 1)
    out = run("patch", write(tmp_path, old))
    assert out.returncode == 0, out.stderr
    assert out.stdout == BASE.replace(ARG + LABEL, OLD_COMMENT + ARG, 1)
    assert placement(out.stdout) == []


def test_patch_moves_a_bare_arg(tmp_path: Path) -> None:
    old = BASE.replace(ARG, "", 1).replace(EARLY_SLOT, EARLY_SLOT + ARG + "\n", 1)
    out = run("patch", write(tmp_path, old))
    assert (out.returncode, out.stdout) == (0, BASE), out.stderr


def test_patch_keeps_the_rest_of_a_customised_file(tmp_path: Path) -> None:
    extra = "\n# project addition\nRUN echo kept\n"
    out = run("patch", write(tmp_path, early(BASE) + extra))
    assert out.returncode == 0, out.stderr
    assert out.stdout == BASE.replace(ARG + LABEL, OLD_COMMENT + ARG + LABEL, 1) + extra


def test_nothing_to_patch_on_a_current_file(tmp_path: Path) -> None:
    out = run("patch", write(tmp_path, BASE))
    assert (out.returncode, out.stdout) == (1, "")


@pytest.mark.parametrize(
    ("mutation", "why"),
    [
        (
            lambda t: early(t).replace(ARG, "ARG CLAUDE_CODE_VERSION=latest\n", 1),
            "has a default",
        ),
        (lambda t: early(t).replace(LABEL, ARG + LABEL, 1), "declared 2 times"),
        (
            lambda t: early(t).replace(
                "@anthropic-ai/claude-code@", "@anthropic-ai/other@", 1
            ),
            "no npm RUN",
        ),
        (lambda t: early(t).replace(LABEL, LABEL + "RUN true\n", 1), "between LABEL"),
    ],
    ids=("default", "duplicate", "no-npm", "run-after-label"),
)
def test_patch_refuses(tmp_path: Path, mutation: object, why: str) -> None:
    out = run("patch", write(tmp_path, mutation(BASE)))  # type: ignore[operator]
    assert (out.returncode, out.stdout) == (3, ""), out.stderr
    assert why in out.stderr and "patch by hand" in out.stderr


@pytest.mark.parametrize(
    "args", (("check",), ("check", "x", "y"), ("fix", "x")), ids=str
)
def test_usage_errors(args: tuple[str, ...]) -> None:
    out = subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, check=False
    )
    assert (out.returncode, out.stdout) == (2, "")


def test_detector_runs_under_mawk(tmp_path: Path) -> None:
    mawk = shutil.which("mawk")
    if mawk is None:
        pytest.skip("mawk not installed")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "awk").symlink_to(mawk)
    env = {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"}
    path = write(tmp_path, early(BASE))
    assert run("check", path, env).returncode == 1
    out = run("patch", path, env)
    assert (out.returncode, out.stdout) == (
        0,
        BASE.replace(ARG + LABEL, OLD_COMMENT + ARG + LABEL, 1),
    )
    refreshed = run("patch", write(tmp_path, assemble_node(pre_271_template())), env)
    assert refreshed.returncode == 0, refreshed.stderr
    assert claude_block(refreshed.stdout) == claude_block(BASE)


def pre_271_template() -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{PRE_271_REV}:{PRE_271_PATH}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"{PRE_271_REV} not in this clone: {result.stderr.strip()}")
    return result.stdout


def test_both_patches_fix_the_pre_271_template(tmp_path: Path) -> None:
    old = assemble_node(pre_271_template())
    assert placement(old) and sudoers_guard.rule_problems(old)
    moved = run("patch", write(tmp_path, old))
    assert moved.returncode == 0, moved.stderr
    narrowed = subprocess.run(
        [
            "bash",
            str(SUDOERS_SCRIPT),
            "patch",
            str(write(tmp_path, moved.stdout, "Dockerfile.moved")),
            str(TEMPLATE_DIR / "devcontainer.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert narrowed.returncode == 0, narrowed.stderr
    assert placement(narrowed.stdout) == []
    assert sudoers_guard.rule_problems(narrowed.stdout) == []
    assert pin_guard.pin_problems(narrowed.stdout) == []


def _upgrade_section() -> str:
    text = SKILL_MD.read_text("utf-8")
    return text[text.index("## Upgrade Mode") :]


def test_skill_md_runs_the_detector_on_upgrade() -> None:
    upgrade = _upgrade_section()
    assert "early-claude-arg.sh check .devcontainer/Dockerfile" in upgrade
    assert "early-claude-arg.sh patch .devcontainer/Dockerfile" in upgrade
    for label in (
        "skipped (assembled; early claude-code arg)",
        "claude arg moved",
        "early claude-code arg, user declined",
        "early claude-code arg, patch by hand",
    ):
        assert label in upgrade, label


def test_skill_md_orders_the_dockerfile_labels() -> None:
    upgrade = _upgrade_section()
    assert (
        "in the order version pin, claude arg, uv pin, runtime copy, sudoers" in upgrade
    )
    assert (
        "skipped (assembled; version pin patched; claude arg moved; uv pin patched; "
        "runtime copy patched; sudoers narrowed)"
    ) in upgrade


def test_skill_md_tells_the_user_to_rebuild() -> None:
    upgrade = _upgrade_section()
    summary = upgrade[upgrade.index("### U5: Summary") :]
    assert "/ralph-run rebuild=true" in summary
    assert "first rebuild redoes every step once" in summary


# The pre-TASK-272 comment under "# ---- Claude ----", verbatim (TASK-274).
OLD_NPM_COMMENT = (
    "# Bumping CLAUDE_CODE_VERSION changes this layer's cache key, so the next\n"
    "# build reinstalls; the label lets `docker image inspect` report the version.\n"
)
HEADER = "# ---- Claude ----\n"


def claude_block(text: str) -> str:
    """From the Claude header through the line ending the npm RUN."""
    start = text.index(HEADER)
    end = text.index("\n", text.index("claude --version", start)) + 1
    return text[start:end]


def test_patch_refreshes_the_pre_272_claude_comment(tmp_path: Path) -> None:
    old = assemble_node(pre_271_template())
    assert claude_block(old).startswith(HEADER + OLD_NPM_COMMENT + LABEL)
    out = run("patch", write(tmp_path, old))
    assert out.returncode == 0, out.stderr
    assert claude_block(out.stdout) == claude_block(BASE)
    assert OLD_NPM_COMMENT not in out.stdout and OLD_COMMENT not in out.stdout


@pytest.mark.parametrize(
    ("old_npm", "old_arg"),
    [
        ("# project note\n", OLD_COMMENT),
        (OLD_NPM_COMMENT, OLD_COMMENT.replace("refuses one.", "refuses it.")),
        (OLD_NPM_COMMENT + "# project note\n", OLD_COMMENT),
        ("# project note\n" + OLD_NPM_COMMENT, OLD_COMMENT),
    ],
    ids=("other-npm-comment", "other-arg-comment", "note-after", "note-before"),
)
def test_patch_keeps_any_other_claude_comment(
    tmp_path: Path, old_npm: str, old_arg: str
) -> None:
    old = (
        assemble_node(pre_271_template())
        .replace(HEADER + OLD_NPM_COMMENT, HEADER + old_npm, 1)
        .replace(OLD_COMMENT + ARG, old_arg + ARG, 1)
    )
    out = run("patch", write(tmp_path, old))
    assert out.returncode == 0, out.stderr
    assert claude_block(out.stdout).startswith(HEADER + old_npm + old_arg + ARG + LABEL)
    assert placement(out.stdout) == []


def test_check_ignores_an_old_comment_over_a_placed_arg(tmp_path: Path) -> None:
    current = claude_block(BASE)
    comment = current[len(HEADER) : current.index(ARG)]
    old = BASE.replace(HEADER + comment, HEADER + OLD_NPM_COMMENT + OLD_COMMENT, 1)
    assert old != BASE
    out = run("check", write(tmp_path, old))
    assert (out.returncode, out.stdout) == (0, ""), out.stderr


def test_patch_needs_the_shipped_template(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    lone = scripts / SCRIPT.name
    shutil.copy(SCRIPT, lone)
    path = write(tmp_path, assemble_node(pre_271_template()))
    out = run("patch", path, script=lone)
    assert (out.returncode, out.stdout) == (2, ""), out.stderr
    assert "Dockerfile.base" in out.stderr
    # A comment patch leaves untouched still moves the ARG without the template.
    moved = run("patch", write(tmp_path, early(BASE), "Dockerfile.early"), script=lone)
    assert moved.returncode == 0, moved.stderr


def test_skill_md_says_the_patch_refreshes_the_old_comment() -> None:
    assert (
        "The patch also refreshes the Claude block comment when it is the old text"
        in _upgrade_section()
    )


def test_patch_keeps_crlf_line_endings(tmp_path: Path) -> None:
    old = assemble_node(pre_271_template()).replace("\n", "\r\n")
    path = tmp_path / "Dockerfile"
    path.write_bytes(old.encode("utf-8"))
    out = subprocess.run(
        ["bash", str(SCRIPT), "patch", str(path)], capture_output=True, check=False
    )
    assert out.returncode == 0, out.stderr
    text = out.stdout.decode("utf-8")
    assert text.count("\n") == text.count("\r\n")
    assert claude_block(text.replace("\r\n", "\n")) == claude_block(BASE)
