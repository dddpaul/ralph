---
id: TASK-110
title: Fix broken backlog task list -l reference in ralph-review skill
status: In Progress
assignee: []
created_date: '2026-05-09 06:15'
updated_date: '2026-05-10 12:48'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 2b of skills/ralph-review/SKILL.md calls a non-existent CLI flag (backlog task list -l feature:<name>). The -l filter does not exist on backlog task list as of backlog.md v1.44.0 (confirmed via backlog task list --help). Today's review had to fall back to grepping task files manually. Replace the broken command with the grep-based pipeline below (already designed and tested), and add a short note explaining why the CLI is not used. Update both this repo's copy and the user-global copy via ralph-sync after merge.

Pre-designed grep pipeline (drop into Step 2b verbatim):

```bash
name=<feature-slug>
grep -rl --include="*.md" -E "^\s*-\s*['\"]?feature:${name}['\"]?\s*\$" backlog/tasks/ \
  | while IFS= read -r f; do
      grep -qE "^status:\s*Done\s*\$" "$f" \
        && grep -m1 -E "^id:\s*TASK-" "$f" | sed -E 's/^id:[[:space:]]*TASK-//'
    done | sort -V
```

Emits one numeric task ID per line; downstream callers feed each into `backlog task view <id> --plain`. The YAML list-item anchor `^\s*-\s*["]?feature:...["]?\s*$` prevents false positives from description text. `sort -V` gives natural numeric ordering.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-review/SKILL.md Step 2b no longer references 'backlog task list -l <label>'; instead uses a grep pipeline that resolves task IDs from backlog/tasks/*.md
- [x] #2 The grep regex anchors on ^\s*-\s*['"]?feature:<name>['"]?\s*$ (YAML list-item form) to prevent false positives from description text
- [x] #3 The pipeline filters by ^status:\s*Done\s*$ so only Done tasks are returned
- [x] #4 Step 2b explains that downstream steps feed each resulting numeric ID into 'backlog task view <id> --plain'
- [x] #5 A short note in SKILL.md documents WHY the grep approach is used (backlog.md v1.44.0 has no -l filter on task list)
- [x] #6 ralph-sync classifies the project copy as [updated] after the change is committed (verifiable via 'bash .claude/skills/ralph-sync/sync.sh classify')
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Replace Step 2b's 'backlog task list -l feature:<name> -s Done --plain' command with the pre-designed grep pipeline anchored on YAML list-item form. Add a brief WHY note explaining that backlog.md v1.44.0 has no -l filter on task list. Verify ralph-sync classifies as [updated] post-commit.
<!-- SECTION:NOTES:END -->
