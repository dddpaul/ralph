"""The devcontainer's sudoers rule for ``node`` (TASK-271).

``init-firewall.sh`` is the only isolation inside the container, and Ralph runs
``claude --dangerously-skip-permissions`` there. The rule used to allow
``/bin/chown`` with any arguments, so ``node`` could take ownership of the
root-owned, sudo-allowed firewall script, rewrite it and run it as root. The
only chown the image needs is the one ``postCreateCommand`` runs, so the rule
grants exactly that invocation.

A ``:`` in a sudoers argument must be escaped as ``\\:`` — unescaped, the file is
a syntax error, and a broken ``sudoers.d`` file can disable sudo altogether. The
``RUN`` step therefore ends with ``visudo -cf`` so a malformed rule fails the
build instead of the container.

The rule is checked as the build writes it: the ``echo`` runs under ``sh``, so
the assertions see the escaping after shell quoting, not the Dockerfile source.
Mutated Dockerfiles show the checks are not vacuous.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import BOTH_IDS, LIVE_DIR, TEMPLATE_DIR, each_copy, load_jsonc

DOCKERFILES = (LIVE_DIR / "Dockerfile", TEMPLATE_DIR / "Dockerfile.base")
each_dockerfile = pytest.mark.parametrize("path", DOCKERFILES, ids=BOTH_IDS)
SUDOERS = "/etc/sudoers.d/node-firewall"
FIREWALL = "/usr/local/bin/init-firewall.sh"
CHOWN = "/bin/chown node\\:node /workspace/.venv"
NARROW_ECHO = f'echo "node ALL=(root) NOPASSWD: {FIREWALL}, {CHOWN}"'
BARE_ECHO = f'echo "node ALL=(root) NOPASSWD: {FIREWALL}, /bin/chown"'
UNESCAPED_ECHO = NARROW_ECHO.replace("node\\:node", "node:node")
RULE = re.compile(r"^node ALL=\(root\) NOPASSWD: (.+)$")
VISUDO = shutil.which("visudo") or next(
    (p for p in ("/usr/sbin/visudo", "/sbin/visudo") if Path(p).exists()), None
)
needs_visudo = pytest.mark.skipif(VISUDO is None, reason="visudo not installed")


def sudoers_step(text: str) -> str:
    """The single ``RUN`` instruction that writes the sudoers file, continuations joined."""
    joined = re.sub(r"\\\n", " ", text)
    steps = [line.strip() for line in joined.splitlines() if SUDOERS in line]
    assert len(steps) == 1, f"expected one step writing {SUDOERS}: {steps}"
    return steps[0]


def written_rule(text: str) -> str:
    """The sudoers line exactly as the build's ``echo`` writes it."""
    match = re.search(
        r'(echo "(?:[^"\\]|\\.)*") > ' + re.escape(SUDOERS), sudoers_step(text)
    )
    assert match, f"no echo into {SUDOERS}"
    result = subprocess.run(
        ["sh", "-c", match.group(1)], capture_output=True, text=True, check=True
    )
    return result.stdout.rstrip("\n")


def rule_problems(text: str) -> list[str]:
    """Every way the Dockerfile's sudoers step grants more than it should or can break."""
    problems: list[str] = []
    rule = written_rule(text)
    match = RULE.match(rule)
    if not match:
        return [f"rule is not a single NOPASSWD grant to node as root: {rule!r}"]
    commands = match.group(1).split(", ")
    if commands != [FIREWALL, CHOWN]:
        problems.append(f"node must be granted exactly {[FIREWALL, CHOWN]}: {commands}")
    step = sudoers_step(text)
    if f"chmod 0440 {SUDOERS}" not in step:
        problems.append("the sudoers file must be chmod 0440")
    if not step.endswith(f"&& visudo -cf {SUDOERS}"):
        problems.append(f"the step must end with visudo -cf {SUDOERS}")
    return problems


def visudo_check(rule: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run ``visudo -cf`` on a file holding ``rule``, as the build does."""
    target = tmp_path / "node-firewall"
    target.write_text(rule + "\n", "utf-8")
    assert VISUDO is not None
    return subprocess.run(
        [VISUDO, "-cf", str(target)], capture_output=True, text=True, check=False
    )


@each_dockerfile
def test_rule_grants_only_the_firewall_and_the_venv_chown(path: Path) -> None:
    assert rule_problems(path.read_text("utf-8")) == []


@each_dockerfile
def test_colon_reaches_the_file_escaped(path: Path) -> None:
    """``sh`` keeps ``\\:`` inside double quotes, so sudoers receives the escape."""
    assert "node\\:node" in written_rule(path.read_text("utf-8"))


@each_copy
def test_post_create_chown_is_the_granted_one(path: Path) -> None:
    """``postCreateCommand`` must run exactly the chown the rule allows, or sudo refuses it."""
    granted = CHOWN.removeprefix("/bin/").replace("\\:", ":")
    assert f"sudo {granted}" in load_jsonc(path)["postCreateCommand"]


@needs_visudo
@each_dockerfile
def test_visudo_accepts_the_rule(path: Path, tmp_path: Path) -> None:
    result = visudo_check(written_rule(path.read_text("utf-8")), tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("echo", "expected"),
    [(BARE_ECHO, "exactly"), (UNESCAPED_ECHO, "exactly")],
    ids=("bare-chown", "unescaped-colon"),
)
def test_broad_or_broken_rule_is_flagged(echo: str, expected: str) -> None:
    text = (TEMPLATE_DIR / "Dockerfile.base").read_text("utf-8")
    assert NARROW_ECHO in text
    problems = rule_problems(text.replace(NARROW_ECHO, echo))
    assert any(expected in p for p in problems), problems


def test_missing_visudo_check_is_flagged() -> None:
    text = (TEMPLATE_DIR / "Dockerfile.base").read_text("utf-8")
    old = text.replace(f" \\\n && visudo -cf {SUDOERS}", "")
    assert old != text
    assert any("visudo" in p for p in rule_problems(old))


@needs_visudo
def test_visudo_rejects_an_unescaped_colon(tmp_path: Path) -> None:
    """The reason for the escape, and for running visudo at build time."""
    text = (TEMPLATE_DIR / "Dockerfile.base").read_text("utf-8")
    rule = written_rule(text.replace(NARROW_ECHO, UNESCAPED_ECHO))
    result = visudo_check(rule, tmp_path)
    assert result.returncode != 0
    assert "syntax error" in result.stdout + result.stderr
