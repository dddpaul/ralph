#!/usr/bin/env bash
# Thin launcher shim for `python -m ralph.user_settings merge`.
#
# Merges the plugin's user-settings.json fragment into the given user settings
# file: appends missing allow rules and keys, never overwrites a value, and
# reports each differing one on stderr. Configuration management runs it from
# the installed plugin's installPath. No merge logic lives here — that stays in
# Python.
set -euo pipefail
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PYTHONPATH="$SCRIPTS_DIR" exec uv run --no-project python -m ralph.user_settings merge "$@"
