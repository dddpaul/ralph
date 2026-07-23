"""End-to-end refine test against a fake ``claude`` (US-009 AC #1).

Drives the real ``refine_orchestrator.py`` as a subprocess with a fake ``claude``
on PATH that speaks the author/reviewer protocol (``fake_refine_claude.py``). No
real LLM is contacted: the CLI, refinement loop, extractor, tool subprocess
layer, and summary writer all run for real against a deterministic climbing-score
stand-in, proving the port converges to threshold and writes ``final.{type}`` +
``summary.md`` with exit 0.

Parity with ``test_e2e_fake_claude.py`` (the coder-loop e2e): the orchestrator
runs out-of-process so PATH resolution and the real ``ClaudeTool`` subprocess
spawn are exercised, not monkeypatched. Refine is backlog-independent, so — unlike
that test — this one needs neither ``backlog`` nor a backlog project on disk.

The reused tool / subprocess / devcontainer / signal layer gets no new unit tests
here (US-009 AC #2): this e2e drives them for real end to end, and their unit
coverage already lives in ``test_tool_claude.py`` / ``test_loop_signal_interrupt.py``
/ ``test_devcontainer.py`` and the ``test_refine_loop.py`` suite.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR = (
    REPO_ROOT / "skills" / "ralph-run" / "scripts" / "refine_orchestrator.py"
)
FAKE_CLAUDE = Path(__file__).resolve().parent / "fixtures" / "fake_refine_claude.py"
SYS_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _install_claude_shim(bin_dir: Path) -> None:
    """Drop a ``claude`` script on PATH that wraps ``fake_refine_claude.py``.

    The refine loop's ``ClaudeTool`` spawns ``["claude", "--model", ...,
    "--print"]``; this shim accepts and ignores every flag, then execs the fake
    under the test interpreter so no ``uv`` resolution is needed at call time.
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    shim = bin_dir / "claude"
    shim.write_text(f'#!/bin/bash\nexec {sys.executable} {FAKE_CLAUDE} "$@"\n')
    _make_executable(shim)


def _run_refine(
    tmp_path: Path,
    *,
    artifact_type: str,
    scores: str,
    threshold: int,
    extra: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke ``refine_orchestrator.py`` with the fake ``claude`` on PATH."""
    bin_dir = tmp_path / "bin"
    _install_claude_shim(bin_dir)
    author = tmp_path / "author.md"
    reviewer = tmp_path / "reviewer.md"
    author.write_text("You are the AUTHOR. Produce the artifact.\n")
    reviewer.write_text("You are the REVIEWER. Score the artifact.\n")

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{SYS_PATH}"
    env["FAKE_REFINE_SCORES"] = scores
    env["FAKE_REFINE_STATE"] = str(tmp_path / "state")

    argv = [
        sys.executable,
        str(ORCHESTRATOR),
        "--prompt",
        "Write a short note about autumn.",
        "--author",
        str(author),
        "--reviewer",
        str(reviewer),
        "--type",
        artifact_type,
        "--threshold",
        str(threshold),
        "--max-iterations",
        "5",
        "--timeout",
        "1",
        "--output-dir",
        str(tmp_path / "iterations"),
        *(extra or []),
    ]
    return subprocess.run(
        argv, env=env, capture_output=True, text=True, timeout=120
    )


@pytest.mark.parametrize("artifact_type", ["md", "puml"])
def test_refine_converges_to_threshold_exit_0(
    tmp_path: Path, artifact_type: str
) -> None:
    """AC #1 — climbing scores 6→7→9 converge at threshold 8 on iteration 3.

    Parametrized over ``--type`` to prove the terminal artifact honors
    ``final.{type}`` (not a hard-coded ``.md``).
    """
    out = tmp_path / "iterations"
    ext = artifact_type

    proc = _run_refine(
        tmp_path, artifact_type=artifact_type, scores="6,7,9", threshold=8
    )

    assert proc.returncode == 0, (
        f"refine exited {proc.returncode}\n--stdout--\n{proc.stdout}\n"
        f"--stderr--\n{proc.stderr}"
    )
    # Converged on the third iteration (6, 7 < 8 ≤ 9), and did not over-run.
    assert "Threshold 8 reached at iteration 3" in proc.stdout
    for n in (1, 2, 3):
        assert (out / f"artifact-v{n}.{ext}").exists(), proc.stdout
        assert (out / f"review-v{n}.md").exists(), proc.stdout
        assert f"Iteration {n}: score" in proc.stdout
    assert not (out / f"artifact-v4.{ext}").exists()

    # final.{type} is the terminal (iteration-3) artifact, byte-for-byte.
    final = out / f"final.{ext}"
    assert final.exists()
    assert final.read_text() == (out / f"artifact-v3.{ext}").read_text()
    assert "# Fake artifact v3" in final.read_text()

    # summary.md carries the score/delta table and the terminal result block.
    summary = (out / "summary.md").read_text()
    assert "| 1 | 6 |" in summary
    assert "| 2 | 7 | +1 |" in summary
    assert "| 3 | 9 | +2 |" in summary
    assert "**Final score:** 9 / 10" in summary
    assert "**Threshold:** 8" in summary
    assert "**Iterations:** 3" in summary
    assert "**Result:** threshold reached" in summary


def test_refine_converges_first_iteration(tmp_path: Path) -> None:
    """A first-iteration threshold hit still writes final + summary and exits 0."""
    out = tmp_path / "iterations"

    proc = _run_refine(tmp_path, artifact_type="md", scores="9", threshold=8)

    assert proc.returncode == 0, proc.stderr
    assert "Threshold 8 reached at iteration 1" in proc.stdout
    assert (out / "final.md").read_text() == (out / "artifact-v1.md").read_text()
    assert not (out / "artifact-v2.md").exists()
    summary = (out / "summary.md").read_text()
    assert "**Iterations:** 1" in summary
    assert "**Result:** threshold reached" in summary
