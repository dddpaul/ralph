# Ralph → Claude Code Plugin Marketplace

## Architecture decision

Convert **this** repo into its own Claude Code plugin marketplace (drivers: **A** easier install/distribution + **B** public sharing). Ship **one cohesive `ralph` plugin** bundling all `ralph-*` skills + both agents (`task-reviewer`, `ralph-reviewer`). The repo stays a Ralph dev repo that dogfoods itself **and** is a marketplace — coexistence, modeled on `dddpaul-claude-skills`.

**Key enabling finding (empirically verified this session):** with `autoAllowBashIfSandboxed: true`, Claude Code authorizes a Bash command by **what it touches, not where the script lives**. Proven with three unlisted-path scripts: read-only ran silently, a write+`rm` *inside* the project ran silently, only a write to `$HOME` failed (in-sandbox syscall failure — no prompt). Therefore the plugin's **versioned, moving** install path (`~/.claude/plugins/cache/<mp>/ralph/<version>/…`) is **irrelevant to permissions**. This lets us **delete** the permission-seeding subsystem rather than port it.

Authoritative plugin mechanics (via claude-code-guide): plugins **cannot** ship permission rules (static manifest injection unsupported); `${CLAUDE_PLUGIN_ROOT}` exists only inside plugin context and points at the versioned dir; no CLI/stable symlink to locate an installed plugin from outside; directory-source installs load **in-place** at a stable path.

## Components / flows

- **`/.claude-plugin/marketplace.json`** — lists one plugin `ralph`, `source: ./plugins/ralph`. Marketplace name **`dddpaul-ralph`** (distinct from `claude-plugins-official/ralph-loop`).
- **`plugins/ralph/.claude-plugin/plugin.json`** — `name: ralph`, semver `version` (drives cache dir), description, author, homepage/repository, license.
- **File moves:** `skills/*` → `plugins/ralph/skills/*`; `agents/*` → `plugins/ralph/agents/*` (orchestrator + `scripts/` + Python `tests/` ride along under `ralph-run`).
- **`ralph.sh` orchestrator resolver** (both shim copies, byte-identical), first hit wins: (1) `$RALPH_ORCHESTRATOR` env override; (2) in-repo `plugins/ralph/skills/ralph-run/scripts/ralph_orchestrator.py`; (3) legacy `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/…` (transition back-compat); (4) glob newest `~/.claude/plugins/cache/*/ralph/*/…/ralph_orchestrator.py` (`sort -V | tail -1`); (5) clear error. `nohup ./ralph.sh` stays the launch entrypoint — its allow-rule is project-relative and path-stable.
- **Skill script-invocations** → `bash ${CLAUDE_PLUGIN_ROOT}/skills/…/<helper>.sh` (ralph-run preflight/wait-heartbeat; ralph-status/watch utc). No allow-rule needed — sandbox covers them.
- **Distribution:** public — `/plugin marketplace add https://github.com/<you>/ralph` → `/plugin install ralph@dddpaul-ralph` (skills+agents available in every project). Dev loop — directory-source marketplace + `/reload-plugins` (**replaces `ralph-sync`**).
- **New onboarding:** install plugin once → `/ralph-init` scaffolds a project → `/ralph-run`.

## Scope cuts

- **One** `ralph` plugin — not split into core/authoring sub-plugins (tightly coupled).
- **No plugin-shipped hooks** and **no manifest permission injection** — unneeded (sandbox covers perms) / unsupported.
- **Not required** to make `wait-heartbeat` read-only — its project-dir `rm` is sandbox-covered; moving the launch-log cleanup is optional belt-and-suspenders, not load-bearing.
- **Existing projects' stale narrow allow-rules** left as harmless no-ops — not force-cleaned.
- Not adding this `ralph` plugin to the existing `dddpaul-claude-skills` marketplace — a marketplace maps 1:1 to a repo, and the ask is to convert *this* repo.

## Open questions

- Final marketplace name (`dddpaul-ralph` proposed) and whether the GitHub repo needs renaming for the `marketplace add` URL.
- Drop the legacy `~/.claude/skills/` resolver branch (3) after the transition window, or keep indefinitely?
- Move `wait-heartbeat`'s launch-log `rm` out, or leave it (sandbox-covered)?
- Devcontainer: confirm `~/.claude/plugins` is mounted so resolver branch (4) works inside the container.

## Hand-off

Next: `ralph-prd` to formalize as PRD (**PRD-shaped**: ~10 tasks with cross-task invariants — resolver contract, "zero allow-rules", R11 parity), then `ralph-backlog` to generate tasks. Feature slug: **`ralph-marketplace`**.

## Distilled for ralph-task

**Direction:** Approach A — convert this repo into a native Claude Code plugin marketplace shipping one cohesive `ralph` plugin; **delete** (not port) the permission-seeding subsystem, since `autoAllowBashIfSandboxed` makes the versioned plugin path irrelevant to permissions.

**Locked decisions (with rationale):**
- **One `ralph` plugin** bundling all `ralph-*` skills + both agents. *Rationale:* the skills are one tightly-coupled workflow, not an independent grab-bag.
- **This repo becomes its own marketplace** (`dddpaul-ralph`), coexisting with its Ralph dev role. *Rationale:* a marketplace maps 1:1 to a repo; the ask is to convert this repo.
- **Delete the permission-seeding subsystem** (ralph-init 3.7b + template narrow allow-rules). *Rationale:* empirically, `autoAllowBashIfSandboxed` authorizes by what a command touches, not the script's path, so the versioned plugin path needs no rules; and plugins can't ship rules anyway.
- **Keep `nohup ./ralph.sh` as launch entrypoint + add a 5-tier orchestrator resolver.** *Rationale:* the `Bash(nohup ./ralph.sh:*)` rule is project-relative/path-stable; launching `uv run <plugin-path>` directly would need the reviewer-rejected `Bash(uv run:*)`.
- **Skill invocations use `${CLAUDE_PLUGIN_ROOT}`.** *Rationale:* only portable in-plugin path reference; harness renders it concrete and sandbox authorizes regardless.
- **`ralph-sync` retires**, replaced by plugin install (public) + directory-source (dev). *Rationale:* plugin install *is* the distribution mechanism now.

**Scope cuts:**
- No plugin-shipped hooks; no manifest permission injection; no multi-plugin split.
- `wait-heartbeat` read-only conversion optional, not required.
- Stale allow-rules in existing projects left as no-ops.

**Acceptance criteria (sketch):**
- `/.claude-plugin/marketplace.json` + `plugins/ralph/.claude-plugin/plugin.json` validate and list plugin `ralph`.
- `skills/*` and `agents/*` moved under `plugins/ralph/`; no references to the old top-level paths remain.
- `uv run pytest` and the bats suite pass from the new paths.
- `ralph.sh` resolves the orchestrator via all 5 tiers; a published-install glob and an in-repo path both work; missing-plugin gives a clear error.
- A full `/ralph-run` launch completes with **zero permission prompts** except the devcontainer bypass.
- `ralph-sync` skill + `sync.sh` deleted; ralph-init 3.7b seeding + template allow-rules deleted.
- R11 parity paths updated; CLAUDE.md "NOT a marketplace" line flipped; README install section rewritten.
- Devcontainer run confirms the plugin cache is reachable inside the container.

**Implementation checklist:**
1. Scaffold `marketplace.json` + `plugin.json`.
2. `git mv` skills + agents → `plugins/ralph/`.
3. Repoint pyproject (`pythonpath`/`testpaths`/ruff `src`) + bats path refs; green `pytest`+bats.
4. Add `ralph.sh` resolver + `RALPH_ORCHESTRATOR`; repoint ralph-init canonical gate → "plugin installed?".
5. Rewrite skill helper invocations → `${CLAUDE_PLUGIN_ROOT}`; drop "verbatim literal `$HOME`" guidance.
6. Delete perm-seeding (ralph-init 3.7b + template narrow allow-rules).
7. Delete `ralph-sync` skill + `sync.sh`.
8. Update R11 parity paths in `task-reviewer-rules.md`.
9. Docs: CLAUDE.md (skill layout, flip marketplace line, drop ralph-sync) + README (install + architecture paths).
10. Devcontainer: confirm `~/.claude/plugins` mounts; add AC test.
