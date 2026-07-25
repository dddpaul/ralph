"""Loop-level wiring for post-loop origin publish (TASK-211).

Verifies that ``loop.run()``:

* snapshots the master ref BEFORE the loop and threads it into
  :func:`ralph.push.maybe_push_after_loop` (only when push is enabled),
* invokes the push after the loop finishes, and
* carries a push failure's non-zero code into the run exit code WITHOUT
  masking an already-failing loop.

The push module's own git behavior is covered hermetically in
``test_push.py``; here it is stubbed so the loop wiring is tested in isolation.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from ralph import loop as loop_module
from ralph import push as push_module
from ralph.args import ParsedArgs
from ralph.signals import IterationSignals
from ralph.tools import OnSpawn, Tool, ToolResult


def _args(**over: Any) -> ParsedArgs:
    base = ParsedArgs(
        tool="claude",
        model="claude-opus-4-8",
        effort="max",
        timeout="15",
        on_error="continue",
        retry_count=0,
        log_file="",
        prompt_file="",
        tasks="",
        block_end_buffer_min=0,
        devcontainer=False,
        max_iterations=1,
    )
    return replace(base, **over)


class _ScriptedTool(Tool):
    def __init__(self, result: ToolResult) -> None:
        self._result = result

    def run(
        self,
        prompt: str,
        timeout_sec: int,
        *,
        on_spawn: OnSpawn | None = None,
    ) -> ToolResult:
        _ = (prompt, timeout_sec, on_spawn)
        return self._result


def _result(exit_code: int, *, complete: bool = False) -> ToolResult:
    return ToolResult(
        stdout_path=Path("/tmp/ralph-push-test.out"),
        exit_code=exit_code,
        signals=IterationSignals(
            task_summary_count=1 if exit_code == 0 else 0,
            complete=complete,
            error_text=None,
        ),
    )


@pytest.fixture
def stubbed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(
        loop_module.tasks_module, "pick_next_task", lambda **_: "TASK-1"
    )
    monkeypatch.setattr(
        loop_module.tasks_module, "count_remaining", lambda *_a, **_k: 0
    )
    monkeypatch.setattr(loop_module.tasks_module, "done_task_ids", lambda: [])
    monkeypatch.setattr(
        loop_module.tasks_module, "current_in_progress_task", lambda: None
    )
    monkeypatch.setattr(loop_module, "ITER_SLEEP_SEC", 0)
    monkeypatch.setenv("RALPH_STATUS_FILE", str(tmp_path / "status.json"))
    monkeypatch.setenv("RALPH_HEARTBEAT_FILE", str(tmp_path / "hb"))
    monkeypatch.delenv(push_module.PUSH_DISABLE_ENV, raising=False)
    return tmp_path


def _record_push(
    monkeypatch: pytest.MonkeyPatch, outcome: push_module.PushOutcome
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_push(
        *, project_root: Path, enabled: bool, rev_before: str | None, **_kw: Any
    ) -> push_module.PushOutcome:
        calls.append(
            {
                "project_root": project_root,
                "enabled": enabled,
                "rev_before": rev_before,
            }
        )
        return outcome

    monkeypatch.setattr(loop_module.push_module, "maybe_push_after_loop", fake_push)
    return calls


def test_push_invoked_after_successful_loop(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #2 — enabled run threads the pre-loop rev into the push and succeeds."""
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_k: _ScriptedTool(
        _result(0, complete=True)
    ))
    monkeypatch.setattr(
        loop_module.push_module, "current_rev", lambda *_a, **_k: "SHA_BEFORE"
    )
    calls = _record_push(
        monkeypatch, push_module.PushOutcome("pushed", "ok", 0)
    )

    rc = loop_module.run(_args(), stubbed)

    assert rc == 0
    assert len(calls) == 1
    assert calls[0]["enabled"] is True
    assert calls[0]["rev_before"] == "SHA_BEFORE"


def test_push_failure_carried_into_exit_code(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #5 — a push failure makes an otherwise-successful run exit non-zero."""
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_k: _ScriptedTool(
        _result(0, complete=True)
    ))
    monkeypatch.setattr(
        loop_module.push_module, "current_rev", lambda *_a, **_k: "SHA_BEFORE"
    )
    _record_push(monkeypatch, push_module.PushOutcome("failed", "boom", 7))

    rc = loop_module.run(_args(), stubbed)

    assert rc == 7


def test_push_failure_does_not_mask_loop_failure(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing loop keeps its own exit code even when the push also fails."""
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_k: _ScriptedTool(
        _result(1)
    ))
    monkeypatch.setattr(
        loop_module.push_module, "current_rev", lambda *_a, **_k: "SHA_BEFORE"
    )
    calls = _record_push(
        monkeypatch, push_module.PushOutcome("failed", "boom", 7)
    )

    rc = loop_module.run(_args(), stubbed)

    # Loop failed → exit 1; push still attempted, but its code must not mask it.
    assert rc == 1
    assert len(calls) == 1


def test_opt_out_skips_rev_snapshot_and_disables_push(
    stubbed: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC #6 — with ``--no-push`` the pre-loop rev is not taken and push is off."""
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_k: _ScriptedTool(
        _result(0, complete=True)
    ))
    rev_calls: list[int] = []
    monkeypatch.setattr(
        loop_module.push_module,
        "current_rev",
        lambda *_a, **_k: rev_calls.append(1) or "SHA",
    )
    calls = _record_push(
        monkeypatch, push_module.PushOutcome("skipped", "disabled", 0)
    )

    rc = loop_module.run(_args(push=False), stubbed)

    assert rc == 0
    assert rev_calls == []  # no snapshot taken when opted out
    assert len(calls) == 1
    assert calls[0]["enabled"] is False
    assert calls[0]["rev_before"] is None
