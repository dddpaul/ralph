"""Unit tests for ``ralph/tools/__init__.py`` (US-003 AC #5).

These tests verify the abstract surface only — concrete tools land in
US-004 (claude) and US-005 (opencode).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from ralph.signals import IterationSignals
from ralph.tools import Tool, ToolResult


def test_tool_is_abstract() -> None:
    with pytest.raises(TypeError):
        Tool()  # type: ignore[abstract]


def test_run_signature() -> None:
    sig = inspect.signature(Tool.run)
    params = list(sig.parameters.values())
    # ``self``, ``prompt: str``, ``timeout_sec: int``
    assert [p.name for p in params] == ["self", "prompt", "timeout_sec"]
    # ``from __future__ import annotations`` keeps annotations as strings.
    assert sig.return_annotation == "ToolResult"


def test_tool_result_fields() -> None:
    signals = IterationSignals(task_summary_count=1, complete=True, error_text=None)
    result = ToolResult(
        stdout_path=Path("/tmp/out.txt"),
        exit_code=0,
        signals=signals,
    )
    assert result.stdout_path == Path("/tmp/out.txt")
    assert result.exit_code == 0
    assert result.signals is signals


def test_tool_result_is_frozen() -> None:
    result = ToolResult(
        stdout_path=Path("/tmp/out.txt"),
        exit_code=0,
        signals=IterationSignals(
            task_summary_count=0, complete=False, error_text=None
        ),
    )
    with pytest.raises(AttributeError):
        result.exit_code = 1  # type: ignore[misc]


def test_concrete_subclass_runs() -> None:
    class _StubTool(Tool):
        def run(self, prompt: str, timeout_sec: int) -> ToolResult:
            _ = (prompt, timeout_sec)
            return ToolResult(
                stdout_path=Path("/tmp/x"),
                exit_code=0,
                signals=IterationSignals(
                    task_summary_count=1, complete=True, error_text=None
                ),
            )

    result = _StubTool().run("hi", 5)
    assert result.signals.complete is True
    assert result.exit_code == 0
