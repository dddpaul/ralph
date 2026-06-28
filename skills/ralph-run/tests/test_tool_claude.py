"""Unit tests for ``ralph/tools/claude.py`` (US-004 AC #7, #8, plus argv shape)."""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from ralph.tools import claude as claude_tool


def test_argv_without_devcontainer_starts_with_claude() -> None:
    tool = claude_tool.ClaudeTool(model="claude-opus-4-8", effort="max")
    argv = tool.build_argv()
    assert argv[0] == "claude"
    assert "--model" in argv
    assert "claude-opus-4-8" in argv
    assert "--effort" in argv
    assert "max" in argv
    assert "--dangerously-skip-permissions" in argv
    assert "--print" in argv


def test_argv_with_devcontainer_is_a_list_with_spaces_intact() -> None:
    """AC #6 — devcontainer prefix is an argv LIST, never a joined string.

    A workspace path containing spaces must survive as a single argv element,
    which is the regression TASK-37 caught in the bash port.
    """
    tool = claude_tool.ClaudeTool(
        model="claude-opus-4-8",
        effort="max",
        devcontainer=True,
        workspace_folder=Path("/workspace with spaces"),
    )
    argv = tool.build_argv()
    assert argv[:5] == [
        "devcontainer",
        "exec",
        "--workspace-folder",
        "/workspace with spaces",
        "claude",
    ]
    # Path is one element — not two halves split on the space.
    assert argv.count("/workspace with spaces") == 1
    assert "with" not in argv  # would only appear if accidentally split


def test_devcontainer_requires_workspace_folder() -> None:
    with pytest.raises(ValueError, match="workspace_folder"):
        claude_tool.ClaudeTool(model="x", effort="y", devcontainer=True)


def test_run_passes_prompt_via_stdin_and_tees_stdout(tmp_path: Path) -> None:
    """The prompt reaches the child via stdin and combined stdout is tee'd.

    Uses ``cat`` as a stand-in CLI: stdin → stdout echo. The tee file should
    contain exactly the prompt bytes the parent wrote.
    """
    prompt = "hello\n## Task Summary\n<promise>COMPLETE</promise>\n"
    result = claude_tool._execute(
        argv=["cat"],
        prompt=prompt,
        timeout_sec=10,
    )
    try:
        assert result.exit_code == 0
        assert result.stdout_path.read_text() == prompt
        assert result.signals.task_summary_count == 1
        assert result.signals.complete is True
    finally:
        result.stdout_path.unlink(missing_ok=True)


def test_child_runs_in_its_own_process_group(tmp_path: Path) -> None:
    """AC #2 — ``start_new_session=True`` makes the child its own pgroup leader.

    A child that inherits the parent's pgid would make the AC #7
    ``os.killpg(getpgid(child), SIGTERM)`` call kill pytest itself; this
    test catches that regression directly.
    """
    holder: dict[str, Any] = {}
    done = threading.Event()

    def target() -> None:
        try:
            claude_tool._execute(
                argv=["sleep", "10"],
                prompt="",
                timeout_sec=30,
                on_spawn=lambda p: holder.__setitem__("proc", p),
            )
        finally:
            done.set()

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5.0
    while "proc" not in holder and time.monotonic() < deadline:
        time.sleep(0.05)
    proc = holder.get("proc")
    assert proc is not None, "Popen was not captured within 5s"

    assert os.getpgid(proc.pid) == proc.pid, (
        "child pgid must equal its pid (i.e. session leader); "
        "without start_new_session=True it would inherit the test runner's pgid"
    )

    proc.terminate()
    assert done.wait(timeout=10), "_execute did not return after terminate"


def test_sigterm_to_process_group_kills_child_within_5s(tmp_path: Path) -> None:
    """AC #7 — SIGTERM to the child's pgroup reaps it with no zombie.

    Models the orchestrator-level signal handler (US-005): when the
    orchestrator catches SIGTERM, it walks active tool subprocesses and
    SIGTERMs their pgroup. Here we drive that path manually so the test is
    self-contained and does not signal pytest.
    """
    holder: dict[str, Any] = {}
    done = threading.Event()

    def target() -> None:
        try:
            result = claude_tool._execute(
                argv=["sleep", "60"],
                prompt="",
                timeout_sec=120,
                on_spawn=lambda p: holder.__setitem__("proc", p),
            )
            holder["result"] = result
        finally:
            done.set()

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5.0
    while "proc" not in holder and time.monotonic() < deadline:
        time.sleep(0.05)
    proc = holder.get("proc")
    assert proc is not None, "Popen was not captured within 5s"

    pgid = os.getpgid(proc.pid)
    os.killpg(pgid, signal.SIGTERM)

    assert done.wait(timeout=6.0), "_execute did not return within 6s of SIGTERM"
    assert proc.poll() is not None, "child still alive (zombie)"
    result = holder["result"]
    # killed-by-signal exit codes are negative under Popen.wait
    assert result.exit_code != 0
    Path(result.stdout_path).unlink(missing_ok=True)


def test_real_timeout_kills_tree_and_returns_exit_124(tmp_path: Path) -> None:
    """AC #4 — Popen.wait timeout triggers SIGTERM→grace→SIGKILL and exit 124.

    The whole call must return well under the child's own ``sleep 60`` —
    proving the parent did NOT wait for the child to exit naturally.
    """
    start = time.monotonic()
    result = claude_tool._execute(
        argv=["sleep", "60"],
        prompt="",
        timeout_sec=1,
    )
    elapsed = time.monotonic() - start
    try:
        assert result.exit_code == claude_tool.TIMEOUT_EXIT_CODE
        assert elapsed < 15, f"_execute took {elapsed:.1f}s; expected <15s"
    finally:
        result.stdout_path.unlink(missing_ok=True)


def test_exit_124_passthrough_is_treated_as_timeout(tmp_path: Path) -> None:
    """AC #8 — a child that naturally exits 124 surfaces 124 on the ToolResult.

    Indistinguishable from a real timeout at the orchestrator-API layer,
    which is exactly the bash parity: ``timeout`` itself uses 124 to signal
    a kill, and the orchestrator's `[[ $EXIT_CODE -eq 124 ]]` branch fires
    whether the child was actually killed or merely exited with that code.
    """
    result = claude_tool._execute(
        argv=["bash", "-c", "exit 124"],
        prompt="",
        timeout_sec=30,
    )
    try:
        assert result.exit_code == 124
    finally:
        result.stdout_path.unlink(missing_ok=True)


def test_tool_run_returns_toolresult_with_tee_path(tmp_path: Path) -> None:
    """``Tool.run`` delegates to ``_execute`` and produces a populated result."""
    tool = claude_tool.ClaudeTool(model="m", effort="e")
    # Override build_argv to avoid needing real claude installed
    object.__setattr__(tool, "build_argv", lambda: ["bash", "-c", "echo ok"])
    result = tool.run("ignored", timeout_sec=10)
    try:
        assert result.exit_code == 0
        assert result.stdout_path.exists()
        assert "ok" in result.stdout_path.read_text()
    finally:
        result.stdout_path.unlink(missing_ok=True)


def test_terminate_tree_safe_on_already_exited_child() -> None:
    """`_terminate_tree` must be a no-op on a child that already exited.

    The mainline path always calls it from the TimeoutExpired branch, but
    the orchestrator-level SIGTERM handler (US-005) may race the child's
    natural exit — the helper must not raise in that case.
    """
    proc = subprocess.Popen(
        ["bash", "-c", "true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    proc.wait(timeout=5)
    claude_tool._terminate_tree(proc)
