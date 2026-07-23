"""Refinement-loop tests for ``ralph.refine.loop`` (US-005 AC #11).

Covers the loop contract with a fake tool that stands in for a real LLM call:
threshold stop (exit 0), max-iterations stop (exit 1), the exit-code contract,
the three ``--on-error`` strategies, ``--resume`` (continue + both nothing-to-do
paths), the ``summary.md`` score/delta table, ``--dry-run`` / ``--verbose``, and
the SIGTERM-forwarding signal handler (AC #10).

The fake distinguishes an author call from a reviewer call by the trailing
output-protocol instruction the composed prompt ends with, and writes a real
transcript file per call so the reused extractor reads it exactly as it would a
tee'd LLM transcript.
"""

from __future__ import annotations

import signal
import subprocess
from pathlib import Path

import pytest

from ralph.refine import loop as loop_module
from ralph.refine.args import RefineArgs
from ralph.refine.loop import _Interrupted, _SignalForwarder
from ralph.refine.roles import REVIEW_INSTRUCTION
from ralph.signals import parse_text
from ralph.tools import OnSpawn, Tool, ToolResult


# --------------------------------------------------------------------------- #
# Fake tool
# --------------------------------------------------------------------------- #
class FakeTool(Tool):
    """A scripted stand-in for the claude/opencode tool.

    Each ``run`` inspects the prompt to tell author from reviewer, writes a
    transcript file, and returns a ``ToolResult``. Author calls emit an
    ``<artifact>`` block; reviewer calls emit the next queued ``SCORE:`` +
    ``<summary>``. Per-call overrides model failures: ``*_exits`` sets a
    nonzero/timeout exit code for the Nth physical call of that role,
    ``break_*`` makes it exit 0 but omit the required tag (an extraction
    failure). A score is consumed only by a successful, non-broken reviewer call.
    """

    def __init__(
        self,
        tmp_path: Path,
        *,
        scores: list[int] | None = None,
        author_exits: dict[int, int] | None = None,
        reviewer_exits: dict[int, int] | None = None,
        break_author: set[int] | None = None,
        break_reviewer: set[int] | None = None,
    ) -> None:
        self._dir = tmp_path / "transcripts"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._scores = list(scores or [])
        self._author_exits = dict(author_exits or {})
        self._reviewer_exits = dict(reviewer_exits or {})
        self._break_author = set(break_author or ())
        self._break_reviewer = set(break_reviewer or ())
        self._author_calls = 0
        self._reviewer_calls = 0
        self.calls: list[tuple[str, str]] = []
        self.on_spawn_seen: list[OnSpawn | None] = []

    def run(
        self,
        prompt: str,
        timeout_sec: int,
        *,
        on_spawn: OnSpawn | None = None,
    ) -> ToolResult:
        _ = timeout_sec
        self.on_spawn_seen.append(on_spawn)
        if prompt.rstrip().endswith(REVIEW_INSTRUCTION):
            role, body, exit_code = "reviewer", *self._reviewer_body()
        else:
            role, body, exit_code = "author", *self._author_body()
        self.calls.append((role, prompt))
        path = self._dir / f"transcript-{len(self.calls)}.out"
        path.write_text(body, encoding="utf-8")
        return ToolResult(
            stdout_path=path, exit_code=exit_code, signals=parse_text(body)
        )

    def _author_body(self) -> tuple[str, int]:
        self._author_calls += 1
        n = self._author_calls
        if (code := self._author_exits.get(n, 0)) != 0:
            return f"author call {n} failed", code
        if n in self._break_author:
            return "author produced no artifact tags", 0
        return f"<artifact>\nARTIFACT v{n}\n</artifact>", 0

    def _reviewer_body(self) -> tuple[str, int]:
        self._reviewer_calls += 1
        n = self._reviewer_calls
        if (code := self._reviewer_exits.get(n, 0)) != 0:
            return f"reviewer call {n} failed", code
        if n in self._break_reviewer:
            return "<summary>no score line here</summary>", 0
        score = self._scores.pop(0)
        return f"SCORE: {score}\n<summary>summary {n}</summary>", 0


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #
@pytest.fixture
def roles(tmp_path: Path) -> tuple[Path, Path]:
    author = tmp_path / "author.md"
    reviewer = tmp_path / "reviewer.md"
    author.write_text("You are the AUTHOR.")
    reviewer.write_text("You are the REVIEWER.")
    return author, reviewer


def _args(
    roles: tuple[Path, Path],
    output_dir: Path,
    **over: object,
) -> RefineArgs:
    author, reviewer = roles
    base: dict[str, object] = {
        "prompt": "task text",
        "draft": "",
        "author": str(author),
        "reviewer": str(reviewer),
        "artifact_type": "md",
        "tool": "claude",
        "model": "m",
        "effort": "medium",
        "timeout": 15,
        "max_iterations": 10,
        "threshold": 8,
        "output_dir": str(output_dir),
        "on_error": "stop",
        "retry_count": 2,
        "devcontainer": False,
        "resume": False,
        "verbose": False,
        "dry_run": False,
    }
    base.update(over)
    return RefineArgs(**base)  # type: ignore[arg-type]


def _run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    args: RefineArgs,
    tool: FakeTool,
) -> int:
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_kw: tool)
    monkeypatch.setattr(loop_module, "ITER_SLEEP_SEC", 0)
    return loop_module.run(args, cwd=tmp_path)


# --------------------------------------------------------------------------- #
# Threshold stop (AC #1, #2, #3) + exit 0
# --------------------------------------------------------------------------- #
def test_threshold_stop_first_iteration_exit_0(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "iterations"
    tool = FakeTool(tmp_path, scores=[9])
    rc = _run(monkeypatch, tmp_path, _args(roles, out, threshold=8), tool)
    assert rc == 0
    assert (out / "artifact-v1.md").exists()
    assert (out / "review-v1.md").exists()
    assert (out / "final.md").read_text() == (out / "artifact-v1.md").read_text()
    assert (out / "summary.md").exists()
    assert "Iteration 1: score 9/10" in capsys.readouterr().out


def test_threshold_stop_multi_iteration_final_is_last(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
) -> None:
    out = tmp_path / "iterations"
    tool = FakeTool(tmp_path, scores=[6, 8])
    rc = _run(monkeypatch, tmp_path, _args(roles, out, threshold=8), tool)
    assert rc == 0
    assert (out / "artifact-v2.md").exists()
    assert (out / "review-v2.md").exists()
    assert (out / "final.md").read_text() == (out / "artifact-v2.md").read_text()
    # Author saw the previous artifact + full review on iteration 2 (AC #3).
    assert tool.calls[2][0] == "author"
    assert "ARTIFACT v1" in tool.calls[2][1]
    assert "SCORE: 6" in tool.calls[2][1]


def test_llm_calls_receive_on_spawn_hook(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
) -> None:
    """AC #2/#10 — every tool call is handed the signal-forwarding on_spawn."""
    out = tmp_path / "iterations"
    tool = FakeTool(tmp_path, scores=[9])
    _run(monkeypatch, tmp_path, _args(roles, out), tool)
    assert tool.on_spawn_seen and all(cb is not None for cb in tool.on_spawn_seen)


# --------------------------------------------------------------------------- #
# Max-iterations stop (AC #4) + exit 1
# --------------------------------------------------------------------------- #
def test_max_iterations_stop_exit_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "iterations"
    tool = FakeTool(tmp_path, scores=[5, 5, 5])
    rc = _run(
        monkeypatch, tmp_path, _args(roles, out, threshold=8, max_iterations=3), tool
    )
    assert rc == 1
    assert (out / "final.md").read_text() == (out / "artifact-v3.md").read_text()
    assert (out / "summary.md").exists()
    assert "max iterations" in capsys.readouterr().err.lower()


def test_max_iterations_summary_marks_threshold_not_reached(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
) -> None:
    out = tmp_path / "iterations"
    tool = FakeTool(tmp_path, scores=[5, 6])
    _run(monkeypatch, tmp_path, _args(roles, out, threshold=8, max_iterations=2), tool)
    summary = (out / "summary.md").read_text()
    assert "max iterations reached without meeting threshold" in summary


# --------------------------------------------------------------------------- #
# summary.md score/delta table (AC #5)
# --------------------------------------------------------------------------- #
def test_summary_table_scores_and_deltas(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
) -> None:
    out = tmp_path / "iterations"
    tool = FakeTool(tmp_path, scores=[6, 4, 8])
    rc = _run(monkeypatch, tmp_path, _args(roles, out, threshold=8), tool)
    assert rc == 0
    summary = (out / "summary.md").read_text()
    assert "| 1 | 6 |" in summary  # baseline row (no signed delta)
    assert "| 2 | 4 | -2 |" in summary
    assert "| 3 | 8 | +4 |" in summary
    assert "**Final score:** 8 / 10" in summary
    assert "**Threshold:** 8" in summary
    assert "**Iterations:** 3" in summary
    assert "**Result:** threshold reached" in summary


# --------------------------------------------------------------------------- #
# --on-error strategies (AC #6)
# --------------------------------------------------------------------------- #
def test_on_error_stop_halts_on_first_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
) -> None:
    out = tmp_path / "iterations"
    tool = FakeTool(tmp_path, scores=[9], author_exits={1: 2})
    rc = _run(monkeypatch, tmp_path, _args(roles, out, on_error="stop"), tool)
    assert rc == 1
    assert not (out / "artifact-v1.md").exists()
    assert not (out / "summary.md").exists()
    assert tool.calls == [("author", tool.calls[0][1])]  # stopped after 1 call


def test_on_error_timeout_124_is_governed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
) -> None:
    """AC #6 — a timeout (exit 124) is a governed failure, not a special case."""
    out = tmp_path / "iterations"
    tool = FakeTool(tmp_path, scores=[9], author_exits={1: 124})
    rc = _run(monkeypatch, tmp_path, _args(roles, out, on_error="stop"), tool)
    assert rc == 1


def test_on_error_continue_skips_failed_iteration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "iterations"
    # Iteration 1's author fails; continue → iteration 2 succeeds at threshold.
    tool = FakeTool(tmp_path, scores=[8], author_exits={1: 1})
    rc = _run(monkeypatch, tmp_path, _args(roles, out, on_error="continue"), tool)
    assert rc == 0
    assert not (out / "artifact-v1.md").exists()
    assert not (out / "review-v1.md").exists()
    assert (out / "artifact-v2.md").exists()
    assert (out / "review-v2.md").exists()
    assert "continuing" in capsys.readouterr().err


def test_on_error_retry_recovers_within_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "iterations"
    # First physical reviewer call fails; the retry (call 2) succeeds at 8.
    tool = FakeTool(tmp_path, scores=[8], reviewer_exits={1: 1})
    rc = _run(
        monkeypatch,
        tmp_path,
        _args(roles, out, on_error="retry", retry_count=2),
        tool,
    )
    assert rc == 0
    assert (out / "review-v1.md").exists()
    assert "retrying" in capsys.readouterr().err.lower()


def test_on_error_retry_exhausted_exits_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
) -> None:
    out = tmp_path / "iterations"
    # 1 initial attempt + 2 retries = 3 author calls, all failing → exit 1.
    tool = FakeTool(
        tmp_path, scores=[9], author_exits={1: 1, 2: 1, 3: 1}
    )
    rc = _run(
        monkeypatch,
        tmp_path,
        _args(roles, out, on_error="retry", retry_count=2),
        tool,
    )
    assert rc == 1
    assert sum(1 for role, _ in tool.calls if role == "author") == 3


def test_on_error_stop_on_extraction_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
) -> None:
    """AC #6 — a clean exit with no <artifact> is a governed failure too."""
    out = tmp_path / "iterations"
    tool = FakeTool(tmp_path, scores=[9], break_author={1})
    rc = _run(monkeypatch, tmp_path, _args(roles, out, on_error="stop"), tool)
    assert rc == 1


# --------------------------------------------------------------------------- #
# --resume (AC #7)
# --------------------------------------------------------------------------- #
def _seed_pair(out: Path, n: int, artifact: str, score: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / f"artifact-v{n}.md").write_text(artifact)
    (out / f"review-v{n}.md").write_text(
        f"SCORE: {score}\n<summary>summary {n}</summary>"
    )


def test_resume_continues_from_last_pair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "iterations"
    _seed_pair(out, 1, "ARTIFACT v1 seed", score=6)
    tool = FakeTool(tmp_path, scores=[8])  # the new iteration-2 reviewer score
    rc = _run(monkeypatch, tmp_path, _args(roles, out, resume=True, threshold=8), tool)
    assert rc == 0
    assert (out / "artifact-v2.md").exists()
    assert (out / "review-v2.md").exists()
    # The resumed author call was a continuation carrying the seeded context.
    assert tool.calls[0][0] == "author"
    assert "ARTIFACT v1 seed" in tool.calls[0][1]
    assert "SCORE: 6" in tool.calls[0][1]
    summary = (out / "summary.md").read_text()
    assert "| 1 | 6 |" in summary
    assert "| 2 | 8 | +2 |" in summary  # delta spans the resume boundary
    assert "Resuming from iteration 2" in capsys.readouterr().out


def test_resume_nothing_to_do_threshold_met(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "iterations"
    _seed_pair(out, 1, "ARTIFACT v1", score=9)
    tool = FakeTool(tmp_path, scores=[])
    rc = _run(monkeypatch, tmp_path, _args(roles, out, resume=True, threshold=8), tool)
    assert rc == 0
    assert tool.calls == []  # no LLM call made
    assert (out / "final.md").exists()
    assert (out / "summary.md").exists()
    assert "Nothing to do: threshold" in capsys.readouterr().out


def test_resume_nothing_to_do_all_iterations_complete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
) -> None:
    out = tmp_path / "iterations"
    _seed_pair(out, 1, "ARTIFACT v1", score=5)
    tool = FakeTool(tmp_path, scores=[])
    rc = _run(
        monkeypatch,
        tmp_path,
        _args(roles, out, resume=True, threshold=8, max_iterations=1),
        tool,
    )
    assert rc == 1
    assert tool.calls == []
    assert (out / "final.md").exists()


def test_resume_with_no_prior_pairs_starts_fresh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
) -> None:
    out = tmp_path / "iterations"
    tool = FakeTool(tmp_path, scores=[9])
    rc = _run(monkeypatch, tmp_path, _args(roles, out, resume=True, threshold=8), tool)
    assert rc == 0
    assert (out / "artifact-v1.md").exists()


# --------------------------------------------------------------------------- #
# --dry-run (AC #8) / --verbose (AC #9)
# --------------------------------------------------------------------------- #
def test_dry_run_prints_prompt_and_makes_no_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "iterations"
    tool = FakeTool(tmp_path, scores=[9])
    rc = _run(monkeypatch, tmp_path, _args(roles, out, dry_run=True), tool)
    assert rc == 0
    assert tool.calls == []
    assert not out.exists()  # dry-run returns before creating the output dir
    stdout = capsys.readouterr().out
    assert "DRY RUN" in stdout
    assert "You are the AUTHOR." in stdout
    assert "task text" in stdout


def test_verbose_prints_composed_prompts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "iterations"
    tool = FakeTool(tmp_path, scores=[9])
    _run(monkeypatch, tmp_path, _args(roles, out, verbose=True), tool)
    stdout = capsys.readouterr().out
    assert "composed prompt: author (iteration 1)" in stdout
    assert "composed prompt: reviewer (iteration 1)" in stdout


# --------------------------------------------------------------------------- #
# Input resolution
# --------------------------------------------------------------------------- #
def test_prompt_value_that_names_a_file_is_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--prompt pointing at a readable file uses the file's contents (AC parity)."""
    out = tmp_path / "iterations"
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("WRITE ABOUT AUTUMN")
    tool = FakeTool(tmp_path, scores=[9])
    _run(
        monkeypatch,
        tmp_path,
        _args(roles, out, prompt=str(prompt_file), dry_run=True),
        tool,
    )
    assert "WRITE ABOUT AUTUMN" in capsys.readouterr().out


def test_missing_author_role_file_returns_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    roles: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "iterations"
    _, reviewer = roles
    args = _args(roles, out)
    args = RefineArgs(**{**args.__dict__, "author": str(tmp_path / "ghost.md")})
    tool = FakeTool(tmp_path, scores=[9])
    rc = _run(monkeypatch, tmp_path, args, tool)
    assert rc == 1
    assert "failed to read author role" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# Signal forwarding (AC #10)
# --------------------------------------------------------------------------- #
def test_signal_forwarder_kills_registered_child() -> None:
    """A pending signal is forwarded to the active child's process group."""
    forwarder = _SignalForwarder()
    proc = subprocess.Popen(
        ["sleep", "60"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        forwarder.set_active_subprocess(proc)
        forwarder._handler(signal.SIGTERM, None)  # simulate the OS delivering it
        assert proc.wait(timeout=6) != 0  # reaped by the forwarded SIGTERM
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_signal_forwarder_raise_if_pending() -> None:
    """The handler sets a pending flag that raise_if_pending surfaces once."""
    forwarder = _SignalForwarder()
    forwarder._handler(signal.SIGINT, None)
    with pytest.raises(_Interrupted):
        forwarder.raise_if_pending()
    forwarder.raise_if_pending()  # flag cleared — second call is a no-op
