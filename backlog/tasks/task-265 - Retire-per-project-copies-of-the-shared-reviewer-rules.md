---
id: TASK-265
title: Retire per-project copies of the shared reviewer rules
status: Done
assignee: []
created_date: '2026-10-05 05:46'
updated_date: '2026-10-05 06:32'
labels: []
dependencies:
  - TASK-263
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to serving the shared reviewer rules from the plugin. Once the agent's loader stops reading the per-project copy, every such file already written into a project is inert — read by nothing, overwritten by nobody. This task removes the machinery that creates those files and deals with the ones already out there.

Three things ralph-init does today that must stop. Init writes the shared rules into the project for Documentation and Mixed projects. Upgrade overwrites that file from the template on every run and reports it as a row in the status table. The .gitignore block it writes re-includes the file so it is tracked and committed.

Do not delete a project's file silently. The copy in a given project may be pristine, may match an older shipped version, or may carry local edits made in spite of the managed header. Report what is found and remove it only after the operator agrees. A silent delete would destroy edits that, however ill-advised, are the project's own, and the managed header is not sufficient warning for an irreversible action taken without asking.

A project that never upgrades again must not be harmed. Its inert file simply sits there. Nothing in this task may make an un-upgraded project worse off than before, which is what makes the staged rollout safe.

Framing to retire alongside the copying: the shipped file is no longer a template whose project mirror must match, so its registration in the parity suite is no longer meaningful and should go rather than be kept as a permanent exemption with an explanatory comment. The replacement coverage — bundle content, tier selection, ordering, overrides and load errors — belongs to the task that introduced the bundle and is not duplicated here.

Interaction with the managed-file drift detector task: if that task lands first, its test pinning the script's managed-file list against the Upgrade status table will fail when this task removes the shared-rules row. That failure is the intended guard — update the detector's list in this task rather than weakening the test.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph-init Init no longer writes the shared rules into a project: grep over plugins/ralph/skills/ralph-init/SKILL.md finds no step that writes a task-reviewer-rules.docs.md file under .claude
- [x] #2 ralph-init Upgrade no longer overwrites that file and no longer carries it as a managed row in the status table
- [x] #3 Upgrade reports an existing legacy copy and removes it only after the operator agrees, never unconditionally — verified by one fixture where the operator declines and the file survives, and one where they agree and it is removed
- [x] #4 The .gitignore block written by ralph-init no longer re-includes the retired file
- [x] #5 tests/unit/template-parity.bats no longer registers the shared rules file as a mirror pair or as a non-mirrored exemption
- [x] #6 A project that keeps the legacy file and never upgrades is unaffected at review time: a fixture containing the file produces a review that does not load it and does not error
- [x] #7 Gates: uv run ruff check . is clean, uv run pytest passes, and LC_ALL=C node_modules/.bin/bats tests/unit passes with no new failures relative to master
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: drop Init 3.7c + its Files-created line + .gitignore re-include; drop U2 item 15 / U3 / U5 rows / U4 overwrite; add scripts/legacy-docs-rules.sh (check: report legacy copy + whether it matches the shipped bundle; retire <answer>: remove only on y/yes) wired into a new Upgrade U1.5 step; repoint the task-reviewer-rules.md duplicate hint at the plugin bundle; remove the row from managed-file-drift.sh and its test oracle; remove the parity-suite exemption test; pytest fixtures for decline/agree; loader inert-copy test asserts exit 0; README + root .gitignore.

Commit: `18ce292` - task-265: stop writing per-project shared reviewer rules and let upgrade retire the legacy copy on consent

Commit: `2c1f6c2` - task-265: describe the shipped docs rules as a plugin bundle and report an absent copy on retire

Done. Init step 3.7c, the Files-created line and the .gitignore re-include removed; Upgrade U2 item 15 / U3 / U4 / U5 rows removed and the row dropped from managed-file-drift.sh (+ test oracle, obsidian gate gone). New scripts/legacy-docs-rules.sh (check reports the copy as matching or differing from the shipped bundle; retire removes only on y/yes, prints removed/kept/absent) wired into new Upgrade U1.7 with a [y/N] prompt; tests/python/test_retire_legacy_docs_rules.py covers decline/agree fixtures. task-reviewer-rules.md duplicate hint now compares against the plugin bundle. Parity-suite exemption test deleted. Loader inert-copy test now models an un-upgraded vault project and asserts exit 0 / no ERROR. Bundle header rewritten (no longer claims upgrade overwrites it) per review. Gates: ruff clean, pytest 771 passed, bats 1..138 with only the master-baseline #124 failure. task-reviewer APPROVED (10) on second pass.

Commit: `dd49224` - task-265: bump plugin version to 0.11.0 (minor)
<!-- SECTION:NOTES:END -->
