"""The claim lifecycle of Ralph runs in enforcing clones (TASK-315).

Every test runs the real ``shared-backlog.sh`` against a bare origin in a temp
directory. The picker reads the backlog of the current directory, so the
in-process tests ``chdir`` into the clone; the race runs two pickers as two
processes, one per clone.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_loop_shared_publish import (
    _args,
    _git,
    _origin_and_clone,
    _result,
    git_home,  # noqa: F401
    needs_tools,
)

from ralph import claims as claims_module
from ralph import loop as loop_module
from ralph import push as push_module
from ralph.args import parse, validate
from ralph.tools import OnSpawn, Tool, ToolResult
from ralph.tools._subprocess import devcontainer_prefix

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SB = str(push_module.SHARED_BACKLOG_SCRIPT)

# (title, assignees, extra backlog args) for TASK-1..6.
TASKS: list[tuple[str, list[str], list[str]]] = [
    ("Plain", [], []),
    ("Second", [], []),
    ("Taken", ["@other"], []),
    ("Shared", ["@tester", "@other"], []),
    ("Mine", ["@tester"], []),
    ("Mine with open dep", ["@tester"], ["--dep", "task-1"]),
]


def _sb(cwd: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", SB, *args], cwd=cwd, env={**os.environ, **env}, check=False, capture_output=True, text=True
    )


def _assignees(origin: Path, n: int) -> list[str]:
    """TASK-N's assignees on origin's master."""
    names = _git(origin, "ls-tree", "-r", "--name-only", "master", "backlog/tasks").splitlines()
    path = next(p for p in names if p.startswith(f"backlog/tasks/task-{n} - "))
    lines = _git(origin, "show", f"master:{path}").splitlines()
    start = lines.index("assignee:") + 1 if "assignee:" in lines else len(lines)
    out: list[str] = []
    for line in lines[start:]:
        if not line.startswith("  - "):
            break
        out.append(line.removeprefix("  - ").strip("'\""))
    return out


@pytest.fixture
def shared(git_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:  # noqa: F811
    """Origin with TASKS, and two enforcing clones a (holder @tester) and b (holder @rival)."""
    _ = git_home
    origin, a = _origin_and_clone(tmp_path)
    for title, assignees, extra in TASKS:
        argv = ["backlog", "task", "create", title, *extra]
        for who in assignees:
            argv += ["-a", who]
        subprocess.run(argv, cwd=a, check=True, capture_output=True)
    _git(a, "add", "-A")
    _git(a, "commit", "-q", "-m", "tasks")
    _git(a, "push", "-q", "origin", "master")
    b = tmp_path / "b"
    _git(tmp_path, "clone", "-q", str(origin), str(b))
    for clone, holder in ((a, "@tester"), (b, "@rival")):
        _git(clone, "config", "ralph.sharedBacklog", "true")
        _git(clone, "config", "ralph.holder", holder)
    monkeypatch.chdir(a)
    return origin, a, b


# --- the run lock ------------------------------------------------------------


@needs_tools
def test_the_run_lock_refuses_a_second_run_and_unrelated_protocol_calls(shared: tuple[Path, Path, Path]) -> None:
    """AC #1, #2 — the session holds the lock; only calls carrying its token pass."""
    _, a, _ = shared
    session = claims_module.RunSession.open(a, "tester")
    try:
        assert os.environ[claims_module.HOLDER_ENV] == "@tester"
        assert os.environ[claims_module.RUN_LOCK_TOKEN_ENV] == session.token
        with pytest.raises(claims_module.ClaimError, match="run lock is not taken"):
            claims_module.RunSession.open(a, "tester")
        unrelated = {claims_module.RUN_LOCK_TOKEN_ENV: ""}
        assert _sb(a, "sync", **unrelated).returncode == 1
        refused = _sb(a, "claim", "1", "--as", "@tester", **unrelated)
        assert refused.returncode == 1
        assert "a Ralph run holds the run lock" in refused.stderr
        assert _sb(a, "sync").returncode == 0  # the run's own call: the token is in the environment
    finally:
        session.close()
    assert claims_module.RUN_LOCK_TOKEN_ENV not in os.environ
    assert _sb(a, "sync").returncode == 0


@needs_tools
@pytest.mark.parametrize("holder", [None, "claude"])
def test_a_missing_holder_refuses_the_run(
    shared: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch, holder: str | None
) -> None:
    """AC #3 — no holder (or the generic @claude): no lock, no iteration, exit 1."""
    _, a, _ = shared
    with pytest.raises(claims_module.ClaimError, match="has no holder"):
        claims_module.RunSession.open(a, holder)
    assert not (a / ".git" / "shared-backlog-run.lock").exists()

    if holder is None:
        _git(a, "config", "--unset", "ralph.holder")
    else:
        _git(a, "config", "ralph.holder", "@claude")
    tool = _RecordingTool()
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_k: tool)
    assert loop_module.run(_args(max_iterations=1), a) == 1
    assert tool.prompts == []


# --- claiming ----------------------------------------------------------------


@needs_tools
def test_default_mode_claims_the_lowest_eligible_task_and_pushes_it(shared: tuple[Path, Path, Path]) -> None:
    """AC #4 — sync, pick, claim, push, re-check."""
    origin, a, _ = shared
    task = claims_module.claim_next(a, holder="@tester", whitelist=None)
    assert task == "TASK-1"
    assert _assignees(origin, 1) == ["@tester"]
    assert _git(origin, "rev-parse", "master") == _git(a, "rev-parse", "master")


@needs_tools
def test_a_lost_claim_moves_to_the_next_candidate(
    shared: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #4 — the rival claims TASK-1 between the pick and the claim."""
    origin, a, b = shared
    real_pick = claims_module.tasks_module.pick_next_task
    raced: list[str] = []

    def pick_then_lose(**kw: Any) -> str | None:
        task = real_pick(**kw)
        if not raced:
            raced.append(task or "")
            assert _sb(b, "claim", "1").returncode == 0
        return task

    monkeypatch.setattr(claims_module.tasks_module, "pick_next_task", pick_then_lose)
    task = claims_module.claim_next(a, holder="@tester", whitelist=None)

    assert raced == ["TASK-1"]
    assert task == "TASK-2"
    assert _assignees(origin, 1) == ["@rival"]
    assert _assignees(origin, 2) == ["@tester"]


_PICKER = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from ralph import claims
gate = Path(sys.argv[3])
while not gate.exists():
    pass
print(claims.claim_next(Path.cwd(), holder=sys.argv[2], whitelist=None))
"""


@needs_tools
def test_two_pickers_in_two_clones_racing_land_exactly_one_claim(
    shared: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    """AC #7 — both start together; TASK-1 ends with one holder, the other run takes TASK-2."""
    origin, a, b = shared
    gate = tmp_path / "go"
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", _PICKER, str(SCRIPTS), holder, str(gate)],
            cwd=clone, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        for clone, holder in ((a, "@tester"), (b, "@rival"))
    ]
    gate.touch()
    results = [proc.communicate(timeout=120) for proc in procs]

    picked = [out.strip().splitlines()[-1] for out, _ in results]
    assert sorted(picked) == ["TASK-1", "TASK-2"], results
    winner = "@tester" if picked[0] == "TASK-1" else "@rival"
    loser = "@rival" if winner == "@tester" else "@tester"
    assert _assignees(origin, 1) == [winner]
    assert _assignees(origin, 2) == [loser]


@needs_tools
def test_tasks_mode_refuses_another_holders_task_unless_forced(shared: tuple[Path, Path, Path]) -> None:
    """AC #5 — a task held by another holder, alone or beside this one."""
    origin, a, _ = shared
    for n in ("3", "4"):
        with pytest.raises(claims_module.ClaimError, match="held by @other.*--force-claim"):
            claims_module.claim_next(a, holder="@tester", whitelist=[n])
    assert _assignees(origin, 3) == ["@other"]

    assert claims_module.claim_next(a, holder="@tester", whitelist=["4"], force=True) == "TASK-4"
    assert _assignees(origin, 4) == ["@tester"]


@needs_tools
def test_default_mode_skips_a_task_with_several_assignees(shared: tuple[Path, Path, Path]) -> None:
    """AC #7 — TASK-4 is shared with @other, so the picker never claims it."""
    origin, a, _ = shared
    task = claims_module.claim_next(a, holder="@tester", whitelist=None, exclude={"TASK-1", "TASK-2"})
    assert task == "TASK-5"
    assert _assignees(origin, 4) == ["@tester", "@other"]


@needs_tools
def test_an_already_held_claim_is_accepted_after_the_checks(shared: tuple[Path, Path, Path]) -> None:
    """AC #6 — TASK-5 is ours and passes; TASK-6 is ours with an open dependency and is refused."""
    origin, a, _ = shared
    before = _git(origin, "rev-parse", "master")
    assert claims_module.claim_next(a, holder="@tester", whitelist=["5"]) == "TASK-5"
    assert _git(origin, "rev-parse", "master") == before

    with pytest.raises(claims_module.ClaimError, match="claiming TASK-6 failed"):
        claims_module.claim_next(a, holder="@tester", whitelist=["6"])
    assert _git(origin, "rev-parse", "master") == before


# --- the devcontainer ----------------------------------------------------------

# Stands in for `devcontainer exec`: like the container, the command sees only
# the --remote-env variables, never the host environment.
_FAKE_DEVCONTAINER = """#!/bin/bash
[ "$1" = exec ] || exit 64; shift
[ "$1" = --workspace-folder ] || exit 64; dir=$2; shift 2
vars=()
while [ "$1" = --remote-env ]; do vars+=("$2"); shift 2; done
cd "$dir" && exec env -i PATH="$PATH" HOME="$HOME" GIT_CONFIG_NOSYSTEM=1 "${vars[@]}" "$@"
"""


@needs_tools
def test_the_delegated_holder_claims_inside_the_container(
    shared: tuple[Path, Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #3, #7 — the container claims as the run's holder and passes the run lock."""
    origin, a, _ = shared
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "devcontainer"
    fake.write_text(_FAKE_DEVCONTAINER)
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    _git(a, "config", "ralph.holder", "@clone-default")

    session = claims_module.RunSession.open(a, "launcher")
    try:
        prefix = devcontainer_prefix(a)
        assert prefix[-4:] == [
            "--remote-env", "SHARED_BACKLOG_HOLDER=@launcher",
            "--remote-env", f"RALPH_RUN_LOCK_TOKEN={session.token}",
        ]
        inside = subprocess.run([*prefix, "bash", SB, "claim", "2"], check=False, capture_output=True, text=True)
        assert inside.returncode == 0, inside.stderr
        bare = [p for p in prefix if "RALPH_RUN_LOCK_TOKEN" not in p][:-1]
        refused = subprocess.run([*bare, "bash", SB, "sync"], check=False, capture_output=True, text=True)
        assert refused.returncode == 1
    finally:
        session.close()
    assert _assignees(origin, 2) == ["@launcher"]
    assert "SHARED_BACKLOG_HOLDER" not in " ".join(devcontainer_prefix(a))


# --- the loop ------------------------------------------------------------------


class _RecordingTool(Tool):
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.tokens: list[str | None] = []

    def run(self, prompt: str, timeout_sec: int, *, on_spawn: OnSpawn | None = None) -> ToolResult:
        _ = (timeout_sec, on_spawn)
        self.prompts.append(prompt)
        self.tokens.append(os.environ.get(claims_module.RUN_LOCK_TOKEN_ENV))
        return _result(0)


@needs_tools
def test_the_loop_claims_before_each_iteration_and_names_the_claim(
    shared: tuple[Path, Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #1, #4 — the run holds the lock throughout and each prompt names the task it claimed."""
    origin, a, _ = shared
    for name in ("RALPH_STATUS_FILE", "RALPH_HEARTBEAT_FILE", "RALPH_RUN_LOG"):
        monkeypatch.setenv(name, str(tmp_path / name))
    monkeypatch.setattr(loop_module, "ITER_SLEEP_SEC", 0)
    tool = _RecordingTool()
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_k: tool)

    rc = loop_module.run(replace(_args(max_iterations=2), push=False, tasks="1"), a)

    assert rc == 0
    assert len(tool.prompts) == 1
    assert "Execute TASK-1 " in tool.prompts[0]
    assert tool.tokens[0]
    assert _assignees(origin, 1) == ["@tester"]
    assert not (a / ".git" / "shared-backlog-run.lock").exists()


def test_force_claim_needs_tasks() -> None:
    """AC #5 — the flag parses, and only makes sense with --tasks."""
    assert parse(["--force-claim", "--tasks", "3"]).force_claim is True
    assert parse([]).force_claim is False
    assert validate(parse(["--force-claim"])) == "Error: --force-claim needs --tasks"
    assert validate(parse(["--force-claim", "--tasks", "3"])) is None
