---
export: true
title: 'PRD: Ralph → Claude Code Plugin Marketplace'
type: design
---

# PRD: Ralph → Claude Code Plugin Marketplace

## Introduction

Convert this repo into its own Claude Code plugin marketplace shipping **one cohesive `ralph` plugin** (all `ralph-*` skills + both agents). Today skills/agents are distributed by hand-copying into `~/.claude/skills/` via the `ralph-sync` skill; installation is manual and updates are ad-hoc. A plugin marketplace makes install/update a single `/plugin` command and lets Ralph be shared publicly. The repo keeps its own Ralph dev role (it dogfoods itself) alongside being a marketplace.

Design source: `design/ralph-marketplace-brainstorm.md` (locked). Empirically-verified enabler: with `autoAllowBashIfSandboxed: true`, Claude Code authorizes a Bash command by **what it touches, not where the script lives** — so the plugin's versioned install path is irrelevant to permissions, and the permission-seeding subsystem is **deleted**, not ported.

## Goals

- One-command public install: `/plugin marketplace add … && /plugin install ralph@dddpaul-ralph`.
- Zero permission prompts on a full `/ralph-run` (except the unavoidable devcontainer bypass).
- Retire `ralph-sync` and the per-project permission-seeding subsystem entirely.
- No regression: `uv run pytest` + the bats suite pass from the new layout; a real Ralph run completes end-to-end.

## User Stories

### US-001: Scaffold marketplace + plugin manifests
**Description:** As a plugin author, I need the marketplace/plugin manifests so Claude Code recognizes the repo as an installable marketplace.

**Acceptance Criteria:**
- [ ] `/.claude-plugin/marketplace.json` exists, names marketplace `dddpaul-ralph`, lists one plugin `ralph` with `source: ./plugins/ralph`
- [ ] `plugins/ralph/.claude-plugin/plugin.json` exists with `name: ralph`, semver `version`, description, author, homepage, repository, license
- [ ] Both files are valid JSON (`jq . <file>` exits 0)
- [ ] `uv run ruff check .` passes

### US-002: Relocate skills + agents into the plugin
**Description:** As a plugin author, I need skills and agents under `plugins/ralph/` so the plugin bundles them.

**Acceptance Criteria:**
- [ ] All 10 `skills/*` moved to `plugins/ralph/skills/*` via `git mv` (history preserved)
- [ ] Both `agents/*` moved to `plugins/ralph/agents/*` via `git mv`
- [ ] `ralph-run` `scripts/` and Python `tests/` moved with the skill
- [ ] `grep -rn "skills/ralph-" --include='*.md' --include='*.py' --include='*.toml' .` shows no stale top-level `skills/` references outside `backlog/archive` and `design/`
- [ ] `ralph-sync` skill (still under `.claude/skills/`) is untouched by this story
**Depends on:** US-001

### US-003: Repoint build/test configuration
> **Backlog note:** folded into US-002 (TASK-188) at task-creation time — a bare `git mv` leaves `pytest` red until the config is repointed, so both land atomically. Kept here for design traceability.

**Description:** As a developer, I need pyproject and bats tests to point at the new paths so the suite runs green.

**Acceptance Criteria:**
- [ ] `pyproject.toml` `pythonpath`, `testpaths`, and ruff `src`/`include`/`strict` reference `plugins/ralph/skills/ralph-run/...`
- [ ] bats files under `tests/` reference the new `plugins/ralph/skills/ralph-run/scripts/...` paths
- [ ] `uv run pytest` passes
- [ ] The bats suite passes
**Depends on:** US-002

### US-004: Orchestrator resolver in ralph.sh
**Description:** As a Ralph operator, I need `ralph.sh` to locate the orchestrator wherever the plugin is installed, so a detached `nohup ./ralph.sh` works without `${CLAUDE_PLUGIN_ROOT}`.

**Acceptance Criteria:**
- [ ] Both `ralph.sh` shim copies (repo-root + `ralph-init` template) resolve the orchestrator by precedence: (1) `$RALPH_ORCHESTRATOR`, (2) in-repo `plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py`, (3) legacy `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/...`, (4) glob newest `~/.claude/plugins/cache/*/ralph/*/…/ralph_orchestrator.py` via `sort -V | tail -1`, (5) clear error
- [ ] The two shim copies are byte-identical (`diff` produces no output)
- [ ] `ralph-init` canonical-orchestrator gate checks "ralph plugin installed?" instead of the fixed `~/.claude/skills/...` path
- [ ] A unit/bats test covers resolver tiers 2 and 4 and the missing-plugin error
- [ ] `bash -n ralph.sh` passes; shell is R5-portable
**Depends on:** US-002

### US-005: Skill helper invocations use `${CLAUDE_PLUGIN_ROOT}`
**Description:** As a skill author, I need helper-script invocations to reference the plugin root so they resolve after install.

**Acceptance Criteria:**
- [ ] `ralph-run` invokes `bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-run/scripts/preflight.sh` and `…/wait-heartbeat.sh`
- [ ] `ralph-status` + `ralph-status-watch` invoke `bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-status/scripts/utc-to-moscow.sh`
- [ ] The "type verbatim, literal unquoted `$HOME`" allow-rule guidance is removed from those SKILL.md files
- [ ] No `$HOME/.claude/skills/` helper paths remain in the moved skills
**Depends on:** US-002

### US-006: Make wait-heartbeat read-only
**Description:** As a maintainer, I want `wait-heartbeat.sh` to perform no filesystem writes so it is unambiguously sandbox-covered.

**Acceptance Criteria:**
- [ ] `wait-heartbeat.sh` no longer removes the launch log (no write/`rm` operations remain)
- [ ] Launch-log cleanup happens instead in the `ralph-run` skill step (or orchestrator), and the launch log is still gone after a successful launch
- [ ] Existing wait-heartbeat tests updated and passing
- [ ] `bash -n` passes on the modified script
**Depends on:** US-002

### US-007: Delete the permission-seeding subsystem
**Description:** As a maintainer, I want the now-unnecessary permission seeding removed so bootstrap is simpler.

**Acceptance Criteria:**
- [ ] `ralph-init` Step 3.7b (rule-seeding) and the perm-matching narrative (~§201-220) are removed
- [ ] The three narrow `Bash(bash $HOME/.claude/skills/...:*)` rules are removed from `skills/ralph-init/templates/claude/settings.local.json`
- [ ] `ralph-init` Step 3.10 no longer verifies those rules
- [ ] A fresh `ralph-init` scaffold produces a project whose `/ralph-run` launches with zero permission prompts except the devcontainer bypass (documented manual smoke test)
**Depends on:** US-005, US-006

### US-008: Delete ralph-sync
**Description:** As a maintainer, I want `ralph-sync` removed since plugin install / directory-source replaces it.

**Acceptance Criteria:**
- [ ] `.claude/skills/ralph-sync/` (SKILL.md + `sync.sh`) deleted
- [ ] No references to `ralph-sync` remain in CLAUDE.md, README, or other skills (grep clean outside `backlog/archive` + `design/`)
**Depends on:** US-002

### US-009: Update R11 template-parity paths
**Description:** As the task-reviewer, I need parity rules to reference the new template location so R11 stays enforceable.

**Acceptance Criteria:**
- [ ] `.claude/task-reviewer-rules.md` R11 paths reference `plugins/ralph/skills/ralph-init/templates/...`
- [ ] The two `ralph.sh` shim copies remain in the parity set and are documented as byte-identical (now carrying the resolver)
- [ ] R11 examples/paths contain no stale top-level `skills/` references
**Depends on:** US-002, US-004

### US-010: Update documentation
**Description:** As a new user, I need docs to describe plugin install and the new layout.

**Acceptance Criteria:**
- [ ] README install section uses `/plugin marketplace add` + `/plugin install ralph@dddpaul-ralph` (replaces `cp -r skills/* ~/.claude/skills/`)
- [ ] README architecture/Key-Files paths point at `plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py`
- [ ] CLAUDE.md skill-layout paths updated; the "This repo is NOT a Claude Code plugin marketplace" line is flipped to describe the marketplace; ralph-sync references removed
- [ ] `uv run ruff check .` passes (no doc-referenced code broke)
**Depends on:** US-002, US-004, US-008

### US-011: Devcontainer plugin-cache reachability
**Description:** As a Ralph operator, I need the plugin reachable inside the devcontainer so resolver tier 4 works there.

**Acceptance Criteria:**
- [ ] Confirmed `~/.claude/plugins` is available inside the container under `CLAUDE_CONFIG_DIR=/home/node/.claude` (mount verified or added in `.devcontainer/devcontainer.json` + template)
- [ ] A documented smoke test shows `ralph.sh`'s resolver finding the orchestrator from inside the container
**Depends on:** US-004

## Functional Requirements

- FR-1: The repo MUST expose a valid `dddpaul-ralph` marketplace with a single `ralph` plugin.
- FR-2: The `ralph` plugin MUST bundle all `ralph-*` skills and both agents under `plugins/ralph/`.
- FR-3: `ralph.sh` MUST resolve the orchestrator across all 5 precedence tiers; both shim copies MUST stay byte-identical.
- FR-4: Skill helper invocations MUST reference `${CLAUDE_PLUGIN_ROOT}`, not `$HOME/.claude/skills/`.
- FR-5: The permission-seeding subsystem and the template narrow allow-rules MUST be removed; a scaffolded project MUST run Ralph with zero prompts except the devcontainer bypass.
- FR-6: `ralph-sync` MUST be removed.
- FR-7: `uv run pytest`, the bats suite, and `uv run ruff check .` MUST pass from the new layout.
- FR-8: R11 parity MUST reference the relocated template paths and remain enforceable.

## Non-Goals

- Dropping the legacy `~/.claude/skills/` resolver tier (3) — kept for the transition; its removal is a **post-transition follow-up**, not part of this feature.
- Force-cleaning stale narrow allow-rules already present in other projects' `settings.local.json` — they are harmless no-ops.
- Splitting into multiple plugins (core/authoring) — one `ralph` plugin only.
- Shipping plugin-level hooks or manifest permission injection — unneeded / unsupported.
- Renaming the GitHub repo (assumed usable as-is for the `marketplace add` URL).

## Technical Considerations

- **Coordinated single branch:** the repo dogfoods itself, so the move + reference updates land together; trickle-merging would leave `ralph-sync`↔`skills/` inconsistent mid-flight.
- **Cross-task invariants the reviewer must check:** (a) the 5-tier resolver contract is consistent across `ralph.sh`, its template, and the ralph-init gate; (b) the "zero allow-rules needed" invariant holds after US-005/006/007; (c) R11 parity paths match the actual relocated templates.
- **Sandbox authorization** is path-independent (verified) — no allow-rules required for read-only or project-dir-writing helpers.

## Success Metrics

- Public install works from a clean machine in two `/plugin` commands.
- A full `/ralph-run` in a freshly `ralph-init`'d project shows zero prompts beyond the devcontainer bypass.
- Test suites green; a real autonomous Ralph iteration completes end-to-end post-migration.

## Open Questions

- Timing of the post-transition follow-up that drops resolver tier 3 (separate future task).
- Whether to publish the marketplace from this repo's existing GitHub remote or a fresh one.
