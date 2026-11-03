"""ralph-run preflight warns about user hooks the devcontainer cannot run (TASK-289).

The container shares only the user ``~/.claude``; its ``$HOME`` is
``/home/node``. A user-global hook whose executable lives elsewhere on the
host fails there with "not found", so preflight names each one on stderr when
``devcontainer=true`` — and never changes the exit code.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ralph import preflight

WARNING = "WARNING: user hook not reachable in the devcontainer"
TRIM = '"$HOME/.config/claude-trim/claude-trim" --hook'
AGTERM = "'/Users/x/.config/agterm/agent-status/agterm-claude-status.sh' active --blink"
PEON = "/Users/x/.claude/hooks/peon-ping/peon.sh"
JQ = "jq -r .x"
GUARDED = '[ "${DEVCONTAINER:-}" = true ] || "$HOME/.config/claude-trim/claude-trim" --hook'
CONFIG_DIR = "/Users/x/.claude"


def _settings(*pairs: tuple[str, str]) -> dict[str, dict[str, list[dict[str, object]]]]:
    """A user settings object holding one hook group per ``(event, command)``."""
    hooks: dict[str, list[dict[str, object]]] = {}
    for event, command in pairs:
        hooks.setdefault(event, []).append({"hooks": [{"type": "command", "command": command}]})
    return {"hooks": hooks}


def _fixture(peon: str) -> str:
    """The five fixture cases, with the peon hook under the given config dir."""
    return json.dumps(
        _settings(
            ("SessionEnd", TRIM),
            ("Stop", AGTERM),
            ("PostToolUse", peon),
            ("UserPromptSubmit", JQ),
            ("SessionStart", GUARDED),
        )
    )


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project that passes every fail-fast check, with stubbed CLIs."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("backlog", 'echo "  TASK-1 - Something"'), ("devcontainer", "exit 0")):
        stub = bin_dir / name
        stub.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        stub.chmod(0o755)
    project = tmp_path / "project"
    (project / "backlog").mkdir(parents=True)
    ralph_sh = project / "ralph.sh"
    ralph_sh.write_text("#!/bin/bash\necho hello\n", encoding="utf-8")
    ralph_sh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.chdir(project)
    monkeypatch.setattr(preflight, "_check_managed_drift", lambda verbose: None)
    return project


def _config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: str | None) -> Path:
    config = tmp_path / "config"
    config.mkdir()
    if settings is not None:
        (config / "settings.json").write_text(settings, encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    return config


def _run(project: Path, devcontainer: str, capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    rc = preflight.main([str(project / "ralph.sh"), devcontainer])
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def _warnings(err: str) -> list[str]:
    return [line for line in err.splitlines() if line.startswith(WARNING)]


@pytest.mark.parametrize(
    ("command", "warned"),
    [(TRIM, True), (AGTERM, True), (PEON, False), (JQ, False), (GUARDED, False)],
    ids=["claude-trim", "agterm", "under-config-dir", "bare-name", "devcontainer-guard"],
)
def test_classifier_fixture_cases(command: str, warned: bool) -> None:
    found = preflight._host_only_hooks_from(_settings(("Stop", command)), "/Users/x", CONFIG_DIR)
    assert found == ([("Stop", command)] if warned else [])


@pytest.mark.parametrize("prefix", ["$HOME", "${HOME}", "~"])
def test_classifier_home_forms(prefix: str) -> None:
    outside = f"{prefix}/bin/tool.sh"
    inside = f'"{prefix}/.claude/hooks/tool.sh" x'
    found = preflight._host_only_hooks_from(
        _settings(("Stop", outside), ("Stop", inside)), "/Users/x", "/elsewhere/.claude"
    )
    assert found == [("Stop", outside)]


def test_devcontainer_true_warns_once_per_host_only_command(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = _config(tmp_path, monkeypatch, None)
    (config / "settings.json").write_text(_fixture(f"{config}/hooks/peon-ping/peon.sh"), encoding="utf-8")
    rc, out, err = _run(project, "true", capsys)
    assert rc == 0
    assert out == f"OK RALPH_PATH={project / 'ralph.sh'}\n"
    assert _warnings(err) == [
        f"{WARNING} — SessionEnd: {TRIM} (guard the hook command with DEVCONTAINER, see ralph-init)",
        f"{WARNING} — Stop: {AGTERM} (guard the hook command with DEVCONTAINER, see ralph-init)",
    ]


def test_devcontainer_false_never_warns(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _config(tmp_path, monkeypatch, _fixture(PEON))
    rc, out, err = _run(project, "false", capsys)
    assert rc == 0
    assert out.endswith(f"OK RALPH_PATH={project / 'ralph.sh'}\n")
    assert _warnings(err) == []


@pytest.mark.parametrize(
    "settings",
    [None, "{not json", json.dumps({"model": "opus"}), "[]"],
    ids=["missing", "unparsable", "no-hooks", "not-an-object"],
)
def test_unreadable_or_hookless_settings_never_warn(
    project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    settings: str | None,
) -> None:
    _config(tmp_path, monkeypatch, settings)
    rc, out, err = _run(project, "true", capsys)
    assert rc == 0
    assert out.endswith(f"OK RALPH_PATH={project / 'ralph.sh'}\n")
    assert _warnings(err) == []


def test_settings_default_to_home_claude_without_config_dir(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    config = tmp_path / "home/.claude"
    config.mkdir(parents=True)
    (config / "settings.json").write_text(json.dumps(_settings(("SessionEnd", TRIM))), encoding="utf-8")
    rc, _out, err = _run(project, "true", capsys)
    assert rc == 0
    assert len(_warnings(err)) == 1
