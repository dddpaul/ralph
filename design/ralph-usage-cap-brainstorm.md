---
export: true
title: Ralph Usage Cap
type: design
---

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

---

## Addendum: ccusage exposes tokens not percentage — pivot to projection-based cap (added 2026-06-11)

### Why

Empirical probing of ccusage 20.1.0 against the live host showed the assumed measurement source does not exist:

- `ccusage blocks --active --token-limit max --json` returns `totalTokens`, `projection.totalTokens`, `costUSD`, `burnRate`, and per-model breakdowns — but **no `used_percent`, no plan-limit field, no `remaining_percent`**.
- `--token-limit max` only affects in-table warnings (warns when usage approaches a threshold *the operator passes in*), not the JSON shape.
- `ccusage weekly --json` is date-grouped totals with no quota awareness.
- `ccusage statusline` shows `$X session / $Y today / $Z block` but no percentage.
- No quota-aware subcommand exists in 20.1.0 (`ccusage --help | grep -i limit\|quota\|remain` is empty).

Anthropic's actual 5h token caps per subscription tier are not published in machine-readable form and not derived by ccusage. The Claude web UI's "remaining %" is computed server-side and not surfaced via any local CLI.

This invalidates the percentage-based design above. The user picked option **β** (projection-based, single absolute-token flag).

### What changed

Polarity: **drop "percentage" entirely.** The cap is an absolute 5h-window token threshold, expressed in tokens. The operator picks the number based on their plan tier (well-known for Max subscribers, fuzzier for Pro — operator chooses what they're comfortable with). The 100-as-disabled convention is replaced by **0-as-disabled** (matches "no threshold").

Measurement: compare ccusage's `blocks[0].projection.totalTokens` (extrapolated 5h-block total at current burn rate) against the operator's cap. Pause proactively *before* the limit is hit — leverages ccusage's own burn-rate math.

| Old shape | New shape |
|---|---|
| `--usage-cap <pct>` (default 80, range 0–100, 100 disables) | `--usage-cap-5h-tokens <N>` (default 0 = disabled, integer) |
| Read 5h.<model>.used_percent + weekly.<model>.used_percent | Read `blocks[0].projection.totalTokens` from `ccusage blocks --active --token-limit max --json` |
| Pause if either window's used% ≥ cap | Pause if `projection.totalTokens` ≥ cap |
| Both 5h + weekly windows | 5h only (weekly dropped — ccusage doesn't expose weekly quota; revisit later as a follow-up) |
| Status: `paused_reason: usage_5h_opus_82pct` | Status: `paused_reason: projected_5h_opus_49M_over_50M_cap` (token-based) |
| Status: `paused_cap` (int %) | Status: `paused_cap_5h_tokens` (int tokens) + `paused_projection_tokens` (int tokens) |
| ralph-status: `Paused: usage 5h opus 82% (cap 80%)` | ralph-status: `Paused: projected 5h opus ~49M tokens (cap 50M)` |

### Implementation checklist

- [ ] Edit TASK-135 description and all 10 ACs in place (`backlog task edit 135 --remove-ac N --ac "..."` per AC, descending order to keep indices stable).
- [ ] usage-check.sh signature unchanged: `$1=MODEL`, `$2=CAP_5H_TOKENS`. Exit codes unchanged. Internal logic switches to `projection.totalTokens` read via `ccusage blocks --active --token-limit max --json | jq '.blocks[0].projection.totalTokens'`.
- [ ] `--token-limit max` flag is harmless even when irrelevant — keep it for forward compatibility with future ccusage versions that may surface a limit field.
- [ ] CAP=0 short-circuit verified in unit tests (PATH-mocked ccusage must NOT be invoked).
- [ ] Brainstorm doc kept; the original sections record the rejected percentage-based path for posterity (rule R14: content preservation).
- [ ] Weekly-window check is dropped from scope for v1; if it turns out to matter, file a follow-up task once Anthropic / ccusage expose a weekly quota field.

---

## Addendum: token cap still binds to subscription limits — pivot to time-based boundary heuristic (added 2026-06-11)

### Why

Option β (projection-based, `--usage-cap-5h-tokens <N>`) closes the percentage-vs-tokens gap but does **not** close the operator-knowledge gap. Picking a sensible `N` still requires knowing the 5h-block token allowance of the subscription tier, which Anthropic does not publish in machine-readable form and no local CLI surfaces.

Probing of all candidate sources confirmed the gap is structural, not a ccusage limitation:

- `claude --help`: no `usage` / `quota` / `limit` / `remaining` / `status` subcommand.
- `claude -p /status`: "/status isn't available in this environment" (interactive-only).
- `claude -p /cost`: returns session cost (USD), not subscription %.
- `ccusage statusline`: emits `$X session / $Y today / $Z block (Nh left)` — dollars and time, no %.
- API rate-limit response headers (`anthropic-ratelimit-tokens-remaining`): API tier TPM/RPM, not subscription 5h window. Wrong dimension.

The percentage the Claude web UI displays is computed server-side and is not exposed via any local source. Any token- or cost-based cap will retain the same operator-knowledge tax.

Two options remained: (a) accept the tax and document tier-by-tier rough caps in the SKILL.md (the "honest documentation" path), or (b) sidestep quota entirely by using the **block-boundary heuristic** — pause when the active 5h block is within N minutes of its end so Ralph never starts a task that would cross the boundary and die mid-stream. The user picked (b).

The boundary heuristic does not catch cumulative drain inside the block — Ralph could still blow through a small plan's quota mid-block without warning. The user accepted that trade as v1 — boundary protection covers the dominant failure mode (task killed by block reset) and needs zero plan knowledge.

### What changed

| Old shape (β) | New shape (time-based) |
|---|---|
| `--usage-cap-5h-tokens <N>` (integer ≥ 0, 0 disables) | `--block-end-buffer-min <N>` (integer ≥ 0, 0 disables) |
| Read `blocks[0].projection.totalTokens` | Read `blocks[0].endTime` and `blocks[0].isActive` |
| Pause if `projection.totalTokens` ≥ cap | Pause if `isActive` and (`endTime - now`) ≤ buffer minutes |
| Both MODEL and CAP args to helper | Single BUFFER_MIN arg (MODEL no longer needed — block end is model-agnostic) |
| Status: `paused_reason: projected_5h_opus_49M_over_50M_cap` | Status: `paused_reason: block_end_in_12min_below_30min_buffer` |
| Status: `paused_cap_5h_tokens`, `paused_projection_tokens` | Status: `paused_buffer_min`, `paused_remaining_min`, `paused_block_end_time` |
| ralph-status: `Paused: projected 5h opus ~49M tokens (cap 50M)` | ralph-status: `Paused: block ends in 12m (buffer 30m)` |
| ccusage command remains `ccusage blocks --active --token-limit max --json` (token-limit flag now irrelevant but harmless) | same — only the parsed fields change |
| 5h window only | 5h window only (same — weekly remains out of scope) |

### Implementation checklist

- [ ] Edit TASK-135 title, description body, and all 10 ACs in place to match the time-based shape.
- [ ] usage-check.sh signature collapses to `$1 = BUFFER_MIN`. Exit codes unchanged. Internal logic switches to `endTime - now` math via `jq` + `date`.
- [ ] BUFFER_MIN=0 short-circuit verified in unit tests (PATH-mocked ccusage must NOT be invoked).
- [ ] `--token-limit max` retained on the ccusage call for forward compatibility, even though no token threshold is consumed.
- [ ] "No active block" (`isActive: false` or `isGap: true`) exits 0 (proceed) — Ralph is not currently in a 5h window, so the boundary doesn't apply.
- [ ] Status fields renamed in `backlog/.ralph-status.json` schema and in ralph-status / ralph-status-watch renderers.
- [ ] Add a one-line scope note: cumulative drain inside the block is **not** detected by this heuristic; future follow-up can add a token-based co-trigger if it bites in practice.
