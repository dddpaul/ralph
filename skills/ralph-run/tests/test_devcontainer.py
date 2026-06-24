"""Unit tests for ``ralph/devcontainer.py`` (TASK-175)."""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pytest

from ralph import devcontainer as devcontainer_module


def test_missing_cli_returns_1_and_prints_install_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(devcontainer_module.shutil, "which", lambda _name: None)
    out = io.StringIO()
    err = io.StringIO()

    rc = devcontainer_module.start_devcontainer(
        Path("/workspace"), stdout=out, stderr=err
    )

    assert rc == 1
    assert "devcontainer" in err.getvalue()
    assert "npm install -g @devcontainers/cli" in err.getvalue()
    assert out.getvalue() == ""


def test_up_success_prints_starting_then_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        devcontainer_module.shutil, "which", lambda _name: "/usr/local/bin/devcontainer"
    )
    captured_argv: list[list[str]] = []

    def fake_run(argv: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        captured_argv.append(argv)
        return subprocess.CompletedProcess(argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(devcontainer_module.subprocess, "run", fake_run)
    out = io.StringIO()
    err = io.StringIO()

    rc = devcontainer_module.start_devcontainer(
        Path("/workspace with spaces"), stdout=out, stderr=err
    )

    assert rc == 0
    assert captured_argv == [
        ["devcontainer", "up", "--workspace-folder", "/workspace with spaces"]
    ]
    text = out.getvalue()
    assert "Starting devcontainer..." in text
    assert "Devcontainer is ready." in text
    assert text.index("Starting devcontainer...") < text.index("Devcontainer is ready.")
    assert err.getvalue() == ""


def test_up_failure_surfaces_stderr_and_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        devcontainer_module.shutil, "which", lambda _name: "/usr/local/bin/devcontainer"
    )
    cli_stderr = "Cannot connect to the Docker daemon\n"

    def fake_run(argv: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv, returncode=2, stdout="", stderr=cli_stderr
        )

    monkeypatch.setattr(devcontainer_module.subprocess, "run", fake_run)
    out = io.StringIO()
    err = io.StringIO()

    rc = devcontainer_module.start_devcontainer(
        Path("/workspace"), stdout=out, stderr=err
    )

    assert rc == 2
    assert "Starting devcontainer..." in out.getvalue()
    assert "Devcontainer is ready." not in out.getvalue()
    assert cli_stderr in err.getvalue()
