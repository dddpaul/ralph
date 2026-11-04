"""The plugin's user-settings fragment, its preflight check and its merge (TASK-298).

A plugin cannot ship allow rules, so ``plugins/ralph/user-settings.json`` holds
the common ones for the user settings file. Preflight names the entries the
user settings miss in one warning; the merge helper appends them without ever
overwriting a value.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from ralph import preflight, user_settings

REPO = Path(__file__).resolve().parents[2]
FRAGMENT = REPO / "plugins/ralph/user-settings.json"
TEMPLATE = REPO / "plugins/ralph/skills/ralph-init/templates/claude/settings.local.json"
SHIM = REPO / "plugins/ralph/skills/ralph-run/scripts/merge-user-settings.sh"
WARNING = "WARNING: user settings miss"


def _fragment() -> dict[str, object]:
    return json.loads(FRAGMENT.read_text(encoding="utf-8"))


def _allow(data: dict[str, object]) -> list[str]:
    return data["permissions"]["allow"]  # type: ignore[index]


def test_fragment_holds_the_template_bash_rules_and_schedule_wakeup() -> None:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    bash = [r for r in _allow(template) if r.startswith("Bash(")]
    assert len(bash) == 46
    assert _allow(_fragment()) == [*bash, "ScheduleWakeup"]


def test_fragment_holds_attribution_and_sandbox_and_nothing_else() -> None:
    fragment = _fragment()
    assert fragment["attribution"] == {"commit": "", "pr": ""}
    assert fragment["sandbox"] == {"enabled": True, "autoAllowBashIfSandboxed": True}
    assert set(fragment) == {"attribution", "permissions", "sandbox"}
    assert set(fragment["permissions"]) == {"allow"}  # type: ignore[arg-type]


def test_fragment_holds_no_skill_rules() -> None:
    assert not [r for r in _allow(_fragment()) if r.startswith("Skill(")]
    assert "Skill(" not in FRAGMENT.read_text(encoding="utf-8")


def test_missing_entries_lists_exactly_what_is_absent() -> None:
    fragment = _fragment()
    settings = {
        "permissions": {"allow": _allow(fragment)[2:], "deny": ["Bash(rm:*)"]},
        "attribution": {"commit": "custom"},
        "sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True},
    }
    missing = user_settings.missing_entries(fragment, settings)
    assert missing == [
        'attribution.pr=""',
        f"permissions.allow: {_allow(fragment)[0]}",
        f"permissions.allow: {_allow(fragment)[1]}",
    ]


def test_complete_settings_miss_nothing() -> None:
    fragment = _fragment()
    assert user_settings.missing_entries(fragment, fragment) == []


def _sample() -> dict[str, object]:
    return {
        "model": "opus",
        "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "jq -r .x"}]}]},
        "permissions": {
            "allow": ["Bash(git add:*)", "WebFetch"],
            "deny": ["Bash(rm:*)"],
            "defaultMode": "plan",
        },
        "attribution": {"commit": "Signed-off-by: me"},
        "sandbox": {"enabled": False, "network": {"allowedDomains": ["example.com"]}},
        "statusLine": {"type": "command", "command": "~/.claude/status.sh"},
    }


def test_merge_appends_keeps_and_reports() -> None:
    fragment = _fragment()
    sample = _sample()
    merged, added, differs = user_settings.merge(fragment, sample)
    assert sample == _sample(), "merge must not change its input"
    allow = _allow(merged)
    assert allow[:2] == ["Bash(git add:*)", "WebFetch"]
    assert sorted(allow) == sorted(set(allow))
    assert set(_allow(fragment)) <= set(allow)
    assert len(allow) == 2 + len(_allow(fragment)) - 1
    for key in ("model", "hooks", "statusLine"):
        assert merged[key] == sample[key]
    assert merged["permissions"]["deny"] == ["Bash(rm:*)"]  # type: ignore[index]
    assert merged["permissions"]["defaultMode"] == "plan"  # type: ignore[index]
    assert merged["attribution"] == {"commit": "Signed-off-by: me", "pr": ""}
    assert merged["sandbox"] == {
        "enabled": False,
        "network": {"allowedDomains": ["example.com"]},
        "autoAllowBashIfSandboxed": True,
    }
    assert differs == [
        'attribution.commit: kept "Signed-off-by: me", fragment has ""',
        "sandbox.enabled: kept false, fragment has true",
    ]
    assert 'attribution.pr=""' in added
    assert "sandbox.autoAllowBashIfSandboxed=true" in added
    assert "permissions.allow: Bash(git add:*)" not in added


def test_merge_reports_a_type_mismatch_without_overwriting() -> None:
    merged, _added, differs = user_settings.merge(_fragment(), {"sandbox": "off"})
    assert merged["sandbox"] == "off"
    assert differs == [
        'sandbox: kept "off", fragment has {"enabled": true, "autoAllowBashIfSandboxed": true}'
    ]


def _run_shim(settings: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SHIM), str(settings)], capture_output=True, text=True, check=False
    )


def test_merge_shim_writes_a_sample_file_and_is_idempotent(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps(_sample(), indent=4) + "\n", encoding="utf-8")
    settings.chmod(0o600)
    first = _run_shim(settings)
    assert first.returncode == 0, first.stderr
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data == user_settings.merge(_fragment(), _sample())[0]
    assert list(data) == list(_sample())
    assert os.stat(settings).st_mode & 0o777 == 0o600
    assert (
        f"added: permissions.allow: {_allow(_fragment())[1]}"
        in first.stdout.splitlines()
    )
    assert (
        "differs: sandbox.enabled: kept false, fragment has true"
        in first.stderr.splitlines()
    )

    digest = hashlib.sha256(settings.read_bytes()).hexdigest()
    inode = settings.stat().st_ino
    second = _run_shim(settings)
    assert second.returncode == 0, second.stderr
    assert second.stdout == ""
    assert hashlib.sha256(settings.read_bytes()).hexdigest() == digest
    assert settings.stat().st_ino == inode


def test_merge_shim_creates_a_missing_file(tmp_path: Path) -> None:
    settings = tmp_path / "claude" / "settings.json"
    result = _run_shim(settings)
    assert result.returncode == 0, result.stderr
    assert json.loads(settings.read_text(encoding="utf-8")) == _fragment()


def test_merge_shim_refuses_invalid_json(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text("{not json", encoding="utf-8")
    result = _run_shim(settings)
    assert result.returncode == 1
    assert result.stderr.startswith("ERROR: ")
    assert settings.read_text(encoding="utf-8") == "{not json"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project that passes every fail-fast check, with a stubbed backlog CLI."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "backlog"
    stub.write_text('#!/bin/sh\necho "  TASK-1 - Something"\n', encoding="utf-8")
    stub.chmod(0o755)
    project = tmp_path / "project"
    (project / "backlog").mkdir(parents=True)
    ralph_sh = project / "ralph.sh"
    ralph_sh.write_text("#!/bin/bash\necho hello\n", encoding="utf-8")
    ralph_sh.chmod(0o755)
    config = tmp_path / "config"
    config.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    monkeypatch.chdir(project)
    return config


def _preflight(capsys: pytest.CaptureFixture[str]) -> tuple[int, list[str]]:
    rc = preflight.main(["./ralph.sh", "false"])
    err = capsys.readouterr().err
    return rc, [line for line in err.splitlines() if "user settings" in line]


def test_preflight_lists_exactly_the_missing_entries_and_changes_nothing(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fragment = _fragment()
    settings = {
        **fragment,
        "permissions": {"allow": _allow(fragment)[1:]},
        "sandbox": {"enabled": False},
    }
    path = project / "settings.json"
    path.write_text(json.dumps(settings), encoding="utf-8")
    before = {p: p.read_bytes() for p in (path, FRAGMENT)}
    rc, lines = _preflight(capsys)
    assert rc == 0
    assert len(lines) == 1
    assert lines[0].startswith(
        f"{WARNING} 2 ralph entries — permissions.allow: {_allow(fragment)[0]}; "
        "sandbox.autoAllowBashIfSandboxed=true ("
    )
    assert {p: p.read_bytes() for p in before} == before


def test_preflight_is_silent_when_nothing_is_missing(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (project / "settings.json").write_text(
        FRAGMENT.read_text(encoding="utf-8"), encoding="utf-8"
    )
    assert _preflight(capsys) == (0, [])


def test_preflight_lists_every_entry_when_user_settings_are_absent(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, lines = _preflight(capsys)
    assert rc == 0
    assert len(lines) == 1
    assert lines[0].startswith(
        f"{WARNING} {len(_allow(_fragment())) + 4} ralph entries — "
    )
    assert not (project / "settings.json").exists()


def test_preflight_warns_once_on_unreadable_settings(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (project / "settings.json").write_text("{not json", encoding="utf-8")
    rc, lines = _preflight(capsys)
    assert rc == 0
    assert len(lines) == 1
    assert lines[0].startswith(
        "WARNING: could not check user settings for ralph entries — "
    )
