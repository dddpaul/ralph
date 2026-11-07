"""Integrate's checks in the devcontainer, under a total timeout (TASK-313).

A run that used the devcontainer runs integrate's configured checks inside it
through ``devcontainer exec``, and the orchestrator gives the integrate call a
total timeout that kills the host process groups and the checks' process tree
in the container, then reports the state left, an interrupted merge included.

The real-script tests put a fake ``devcontainer`` on PATH. Like ``docker exec``
it starts the command outside its own process tree (a new session, reparented
away from the client), so killing the client leaves the "container" side
running; only the tag-based reap stops it. They need Linux ``/proc`` and
``setsid``.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_loop_shared_publish import (
    _args,
    _commit,
    _git,
    _origin_and_clone,
    _result,
    git_home,  # noqa: F401
    needs_tools,
    stubbed,  # noqa: F401
)

from ralph import checks_context
from ralph import loop as loop_module
from ralph import push as push_module
from ralph.tools import OnSpawn, Tool, ToolResult

_FAKE_DEVCONTAINER = """\
#!/usr/bin/env bash
# devcontainer exec --workspace-folder DIR [--remote-env K=V]... CMD...
[ "$1" = exec ] || exit 2
shift
printf '%s\\n' "exec $*" >>"$FAKE_DEVCONTAINER_LOG"
envs=''
while :; do
  case "$1" in
    --workspace-folder) shift 2 ;;
    --remote-env) envs="$envs $2"; shift 2 ;;
    *) break ;;
  esac
done
st=$(mktemp "${TMPDIR:-/tmp}/fake-devcontainer.XXXXXX"); rm -f "$st"
# The "container" side: a new session, reparented away from this client.
( setsid env $envs sh -c '"$@"; echo $? >"$0.tmp"; mv "$0.tmp" "$0"' "$st" "$@" </dev/null & )
while [ ! -f "$st" ]; do sleep 0.1; done
rc=$(cat "$st"); rm -f "$st"
exit "$rc"
"""

# Each check process appends its pid to pids.txt: the shell, and a background
# sleep it leaves behind.
_HANGING_CHECKS = "echo $$ >>{pids}; sleep 300 & echo $! >>{pids}; wait"

needs_container_sim = pytest.mark.skipif(
    shutil.which("backlog") is None
    or shutil.which("jq") is None
    or shutil.which("setsid") is None
    or not Path("/proc/self/environ").exists(),
    reason="needs the backlog CLI, jq, setsid and /proc",
)


def _alive(pid: int) -> bool:
    """``True`` while ``pid`` runs; a zombie no init has reaped yet counts as dead."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    return stat.rsplit(")", 1)[1].split()[0] != "Z"


def _pids(path: Path) -> list[int]:
    return [int(line) for line in path.read_text().split()] if path.exists() else []


def _wait_for_pids(path: Path, count: int, timeout: float = 20) -> list[int]:
    deadline = time.monotonic() + timeout
    while len(_pids(path)) < count and time.monotonic() < deadline:
        time.sleep(0.1)
    return _pids(path)


def _lock_dir(clone: Path) -> Path:
    return clone / ".git" / "shared-backlog-protocol.lock"


@pytest.fixture
def fake_devcontainer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Put the fake ``devcontainer`` first on PATH; return the log of its calls."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "devcontainer"
    fake.write_text(_FAKE_DEVCONTAINER)
    fake.chmod(0o755)
    log = tmp_path / "devcontainer.log"
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_DEVCONTAINER_LOG", str(log))
    monkeypatch.delenv("SHARED_BACKLOG_DEADLINE", raising=False)
    monkeypatch.delenv(push_module.INTEGRATE_TIMEOUT_ENV, raising=False)
    return log


def _diverged(tmp_path: Path, checks: str) -> tuple[Path, Path]:
    """An origin and a clone whose masters each carry a commit the other lacks."""
    origin, clone = _origin_and_clone(tmp_path, {"sharedBacklog": True, "checks": checks})
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(origin), str(other))
    _commit(other, "elsewhere.txt")
    _git(other, "push", "-q", "origin", "master")
    _commit(clone, "mine.txt")
    return origin, clone


# --- units ---------------------------------------------------------------------


def test_devcontainer_env_runs_the_checks_through_devcontainer_exec_with_a_tag() -> None:
    """AC #1 — the prefix is a devcontainer exec on the project, tagging what it starts."""
    tag = checks_context.new_tag()
    env = checks_context.devcontainer_env(Path("/work/proj"), tag)

    assert env["SHARED_BACKLOG_CHECKS_EXEC"].split() == [
        "devcontainer", "exec", "--workspace-folder", "/work/proj", "--remote-env", tag,
    ]
    assert tag.startswith(f"{checks_context.TAG_VAR}=")
    kill = env["SHARED_BACKLOG_CHECKS_KILL"]
    assert kill.startswith("devcontainer exec --workspace-folder /work/proj sh -c ")
    assert kill.endswith(tag)
    assert "--remote-env" not in kill  # the reaper must not carry the tag itself


def test_devcontainer_env_refuses_a_path_with_whitespace() -> None:
    with pytest.raises(ValueError, match="whitespace"):
        checks_context.devcontainer_env(Path("/work/my proj"), checks_context.new_tag())


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, push_module.DEFAULT_INTEGRATE_TIMEOUT_SEC), ("90", 90), ("0", 1800), ("soon", 1800)],
)
def test_integrate_timeout(monkeypatch: pytest.MonkeyPatch, raw: str | None, expected: int) -> None:
    if raw is None:
        monkeypatch.delenv(push_module.INTEGRATE_TIMEOUT_ENV, raising=False)
    else:
        monkeypatch.setenv(push_module.INTEGRATE_TIMEOUT_ENV, raw)
    assert push_module.integrate_timeout() == expected


class _OneCommitTool(Tool):
    def __init__(self, master: list[int]) -> None:
        self._master = master

    def run(self, prompt: str, timeout_sec: int, *, on_spawn: OnSpawn | None = None) -> ToolResult:
        _ = (prompt, timeout_sec, on_spawn)
        self._master[0] += 1
        return _result(0)


@pytest.mark.parametrize("devcontainer", [True, False])
def test_the_loop_passes_the_runs_devcontainer_to_integrate(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch, devcontainer: bool  # noqa: F811
) -> None:
    """AC #1 — integrate runs its checks in the devcontainer exactly when the run used one."""
    _ = stubbed
    master = [0]
    calls: list[dict[str, Any]] = []

    def fake_integrate(**kw: Any) -> push_module.PushOutcome:
        calls.append(kw)
        return push_module.PushOutcome("pushed", "ok", 0)

    monkeypatch.setattr(loop_module, "start_devcontainer", lambda *_a, **_k: 0)
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_k: _OneCommitTool(master))
    monkeypatch.setattr(push_module, "current_rev", lambda *_a, **_k: f"SHA{master[0]}")
    monkeypatch.setattr(push_module, "shared_backlog_enforced", lambda _root: True)
    monkeypatch.setattr(push_module, "integrate", fake_integrate)

    rc = loop_module.run(replace(_args(max_iterations=1), devcontainer=devcontainer), stubbed)

    assert rc == 0
    assert [c["devcontainer"] for c in calls] == [devcontainer]


# --- the real script, with a fake devcontainer -----------------------------------


@needs_container_sim
def test_checks_run_inside_the_devcontainer(
    git_home: Path, fake_devcontainer: Path, tmp_path: Path  # noqa: F811
) -> None:
    """AC #1 — the configured checks run through devcontainer exec; the merge lands."""
    _ = git_home
    origin, clone = _diverged(tmp_path, f"echo in-container >>{tmp_path / 'checks.log'}")

    outcome = push_module.integrate(
        project_root=clone, task_id="TASK-7", devcontainer=True, out=io.StringIO(), err=io.StringIO()
    )

    assert outcome.exit_code == 0
    calls = fake_devcontainer.read_text()
    assert f"exec --workspace-folder {clone} --remote-env {checks_context.TAG_VAR}=" in calls
    assert "sh -c echo in-container" in calls
    assert (tmp_path / "checks.log").read_text() == "in-container\n"
    assert _git(origin, "rev-parse", "master") == _git(clone, "rev-parse", "master")


@needs_container_sim
def test_the_orchestrator_timeout_kills_the_checks_in_the_container(
    git_home: Path, fake_devcontainer: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    """AC #2, #3 — on the orchestrator's timeout no check process survives; the lock is released."""
    _ = (git_home, fake_devcontainer)
    pids = tmp_path / "pids.txt"
    origin, clone = _diverged(tmp_path, _HANGING_CHECKS.format(pids=pids))
    origin_before = _git(origin, "rev-parse", "master")
    monkeypatch.setenv("SHARED_BACKLOG_DEADLINE", "300")  # only the orchestrator's timeout fires
    err = io.StringIO()

    outcome = push_module.integrate(
        project_root=clone, task_id="TASK-7", devcontainer=True, timeout_sec=5, out=io.StringIO(), err=err
    )

    assert outcome.exit_code == push_module.INTEGRATE_TIMEOUT_EXIT_CODE
    started = _pids(pids)
    assert len(started) == 2
    assert not _lock_dir(clone).exists()
    assert [p for p in started if _alive(p)] == []
    assert "ran past its 5s timeout" in err.getvalue()
    assert "not reset" in err.getvalue()
    assert _git(origin, "rev-parse", "master") == origin_before


@needs_container_sim
def test_no_check_survives_the_scripts_own_deadline_once_the_lock_is_released(
    git_home: Path, fake_devcontainer: Path, tmp_path: Path  # noqa: F811
) -> None:
    """AC #3 — the script itself stops the container side before it releases the lock."""
    _ = (git_home, fake_devcontainer)
    pids = tmp_path / "pids.txt"
    _, clone = _diverged(tmp_path, _HANGING_CHECKS.format(pids=pids))
    tag = checks_context.new_tag()
    env = {**os.environ, **checks_context.devcontainer_env(clone, tag), "SHARED_BACKLOG_DEADLINE": "4"}

    result = subprocess.run(
        ["bash", str(push_module.SHARED_BACKLOG_SCRIPT), "integrate"],
        cwd=clone, env=env, check=False, capture_output=True, text=True, timeout=120,
    )

    # The script has exited, so its EXIT trap has released the lock.
    assert result.returncode != 0
    assert "deadline" in result.stderr
    assert not _lock_dir(clone).exists()
    started = _pids(pids)
    assert len(started) == 2
    assert [p for p in started if _alive(p)] == []
    assert "check process(es) left in the devcontainer" in result.stderr
    assert "killed 0 check" not in result.stderr


@needs_tools
def test_a_timeout_reports_the_interrupted_merge_and_does_not_reset_it(
    git_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    """AC #4 — a timeout during the merge commit leaves MERGE_HEAD and HEAD as they were, and says so."""
    _ = git_home
    _, clone = _diverged(tmp_path, "true")
    head_before = _git(clone, "rev-parse", "HEAD")
    hook = clone / ".git" / "hooks" / "commit-msg"
    hook.write_text("#!/bin/sh\nsleep 300\n")
    hook.chmod(0o755)
    monkeypatch.setenv("SHARED_BACKLOG_DEADLINE", "300")
    err = io.StringIO()

    outcome = push_module.integrate(
        project_root=clone, task_id="TASK-7", timeout_sec=4, out=io.StringIO(), err=err
    )

    assert outcome.exit_code == push_module.INTEGRATE_TIMEOUT_EXIT_CODE
    assert (clone / ".git" / "MERGE_HEAD").exists()
    assert _git(clone, "rev-parse", "HEAD") == head_before
    assert "a merge is in progress" in err.getvalue()
    assert "not reset" in err.getvalue()
    assert not _lock_dir(clone).exists()
