# Feature Review: ralph-usage-cap (2026-06-12)

**Verdict: Aligned**

Authoritative intent = TASK-135 acceptance criteria (10 ACs) + brainstorm second addendum (2026-06-11) "What changed" table. The original percentage-based and first-addendum projection-based sections are preserved for R14 content preservation but are explicitly out of design scope.

Diff range: `f6a5897..HEAD` (11 files, 897 insertions, 40 deletions). Two implementation commits (`65e31fb` initial, `392dfc7` R12 fix) plus task-lifecycle commits.

---

## Intent → Implementation Matrix

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| AC#1 | `usage-check.sh` exists, `$1=BUFFER_MIN`, exit 0/1/2 with the specific cases | Met | `skills/ralph-run/scripts/usage-check.sh` L20-101. BUFFER_MIN short-circuit at L29, missing ccusage L33, missing jq L37, missing date L41, ccusage nonzero L51, unparseable JSON L56, no active block / isGap L61-67, missing endTime L70-74, malformed endTime L77-83, threshold compare L96-99. Stdout string format `block_end_in_${REMAINING_MIN}min_below_${BUFFER_MIN}min_buffer` matches AC text exactly. |
| AC#2 | `ralph.sh` accepts `--block-end-buffer-min <N>`, default 0=disabled, integer ≥ 0; mirrored byte-identical in ralph-init template | Met | `ralph.sh` L51 default 0, L133-140 both `--flag value` and `--flag=value` forms, L209-212 integer validation, L484 short-circuit (no ccusage invocation). R11 parity confirmed by `diff ralph.sh skills/ralph-init/templates/root/ralph.sh` and `diff ralph.sh skills/ralph-run/scripts/ralph.sh` — both IDENTICAL byte-for-byte. |
| AC#3 | `preflight.sh` invokes helper, exit 1 refuses, exit 2 writes disabled-flag and warns and continues; BUFFER_MIN=0 = no invocation | Met | `skills/ralph-run/scripts/preflight.sh` L11 default 0, L18-19 flag parsing, L124-128 integer validation, L129 gates the helper call on BUFFER_MIN>0, L143-147 exit 1 refusal with reason string, L148-153 exit 2 warns to stderr + creates `backlog/.ralph-usage-check-disabled`, L158-160 buffer=0 skip message. |
| AC#4 | ralph.sh main loop calls helper at top of each iteration; exit 1 sets STATE=paused + 5 PAUSED_*; exit 2 warns once via flag file | Met | `ralph.sh` L719-730 calls `_check_usage_or_pause` at the top of the `for i in $(seq 1 MAX_ITERATIONS)` body (before any task selection or `claude --print`). L483-527 helper function: L484 short-circuit, L499-513 exit 1 populates all five PAUSED_* fields + re-reads endTime for the status payload, L515-521 exit 2 once-only warn gated by `-f USAGE_DISABLED_FLAG`. |
| AC#5 | `.ralph-status.json` gains 5 fields populated only when state=paused | Met | `ralph.sh` L397-408 `_update_status` populates `paused_reason_json` / `paused_buffer_json` / `paused_remaining_json` / `paused_block_end_json` / `paused_at_json` only inside `if [[ "$state" == "paused" ]]`. L412 emits them as JSON fields. Default value `null` preserves the "only when paused" contract. |
| AC#6 | `ralph-status` renders extra paused line + resume hint | Met | `skills/ralph-status/SKILL.md` L26 extracts the five paused_* fields. L102-107 renders `Paused: block ends in <N>m (buffer <M>m)` followed by `resume with /ralph-run`. L109 explicitly forbids auto-resume. |
| AC#7 | `ralph-status-watch` treats paused as terminal, does NOT declare crash | Met | `skills/ralph-status-watch/SKILL.md` L44 state enum includes `"paused"`. L67 Rule (e) condition includes paused. L108 explicitly: "do NOT schedule the next tick. `paused` is a clean operator-resumable terminal state; the watch loop must NOT declare crash via heartbeat staleness when state=paused." Rule (f) condition at L114 still requires `state == "running"`, so a paused state can never trigger crash. |
| AC#8 | settings.local.json template gains 2 allowlist rules | Met | `skills/ralph-init/templates/claude/settings.local.json` L31 `Bash(ccusage:*)` and L32 `Bash(./skills/ralph-run/scripts/usage-check.sh:*)`. |
| AC#9 | `tests/unit/usage-check.bats` covers 10 enumerated cases | Met | All 10 enumerated cases present (buffer=0 short-circuit, no-active-block isActive=false, gap-block isGap=true, remaining-above-buffer pass, remaining-at-or-below-buffer fail, ccusage-missing exit-2, jq-missing exit-2, ccusage-nonzero exit-2, malformed-JSON exit-2, endTime-field-missing exit-2). File has 12 tests total — 10 ACed + 2 bonus (non-integer arg / no-arg). |
| AC#10 | `tests/integration/usage-pause.bats` covers 4 enumerated cases | Met | All 4 enumerated cases present (preflight refuses on usage-check 1, preflight warns + creates disabled-flag on usage-check 2, ralph.sh loop sets state=paused on mid-loop usage-check 1, per-iteration warn fires exactly once across iterations) + 1 bonus (preflight skips ccusage when buffer=0). |
| Brainstorm 2nd addendum: single BUFFER_MIN arg (MODEL dropped) | Helper signature: `$1=BUFFER_MIN` only | Met | usage-check.sh L20, no MODEL handling anywhere. |
| Brainstorm 2nd addendum: reads `blocks[0].endTime` and `blocks[0].isActive` | Time-based logic only | Met | usage-check.sh L61-62 reads isActive/isGap, L70 reads endTime. No `projection.totalTokens` read. |
| Brainstorm 2nd addendum: paused_reason format `block_end_in_<rem>min_below_<buffer>min_buffer` | Reason string format | Met | usage-check.sh L97 emits exactly that format; ralph.sh L503 regex parses it back. |
| Brainstorm 2nd addendum: paused_buffer_min, paused_remaining_min, paused_block_end_time | Renamed status fields (NOT `paused_cap_5h_tokens`) | Met | All field names match the time-based addendum. No token-based field names leak through. |
| Brainstorm 2nd addendum: ralph-status renders `block ends in 12m (buffer 30m)` | Renderer text | Met | ralph-status SKILL.md L105 uses the exact time-based wording. |
| Brainstorm 2nd addendum: `--token-limit max` retained for forward compat | ccusage CLI invocation | Met | usage-check.sh L49 and ralph.sh L510 both pass `--token-limit max`. Comment at L46-48 explicitly notes the retention reason. |
| Brainstorm 2nd addendum: "No active block (isActive=false or isGap=true) exits 0" | No-block proceed semantics | Met | usage-check.sh L66 `[[ "$IS_ACTIVE" != "true" || "$IS_GAP" == "true" ]]` exits 0. |

---

## Scope Cut Compliance

Brainstorm "Out of scope (deliberate)" items:

- **Cumulative drain inside block** — correctly cut. No `projection.totalTokens` / `totalTokens` read anywhere in the diff.
- **Auto-resume / sleep-until-next-block** — correctly cut. ralph.sh L727 prints "Resume with /ralph-run" and exits; ralph-status SKILL.md L109 reiterates the no-auto-resume contract.
- **Env-var fallback `RALPH_BLOCK_END_BUFFER_MIN`** — correctly cut. Diff shows only `RALPH_USAGE_CHECK_SCRIPT` and `RALPH_USAGE_DISABLED_FLAG` env vars, both used for test-injection of paths, not as a buffer-value fallback.
- **Token / dollar / percentage caps** — correctly cut. No `--usage-cap` or `--usage-cap-5h-tokens` flag, no percentage or token-threshold logic.
- **Auto-install ccusage in devcontainer Dockerfile** — correctly cut. Diff does not touch any Dockerfile.
- **Weekly window** — correctly cut. No `ccusage weekly` call anywhere.

No scope cut violations detected.

---

## Drift

No drift detected.

Scanned the 11-file diff for hunks not traceable to an AC or addendum item:

- `skills/ralph-status-watch/SKILL.md` line-44 / line-67 changes to the state enumeration — traceable to AC #7 and to the second pass of task-reviewer feedback (commit `392dfc7` "Fix R12 contradiction in ralph-status-watch state enumeration"). The R12 contradiction was that state-list and Rule-(e) condition listed different terminal states; the fix harmonizes them.
- `backlog/tasks/task-135 - …md` — task file modifications (description rewrite + ACs to reflect the 2nd-pivot shape, status flips, implementation notes). Standard task-lifecycle artifact, traceable to Task Lifecycle Step 5/6.

---

## Reviewer Notes

- **R11 parity is hard-verified, not just claimed.** `diff` between the three ralph.sh copies returns no output for both pairs (`ralph.sh` ↔ `skills/ralph-init/templates/root/ralph.sh`; `ralph.sh` ↔ `skills/ralph-run/scripts/ralph.sh`). This survives the second-pivot rewrite cleanly.
- **The helper guards `date` availability** in addition to ccusage/jq (usage-check.sh L41-44). AC #1 mentions "ccusage missing, jq/date missing" — implementation covers all three. Bonus rigor, not drift.
- **endTime field re-read in ralph.sh for status payload (L508-511) is a small duplication.** The helper computed `endTime`, exited 1, and dropped it; ralph.sh then re-invokes ccusage+jq to recover it for `paused_block_end_time`. Functionally correct and noted as "best effort" with empty fallback. Could in principle be passed via stdout from the helper, but the current design keeps the helper's stdout contract minimal (one grep-friendly reason token). Not a bug, just a design observation.
- **PAUSED_REMAINING_MIN extraction via regex on the reason string** (ralph.sh L503-507) couples the status-payload code to the reason-string format. Same observation as above — works correctly with the AC-mandated reason string, no functional issue.
- **Test count corroboration:** AC #9 enumerates 10 unit cases, file has 12 (10 mandated + 2 bonus argument-validation cases). AC #10 enumerates 4 integration cases, file has 5 (4 mandated + 1 bonus buffer=0 negative). Implementation notes claim "17 new tests pass (12 unit + 5 integration)" — matches the file structure.
- **Brainstorm 1st addendum (rejected projection-based path) and original percentage-based section** are preserved verbatim in the brainstorm file (R14 content preservation). Diff confirms no leakage of `projection.totalTokens` / `used_percent` / `--usage-cap` into the implementation files.
- **One minor lint-level observation in preflight.sh L154-156:** the default `*)` case prints `verbose "check usage: WARN (unexpected exit $_uc_rc — continuing)"` but does not write the disabled-flag file or stderr-warn the user. Since usage-check.sh only emits 0/1/2 by contract, this branch is dead code — it would only fire if the helper contract changed. Cosmetic; not in scope of any AC.
