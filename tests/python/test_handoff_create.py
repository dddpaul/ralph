"""How /ralph-handoff creates a task for each destination shared-backlog state (TASK-317).

``plugins/ralph/skills/ralph-handoff/scripts/handoff-create.sh`` reads the
destination's marker (``"sharedBacklog"`` in ``.claude/ralph.json``) and its
clone switch (``git config ralph.sharedBacklog``). With the switch on it
creates through the plugin's ``shared-backlog.sh create`` and reports the ID as
final only after create returns 0; with the marker on and the switch off it
refuses and names ``enable``; with both off it keeps today's uncommitted file
with a provisional ID. Each state runs against destinations that are behind
origin, ahead of it, dirty and on a task branch.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from devcontainer_config import REPO_ROOT

HELPER = REPO_ROOT / "plugins/ralph/skills/ralph-handoff/scripts/handoff-create.sh"
SKILL = REPO_ROOT / "plugins/ralph/skills/ralph-handoff/SKILL.md"
BASH = shutil.which("bash") or "/bin/bash"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None or shutil.which("backlog") is None,
    reason="jq and the backlog CLI are needed",
)

# (marker file content or None for absent, switch value or None for unset, mode)
STATES = {
    "both-on": ('{"sharedBacklog": true}\n', "true", "protocol"),
    "marker-on-switch-unset": ('{"sharedBacklog": true}\n', None, "refuse"),
    "marker-on-switch-false": ('{"sharedBacklog": true}\n', "false", "refuse"),
    "marker-absent-switch-on": (None, "true", "protocol"),
    "marker-false-switch-on": ('{"sharedBacklog": false}\n', "true", "protocol"),
    "marker-absent-switch-unset": (None, None, "local"),
    "marker-false-switch-false": ('{"sharedBacklog": false}\n', "false", "local"),
}
MATRIX_STATES = [
    "both-on",
    "marker-on-switch-unset",
    "marker-absent-switch-on",
    "marker-absent-switch-unset",
]
SITUATIONS = ["behind", "ahead", "dirty", "task-branch"]


def git(cwd: Path, env: dict[str, str], *args: str) -> str:
    """Run git in ``cwd`` and return its stripped stdout."""
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    """An environment isolated from the host's git config, holder and run lock."""
    home = tmp_path / "home"
    home.mkdir()
    out = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("GIT_", "SHARED_BACKLOG_", "CLAUDE_"))
        and k != "RALPH_RUN_LOCK_TOKEN"
    }
    out.update(HOME=str(home), GIT_CONFIG_NOSYSTEM="1")
    for key, value in (
        ("user.name", "tester"),
        ("user.email", "t@example.invalid"),
        ("init.defaultBranch", "master"),
    ):
        subprocess.run(["git", "config", "--global", key, value], env=out, check=True)
    return out


def make_origin(tmp_path: Path, env: dict[str, str], marker: str | None) -> Path:
    """A bare origin whose master holds TASK-1 and TASK-2 and the given marker."""
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], env=env, check=True)
    (seed / "backlog/tasks").mkdir(parents=True)
    (seed / "backlog/config.yml").write_text(
        'task_prefix: "task"\nstatuses: ["To Do", "In Progress", "Done"]\n'
    )
    (seed / "x.txt").write_text("one\n")
    if marker is not None:
        (seed / ".claude").mkdir()
        (seed / ".claude/ralph.json").write_text(marker)
    git(seed, env, "init", "-q")
    for title in ("One", "Two"):
        subprocess.run(
            ["backlog", "task", "create", title],
            cwd=seed,
            env=env,
            check=True,
            capture_output=True,
        )
    git(seed, env, "add", "-A")
    git(seed, env, "commit", "-q", "-m", "init")
    git(seed, env, "push", "-q", str(origin), "master")
    return origin


def clone(origin: Path, path: Path, env: dict[str, str]) -> Path:
    git(origin.parent, env, "clone", "-q", str(origin), str(path))
    return path.resolve()


def set_switch(dest: Path, env: dict[str, str], switch: str | None) -> None:
    if switch is not None:
        git(dest, env, "config", "ralph.sharedBacklog", switch)


def backlog_create(cwd: Path, env: dict[str, str], title: str) -> None:
    subprocess.run(
        ["backlog", "task", "create", title],
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
    )


def arrange(
    situation: str, dest: Path, other: Path, env: dict[str, str]
) -> None:
    """Put ``dest`` into ``situation``; ``other`` is a second clone of origin."""
    if situation == "behind":
        backlog_create(other, env, "Pushed elsewhere")
        git(other, env, "add", "-A")
        git(other, env, "commit", "-q", "-m", "task-3: add task")
        git(other, env, "push", "-q", "origin", "master")
        git(dest, env, "fetch", "-q", "origin")
    elif situation == "ahead":
        (dest / "x.txt").write_text("two\n")
        git(dest, env, "commit", "-q", "-am", "local change")
    elif situation == "dirty":
        (dest / "x.txt").write_text("dirty\n")
        (dest / "untracked.txt").write_text("u\n")
        git(dest, env, "add", "x.txt")
        (dest / "x.txt").write_text("dirtier\n")
    elif situation == "task-branch":
        git(dest, env, "checkout", "-q", "-b", "task-9")
        (dest / "x.txt").write_text("branch\n")
        git(dest, env, "commit", "-q", "-am", "task-9: work")


def snapshot(dest: Path, env: dict[str, str]) -> tuple[str, ...]:
    """Branch, HEAD, index and working tree of ``dest``."""
    return (
        git(dest, env, "symbolic-ref", "-q", "HEAD"),
        git(dest, env, "rev-parse", "HEAD"),
        git(dest, env, "status", "--porcelain=v1", "--untracked-files=all"),
        git(dest, env, "diff", "--cached"),
        git(dest, env, "diff"),
    )


def origin_tasks(origin: Path, env: dict[str, str]) -> list[str]:
    out = git(
        origin, env, "ls-tree", "-r", "--name-only", "master", "backlog/tasks"
    )
    return out.splitlines()


def run(
    env: dict[str, str], *args: str | Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [BASH, str(HELPER), *map(str, args)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
        timeout=120,
    )


def fields(stdout: str) -> dict[str, str]:
    return dict(line.split(": ", 1) for line in stdout.splitlines() if ": " in line)


@pytest.mark.parametrize("state", list(STATES))
def test_mode_follows_the_state_table(
    tmp_path: Path, env: dict[str, str], state: str
) -> None:
    marker, switch, mode = STATES[state]
    dest = clone(make_origin(tmp_path, env, marker), tmp_path / "dest", env)
    set_switch(dest, env, switch)
    result = run(env, "mode", dest)
    assert result.stdout.strip() == mode
    assert result.returncode == (1 if mode == "refuse" else 0), result.stderr


@pytest.mark.parametrize("situation", SITUATIONS)
@pytest.mark.parametrize("state", MATRIX_STATES)
def test_create_follows_the_state_table(
    tmp_path: Path, env: dict[str, str], state: str, situation: str
) -> None:
    marker, switch, mode = STATES[state]
    origin = make_origin(tmp_path, env, marker)
    dest = clone(origin, tmp_path / "dest", env)
    other = clone(origin, tmp_path / "other", env)
    set_switch(dest, env, switch)
    arrange(situation, dest, other, env)
    before_dest = snapshot(dest, env)
    before_origin = origin_tasks(origin, env)

    result = run(env, "create", dest, "Handed off", "--ac", "first", "--ac", "second")

    if mode == "protocol":
        assert result.returncode == 0, result.stderr
        out = fields(result.stdout)
        assert out["mode"] == "protocol" and out["state"] == "final"
        assert out["path"] in origin_tasks(origin, env)
        assert out["path"] not in before_origin
        assert out["path"].startswith("backlog/tasks/" + out["id"].lower() + " - ")
        assert snapshot(dest, env) == before_dest
        body = git(origin, env, "show", f"master:{out['path']}")
        assert "- [ ] #1 first" in body and "- [ ] #2 second" in body
    elif mode == "refuse":
        assert result.returncode == 1
        assert result.stdout == ""
        assert "scripts/shared-backlog.sh enable" in result.stderr
        assert snapshot(dest, env) == before_dest
        assert origin_tasks(origin, env) == before_origin
    else:
        assert result.returncode == 0, result.stderr
        out = fields(result.stdout)
        assert out["mode"] == "local" and out["state"] == "provisional"
        assert (dest / out["path"]).is_file()
        untracked = git(dest, env, "ls-files", "--others", "--exclude-standard")
        assert out["path"] in untracked.splitlines()
        assert git(dest, env, "rev-parse", "HEAD") == before_dest[1]
        assert origin_tasks(origin, env) == before_origin


def test_protocol_reports_no_id_when_create_fails(
    tmp_path: Path, env: dict[str, str]
) -> None:
    origin = make_origin(tmp_path, env, '{"sharedBacklog": true}\n')
    dest = clone(origin, tmp_path / "dest", env)
    set_switch(dest, env, "true")
    git(dest, env, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    result = run(env, "create", dest, "Handed off")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "no task ID to report" in result.stderr
    assert list((dest / "backlog/tasks").glob("task-3 *")) == []


def test_the_skill_runs_the_helper_in_preflight_and_create() -> None:
    text = SKILL.read_text()
    helper = "${CLAUDE_PLUGIN_ROOT}/skills/ralph-handoff/scripts/handoff-create.sh"
    assert f'bash {helper} mode "$DEST"' in text
    assert f'bash {helper} create "$DEST"' in text
    assert "scripts/shared-backlog.sh enable" in text
