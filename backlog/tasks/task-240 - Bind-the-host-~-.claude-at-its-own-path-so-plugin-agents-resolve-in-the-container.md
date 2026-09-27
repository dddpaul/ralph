---
id: TASK-240
title: >-
  Bind the host ~/.claude at its own path so plugin agents resolve in the
  container
status: Done
assignee: []
created_date: '2026-09-26 08:51'
updated_date: '2026-09-27 07:22'
labels:
  - 'feature:ralph-init'
dependencies:
  - TASK-239
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The devcontainer template binds the host `~/.claude` at `/home/node/.claude`. Claude Code's plugin registries (`plugins/known_marketplaces.json`, `plugins/installed_plugins.json`) record **absolute host paths** such as `/Users/<user>/.claude/plugins/marketplaces/<name>`, so a marketplace resolves only when that literal path also exists inside the container. Under the template it does not. Every user plugin then dies with `Marketplace <name> failed to load: cache-miss`, and the `task-reviewer` agent shipped by `ralph@dddpaul-ralph` never registers — so the Review step of the Task Lifecycle inside a devcontainer run silently degrades from the real reviewer to a plain agent reading a rules file. The run still reports APPROVED, which is why this went unnoticed for a long time.

A downstream project hit this and fixed it locally by binding the same host `~/.claude` a second time at its own host path. Verified there against a live container: `claude plugin list` reports `ralph@dddpaul-ralph enabled` and `claude plugin details ralph@dddpaul-ralph` lists both agents (`task-reviewer`, `ralph-reviewer`). The fix never came back upstream, so the template still ships the defect and that project now carries a `devcontainer.json` that diverges from the template — which upgrade mode U4 would overwrite on the next upgrade, taking the fix with it. Absorbing it here is what lets every project take the template file verbatim again.

## Scope

In scope:
- Add a second bind of the host `~/.claude` at its own host path to the template `devcontainer.json`: `"source=${localEnv:HOME}/.claude,target=${localEnv:HOME}/.claude,type=bind"`.
- Mirror it into the live `.devcontainer/devcontainer.json` — template-parity lists that pair as `exact`, so the two files must stay byte-identical.
- Carry a short comment saying why the literal host path has to exist inside the container, so a later reader does not prune the mount as a duplicate of the `/home/node/.claude` bind.
- Update `ralph-init` SKILL.md prose (Init and Upgrade Mode) and state that a mount change takes effect only when the container is recreated.
- Add a bats regression test asserting the mount in BOTH files.

Out of scope:
- Changing `CLAUDE_CONFIG_DIR`. It stays `/home/node/.claude`; nothing is written through the second path, which is exactly why the mount is safe.
- The symlink fallback that covers a plain `docker run` mounting only `/home/node/.claude`. The downstream project has one in its own postCreate script; the template has no such path and does not need it.
- Anything about how the project `.claude` directory is shared — TASK-239 owns that, and this task must not disturb its mounts.
- The `.venv` volume overlay — TASK-235 already shipped it.
- Retrofitting projects that applied the fix by hand; they pick it up through the upgrade flow.

## Files

- `plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json` (exists) — the mounts array.
- `.devcontainer/devcontainer.json` (exists) — the live copy; `tests/unit/template-parity.bats` line 53 pins this pair as `exact`.
- `plugins/ralph/skills/ralph-init/SKILL.md` (exists) — the prose describing the devcontainer mounts.
- `tests/unit/devcontainer-claude-hostpath-bind.bats` (to-create) — regression test; `tests/unit/devcontainer-venv-overlay.bats` (exists) is the shape to copy, including its mutation check against the pre-fix file.

## Source

Source: /Users/paul/Private/Alfa/Projects/standard/stacks@92793d6baeb7
Source task (read-only context, in that repo's backlog): TASK-315 — merged and reviewed there; its `.devcontainer/devcontainer.json` and `.devcontainer/init-claude-config.sh` carry the working implementation and the diagnosis in comments.

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The template devcontainer.json mounts the host ${localEnv:HOME}/.claude a second time at target ${localEnv:HOME}/.claude, type=bind — verified by grep over plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json
- [x] #2 The live .devcontainer/devcontainer.json carries the identical mount and the exact-parity row for that pair still passes in tests/unit/template-parity.bats
- [x] #3 containerEnv CLAUDE_CONFIG_DIR is still /home/node/.claude in both files — the new mount adds no write path to the host config
- [x] #4 The mount carries a comment naming the cache-miss failure it prevents, so it is not pruned later as a duplicate of the /home/node/.claude bind
- [x] #5 Both devcontainer.json files parse as JSON after stripping line-leading // comments
- [x] #6 ralph-init SKILL.md describes the mount in Init and Upgrade Mode and states that a mount change needs the container recreated
- [x] #7 A bats regression test asserts the mount in BOTH the template and the live file, and fails against the pre-fix version of each (mutation-checked, same shape as tests/unit/devcontainer-venv-overlay.bats)
- [x] #8 uv run ruff check . is clean, uv run pytest passes, and LC_ALL=C bats tests/unit passes with only the new tests added to the count
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Handoff acceptance checklist (run per CLAUDE.md Handoff Inbox, autonomous mode): GREEN.
1. All four (exists) paths present: templates/devcontainer/devcontainer.json, .devcontainer/devcontainer.json, ralph-init/SKILL.md, tests/unit/devcontainer-venv-overlay.bats.
2. Every AC is a grep / jq / diff / test invocation - objectively pass/fail.
3. Dependency TASK-239 is Done.
4. Out-of-scope items are separable: no CLAUDE_CONFIG_DIR change, no symlink fallback, no touching TASK-239 mounts, no .venv change.
One yellow footnote that does not block: AC#7 claims devcontainer-venv-overlay.bats carries 'its mutation check against the pre-fix file'. It does not - no bats file in this suite has a mutation check. Honouring the AC literally by building a real, self-contained mutation check into the new test (derive the pre-fix copy in a temp dir by deleting the mount + comment, then assert the detector returns empty), and copying venv-overlay.bats for shape/style otherwise.
PORT SOURCE UNAVAILABLE: Source path /Users/paul/... is not mounted in this container, so fidelity to the unseen stacks@92793d6 implementation is unverifiable; the task body specifies the exact mount string, so implementing to spec.

Plan:
1. Insert the second bind (source=${localEnv:HOME}/.claude,target=${localEnv:HOME}/.claude,type=bind) into .devcontainer/devcontainer.json mounts, right after the /home/node/.claude bind, preceded by a whole-line // comment naming the cache-miss failure so it is not pruned as a duplicate.
2. Copy the file verbatim to templates/devcontainer/devcontainer.json so the 'exact' parity row stays silent.
3. Add tests/unit/devcontainer-claude-hostpath-bind.bats: JSONC validity, the mount present in both files with source==target==${localEnv:HOME}/.claude and type=bind, the comment present, CLAUDE_CONFIG_DIR still /home/node/.claude, no write path added, byte parity, plus the mutation test.
4. ralph-init SKILL.md: new Init-mode note next to the shared-.claude note, and extend the U4/U5 recreate paragraph (line ~652) to name the host-path bind.
Gate note: bats was absent from this checkout (no node_modules) - installed with npm install --no-save bats. Baseline on branch point: 125 ok / 1 not ok (#112 'R11: settings.local.json keeps the template JSON shape' - gitignored per-developer file drift, pre-existing), pytest 498 passed, ruff clean.

Commit: `abc93be` - task-240: bind the host ~/.claude at its own path so plugin agents resolve in the container

Commit: `0407c8b` - task-240: scope the no-write claim to the new mount and tighten the mutation test

IMPLEMENTED. Both devcontainer.json files (live + ralph-init template, byte-identical per R11 'exact' parity) now bind the host ~/.claude a second time at target=${localEnv:HOME}/.claude, type=bind, immediately after the /home/node/.claude bind, behind a 10-line comment that names the cache-miss failure and opens with 'NOT a duplicate of the bind above - do not prune it'. The change is purely additive: zero deleted lines, CLAUDE_CONFIG_DIR still /home/node/.claude, TASK-239's mounts and the .venv overlay untouched, no symlink fallback.

New test tests/unit/devcontainer-claude-hostpath-bind.bats (9 tests): JSONC validity, mount present in both files, source==target==${localEnv:HOME}/.claude with type=bind and not type=volume, the /home/node/.claude bind still present alongside, CLAUDE_CONFIG_DIR unchanged, exactly two mounts source the host .claude, the comment names cache-miss and 'not a duplicate', byte parity, plus a self-contained mutation test.

AC#7 premise was FALSE and is recorded as such: the task body claims devcontainer-venv-overlay.bats carries 'its mutation check against the pre-fix file'. No bats file in this suite has one. Honoured the AC by building a real mutation check instead, and proved it twice out-of-band: (a) against master's content for both devcontainer.json files, exactly 5 of the 9 new tests fail (2,3,6,7,9); (b) widening the detector regex to target=.*\.claude against the fixed files leaves 8 green and fails only the mutation test. So the check is non-vacuous in both directions - it catches a detector that matches nothing AND one that matches too much.

Prose: ralph-init SKILL.md gained an Init-mode note (Step 3.6, next to the shared-.claude and .venv notes) explaining registry-recorded host paths, the silent Review degradation, the claude plugin list / claude plugin details verification pair, the $HOME=/home/node collapse case with a warning that U4 overwrites local edits, and an explicit refusal of the two wrong fixes (editing the registry JSONs; extraKnownMarketplaces). Upgrade mode: the U4 paragraph now names the host-path bind among the mount-carrying settings, and the U5 summary block states that until the container is recreated claude plugin list still reports cache-miss and Review runs without the real reviewer. README.md gained a matching section, and its pre-existing 'No extra mount is required' sentence was corrected to distinguish the shim (glob-resolved, needs no mount) from plugin components (registry-resolved, need this mount) - verified against ralph.sh's resolver rather than assumed.

REVIEW: the real task-reviewer agent is UNREGISTERED in this container - which is precisely the defect this task fixes (it ships inside ralph@dddpaul-ralph, which fails to load with cache-miss; available agents were claude/Explore/general-purpose/Plan/statusline-setup). Substituted an independent claude agent carrying the full reviewer charter plus .claude/task-reviewer-rules.md (R1-R16). First pass returned CHANGES REQUESTED on one blocking R12 finding: new SKILL.md prose claimed 'the host's own Claude config cannot be corrupted by a container run', which is false, contradicted its own next sentence, and would have hidden the very defect TASK-241 owns. Fixed by scoping the claim to the new mount and stating that /home/node/.claude is itself a read-write bind through which container runs do write. Also fixed three non-blocking items: dropped the inaccurate 'Read-only in practice' label on an rw mount, corrected a bats comment that overclaimed what the mutation test asserts, and replaced BATS_TEST_TMPDIR with mktemp -d (the apt-installed CI bats does not guarantee bats-core >=1.4.0). Re-review: VERDICT APPROVED, with the reviewer independently re-running all gates and re-proving the mutation evidence.

PORT SOURCE UNAVAILABLE - stated assumption: the Source path /Users/paul/Private/Alfa/Projects/standard/stacks@92793d6 is not mounted in this container, so fidelity to the unseen stacks implementation is the one thing that could not be verified. The task body specified the exact mount string, so this was implemented to spec, not ported. Two peripheral claims rest on that downstream testimony (the extraKnownMarketplaces ineffectiveness and the literal 'Agents (2)' output format); every load-bearing fact around them was verified locally - the registries do store installLocation/installPath as /Users/paul/... host paths, claude plugin list runs without auth and does report cache-miss, and plugins/ralph/agents/ holds exactly task-reviewer.md and ralph-reviewer.md.

GATES: uv run ruff check . clean; uv run pytest 498 passed; LC_ALL=C bats tests/unit 135 tests, 134 ok / 1 not ok. The single failure is pre-existing and not caused by this diff: #121 'R11: settings.local.json keeps the template JSON shape', on .claude/settings.local.json, which is gitignored and untracked (host developer state - attribution/permissions keys). Baseline at the branch point was the same 1 failure with 125 ok, so the count moved by exactly the 9 new tests. NOTE FOR FUTURE ITERATIONS: this checkout has no node_modules and bats is not on PATH; installed ad-hoc with npm install --no-save bats (node_modules/ is gitignored, so nothing was committed).

NOT VERIFIED IN A LIVE CONTAINER, by construction: mounts apply only at container creation, so this fix is INERT until the first devcontainer=true rebuild=true run. The container running this task cannot test its own new mount - /Users does not exist here, sudo is NOPASSWD-pinned, and unshare -rm is not permitted. Whoever next rebuilds should confirm with claude plugin list (expect enabled, not cache-miss) and claude plugin details ralph@dddpaul-ralph (expect Agents (2) task-reviewer, ralph-reviewer).

Commit: `9a19922` - task-240: reword the no-write claim in the ralph-init note

Commit: `af07725` - task-240: bump plugin version to 0.6.1 (patch)
<!-- SECTION:NOTES:END -->
