"""``--rebuild`` argv & wiring tests (TASK-237).

A bare ``devcontainer up`` reuses any existing container, so
``devcontainer.json`` mount changes — like the ``.venv`` volume overlay from
TASK-235 — never take effect. ``--rebuild`` appends
``--remove-existing-container`` to force a fresh container.

These tests pin BOTH argv shapes so the default path can never grow an
extra flag by accident, and they pin the loop wiring that makes
``--rebuild`` a no-op unless ``--devcontainer`` is also set.
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pytest

from ralph import devcontainer as devcontainer_module
from ralph import loop as loop_module
from ralph.args import ParsedArgs, parse
from ralph.signals import IterationSignals
from ralph.tools import OnSpawn, Tool, ToolResult

_BASE_ARGV = ["devcontainer", "up", "--workspace-folder", "/workspace"]


@pytest.fixture
def captured_argv(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Stub out the CLI lookup and ``subprocess.run``; record every argv."""
    monkeypatch.setattr(
        devcontainer_module.shutil, "which", lambda _name: "/usr/local/bin/devcontainer"
    )
    recorded: list[list[str]] = []

    def fake_run(argv: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        recorded.append(list(argv))
        return subprocess.CompletedProcess(argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(devcontainer_module.subprocess, "run", fake_run)
    return recorded


def test_rebuild_true_appends_remove_existing_container(
    captured_argv: list[list[str]],
) -> None:
    out = io.StringIO()
    err = io.StringIO()

    rc = devcontainer_module.start_devcontainer(
        Path("/workspace"), rebuild=True, stdout=out, stderr=err
    )

    assert rc == 0
    assert captured_argv == [[*_BASE_ARGV, "--remove-existing-container"]]
    assert "Rebuilding devcontainer" in out.getvalue()
    assert "Devcontainer is ready." in out.getvalue()
    assert err.getvalue() == ""


def test_rebuild_false_argv_is_unchanged_from_today(
    captured_argv: list[list[str]],
) -> None:
    out = io.StringIO()
    err = io.StringIO()

    rc = devcontainer_module.start_devcontainer(
        Path("/workspace"), rebuild=False, stdout=out, stderr=err
    )

    assert rc == 0
    assert captured_argv == [_BASE_ARGV]
    assert "--remove-existing-container" not in captured_argv[0]
    assert "Starting devcontainer..." in out.getvalue()
    assert err.getvalue() == ""


def test_rebuild_defaults_to_off(captured_argv: list[list[str]]) -> None:
    """Omitting the keyword must produce the pre-TASK-237 argv verbatim."""
    rc = devcontainer_module.start_devcontainer(
        Path("/workspace"), stdout=io.StringIO(), stderr=io.StringIO()
    )

    assert rc == 0
    assert captured_argv == [_BASE_ARGV]


def test_parser_accepts_rebuild_and_defaults_false() -> None:
    assert parse([]).rebuild is False
    assert parse(["--devcontainer"]).rebuild is False
    assert parse(["--rebuild", "--devcontainer"]).rebuild is True
    # Order-independent, and it does not disturb the positional.
    parsed = parse(["--devcontainer", "5", "--rebuild"])
    assert parsed.rebuild is True
    assert parsed.devcontainer is True
    assert parsed.max_iterations == 5
    # --rebuild alone parses fine (it is a no-op at run time, not an error).
    assert parse(["--rebuild"]).rebuild is True
    assert parse(["--rebuild"]).devcontainer is False


def _args(*, devcontainer: bool, rebuild: bool) -> ParsedArgs:
    return ParsedArgs(
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
        devcontainer=devcontainer,
        max_iterations=1,
        rebuild=rebuild,
    )


class _StubTool(Tool):
    def run(
        self,
        prompt: str,
        timeout_sec: int,
        *,
        on_spawn: OnSpawn | None = None,
    ) -> ToolResult:
        _ = (prompt, timeout_sec, on_spawn)
        return ToolResult(
            stdout_path=Path("/tmp/ralph-test.out"),
            exit_code=0,
            signals=IterationSignals(
                task_summary_count=1, complete=True, error_text=None
            ),
        )


@pytest.fixture
def stubbed_loop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, list[bool]]:
    """Run ``loop.run`` with everything stubbed; record each ``rebuild=`` value."""
    monkeypatch.setattr(loop_module.tasks_module, "pick_next_task", lambda **_: "TASK-1")
    monkeypatch.setattr(loop_module.tasks_module, "count_remaining", lambda *_a, **_kw: 1)
    monkeypatch.setattr(loop_module.tasks_module, "done_task_ids", lambda: [])
    monkeypatch.setattr(
        loop_module.tasks_module, "current_in_progress_task", lambda: None
    )
    monkeypatch.setattr(loop_module, "ITER_SLEEP_SEC", 0)
    monkeypatch.setenv("RALPH_STATUS_FILE", str(tmp_path / "status.json"))
    monkeypatch.setenv("RALPH_HEARTBEAT_FILE", str(tmp_path / "heartbeat"))

    seen: list[bool] = []

    def fake_start(_workspace: Path, *, rebuild: bool = False, **_kw: object) -> int:
        seen.append(rebuild)
        return 0

    monkeypatch.setattr(loop_module, "start_devcontainer", fake_start)
    monkeypatch.setattr(loop_module, "build_tool", lambda *_a, **_kw: _StubTool())
    return tmp_path, seen


def test_loop_forwards_rebuild_to_start_devcontainer(
    stubbed_loop: tuple[Path, list[bool]],
) -> None:
    project_root, seen = stubbed_loop
    assert loop_module.run(_args(devcontainer=True, rebuild=True), project_root) == 0
    assert seen == [True]


def test_loop_passes_rebuild_false_by_default(
    stubbed_loop: tuple[Path, list[bool]],
) -> None:
    project_root, seen = stubbed_loop
    assert loop_module.run(_args(devcontainer=True, rebuild=False), project_root) == 0
    assert seen == [False]


def test_rebuild_is_a_noop_without_devcontainer(
    stubbed_loop: tuple[Path, list[bool]],
) -> None:
    """No ``--devcontainer`` → no bring-up at all, so ``--rebuild`` does nothing."""
    project_root, seen = stubbed_loop
    assert loop_module.run(_args(devcontainer=False, rebuild=True), project_root) == 0
    assert seen == []
