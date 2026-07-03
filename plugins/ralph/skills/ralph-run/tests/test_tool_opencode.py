"""Unit tests for ``ralph/tools/opencode.py`` (US-005 AC #1)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from ralph.tools import opencode as opencode_tool
from ralph.tools._subprocess import TIMEOUT_EXIT_CODE


def test_argv_without_devcontainer_starts_with_opencode_run() -> None:
    tool = opencode_tool.OpencodeTool()
    argv = tool.build_argv("hello prompt")
    assert argv == ["opencode", "run", "hello prompt"]


def test_argv_with_devcontainer_is_a_list_with_spaces_intact() -> None:
    """Devcontainer prefix is an argv LIST, never a joined string (TASK-37)."""
    tool = opencode_tool.OpencodeTool(
        devcontainer=True,
        workspace_folder=Path("/workspace with spaces"),
    )
    argv = tool.build_argv("the prompt body")
    assert argv == [
        "devcontainer",
        "exec",
        "--workspace-folder",
        "/workspace with spaces",
        "opencode",
        "run",
        "the prompt body",
    ]
    assert argv.count("/workspace with spaces") == 1
    assert "with" not in argv


def test_devcontainer_requires_workspace_folder() -> None:
    with pytest.raises(ValueError, match="workspace_folder"):
        opencode_tool.OpencodeTool(devcontainer=True)


def test_prompt_reaches_child_as_positional_arg() -> None:
    """The prompt is passed as argv[2], NOT stdin.

    Uses ``echo`` to confirm argv positioning: ``echo <prompt>`` writes the
    prompt to stdout if and only if the prompt arrived as a positional arg.
    """
    tool = opencode_tool.OpencodeTool()
    prompt = "hello world\n## Task Summary\n<promise>COMPLETE</promise>"

    # Override build_argv to substitute echo for opencode while preserving
    # the positional-prompt contract.
    object.__setattr__(
        tool,
        "build_argv",
        lambda p: ["echo", p],
    )
    result = tool.run(prompt, timeout_sec=10)
    try:
        assert result.exit_code == 0
        text = result.stdout_path.read_text()
        assert "hello world" in text
        # Signals should surface complete=True even when the agent ran inside echo.
        assert result.signals.complete is True
    finally:
        result.stdout_path.unlink(missing_ok=True)


def test_timeout_returns_exit_124() -> None:
    """An infinitely-blocked subprocess returns ``TIMEOUT_EXIT_CODE`` (124)."""
    tool = opencode_tool.OpencodeTool()
    object.__setattr__(
        tool, "build_argv", lambda _p: ["sleep", "60"]
    )
    start = time.monotonic()
    result = tool.run("ignored", timeout_sec=1)
    elapsed = time.monotonic() - start
    try:
        assert result.exit_code == TIMEOUT_EXIT_CODE
        assert elapsed < 15, f"opencode run took {elapsed:.1f}s; expected <15s"
    finally:
        result.stdout_path.unlink(missing_ok=True)
