---
id: TASK-122
title: >-
  Promote ralph-init's jq merge to numbered sub-step + add post-init
  verification
status: Done
assignee: []
created_date: '2026-05-14 06:53'
updated_date: '2026-05-14 14:56'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Defect

skills/ralph-init/SKILL.md Step 3.7 currently bundles two distinct actions into one section:

1. Write template settings.local.json (top of 3.7, lines ~154-156)
2. Run jq merge to add narrow script rules for preflight.sh/wait-heartbeat.sh/utc-to-moscow.sh (lines ~158-177)

The merge sits as a free-flowing 'After writing settings.local.json, merge narrow script rules' instruction inside 3.7 — not its own numbered sub-step. Witnessed (2026-05-11): a fresh ralph-init bootstrap by Claude in a sibling session produced settings.local.json with only the template entries — the jq merge was skipped. The instruction is technically present but easy for Claude to read past after acting on the bigger 'write template' instruction.

There is no end-of-init verification that the 3 narrow rules actually landed, so the omission is silent.

## What

Two changes to skills/ralph-init/SKILL.md.

### Change 1 — split Step 3.7 into named sub-steps

Make the jq merge its own visible numbered sub-step. Suggested structure:

```markdown
### 3.7a settings.json, hooks, and settings.local.json (template write)
Read templates/claude/settings.json → write to .claude/settings.json...
Read each templates/claude/hooks/*-guard.sh ... → write to .claude/hooks/...
Read templates/claude/settings.local.json → write to .claude/settings.local.json

### 3.7b Merge narrow script rules into settings.local.json permissions
Resolve the user's home directory ... (existing prose + jq block)
```

The split forces Claude to treat the merge as a discrete required action, not an afterthought.

### Change 2 — add post-init verification sub-step

After all init Step 3.x sub-steps complete and before Step 4 'Confirm', add a new sub-step (e.g. '### 3.x Verify settings.local.json permissions') that runs:

```bash
expected=(
  "$HOME/.claude/skills/ralph-run/scripts/preflight.sh"
  "$HOME/.claude/skills/ralph-run/scripts/wait-heartbeat.sh"
  "$HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh"
)
missing=()
for p in "${expected[@]}"; do
  grep -q -F "$p" .claude/settings.local.json || missing+=("$p")
done
if (( ${#missing[@]} > 0 )); then
  echo "WARN: settings.local.json missing narrow rules:"
  printf '  - Bash(bash %s:*)\\n' "${missing[@]}"
  echo "Re-run the jq merge from Step 3.7b to fix."
fi
```

If any path is missing, print a clear WARN listing which rules are absent + the remediation pointer. If all present, print PASS.

### Change 3 — wire same verification into upgrade flow

SKILL.md line ~371 documents that upgrade also runs the narrow-rule merge. The verification sub-step should also fire after the upgrade flow's settings.local.json handling, with the same check.

## Source files

- skills/ralph-init/SKILL.md — Step 3.7 (split) + new verification sub-step + upgrade flow reference

## Scope

- SKILL.md prose only. No template file changes. No new scripts.
- The verification is read-only (no auto-fix). User-facing WARN with exact remediation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-init/SKILL.md Step 3.7 is split into two named sub-steps where the second is dedicated to the jq merge (e.g. '### 3.7b' or equivalent named heading) containing the existing RULE1/RULE2/RULE3 + jq block verbatim
- [x] #2 skills/ralph-init/SKILL.md gains a new verification sub-step after the Step 3.x init writes (before Step 4 'Confirm') that grep-checks settings.local.json for the 3 expected script paths and prints a WARN listing any missing rule + remediation pointer to the merge sub-step
- [x] #3 skills/ralph-init/SKILL.md upgrade flow section (current line ~371 area covering settings.local.json) references the same verification check so it fires post-upgrade too
- [x] #4 The verification grep uses fixed-string match (grep -F) for the 3 paths so it tolerates regex-special characters in HOME paths
- [x] #5 No template files are modified — diff scope is exactly skills/ralph-init/SKILL.md plus the task markdown
- [x] #6 After merge, bash .claude/skills/ralph-sync/sync.sh classify shows skill ralph-init as [unchanged] (post-sync)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. Split Step 3.7 into 3.7a (template writes) and 3.7b (jq merge for narrow script rules) — moves the merge to a named sub-step instead of free-flowing prose inside 3.7.
2. Add a new Step 3.10 'Verify settings.local.json permissions' that grep -F checks for the 3 expected paths and prints PASS or a WARN with remediation. Place after 3.9 (Obsidian) but before Step 4 (Summary).
3. Update U4 in upgrade flow to also reference the verification check (post-upgrade fire).
4. Confirm scope: only SKILL.md prose + task md change. Run ralph-sync classify post-merge for AC6.

Implementation: Step 3.7 split into 3.7a (template write) + 3.7b (jq merge); added Step 3.10 verification with grep -F fixed-string match for the 3 expected script paths; upgrade flow (U4 line) updated to reference Step 3.7b + Step 3.10. Snippet passes bash -n. Ralph's iteration 1 (which hit rate limit) already split 3.7a/b — this interactive completion added 3.10 + wired U4.

Commit: `e1bf722` - task-122: Promote jq merge to 3.7b and add 3.10 verification

Reviewer APPROVED (e1bf722).

Post-merge: ralph-sync applied (skill ralph-init updated); classify now shows [unchanged]. AC #6 verified.
<!-- SECTION:NOTES:END -->
