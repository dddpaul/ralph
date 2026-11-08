"""Publishing through shared-backlog integrate in enforcing clones (TASK-312).

A clone with ``ralph.sharedBacklog`` true publishes each iteration that
advanced master and did not stop the run (a timed-out or on-error=continue one
too, TASK-337) through ``shared-backlog.sh integrate --task N``, and once more
at the end of the run; a failed publish stops the run. The stubbed tests
pin the loop wiring; the last ones run the real script against a bare origin,
where ``enable`` sets the switch.
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import ralph_orchestrator
from ralph import loop as loop_module
from ralph import preflight
from ralph import push as push_module
from ralph.args import ParsedArgs
from ralph.signals import IterationSignals
from ralph.status import StatusFile
from ralph.tools import OnSpawn, Tool, ToolResult
from ralph.tools._subprocess import TIMEOUT_EXIT_CODE


def _args(**over: Any) -> ParsedArgs:
    base = ParsedArgs(
        tool="claude",
        model="claude-opus-5",
        effort="max",
        timeout="15",
        on_error="continue",
        retry_count=0,
        log_file="",
        prompt_file="",
        tasks="",
        block_end_buffer_min=0,
        devcontainer=False,
        max_iterations=3,
    )
    return replace(base, **over)


def _result(exit_code: int) -> ToolResult:
    return ToolResult(
        stdout_path=Path("/tmp/ralph-shared-publish-test.out"),
        exit_code=exit_code,
        signals=IterationSignals(task_summary_count=1, complete=False, error_text=None),
    )


class _Master:
    """A fake master ref the scripted tool advances."""

    def __init__(self) -> None:
        self.sha = 0

    def rev(self, *_a: Any, **_k: Any) -> str:
        return f"SHA{self.sha}"


class _AdvancingTool(Tool):
    """Each run returns the next exit code and advances master when told to."""

    def __init__(self, master: _Master, plan: list[tuple[int, bool]]) -> None:
        self._master = master
        self._plan = plan
        self.runs = 0

    def run(self, prompt: str, timeout_sec: int, *, on_spawn: OnSpawn | None = None) -> ToolResult:
        _ = (prompt, timeout_sec, on_spawn)
        exit_code, advance = self._plan[self.runs]
        self.runs += 1
        if advance:
            self._master.sha += 1
        return _result(exit_code)


@pytest.fixture
def stubbed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    picks = iter(["TASK-1", "TASK-2", "TASK-3", "TASK-4"])
    monkeypatch.setattr(loop_module.tasks_module, "pick_next_task", lambda **_: next(picks))
    # An enforcing run claims its task first (TASK-315); here the claim is the stubbed pick.
    monkeypatch.setattr(loop_module.claims_module, "claim_next", lambda *_a, **_k: next(picks))
    monkeypatch.setattr(loop_module.tasks_module, "count_remaining", lambda *_a, **_k: 0)
    monkeypatch.setattr(loop_module.tasks_module, "done_task_ids", list)
    monkeypatch.setattr(loop_module.tasks_module, "current_in_progress_task", lambda: None)
    monkeypatch.setattr(loop_module.tasks_module, "fetch_task", lambda _tid: None)
    monkeypatch.setattr(loop_module, "ITER_SLEEP_SEC", 0)
    monkeypatch.setenv("RALPH_STATUS_FILE", str(tmp_path / "status.json"))
    monkeypatch.setenv("RALPH_HEARTBEAT_FILE", str(tmp_path / "hb"))
    monkeypatch.setenv("RALPH_RUN_LOG", str(tmp_path / "run.log"))
    monkeypatch.delenv(push_module.PUSH_DISABLE_ENV, raising=False)
    monkeypatch.setattr(push_module, "local_state", lambda *_a, **_k: "local master at SHA")
    return tmp_path


def _wire(
    monkeypatch: pytest.MonkeyPatch,
    plan: list[tuple[int, bool]],
    *,
    enforced: bool = True,
    integrate_rc: int = 0,
) -> tuple[_AdvancingTool, list[str | None], list[int]]:
    master = _Master()
    tool = _AdvancingTool(master, plan)
    integrates: list[str | None] = []
    pushes: list[int] = []

    def fake_integrate(*, project_root: Path, task_id: str | None, **_kw: Any) -> push_module.PushOutcome:
        _ = project_root
        integrates.append(task_id)
        if integrate_rc:
            return push_module.PushOutcome("failed", "integrate failed", integrate_rc)
        return push_module.PushOutcome("pushed", "ok", 0)

    def fake_push(**_kw: Any) -> push_module.PushOutcome:
        pushes.append(1)
        return push_module.PushOutcome("skipped", "stub", 0)

    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_k: tool)
    monkeypatch.setattr(push_module, "current_rev", master.rev)
    monkeypatch.setattr(push_module, "shared_backlog_enforced", lambda _root: enforced)
    monkeypatch.setattr(push_module, "integrate", fake_integrate)
    monkeypatch.setattr(push_module, "maybe_push_after_loop", fake_push)
    fake_session(monkeypatch)
    return tool, integrates, pushes


class _FakeSession:
    holder = "@tester"

    def close(self) -> None:
        pass


def fake_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand in for the run lock of an enforcing run (TASK-315)."""
    monkeypatch.setattr(loop_module.claims_module.RunSession, "open", lambda *_a: _FakeSession())


def test_integrate_runs_after_each_iteration_that_advanced_master(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #1 — one integrate per advancing iteration, none for the idle one, no extra at the end."""
    _, integrates, pushes = _wire(monkeypatch, [(0, True), (0, False), (0, True)])

    rc = loop_module.run(_args(), stubbed)

    assert rc == 0
    assert integrates == ["TASK-1", "TASK-3"]
    assert pushes == []  # an enforcing clone never runs the plain git push


def test_end_of_run_integrate_covers_an_advance_no_iteration_published(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #1 — a failed iteration that stopped the run and still moved master is published at the end."""
    _, integrates, _ = _wire(monkeypatch, [(0, True), (1, True)], integrate_rc=0)

    loop_module.run(_args(max_iterations=2, on_error="stop"), stubbed)

    assert integrates == ["TASK-1", "TASK-2"]


def _record_claims(monkeypatch: pytest.MonkeyPatch, events: list[str]) -> None:
    claim = loop_module.claims_module.claim_next

    def recording_claim(*a: Any, **k: Any) -> str | None:
        task = claim(*a, **k)
        events.append(f"claim {task}")
        return task

    monkeypatch.setattr(loop_module.claims_module, "claim_next", recording_claim)


@pytest.mark.parametrize("exit_code", [TIMEOUT_EXIT_CODE, 1])
def test_a_failed_iteration_that_moved_master_is_published_before_the_next_claim(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int
) -> None:
    """TASK-337 AC #1, #2 — a timed-out or on-error=continue iteration publishes like a successful one."""
    _, integrates, _ = _wire(monkeypatch, [(exit_code, True), (0, False)])
    events: list[str] = []
    _record_claims(monkeypatch, events)
    integrate = push_module.integrate

    def recording_integrate(**kw: Any) -> push_module.PushOutcome:
        events.append(f"integrate {kw['task_id']}")
        return integrate(**kw)

    monkeypatch.setattr(push_module, "integrate", recording_integrate)

    rc = loop_module.run(_args(max_iterations=2, on_error="continue"), stubbed)

    assert rc == 1  # the failed iteration still fails the run
    assert integrates == ["TASK-1"]
    assert events == ["claim TASK-1", "integrate TASK-1", "claim TASK-2"]


@pytest.mark.parametrize("exit_code", [TIMEOUT_EXIT_CODE, 1])
def test_a_failed_iteration_that_did_not_move_master_publishes_nothing(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int
) -> None:
    """TASK-337 AC #3."""
    tool, integrates, _ = _wire(monkeypatch, [(exit_code, False), (exit_code, False)])

    loop_module.run(_args(max_iterations=2, on_error="continue"), stubbed)

    assert tool.runs == 2
    assert integrates == []


@pytest.mark.parametrize("exit_code", [TIMEOUT_EXIT_CODE, 1])
def test_a_failed_publish_after_a_failed_iteration_ends_the_run(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], exit_code: int
) -> None:
    """TASK-337 AC #4 — no next iteration and no end-of-run retry."""
    tool, integrates, _ = _wire(monkeypatch, [(exit_code, True), (0, True)], integrate_rc=2)

    rc = loop_module.run(_args(max_iterations=2, on_error="continue"), stubbed)

    assert rc == 2
    assert tool.runs == 1
    assert integrates == ["TASK-1"]
    assert "end-of-run publish is not attempted" in capsys.readouterr().err


def test_failed_publish_stops_the_run_even_with_on_error_continue(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC #2 — no next iteration, no final retry, the run exits with the script's code."""
    tool, integrates, _ = _wire(monkeypatch, [(0, True), (0, True), (0, True)], integrate_rc=2)

    rc = loop_module.run(_args(on_error="continue"), stubbed)

    assert rc == 2
    assert tool.runs == 1
    assert integrates == ["TASK-1"]
    err = capsys.readouterr().err
    assert "Publishing TASK-1 after iteration 1 failed (exit 2); local master at SHA" in err
    assert "end-of-run publish is not attempted" in err
    status = StatusFile.model_validate_json((stubbed / "status.json").read_text())
    assert status.state == "failed"
    assert "Publishing TASK-1 after iteration 1 failed" in status.errors[-1].message


def test_no_push_in_an_enforcing_clone_publishes_nothing(stubbed: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC #3 — the opted-out single-task run neither integrates nor pushes the work."""
    _, integrates, pushes = _wire(monkeypatch, [(0, True)])

    rc = loop_module.run(_args(push=False, tasks="1", max_iterations=1), stubbed)

    assert rc == 0
    assert integrates == []
    assert pushes == []


def test_a_clone_that_does_not_enforce_keeps_the_end_of_run_push(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #5 — no integrate, one end-of-run push."""
    _, integrates, pushes = _wire(monkeypatch, [(0, True), (0, True)], enforced=False)

    loop_module.run(_args(max_iterations=2), stubbed)

    assert integrates == []
    assert pushes == [1]


def _refusal_status(path: Path) -> StatusFile:
    status = StatusFile.model_validate_json(path.read_text())
    assert status.state == "failed"
    assert status.exit_code == 1
    assert status.completed_at is not None
    return status


def test_a_prompt_file_refusal_writes_a_failed_status(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """TASK-337 AC #5 — the refusal message lands in the status file."""
    _wire(monkeypatch, [])
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Pick any task.\n")

    assert loop_module.run(_args(prompt_file=str(prompt)), stubbed) == 1

    status = _refusal_status(stubbed / "status.json")
    assert "--prompt-file in a clone that enforces the shared-backlog protocol" in status.errors[0].message


def test_a_refused_run_lock_writes_a_failed_status(stubbed: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """TASK-337 AC #5 — a holder or run-lock refusal is recorded the same way."""
    _wire(monkeypatch, [])

    def refuse(*_a: Any) -> None:
        raise loop_module.claims_module.ClaimError("the run has no holder")

    monkeypatch.setattr(loop_module.claims_module.RunSession, "open", refuse)

    assert loop_module.run(_args(), stubbed) == 1

    assert _refusal_status(stubbed / "status.json").errors[0].message == "the run has no holder"


def test_a_refusal_leaves_a_live_runs_status_alone(stubbed: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """TASK-337 AC #5 — the run that holds the lock stays visible to /ralph-status."""
    _wire(monkeypatch, [])
    live = subprocess.Popen(["sleep", "30"])
    try:
        path = stubbed / "status.json"
        running = loop_module._initial_status(_args(), 900)  # pyright: ignore[reportPrivateUsage]
        running.pid = live.pid
        running.write_atomic(path)
        before = path.read_bytes()

        loop_module.write_refusal_status(_args(), stubbed, "the run lock is not taken", 1)

        assert path.read_bytes() == before
    finally:
        live.kill()
        live.wait()

    loop_module.write_refusal_status(_args(), stubbed, "the run lock is not taken", 1)
    assert _refusal_status(path).errors[0].message == "the run lock is not taken"


@pytest.mark.parametrize(
    ("enforced", "enabled", "tasks", "refused"),
    [
        (True, False, [], True),
        (True, False, ["1", "2"], True),
        (True, False, ["1"], False),
        (True, True, [], False),
        (False, False, [], False),
    ],
)
def test_no_push_refusal(enforced: bool, enabled: bool, tasks: list[str], refused: bool) -> None:
    """AC #3, #4 — only an enforcing clone's opted-out run without exactly one task is refused."""
    result = push_module.no_push_refusal(enforced=enforced, enabled=enabled, task_whitelist=tasks)
    assert (result is not None) is refused


def test_orchestrator_refuses_no_push_without_one_task(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """AC #4 — the refusal comes before the loop starts."""
    monkeypatch.setenv("RALPH_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(push_module, "shared_backlog_enforced", lambda _root: True)
    monkeypatch.setenv("RALPH_STATUS_FILE", str(tmp_path / "status.json"))
    monkeypatch.setattr(loop_module.tasks_module, "count_remaining", lambda *_a, **_k: 0)
    started: list[int] = []
    monkeypatch.setattr(ralph_orchestrator, "run_loop", lambda *_a: started.append(1) or 0)

    assert ralph_orchestrator.main(["--no-push", "--tasks", "1,2"]) == 1
    assert "needs --tasks naming exactly one task" in capsys.readouterr().err
    assert started == []
    assert "needs --tasks naming exactly one task" in _refusal_status(tmp_path / "status.json").errors[0].message

    monkeypatch.setenv(push_module.PUSH_DISABLE_ENV, "1")
    assert ralph_orchestrator.main([]) == 1
    assert started == []

    assert ralph_orchestrator.main(["--tasks", "1"]) == 0
    assert started == [1]


@pytest.mark.parametrize(
    ("argv", "rc"),
    [(["--no-push"], 1), (["--no-push", "--tasks", "1,2"], 1), (["--no-push", "--tasks", "1"], 0), ([], 0)],
)
def test_preflight_check_no_push(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], argv: list[str], rc: int
) -> None:
    """AC #4 — the ralph-run preflight refuses the same runs with an ERROR line."""
    monkeypatch.delenv(push_module.PUSH_DISABLE_ENV, raising=False)
    monkeypatch.setattr(preflight, "_git_stdout", lambda *_a: "true")
    tasks = argv[argv.index("--tasks") + 1] if "--tasks" in argv else ""

    assert preflight._check_no_push("--no-push" in argv, tasks, False) == rc  # pyright: ignore[reportPrivateUsage]
    out = capsys.readouterr().out
    assert ("ERROR: --no-push (or RALPH_NO_PUSH)" in out) is (rc == 1)


@pytest.mark.parametrize(
    ("detail", "klass"),
    [
        (" ! [rejected]        master -> master (fetch first)", "non-fast-forward"),
        ("remote: Permission denied to bot.\nfatal: unable to access 'https://x/'", "auth"),
        ("fatal: Could not read from remote repository.", "unreachable"),
        ("error: failed to push some refs to '/o.git'", "hook"),
        (" ! [remote rejected] master -> master (pre-receive hook declined)", "hook"),
        (" ! [remote rejected] master -> master (protected branch)", "rejected"),
    ],
)
def test_classify_push_failure(detail: str, klass: str) -> None:
    """AC #5 — the same classes shared-backlog.sh names."""
    assert push_module.classify_push_failure(detail) == klass


# --- real git and the real shared-backlog.sh -------------------------------


@pytest.fixture
def git_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isolate git from the user's config and the host's shared-backlog variables."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "RALPH_RUN_LOCK_TOKEN", "SHARED_BACKLOG_HOLDER",
                 "SHARED_BACKLOG_CHECKS", "SHARED_BACKLOG_CHECKS_EXEC"):
        monkeypatch.delenv(name, raising=False)
    for key, value in (("user.name", "tester"), ("user.email", "t@example.invalid"),
                       ("init.defaultBranch", "master"), ("commit.gpgsign", "false")):
        _git(home, "config", "--global", key, value)
    return home


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _commit(repo: Path, name: str) -> None:
    (repo / name).write_text(name + "\n", encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", name)


def _origin_and_clone(tmp_path: Path, marker: dict[str, Any] | None = None) -> tuple[Path, Path]:
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    _git(tmp_path, "init", "-q", "--bare", str(origin))
    (seed / "backlog").mkdir(parents=True)
    (seed / "backlog" / "config.yml").write_text('task_prefix: "task"\nstatuses: ["To Do", "In Progress", "Done"]\n')
    for sub in ("tasks", "drafts", "completed", "archive/tasks", "docs", "decisions"):
        (seed / "backlog" / sub).mkdir(parents=True)
        (seed / "backlog" / sub / ".gitkeep").touch()
    (seed / ".claude").mkdir()
    (seed / ".claude" / "ralph.json").write_text(json.dumps(marker or {"sharedBacklog": True, "checks": "true"}))
    _git(seed, "init", "-q")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-q", "-m", "init")
    _git(seed, "remote", "add", "origin", str(origin))
    _git(seed, "push", "-q", "origin", "master")
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", str(origin), str(clone))
    return origin, clone


def _enable(clone: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(push_module.SHARED_BACKLOG_SCRIPT), "enable", "--holder", "@tester"],
        cwd=clone, check=False, capture_output=True, text=True,
    )


needs_tools = pytest.mark.skipif(
    shutil.which("backlog") is None or shutil.which("jq") is None, reason="needs the backlog CLI and jq"
)


class _CommittingTool(Tool):
    def __init__(self, repo: Path) -> None:
        self._repo = repo
        self.runs = 0

    def run(self, prompt: str, timeout_sec: int, *, on_spawn: OnSpawn | None = None) -> ToolResult:
        _ = (prompt, timeout_sec, on_spawn)
        self.runs += 1
        _commit(self._repo, f"work-{self.runs}.txt")
        return _result(0)


@needs_tools
def test_enforcing_clone_publishes_each_iteration_through_integrate(
    git_home: Path, stubbed: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC #1 — enable sets the switch; each iteration's work reaches origin by a merge."""
    _ = git_home
    origin, clone = _origin_and_clone(tmp_path)
    assert _enable(clone).returncode == 0
    assert push_module.shared_backlog_enforced(clone) is True
    (clone / ".git" / "hooks" / "pre-push").unlink()  # the plugin shim needs an installed plugin
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(origin), str(other))
    _commit(other, "elsewhere.txt")
    _git(other, "push", "-q", "origin", "master")
    tool = _CommittingTool(clone)
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_k: tool)

    rc = loop_module.run(_args(max_iterations=2), clone)

    assert rc == 0
    assert tool.runs == 2
    origin_master = _git(origin, "rev-parse", "master")
    assert origin_master == _git(clone, "rev-parse", "master")
    log = _git(origin, "log", "--format=%s", "master")
    assert "task-1: merge origin/master" in log
    assert "work-2.txt" in log


@needs_tools
def test_enforcing_clone_stops_on_a_failed_integrate(
    git_home: Path, stubbed: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC #2 — checks failing on the merged tree stop the run; origin keeps its master."""
    _ = git_home
    origin, clone = _origin_and_clone(tmp_path, {"sharedBacklog": True, "checks": "false"})
    assert _enable(clone).returncode == 0
    (clone / ".git" / "hooks" / "pre-push").unlink()
    origin_before = _git(origin, "rev-parse", "master")
    tool = _CommittingTool(clone)
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_k: tool)

    rc = loop_module.run(_args(max_iterations=3, on_error="continue"), clone)

    assert rc == 1
    assert tool.runs == 1
    assert _git(origin, "rev-parse", "master") == origin_before


def test_failed_plain_push_names_its_class(git_home: Path, tmp_path: Path) -> None:
    """AC #5 — a non-fast-forward rejection and a pre-push hook refusal are named."""
    _ = git_home
    origin, clone = _origin_and_clone(tmp_path)
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(origin), str(other))
    _commit(other, "elsewhere.txt")
    _git(other, "push", "-q", "origin", "master")
    before = _git(clone, "rev-parse", "master")
    _commit(clone, "mine.txt")

    err = io.StringIO()
    outcome = push_module.maybe_push_after_loop(
        project_root=clone, enabled=True, rev_before=before, out=io.StringIO(), err=err
    )
    assert outcome.failure_class == "non-fast-forward"
    assert "(non-fast-forward, exit" in err.getvalue()

    _git(clone, "pull", "-q", "--no-rebase", "origin", "master")
    hook = clone / ".git" / "hooks" / "pre-push"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    outcome = push_module.maybe_push_after_loop(
        project_root=clone, enabled=True, rev_before=before, out=io.StringIO(), err=io.StringIO()
    )
    assert outcome.failure_class == "hook"

    hook.unlink()
    _git(clone, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    outcome = push_module.maybe_push_after_loop(
        project_root=clone, enabled=True, rev_before=before, out=io.StringIO(), err=io.StringIO()
    )
    assert outcome.failure_class == "unreachable"
