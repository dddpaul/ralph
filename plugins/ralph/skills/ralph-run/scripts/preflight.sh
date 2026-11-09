#!/usr/bin/env bash
# Thin launcher shim for the ralph.preflight Python module.
#
# Exists solely so /ralph-run can invoke the module as `bash <abs-path>` (no
# inline env-var prefix), which Claude Code's permission matcher CAN key an
# allow rule on. It sets PYTHONPATH to its own directory (where the `ralph`
# package lives) and execs the module. No orchestration logic lives here —
# that stays in Python.
#
# `uv run` puts the interpreter environment's bin directory first on PATH (for
# Homebrew Python that is /opt/homebrew/bin, which may hold its own backlog);
# RALPH_CALLER_PATH carries the caller's PATH so the module restores it and
# resolves backlog, devcontainer and ccusage the way the caller would.
set -euo pipefail
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
RALPH_CALLER_PATH="$PATH" PYTHONPATH="$SCRIPTS_DIR" exec uv run --no-project python -m ralph.preflight "$@"
