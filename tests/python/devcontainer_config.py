"""Shared reader for the devcontainer config files under test.

``devcontainer.json`` is JSONC: it carries ``//`` comments, so ``json.loads``
cannot read it raw. Every comment in the file sits on a line of its own, so
blanking those whole lines yields valid JSON. Inline trailing comments are
deliberately NOT stripped — the file has none, and a naive ``//`` split would
cut through values such as ``http://host.docker.internal:3128``.

Every ``test_devcontainer_*`` module reads config through this module, so the
live copy and the ralph-init template are always parsed the same way.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LIVE_DIR = REPO_ROOT / ".devcontainer"
TEMPLATE_DIR = REPO_ROOT / "plugins/ralph/skills/ralph-init/templates/devcontainer"
LIVE = LIVE_DIR / "devcontainer.json"
TEMPLATE = TEMPLATE_DIR / "devcontainer.json"
# Every devcontainer.json assertion runs on both copies: the live file and the
# ralph-init template that scaffolds it into new projects.
BOTH = (LIVE, TEMPLATE)
BOTH_IDS = ("live", "template")
each_copy = pytest.mark.parametrize("path", BOTH, ids=BOTH_IDS)

_COMMENT_LINE = re.compile(r"^[ \t]*//.*$", re.MULTILINE)
_COMMENT_ONLY = re.compile(r"^[ \t]*//")


def strip_jsonc(text: str) -> str:
    """Blank every whole-line ``//`` comment, keeping line numbers intact.

    Args:
        text: JSONC source.

    Returns:
        The source with comment-only lines emptied.
    """
    return _COMMENT_LINE.sub("", text)


def loads_jsonc(text: str) -> Any:
    """Parse JSONC source whose comments are all on lines of their own.

    Args:
        text: JSONC source.

    Returns:
        The decoded JSON value.

    Raises:
        json.JSONDecodeError: If the source is not valid once comments are gone.
    """
    return json.loads(strip_jsonc(text))


def load_jsonc(path: Path) -> Any:
    """Read and parse a JSONC file.

    Args:
        path: File to read.

    Returns:
        The decoded JSON value.
    """
    return loads_jsonc(path.read_text(encoding="utf-8"))


def comment_text(text: str) -> str:
    """Return only the whole-line ``//`` comments of a JSONC source.

    Args:
        text: JSONC source.

    Returns:
        The comment lines joined by newlines.
    """
    return "\n".join(line for line in text.splitlines() if _COMMENT_ONLY.match(line))


def mounts_matching(config: dict[str, Any], pattern: str) -> list[str]:
    """Return the ``mounts`` entries matching a regular expression.

    Args:
        config: Decoded devcontainer.json.
        pattern: Regex searched (not anchored) in each mount string.

    Returns:
        The matching mount strings, in file order.
    """
    return [m for m in config.get("mounts", []) if re.search(pattern, m)]


def target_pattern(target: str) -> str:
    """Regex matching a mount whose ``target=`` is exactly ``target``.

    Args:
        target: Literal target path, e.g. ``/workspace/.venv``.

    Returns:
        A regex that stops at the next ``,`` or end of string, so
        ``/workspace/.claude`` does not also match ``/workspace/.claude/x``.
    """
    return rf"target={re.escape(target)}(,|$)"


def source_pattern(source: str) -> str:
    """Regex matching a mount whose ``source=`` is exactly ``source``.

    Args:
        source: Literal source path.

    Returns:
        A regex that stops at the next ``,`` or end of string.
    """
    return rf"source={re.escape(source)}(,|$)"
