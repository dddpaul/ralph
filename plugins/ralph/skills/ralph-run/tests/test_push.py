"""Tests for post-loop origin publish (TASK-211, AC #1-#7).

Each scenario runs against real, hermetic git repositories built under
``tmp_path`` — a working repo plus a bare repo standing in for ``origin`` — so
the push path is exercised end-to-end without touching any network remote.
``ralph/push.py`` anchors every git call to ``project_root``; giving each repo
its own ``git init`` root means git's repo discovery stops there and never
walks up into the surrounding workspace checkout.

AC #7 explicitly enumerates the five scenarios covered here:
default-enabled-and-pushed, opt-out-no-push, no-origin-no-push,
no-op-loop-no-push, and push-failure-surfaced.
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pytest

from ralph import push as push_module


def _git(repo: Path, *args: str) -> str:
    """Run ``git <args>`` in ``repo`` (check=True) and return stripped stdout."""
    result = subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.email=test@ralph.local",
            "-c",
            "user.name=Ralph Test",
            *args,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _init_work_repo(path: Path) -> None:
    """Create a git repo on ``master`` with one initial commit."""
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "master")
    (path / "README").write_text("init\n", encoding="utf-8")
    _git(path, "add", "README")
    _git(path, "commit", "-q", "-m", "init")


def _init_bare_origin(path: Path) -> None:
    """Create a bare repo to stand in for the ``origin`` remote."""
    subprocess.run(
        ["git", "init", "--bare", "-q", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )


def _advance_master(path: Path, marker: str = "advance") -> None:
    """Add a commit so ``master`` moves forward."""
    (path / marker).write_text(marker, encoding="utf-8")
    _git(path, "add", marker)
    _git(path, "commit", "-q", "-m", marker)


def _origin_master_sha(bare: Path) -> str | None:
    """Return the SHA of ``master`` in the bare origin, or ``None`` if unset."""
    result = subprocess.run(
        ["git", "--git-dir", str(bare), "rev-parse", "--verify", "--quiet", "master"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or None


# --------------------------------------------------------------------------
# push_enabled — opt-out resolution (AC #1, #6)
# --------------------------------------------------------------------------


def test_push_enabled_default_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC #1 — enabled by default: cli push True, no env opt-out."""
    monkeypatch.delenv(push_module.PUSH_DISABLE_ENV, raising=False)
    assert push_module.push_enabled(True) is True


def test_push_enabled_cli_opt_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC #6 — the ``--no-push`` CLI flag (cli push False) disables push."""
    monkeypatch.delenv(push_module.PUSH_DISABLE_ENV, raising=False)
    assert push_module.push_enabled(False) is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " on "])
def test_push_enabled_env_opt_out_truthy(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """AC #6 — a truthy ``RALPH_NO_PUSH`` disables push even with cli push True."""
    monkeypatch.setenv(push_module.PUSH_DISABLE_ENV, value)
    assert push_module.push_enabled(True) is False


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "nope"])
def test_push_enabled_env_non_truthy_keeps_default(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """A non-truthy env value does not disable the default-on behavior."""
    monkeypatch.setenv(push_module.PUSH_DISABLE_ENV, value)
    assert push_module.push_enabled(True) is True


# --------------------------------------------------------------------------
# git helpers
# --------------------------------------------------------------------------


def test_current_rev_returns_sha(tmp_path: Path) -> None:
    work = tmp_path / "work"
    _init_work_repo(work)
    rev = push_module.current_rev(work, "master")
    assert rev is not None and len(rev) == 40


def test_current_rev_none_outside_git_repo(tmp_path: Path) -> None:
    """A non-git directory resolves to None (conservative 'did not advance')."""
    assert push_module.current_rev(tmp_path, "master") is None


def test_has_origin_remote_true_and_false(tmp_path: Path) -> None:
    work = tmp_path / "work"
    _init_work_repo(work)
    assert push_module.has_origin_remote(work) is False
    bare = tmp_path / "origin.git"
    _init_bare_origin(bare)
    _git(work, "remote", "add", "origin", str(bare))
    assert push_module.has_origin_remote(work) is True


# --------------------------------------------------------------------------
# maybe_push_after_loop — the five AC #7 scenarios
# --------------------------------------------------------------------------


def test_default_enabled_and_pushed(tmp_path: Path) -> None:
    """AC #2, #7 — enabled + origin + advanced master → master reaches origin."""
    work = tmp_path / "work"
    bare = tmp_path / "origin.git"
    _init_work_repo(work)
    _init_bare_origin(bare)
    _git(work, "remote", "add", "origin", str(bare))

    rev_before = push_module.current_rev(work, "master")
    _advance_master(work)
    rev_after = push_module.current_rev(work, "master")

    out, err = io.StringIO(), io.StringIO()
    outcome = push_module.maybe_push_after_loop(
        project_root=work, enabled=True, rev_before=rev_before, out=out, err=err
    )

    assert outcome.action == "pushed"
    assert outcome.exit_code == 0
    assert _origin_master_sha(bare) == rev_after
    assert err.getvalue() == ""


def test_opt_out_no_push(tmp_path: Path) -> None:
    """AC #6, #7 — opted out (enabled False): advanced master is NOT pushed."""
    work = tmp_path / "work"
    bare = tmp_path / "origin.git"
    _init_work_repo(work)
    _init_bare_origin(bare)
    _git(work, "remote", "add", "origin", str(bare))

    rev_before = push_module.current_rev(work, "master")
    _advance_master(work)

    out, err = io.StringIO(), io.StringIO()
    outcome = push_module.maybe_push_after_loop(
        project_root=work, enabled=False, rev_before=rev_before, out=out, err=err
    )

    assert outcome.action == "skipped"
    assert outcome.exit_code == 0
    assert _origin_master_sha(bare) is None  # nothing pushed
    assert err.getvalue() == ""


def test_no_origin_no_push(tmp_path: Path) -> None:
    """AC #3, #7 — no origin remote → skip cleanly, no push, no error raised."""
    work = tmp_path / "work"
    _init_work_repo(work)
    rev_before = push_module.current_rev(work, "master")
    _advance_master(work)

    out, err = io.StringIO(), io.StringIO()
    outcome = push_module.maybe_push_after_loop(
        project_root=work, enabled=True, rev_before=rev_before, out=out, err=err
    )

    assert outcome.action == "skipped"
    assert "origin" in outcome.reason
    assert outcome.exit_code == 0
    assert err.getvalue() == ""


def test_no_op_loop_no_push(tmp_path: Path) -> None:
    """AC #4, #7 — master unchanged (rev_before == rev_after) → nothing pushed."""
    work = tmp_path / "work"
    bare = tmp_path / "origin.git"
    _init_work_repo(work)
    _init_bare_origin(bare)
    _git(work, "remote", "add", "origin", str(bare))

    rev_before = push_module.current_rev(work, "master")
    # No _advance_master: the loop was a no-op.

    out, err = io.StringIO(), io.StringIO()
    outcome = push_module.maybe_push_after_loop(
        project_root=work, enabled=True, rev_before=rev_before, out=out, err=err
    )

    assert outcome.action == "skipped"
    assert "did not advance" in outcome.reason
    assert outcome.exit_code == 0
    assert _origin_master_sha(bare) is None
    assert err.getvalue() == ""


def test_push_failure_surfaced(tmp_path: Path) -> None:
    """AC #5, #7 — an attempted push that fails yields non-zero + logged error."""
    work = tmp_path / "work"
    _init_work_repo(work)
    # origin points at a path with no repo → git push fails.
    _git(work, "remote", "add", "origin", str(tmp_path / "does-not-exist.git"))

    rev_before = push_module.current_rev(work, "master")
    _advance_master(work)

    out, err = io.StringIO(), io.StringIO()
    outcome = push_module.maybe_push_after_loop(
        project_root=work, enabled=True, rev_before=rev_before, out=out, err=err
    )

    assert outcome.action == "failed"
    assert outcome.exit_code != 0
    logged = err.getvalue()
    assert "ERROR" in logged
    assert "failed" in logged


def test_rev_before_none_is_conservative_skip(tmp_path: Path) -> None:
    """A None rev_before (unresolvable pre-loop) is treated as 'did not advance'."""
    work = tmp_path / "work"
    bare = tmp_path / "origin.git"
    _init_work_repo(work)
    _init_bare_origin(bare)
    _git(work, "remote", "add", "origin", str(bare))

    out, err = io.StringIO(), io.StringIO()
    outcome = push_module.maybe_push_after_loop(
        project_root=work, enabled=True, rev_before=None, out=out, err=err
    )

    assert outcome.action == "skipped"
    assert outcome.exit_code == 0
    assert _origin_master_sha(bare) is None
