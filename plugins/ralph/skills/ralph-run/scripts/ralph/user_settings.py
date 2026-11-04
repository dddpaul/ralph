"""The plugin's user-settings fragment: what user settings miss, and a merge.

A plugin cannot ship allow rules, so ``plugins/ralph/user-settings.json`` holds
the common ones (plus ``attribution`` and ``sandbox``) for the user settings
file. The ``/ralph-run`` preflight lists the fragment entries the user settings
miss; configuration management runs the merge.

The merge never overwrites: it appends missing list items (the allow rules),
adds missing keys, and reports every value that differs from the fragment.

Usage: ``python -m ralph.user_settings merge <settings.json> [--fragment <path>]``
prints one ``added: <entry>`` line per change on stdout and one
``differs: <entry>`` line per kept differing value on stderr.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import cast

# user_settings.py → ralph/ → scripts/ → ralph-run/ → skills/ → the plugin root.
FRAGMENT = Path(__file__).resolve().parents[4] / "user-settings.json"


def load_json_object(path: Path) -> dict[str, object]:
    """Parse ``path`` as a JSON object; a missing file is an empty object.

    Raises:
        ValueError: the file is not valid JSON or not an object.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    data: object = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level is not a JSON object")
    return cast(dict[str, object], data)


def _label(path: str, value: object) -> str:
    return f"{path}={json.dumps(value, ensure_ascii=False)}"


def _item_label(path: str, item: object) -> str:
    """Label a list item: an allow rule reads as ``permissions.allow: <rule>``."""
    return f"{path}: {item}" if isinstance(item, str) else _label(path, item)


def _merge_into(
    target: dict[str, object],
    fragment: dict[str, object],
    prefix: str,
    added: list[str],
    differs: list[str],
) -> None:
    """Merge ``fragment`` into ``target`` in place, recording every entry."""
    for key, want in fragment.items():
        path = f"{prefix}{key}"
        if key not in target:
            target[key] = json.loads(json.dumps(want))
            added.extend(_leaves(path, want))
            continue
        have = target[key]
        if isinstance(want, dict) and isinstance(have, dict):
            _merge_into(
                cast(dict[str, object], have),
                cast(dict[str, object], want),
                f"{path}.",
                added,
                differs,
            )
        elif isinstance(want, list) and isinstance(have, list):
            have_list = cast(list[object], have)
            for item in cast(list[object], want):
                if item not in have_list:
                    have_list.append(item)
                    added.append(_item_label(path, item))
        elif have != want:
            differs.append(
                f"{path}: kept {json.dumps(have, ensure_ascii=False)}, fragment has "
                f"{json.dumps(want, ensure_ascii=False)}"
            )


def _leaves(path: str, value: object) -> list[str]:
    """Label every entry ``value`` holds, as ``_merge_into`` reports them."""
    if isinstance(value, dict):
        return [
            leaf
            for k, v in cast(dict[str, object], value).items()
            for leaf in _leaves(f"{path}.{k}", v)
        ]
    if isinstance(value, list):
        return [_item_label(path, item) for item in cast(list[object], value)]
    return [_label(path, value)]


def merge(
    fragment: dict[str, object], settings: dict[str, object]
) -> tuple[dict[str, object], list[str], list[str]]:
    """Return ``(merged, added, differs)``; ``settings`` itself is not changed."""
    merged = cast(dict[str, object], json.loads(json.dumps(settings)))
    added: list[str] = []
    differs: list[str] = []
    _merge_into(merged, fragment, "", added, differs)
    return merged, added, differs


def missing_entries(
    fragment: dict[str, object], settings: dict[str, object]
) -> list[str]:
    """List the fragment entries ``settings`` lacks; a differing value is not missing."""
    return merge(fragment, settings)[1]


def _write_atomic(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".settings.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        if path.exists():
            os.chmod(tmp, path.stat().st_mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _usage() -> int:
    print(
        "Usage: merge-user-settings.sh <settings.json> [--fragment <path>]",
        file=sys.stderr,
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] != "merge":
        return _usage()
    args = args[1:]
    fragment_path = FRAGMENT
    if len(args) == 3 and args[1] == "--fragment":
        fragment_path = Path(args[2])
    elif len(args) != 1:
        return _usage()
    settings_path = Path(args[0])
    try:
        fragment = load_json_object(fragment_path)
        settings = load_json_object(settings_path)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    merged, added, differs = merge(fragment, settings)
    if added:
        _write_atomic(settings_path, merged)
    for entry in added:
        print(f"added: {entry}")
    for entry in differs:
        print(f"differs: {entry}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
