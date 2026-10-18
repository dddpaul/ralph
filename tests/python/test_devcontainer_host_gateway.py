"""The devcontainer maps host.docker.internal to the host gateway (TASK-277).

The proxy vars (``HTTP_PROXY``/``HTTPS_PROXY`` at ``host.docker.internal:3128``)
and ``MCP_GATEWAY_HOST`` all name ``host.docker.internal``, and
``init-firewall.sh`` fetches ``https://api.github.com/meta`` through that proxy
in ``postStartCommand``. Docker Desktop and colima resolve the name; a plain
Linux Docker Engine does not, so ``devcontainer up`` failed there at
``postStartCommand``. ``--add-host=host.docker.internal:host-gateway`` maps it on
every runtime: Docker Desktop's host, colima's Mac, a Linux engine's bridge
gateway.

``runArgs`` must stay a single line: ``merge-runargs.sh`` only merges a
one-line array during Upgrade U4.
"""

from __future__ import annotations

from pathlib import Path

from devcontainer_config import comment_text, each_copy, load_jsonc, loads_jsonc

ADD_HOST = "--add-host=host.docker.internal:host-gateway"
CAPS = ("--cap-add=NET_ADMIN", "--cap-add=NET_RAW")


def run_args(text: str) -> list[str]:
    """The ``runArgs`` array of a JSONC source."""
    return loads_jsonc(text).get("runArgs", [])


@each_copy
def test_run_args_map_host_docker_internal_to_host_gateway(path: Path) -> None:
    args = load_jsonc(path)["runArgs"]
    assert ADD_HOST in args
    assert args.count(ADD_HOST) == 1


@each_copy
def test_run_args_keep_the_firewall_capabilities(path: Path) -> None:
    args = load_jsonc(path)["runArgs"]
    for cap in CAPS:
        assert cap in args


@each_copy
def test_run_args_stay_on_one_line(path: Path) -> None:
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if '"runArgs":' in ln]
    assert len(lines) == 1
    assert lines[0].rstrip().endswith("],")
    assert ADD_HOST in lines[0]


@each_copy
def test_add_host_is_explained(path: Path) -> None:
    comments = comment_text(path.read_text(encoding="utf-8"))
    for needle in ("--add-host", "host-gateway", "Linux Docker Engine", "colima", "Docker Desktop"):
        assert needle in comments


@each_copy
def test_proxy_and_gateway_still_name_host_docker_internal(path: Path) -> None:
    env = load_jsonc(path)["containerEnv"]
    assert env["HTTPS_PROXY"] == "http://host.docker.internal:3128"
    assert env["MCP_GATEWAY_HOST"] == "host.docker.internal"


@each_copy
def test_dropping_the_runarg_is_caught(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    mutated = text.replace(f', "{ADD_HOST}"', "")
    assert mutated != text
    assert ADD_HOST not in run_args(mutated)
