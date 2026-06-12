# Ralph Usage Cap

Pause the Ralph autonomous loop when Claude Code subscription usage hits a configurable cap (default 80% used) so Ralph never starts a task it cannot finish before the quota resets.

## Architecture decision

- **Measurement source:** `ccusage` (third-party CLI that parses `~/.claude/projects/**/*.jsonl`).
- **Polarity:** *used* tokens (matches the Claude web UI), not *remaining*. Pause when used ≥ cap.
- **Hook points:** both preflight (`skills/ralph-run/scripts/preflight.sh`) and per-iteration (top of `ralph.sh` main loop body, before each `claude --print`).
- **Stop behavior:** clean exit, new terminal state `paused` written to `backlog/.ralph-status.json`. No auto-resume.
- **Scope of check:** active model only (whatever `--model` is set to, default `claude-opus-4-7`), both windows (5h *and* weekly). Pause if either window's used% ≥ cap.
- **Configurability:** `--usage-cap <pct>` CLI flag on `ralph.sh`, default 80, range 0–100. `100` reserved as "disabled" — short-circuits without calling ccusage.
- **Missing ccusage / jq / parse failure:** fail-open. Warn once to stderr, continue running. Per-iteration warns suppressed via `backlog/.ralph-usage-check-disabled` flag file.

## Components / flows

- **New helper `skills/ralph-run/scripts/usage-check.sh`** (~50 LOC). Args: `$1 = MODEL`, `$2 = USAGE_CAP`. Exit codes: `0` OK, `1` cap tripped (prints `usage_<window>_<model_short>_<pct>pct` to stdout), `2` cannot measure (warn-skip). Calls `ccusage blocks --json` (verify exact command shape during implementation), extracts 5h + weekly used% for the active model via `jq`.
- **`preflight.sh` gains one step:** runs `usage-check.sh "$MODEL" "$USAGE_CAP"`. Exit 1 → refuse launch with the reason string. Exit 2 → warn, continue, write the disabled-flag file.
- **`ralph.sh` main loop:** at top of each iteration body (before the existing `timeout … claude --print` line around L696), call `usage-check.sh`. Exit 1 → set `state=paused`, populate `paused_reason` / `paused_cap` / `paused_at`, `break`. Exit 2 → continue silently if the disabled-flag file exists, else warn once and write the flag.
- **`backlog/.ralph-status.json` gains 3 new fields** (populated only when `state=paused`): `paused_reason` (e.g. `usage_5h_opus_82pct`), `paused_cap` (int, echo of the active cap), `paused_at` (ISO 8601 UTC).
- **`ralph-status` skill** renders an extra line when `state=paused`: `Paused:  usage 5h opus 82% (cap 80%)  resume with /ralph-run`.
- **`ralph-status-watch` skill** treats `paused` as a clean terminal state alongside `completed` / `failed` — stops polling, does not declare crash.
- **`ralph-init` template parity (R11):** `--usage-cap` flag mirrored in `skills/ralph-init/templates/root/ralph.sh`; new allowlist rules for `Bash(ccusage:*)` and `Bash(./skills/ralph-run/scripts/usage-check.sh:*)` mirrored in the template `settings.local.json` jq-merge fragment.
- **Tests:** new `tests/unit/usage-check.bats` (8–10 cases — above-cap pass, 5h-below, weekly-below, ccusage-missing, jq-missing, ccusage-nonzero, malformed-json, missing-block, `--usage-cap 100` short-circuit verified by PATH-mocked ccusage). New `tests/integration/usage-pause.bats` (preflight cap-trip refusal, preflight exit-2 warn-continue, ralph.sh mid-loop pause, one-time-warn invariant). Update `tests/integration/status-file-integration.bats` to assert the three new paused fields.

## Scope cuts

- **Auto-resume (sleep until reset):** rejected. Long-blocking loop would break heartbeats and confuse ralph-status-watch. Pause-resume is operator-driven via re-running `/ralph-run`.
- **Per-window separate caps** (different threshold for 5h vs weekly): premature; YAGNI.
- **Env-var fallback `RALPH_USAGE_CAP`:** the CLI flag covers the common case; add only on request.
- **Auto-install ccusage in devcontainer Dockerfile:** rejected. Fail-open with warning keeps backward compatibility; users opt in by installing ccusage themselves.
- **Checking all models (both Opus and Sonnet) regardless of active model:** rejected. False positives on Sonnet exhaustion would pause an Opus loop.
- **Using API rate-limit headers as the measurement source:** rejected. They reflect API-tier RPM/TPM, not subscription 5h/weekly windows.
- **Splitting status rendering into a separate task:** rejected. Status delta is a few lines of skill code; staying inside one purpose-value keeps the PR coherent.

## Open questions

- **ccusage CLI output schema:** the assumed field names (`tokens.used_pct` etc.) are pending verification against the installed ccusage version at implementation time. If the schema differs, `usage-check.sh` absorbs the difference; no design change.
- **`ccusage` invocation that surfaces both 5h *and* weekly in one call:** `ccusage blocks --json` is the assumed best bet but `ccusage weekly --json` may be needed as a second call. Implementer decides based on actual CLI surface.
- **Model-name matching in ccusage output:** ralph.sh passes `claude-opus-4-7` but ccusage may key on `claude-opus-4` or `opus-4-7`. The helper needs a prefix-match strategy. Trivial fix at build time.

## Hand-off

Next: `ralph-task` with `feature=ralph-usage-cap` to create the single backlog task carrying the AC set (preflight integration, loop integration, status fields, ralph-status rendering, ralph-status-watch terminal-state handling, ralph-init template parity for `--usage-cap` flag + allowlist, the two new bats files, and the existing-bats update). PRD-shape escape valve: ralph-task's pre-check will redirect to `ralph-prd` → `ralph-backlog` if it disagrees on size — but at ~8 ACs this fits the one-task heuristic.
