"""Stale-container detection tests (TASK-258).

``devcontainer up`` reuses an existing container, and ``devcontainer.json`` /
``Dockerfile`` changes apply only at creation. ``start_devcontainer`` refuses
to reuse a container older than either file and names the ``rebuild=true``
remedy. Every unknowable case (no docker, no container, failing docker,
unparseable timestamp) must leave the launch exactly as it was before.

Container creation time and file mtimes are stubbed — no real docker.
"""

from __future__ import annotations

import io
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ralph import devcontainer as devcontainer_module

CREATED = datetime(2026, 9, 27, 13, 13, 6, tzinfo=UTC)
BEFORE = datetime(2026, 9, 26, 0, 0, 0, tzinfo=UTC)
AFTER = datetime(2026, 9, 27, 16, 40, 22, tzinfo=UTC)


def _workspace(
    tmp_path: Path, *, json_at: datetime, dockerfile_at: datetime | None
) -> Path:
    dc = tmp_path / ".devcontainer"
    dc.mkdir()
    files = {"devcontainer.json": json_at, "Dockerfile": dockerfile_at}
    for name, when in files.items():
        if when is None:
            continue
        path = dc / name
        path.write_text("{}\n")
        os.utime(path, (when.timestamp(), when.timestamp()))
    return tmp_path


@pytest.fixture
def up_calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Stub ``devcontainer`` on PATH and record the ``up`` argv; docker absent."""

    def which(name: str) -> str | None:
        return "/usr/local/bin/devcontainer" if name == "devcontainer" else None

    monkeypatch.setattr(devcontainer_module.shutil, "which", which)
    recorded: list[list[str]] = []

    def fake_run(argv: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        recorded.append(list(argv))
        return subprocess.CompletedProcess(argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(devcontainer_module.subprocess, "run", fake_run)
    return recorded


def _created(monkeypatch: pytest.MonkeyPatch, value: datetime | None) -> None:
    monkeypatch.setattr(devcontainer_module, "container_created_at", lambda _ws: value)


def _start(ws: Path, **kw: bool) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    rc = devcontainer_module.start_devcontainer(ws, stdout=out, stderr=err, **kw)
    return rc, out.getvalue(), err.getvalue()


@pytest.mark.parametrize(
    ("json_at", "dockerfile_at", "stale_name"),
    [
        (AFTER, BEFORE, "devcontainer.json"),
        (BEFORE, AFTER, "Dockerfile"),
    ],
)
def test_stale_container_is_refused_with_both_timestamps_and_remedy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    up_calls: list[list[str]],
    json_at: datetime,
    dockerfile_at: datetime,
    stale_name: str,
) -> None:
    ws = _workspace(tmp_path, json_at=json_at, dockerfile_at=dockerfile_at)
    _created(monkeypatch, CREATED)

    rc, out, err = _start(ws)

    assert rc == devcontainer_module.STALE_CONTAINER_EXIT != 0
    assert up_calls == []
    assert "STALE DEVCONTAINER" in err
    assert CREATED.isoformat() in err
    assert AFTER.isoformat() in err
    assert stale_name in err
    assert "rebuild=true" in err
    assert f"--workspace-folder {ws} --remove-existing-container" in err
    assert "Devcontainer is ready." not in out


def test_current_container_is_reused_silently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, up_calls: list[list[str]]
) -> None:
    ws = _workspace(tmp_path, json_at=BEFORE, dockerfile_at=BEFORE)
    _created(monkeypatch, CREATED)

    rc, out, err = _start(ws)

    assert rc == 0
    assert up_calls == [["devcontainer", "up", "--workspace-folder", str(ws)]]
    assert "Devcontainer is ready." in out
    assert err == ""


def test_missing_dockerfile_only_checks_devcontainer_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, up_calls: list[list[str]]
) -> None:
    ws = _workspace(tmp_path, json_at=BEFORE, dockerfile_at=None)
    _created(monkeypatch, CREATED)

    assert _start(ws)[0] == 0
    assert len(up_calls) == 1


def test_rebuild_skips_the_check_and_argv_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, up_calls: list[list[str]]
) -> None:
    ws = _workspace(tmp_path, json_at=AFTER, dockerfile_at=AFTER)

    def must_not_probe(_ws: Path) -> datetime:
        raise AssertionError("rebuild=True must not probe the existing container")

    monkeypatch.setattr(devcontainer_module, "container_created_at", must_not_probe)

    rc, out, err = _start(ws, rebuild=True)

    assert rc == 0
    assert up_calls == [
        [
            "devcontainer",
            "up",
            "--workspace-folder",
            str(ws),
            "--remove-existing-container",
        ]
    ]
    assert err == ""


# --- degraded cases: the real ``container_created_at`` over stubbed docker ---


def _docker(
    monkeypatch: pytest.MonkeyPatch, *, on_path: bool, responses: dict[str, object]
) -> list[list[str]]:
    """Stub docker. ``responses`` maps a docker subcommand to a CompletedProcess or exception."""

    def which(name: str) -> str | None:
        if name == "docker":
            return "/usr/bin/docker" if on_path else None
        return "/usr/local/bin/devcontainer"

    monkeypatch.setattr(devcontainer_module.shutil, "which", which)
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        if argv[0] == "docker":
            reply = responses[argv[1]]
            if isinstance(reply, BaseException):
                raise reply
            assert isinstance(reply, subprocess.CompletedProcess)
            return reply
        return subprocess.CompletedProcess(argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(devcontainer_module.subprocess, "run", fake_run)
    return calls


def _ok(stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode=0, stdout=stdout, stderr="")


def _fail() -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode=1, stdout="", stderr="boom")


@pytest.mark.parametrize(
    ("on_path", "responses"),
    [
        pytest.param(False, {}, id="no-docker-binary"),
        pytest.param(True, {"ps": _ok("")}, id="no-matching-container"),
        pytest.param(True, {"ps": _fail()}, id="ps-fails"),
        pytest.param(True, {"ps": OSError("exec failed")}, id="ps-raises"),
        pytest.param(
            True, {"ps": _ok("abc123\n"), "inspect": _fail()}, id="inspect-fails"
        ),
        pytest.param(
            True,
            {"ps": _ok("abc123\n"), "inspect": subprocess.TimeoutExpired("docker", 10)},
            id="inspect-times-out",
        ),
        pytest.param(
            True,
            {"ps": _ok("abc123\n"), "inspect": _ok("not-a-date")},
            id="inspect-garbage",
        ),
    ],
)
def test_degraded_probe_leaves_launch_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    on_path: bool,
    responses: dict[str, object],
) -> None:
    # Config is newer than any container could be — only the probe failing
    # can explain a clean launch.
    ws = _workspace(tmp_path, json_at=AFTER, dockerfile_at=AFTER)
    calls = _docker(monkeypatch, on_path=on_path, responses=responses)

    rc, out, err = _start(ws)

    assert rc == 0
    assert calls[-1] == ["devcontainer", "up", "--workspace-folder", str(ws)]
    assert "Starting devcontainer..." in out
    assert "Devcontainer is ready." in out
    assert err == ""


def test_probe_reads_docker_created_with_nanoseconds_and_newest_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _docker(
        monkeypatch,
        on_path=True,
        responses={
            "ps": _ok("newest1\nolder22\n"),
            "inspect": _ok("2026-09-27T13:13:06.123456789Z\n"),
        },
    )

    created = devcontainer_module.container_created_at(tmp_path)

    assert created == datetime(2026, 9, 27, 13, 13, 6, 123456, tzinfo=UTC)
    assert calls == [
        [
            "docker",
            "ps",
            "-aq",
            "--filter",
            f"label=devcontainer.local_folder={tmp_path}",
        ],
        ["docker", "inspect", "newest1", "--format", "{{.Created}}"],
    ]


def test_stale_detected_end_to_end_through_stubbed_docker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _workspace(tmp_path, json_at=AFTER, dockerfile_at=BEFORE)
    calls = _docker(
        monkeypatch,
        on_path=True,
        responses={"ps": _ok("abc123\n"), "inspect": _ok("2026-09-27T13:13:06Z\n")},
    )

    rc, _out, err = _start(ws)

    assert rc == devcontainer_module.STALE_CONTAINER_EXIT
    assert all(argv[0] == "docker" for argv in calls)
    assert "2026-09-27T13:13:06+00:00" in err
    assert "rebuild=true" in err
