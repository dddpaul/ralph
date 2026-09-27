---
id: TASK-241
title: >-
  Stop container runs from writing container-only paths into shared plugin
  registries
status: Done
assignee: []
created_date: '2026-09-27 06:33'
updated_date: '2026-09-27 07:44'
labels: []
dependencies:
  - TASK-240
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The devcontainer shares one Claude config directory between two machines with different filesystem roots: it binds the host `~/.claude` at `/home/node/.claude` and sets `CLAUDE_CONFIG_DIR=/home/node/.claude`. Claude Code's plugin registries store **absolute** paths, so whichever side writes a registry entry bakes in its own root, and the other side can no longer resolve it. Both shapes are currently present in the same config directory:

```
# installed_plugins.json -- HOST shape
ralph@dddpaul-ralph  installPath = /Users/paul/.claude/plugins/cache/dddpaul-ralph/ralph/0.5.1

# known_marketplaces.json -- CONTAINER shape (written from inside a container)
dddpaul-ralph -> /home/node/.claude/plugins/marketplaces/dddpaul-ralph
```

The host has a real marketplace directory at its own root, so the container-shaped entry above does not resolve on the host.

Observed symptom: during one session the `ralph:task-reviewer` agent resolved and ran a full review, and later in that same session both `ralph:task-reviewer` and `ralph:ralph-reviewer` became unavailable on the host, after several devcontainer runs had written to the shared config. That is the same silent-degradation failure mode TASK-240 documents (a plugin cache-miss makes the Review step fall back to a plain agent while still reporting APPROVED), except in the host direction.

This is the same class of defect as TASK-235 (`.venv`): one directory shared by host and container, with absolute interpreter/plugin paths baked in by whichever side wrote last.

## Relationship to TASK-240

TASK-240 makes the **container tolerant of host-shaped paths** by binding the host `~/.claude` a second time at its own host path (a read-only additional path; it adds no write path). It does not stop a container from writing **container-shaped** paths into the shared registries, and it does not repair entries already corrupted that way. This task owns that reverse direction. Sequenced after TASK-240 only to avoid two tasks editing the same `mounts` array.

## Candidate approaches (pick one, record the rationale)

1. Give the container its own `CLAUDE_CONFIG_DIR` on a container-local volume so it never writes into the host registry. Strongest isolation; costs shared plugin state (the container would need its own install).
2. Make both roots resolvable from both sides, so whichever shape gets written still resolves everywhere. Symmetric extension of TASK-240's idea.
3. Normalize on startup: an idempotent step that rewrites registry paths to the local root, run on both sides.
4. Keep registries container-local and share only the path-shape-free subpaths.

Approach 1 is the cleanest conceptually but changes what the container can see; approach 2 is the smallest delta given TASK-240. The invariant below is what matters, not the mechanism.

## Invariant to achieve

After a devcontainer run, the ralph plugin resolves on BOTH sides: the host registers `ralph:task-reviewer` / `ralph:ralph-reviewer`, and the container reports no marketplace cache-miss. No run leaves a path rooted at the other machine in the shared registries.

## Scope notes

- Any `.devcontainer/devcontainer.json` change must be mirrored to `plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json` (the pair is pinned `exact` by template parity) and `plugins/ralph/skills/ralph-init/SKILL.md` updated in BOTH Init and Upgrade Mode.
- Mount changes take effect only when the container is recreated (`--rebuild` / `/ralph-run rebuild=true`).
- Out of scope: the `.venv` overlay (TASK-235, shipped) and TASK-240's own second bind.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Diagnosis is recorded in the task notes: which files under the shared Claude config carry absolute paths, and which root shape each held before the fix, with the concrete values
- [x] #2 The chosen approach is recorded in the task notes together with the rejected alternatives and the reason each was rejected
- [x] #3 After a devcontainer run, the shared plugin registries contain no path rooted at the other machine (no /home/node/... entry when read from the host)
- [x] #4 After a devcontainer run, the host still resolves the ralph plugin: claude plugin list reports ralph@dddpaul-ralph enabled and both shipped agents register
- [x] #5 Inside the container the ralph plugin still resolves with no marketplace cache-miss, so TASK-240's outcome is not regressed
- [x] #6 Any .devcontainer/devcontainer.json change is mirrored to plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json so the exact-parity row in tests/unit/template-parity.bats still passes
- [x] #7 If the devcontainer template changes, ralph-init SKILL.md is updated in BOTH Init and Upgrade Mode, including the U2 files-to-check list where a new managed file is introduced
- [x] #8 A regression test asserts the invariant and fails against the pre-fix configuration (mutation-checked)
- [x] #9 uv run ruff check . is clean, uv run pytest passes, and LC_ALL=C bats tests/unit passes with no new failures beyond the known pre-existing ones
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Blast radius measured on the host (2026-09-27): the corruption is NOT ralph-specific. 11 of 12 marketplaces in known_marketplaces.json carry a container-rooted installLocation (/home/node/.claude/plugins/marketplaces/<name>); only zai-coding-plugins is still host-rooted, and it is the one entry untouched since 2026-06-24. Ten entries were rewritten in one batch at 06:32 and dddpaul-ralph again at 06:49, i.e. a single devcontainer startup refreshing all marketplaces relocates every one of them to a path that does not exist on the host. Consequence: host-side resolution of the entire plugin ecosystem breaks, not just the ralph agents, and '/plugin marketplace update <name>' fails ('could not be refreshed') because it tries to git-pull a directory absent on this machine. All 11 host clones are intact git repos at the exactly mirrored path, so recovery is a pure installLocation rewrite (/home/node -> $HOME) with no re-clone needed. This raises the task's importance: the invariant should be stated over ALL marketplaces, not only ralph@dddpaul-ralph.

TRIGGER EVIDENCE from the TASK-240 run (2026-09-27, correcting an earlier overclaim). The registries were repaired at 06:53 UTC, then the 240 run started 06:56:57 with --rebuild, so a brand-new container started Claude Code. Result: installLocation was NOT rewritten - 0 of 12 entries container-rooted afterwards - although dddpaul-ralph's lastUpdated was touched at 06:57:28, so the container did write to the registry file. Crucially that container was created from the PRE-240 config (mounts apply at container creation and 240's bind was authored during the run), and the 240 run's own notes confirm the real task-reviewer was UNREGISTERED in-container with a cache-miss. So a cache-miss does NOT by itself cause the relocation, and it is NOT true that every container start rewrites the paths - the earlier '06:32 batch rewrote ten marketplaces' event had some more specific trigger that is still unidentified. Identifying that trigger is part of this task: extend AC #1's diagnosis to name the operation that performs the relocation (candidates: a marketplace add/install/refresh path, or first-run initialization when a registry entry's directory is absent), rather than assuming container startup. Note also that 240's host-path bind only becomes live in a container created after 240 merged, so the first container able to resolve host-rooted paths is the next --rebuild.

Plan: adopt approach 2 taken to its conclusion — repoint containerEnv CLAUDE_CONFIG_DIR from /home/node/.claude to ${localEnv:HOME}/.claude in .devcontainer/devcontainer.json + the ralph-init template (byte parity), keeping BOTH host-.claude binds. The container then reads and writes the shared config through the host's own root, so every absolute path it records (installLocation / installPath) is host-shaped and resolves on both machines; the /home/node/.claude bind stays so $HOME/.claude and anything hardcoding it still land on the same bytes. Tests: rewrite the now-false CLAUDE_CONFIG_DIR assertion in tests/unit/devcontainer-claude-hostpath-bind.bats, add tests/unit/devcontainer-claude-config-root.bats (config root is the host path in both copies, no /home/node root, the bind that makes it resolvable is present, a registry-shape detector over known_marketplaces.json / installed_plugins.json, all mutation-checked against a derived pre-fix copy and a synthetic corrupted registry). Docs: README.md devcontainer notes + ralph-init SKILL.md Init note (line 241 reverses) and U4 upgrade summary.

DIAGNOSIS (AC #1). Files under the shared Claude config that carry absolute paths, with the concrete shapes observed on 2026-09-27:
(a) plugins/known_marketplaces.json — one installLocation per marketplace. Pre-fix snapshot (the repair backup known_marketplaces.json.bak-20260927095314): 11 of 12 entries CONTAINER-shaped, e.g. /home/node/.claude/plugins/marketplaces/dddpaul-ralph, /home/node/.claude/plugins/marketplaces/anthropic-agent-skills, ...revdiff, ...claudeclaw (only zai-coding-plugins, a source=directory entry under /Users/paul/.npm/_npx/..., was untouched). Current (post-repair) file: 0 of 12 container-shaped, all /Users/paul/.claude/plugins/marketplaces/<name>.
(b) plugins/installed_plugins.json — one installPath per installed plugin plus a projectPath. All 17 installPath values are HOST-shaped (/Users/paul/.claude/plugins/cache/<marketplace>/<plugin>/<version>), and projectPath is /Users/paul/Private/Projects/ai/ralph.
No other file under the config root participates in plugin resolution by absolute path.
TRIGGER, identified by experiment rather than inference. With a scratch CLAUDE_CONFIG_DIR=/tmp/cfgtest holding one marketplace backed by a local git repo: (1) installLocation rooted OUTSIDE the config root -> 'claude plugin marketplace update' fails hard with «Marketplace 'fake-mkt' has a corrupted installLocation (/Users/paul/.claude/plugins/marketplaces/fake-mkt) — expected a path inside /tmp/cfgtest/plugins/marketplaces. ... Run claude plugin marketplace remove <name> and re-add it» and leaves the registry BYTE-UNCHANGED; (2) the same entry rooted INSIDE the config root with the directory missing -> silently re-clones in place and keeps the path; (3) plain 'marketplace list' never writes. So no read or refresh path relocates an entry: Claude Code validates installLocation against $CLAUDE_CONFIG_DIR/plugins/marketplaces and refuses anything else. The relocation is therefore performed by the write paths that MINT an entry under the current config root — an add / re-add / install, i.e. exactly the remove+re-add recovery that error message prescribes, run from inside a container whose config root is /home/node/.claude (an older Claude Code whose refresh relocated instead of erroring produces the same result). The invariant-level cause is the same either way and is what this task fixes: the container's config root differs from the host's, so whichever side mints an entry bakes in a root the other side then rejects. Corollary: under CLAUDE_CONFIG_DIR=/home/node/.claude every host-rooted entry is 'corrupted' for the container and every container-rooted entry is 'corrupted' for the host — the guard makes the two roots mutually exclusive, which is why the failure hits all 12 marketplaces and not just ralph's.

APPROACH (AC #2). Chose approach 2 in its strongest form: keep the single shared config directory and both binds, and repoint containerEnv CLAUDE_CONFIG_DIR from /home/node/.claude to ${localEnv:HOME}/.claude. The container then reads AND writes the shared config through the host's own root, so every absolute path it mints is host-shaped; TASK-240's second bind is what makes that root exist inside the container, and the /home/node/.claude bind stays as the $HOME alias for anything that ignores CLAUDE_CONFIG_DIR. One-line delta, no new machinery, and it satisfies Claude Code's own installLocation guard on both sides.
Rejected: (1) container-local CLAUDE_CONFIG_DIR on a volume — strongest isolation but costs the shared plugin state outright: the container would need its own marketplace add + plugin install, i.e. exactly the operation identified above as the one that mints paths, and the ralph task-reviewer agent would have to be re-installed per container. (3) startup normalization that rewrites registry paths to the local root — needs a new script on both sides, runs as a mutation of the user's real config on every start, and is a repair loop for a corruption that this change simply never creates; it also cannot run on the host, where nothing in Ralph is invoked at login. (4) sharing only path-shape-free subpaths — the registries ARE the path-shaped part, so this is approach 1 with extra steps.
Superseded claim: TASK-240's note and ralph-init SKILL.md said CLAUDE_CONFIG_DIR 'must not be repointed at the host path' because that would add a write path. That premise is inverted — /home/node/.claude is itself a read-write bind of the same directory, so the writes were already happening; only their recorded shape changed. Both the SKILL.md paragraph and the assertion in tests/unit/devcontainer-claude-hostpath-bind.bats were updated accordingly.

VERIFICATION. AC #3: the shared registries hold zero /home/node-rooted paths after this container's run (jq '.. | strings | select(startswith("/home/node/"))' over both files -> empty); the new bats test asserts it against the live config and is skipped only where the local root is itself under /home/node. AC #5: inside this container, 'CLAUDE_CONFIG_DIR=/Users/paul/.claude claude plugin list' and 'claude plugin details ralph@dddpaul-ralph' give byte-identical output to the same commands under /home/node/.claude — ralph@dddpaul-ralph enabled, 'Agents (2) task-reviewer, ralph-reviewer', no cache-miss — so moving the config root does not regress TASK-240's outcome. AC #4 caveat: the host's own 'claude plugin list' cannot be run from inside the container. What was verified instead is the same code path over the same files with the host root (above), plus that all 12 host marketplace clones exist at their recorded paths. The literal host-side check, and the fix itself, apply only after the next container recreate (--rebuild / /ralph-run rebuild=true) — mounts and containerEnv are read at container creation. AC #8 mutation check: the config-root assertion is driven to failure on a derived pre-fix copy of both devcontainer.json files, the registry detector is driven on a synthetic container-rooted registry, and the live-registry test was additionally run against the REAL pre-repair snapshot (known_marketplaces.json.bak-20260927095314) where it fails and prints all 11 relocated paths. AC #9: ruff clean; pytest 498 passed; bats tests/unit 143 ok / 1 not ok — 'R11: settings.local.json keeps the template's JSON shape', pre-existing and environment-specific (it skips on a clean master worktree because the file is gitignored; in this container /workspace/.claude/settings.local.json carries the host's attribution/permissions keys). AC #7: no new managed file, so the U2 list needs no new row; the existing .devcontainer/devcontainer.json row covers it. Both the Init note and the U4 upgrade note (including the U5 summary text, now with a one-time host repair instruction) were updated.

Commit: `a807193` - task-241: root the container's Claude config at the host path so plugin registries stay resolvable on both machines

Commit: `c3f2207` - task-241: drop the stale CLAUDE_CONFIG_DIR claims from the README devcontainer notes

task-reviewer: APPROVED (c3f2207) after two README R12 fixes (a stale 'where CLAUDE_CONFIG_DIR points' parenthetical and the mount-check smoke-test expected output, both now host-rooted).

Commit: `30864f6` - task-241: bump plugin version to 0.6.2 (patch)
<!-- SECTION:NOTES:END -->
