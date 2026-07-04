# Feature Review: ralph-marketplace

**Date:** 2026-07-04
**Reviewer:** ralph-reviewer agent (cumulative cross-task review)
**Feature slug:** ralph-marketplace
**In-scope tasks:** TASK-187, 188, 190, 191, 192, 193, 194, 195, 196, 197 (TASK-189 folded into 188, archived)
**Diff range:** `5472d90` (task-184, pre-feature) → HEAD

**Verdict: Aligned**

**Passes run:** 1 (PRD Coverage), 2 (Non-Goal Protection), 3 (Brainstorm Scope Cuts), 4 (Success-Metric Realism), 5 (Out-of-Scope Creep)
**Passes skipped:** none — PRD and brainstorm both present; PRD carries Non-Goals and Success Metrics sections.

_No custom rules file at `.claude/ralph-review-rules.md` (absent) — standard rubric only._

All three cross-task invariants independently re-verified against `master` rather than trusting the task notes. All three hold. Gates re-run from the new layout: `uv run ruff check .` clean, `uv run pytest` 185 passed.

## Intent → Implementation Matrix

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| US-001 / FR-1 | `dddpaul-ralph` marketplace + `ralph` plugin manifests, valid JSON | Delivered | `.claude-plugin/marketplace.json` (name `dddpaul-ralph`, 1 plugin, `source: ./plugins/ralph`) + `plugins/ralph/.claude-plugin/plugin.json` (`name: ralph`, `version 0.1.0`, author/homepage/repository/license); both `jq .` exit 0 |
| US-002 / FR-2 | 10 skills + 2 agents relocated under `plugins/ralph/`, scripts+tests ride along | Delivered | `plugins/ralph/skills/` (10 dirs), `plugins/ralph/agents/{ralph-reviewer,task-reviewer}.md`, `ralph-run/scripts/` + `ralph-run/tests/`; old top-level `skills/` and `agents/` dirs absent |
| US-003 | pyproject + bats repointed; suites green | Delivered | `pyproject.toml:15,21,22,26,27` all point at `plugins/ralph/skills/ralph-run/...`; pytest 185 passed |
| US-004 / FR-3 (a) | 5-tier resolver, both shims byte-identical | Delivered | `ralph.sh:17-63` tiers 1→5 in exact PRD order (env → in-repo → `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills` → `plugins/cache/*/ralph/*/…` via `sort -V \| tail -n 1` → clear error). Both copies sha `2b2fc18…` (identical); `bash -n` clean; ralph-init gate checks plugin-installed (`SKILL.md` plugin-cache glob) not fixed path |
| US-005 / FR-4 (b) | Helpers use `${CLAUDE_PLUGIN_ROOT}`; verbatim-`$HOME` guidance gone | Delivered | `ralph-run/SKILL.md:82,122`, `ralph-status/SKILL.md:63`, `ralph-status-watch/SKILL.md:73`; no `$HOME/.claude/skills` helper paths remain in moved skills (only a narrative line documenting the removal) |
| US-006 (b) | wait-heartbeat read-only; cleanup relocated | Delivered | `wait-heartbeat.sh` execs module only (no write/rm); `wait_heartbeat.py` has no unlink/write (only `sys.stdout.buffer.write`); cleanup moved to `ralph-run/SKILL.md:122` (`&& rm -f backlog/.ralph-launch.log`) |
| US-007 / FR-5 (b) | Permission-seeding subsystem deleted | Delivered | ralph-init Step 3.7b is now the pptx merge (no RULE_PRE/HB/UTC seeding); template `settings.local.json` carries zero narrow `.claude/skills` rules; Step 3.10 verifies only pptx rules; zero-prompt smoke test at `SKILL.md:329` |
| US-008 / FR-6 | `ralph-sync` deleted | Delivered | `.claude/skills/ralph-sync/` gone; `git ls-files` shows no tracked ralph-sync files except backlog task history |
| US-009 / FR-8 (c) | R11 parity repointed | Delivered | `task-reviewer-rules.md:96-118` — 9-row table all `plugins/ralph/skills/ralph-init/templates/...`; both shims in parity set, documented byte-identical; no stale top-level `skills/` inside R11 |
| US-010 | Docs updated | Delivered | README:28-29,54-55 use `/plugin marketplace add` + `/plugin install ralph@dddpaul-ralph`; arch paths at `plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py`; CLAUDE.md:107 flips to "This repo **IS** its own Claude Code plugin marketplace" |
| US-011 | Devcontainer plugin-cache reachable | Delivered | `.devcontainer/devcontainer.json` == template (diff empty); whole-`~/.claude` bind mount covers `plugins/cache/`; README:325-353 documents tier-4 smoke test |
| FR-7 | pytest + bats + ruff green from new layout | Delivered (with caveat) | ruff clean; pytest 185 passed; shim.bats — see Drift note 4 (macOS symlink artifact, not a defect) |

## Non-Goal Violations

None detected.
- Legacy tier-3 resolver **kept** (`ralph.sh:31-36`) — matches the "removal is a post-transition follow-up" non-goal.
- **One** plugin only — `marketplace.json .plugins | length == 1`; no core/authoring split.
- **No plugin hooks / manifest perms** — `plugin.json` keys are only author/description/homepage/keywords/license/name/repository/version; `has("hooks")==false`, `has("permissions")==false`.
- **Repo not renamed** — plugin `ralph`, marketplace `dddpaul-ralph`, homepage `github.com/dddpaul/ralph` (assumed usable as-is).

## Scope Cut Violations

None detected. Every brainstorm scope cut is honored: single plugin, no shipped hooks, no manifest permission injection, stale allow-rules in other projects left untouched, not added to `dddpaul-claude-skills`. The one "optional" cut — making wait-heartbeat read-only — was intentionally promoted to US-006 and implemented (belt-and-suspenders, PRD-sanctioned; not a violation).

## Success Metric Assessment

| Metric | Status | Notes |
|--------|--------|-------|
| Public install in two `/plugin` commands | Hypothesis only | Requires a clean-machine/network install; not automatable in-repo. Manifests validate and install strings are documented, but no test exercises the real `/plugin` path. Acceptable and expected. |
| Zero prompts beyond devcontainer bypass on a fresh `ralph-init` run | Hypothesis only | Backed by the documented manual smoke test (`ralph-init/SKILL.md:329-361`) which exercises the real permission matcher. Structurally supported: template `settings.local.json` sets `autoAllowBashIfSandboxed: true`, helpers are read-only and `${CLAUDE_PLUGIN_ROOT}`-invoked. No automated assertion (the unit tests can't drive the harness). |
| Test suites green; real autonomous iteration completes | Measurable (suites) / Hypothesis (real run) | pytest 185 + ruff verified this session; the "real end-to-end iteration" is a manual claim. |

## Drift List

No unexplained scope creep in the code. The diff is ~90 pure `git mv` renames + config repoint + resolver + doc edits, all traceable to a requirement. Four minor hygiene notes (none blocking, none touching the three cross-task invariants):

1. `.claude/task-reviewer-rules.md:3` and `:186` and `:206` still carry stale **top-level** `agents/task-reviewer.md` and `skills/ralph-task/SKILL.md` / `skills/ralph-init/templates/...` references — but these live in R16 and the header/loading narrative, **outside R11**. TASK-195 scoped its edits to R11 only, and no AC covers R16, so this is expected and invariant (c) still holds (R11 is clean). Recommend a follow-up sweep to repoint the R16/header references to `plugins/ralph/...`.
2. `backlog/docs/doc-1 …` and `doc-2 …` reference the old `skills/ralph-run/scripts/ralph.sh`. These are immutable historical research/overview docs (they predate even the Python port). `backlog/docs/` is technically not in the AC's excluded set (`backlog/archive` + `design/`), but the content is historical narrative, not live wiring. Cosmetic.
3. `plugins/ralph/skills/ralph-run/scripts/wait-heartbeat.sh` header comment still rationalizes the shim as existing so the "permission matcher CAN key an allow rule on" it — stale reasoning now that the allow-rule subsystem is deleted. Harmless, not load-bearing.
4. `tests/integration/shim.bats` "resolver tier 2" reports a **false** failure on this macOS host: `setup_test_dir` uses `mktemp` under `/var/folders/…` (a symlink to `/private/var/…`), and the shim's `RALPH_PROJECT_ROOT="$(… pwd -P)"` canonicalizes to `/private/var/…` while the test builds the expected `$orch` from the non-canonical `/var/…` path. Tier-2 reproduced with a canonical scratch path and it resolved exactly (`UV_RAN=<orch>`); tiers 4 and 5 pass, and the byte-identity test passes. This is a test-harness/`pwd -P` portability nit (the TASK-190 reviewer got 4/4 on their host), not a resolver defect. Optional: canonicalize `TEST_DIR` (or the expected path) in `helpers/common.bash` so the suite is robust on macOS.

## Reviewer Notes

- The three high-risk cross-task invariants are all solid: (a) resolver precedence is exactly the US-004 order, both shim copies are genuinely byte-identical (verified by sha, not just `diff`), and tier-2/tier-4 resolution behavior manually confirmed; (b) the zero-allow-rules invariant is complete end-to-end — seeding step gone, template has no narrow skills rules, helpers `${CLAUDE_PLUGIN_ROOT}`-invoked, wait-heartbeat write-free; (c) R11 parity table is fully repointed with the shim pair correctly documented as byte-identical.
- The task decomposition handled cross-task ordering cleanly — each task's notes accurately predicted which stale references belonged to sibling tasks, and the final state has no gaps between them.
- Suggested single follow-up task: repoint the remaining R16/header `skills/` + `agents/` references in `.claude/task-reviewer-rules.md` and (optionally) harden `shim.bats` against the macOS symlink path issue. Neither blocks this feature.
