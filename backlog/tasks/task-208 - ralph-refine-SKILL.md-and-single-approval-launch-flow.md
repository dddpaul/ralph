---
id: TASK-208
title: ralph-refine SKILL.md and single-approval launch flow
status: Done
assignee: []
created_date: '2026-07-22 16:29'
updated_date: '2026-07-23 08:52'
labels:
  - 'feature:ralph-refine'
dependencies:
  - TASK-206
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-008 of ralph-refine. Add the ralph-refine SKILL.md so the skill is separately invocable and documents the single-approval launch flow (one sandbox-bypass prompt, mirroring ralph-run). See design/ralph-refine-prd.md US-008 and doc-4 invariant 4.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 plugins/ralph/skills/ralph-refine/SKILL.md exists with a description that makes the skill separately invocable/discoverable
- [x] #2 Documents invocation: ./refine.sh --prompt/--author/--reviewer, the --draft mode, --type, --threshold, and output landing in iterations/
- [x] #3 References the bundled example role sets
- [x] #4 No plugin.json edit required (skills auto-discover) — verified the skill is listed by the plugin loader
- [x] #5 Single-approval flow: when the skill launches refine on the user's behalf, exactly one permission prompt fires (the sandbox-bypass refine.sh launch); the SKILL.md documents this and issues the launch as a single sandbox-bypass Bash call
- [x] #6 Any helper command the SKILL.md runs is either a read-only sandbox-safe check or a bash <abs-path> shim covered by a seeded Bash(bash <abs-path>:*) allow rule — no second prompt
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add plugins/ralph/skills/ralph-refine/SKILL.md (foreground refine, phase-1). Structure mirrors ralph-run SKILL.md but simpler (no nohup/heartbeat — refine is foreground per FR-5). Sections: discoverable frontmatter description; Step 1 parse args (map skill key=value → refine.sh flags: prompt/draft/author/reviewer/type/threshold/max_iterations/tool/model/effort/timeout/output_dir/on_error/retry_count/devcontainer/resume/verbose/dry_run); Step 2 locate ./refine.sh (read-only, sandbox-safe, no prompt); Step 3 single sandbox-bypass launch (dangerouslyDisableSandbox:true — the ONE prompt); Step 4 relay foreground output (final.{ext}+summary.md land in iterations/); reference bundled examples/{article,drawio,plantuml}. Single-approval invariant: only the launch prompts; every helper is read-only sandbox-safe (AC#6 branch 1) → no seeded allow rule / no plugin.json edit (AC#4 skills auto-discover; marketplace.json+plugin.json carry no skills array). No R11 obligation (SKILL.md not in R11 table). Verify: bash -n unaffected; ruff+pytest stay green (markdown-only).

Commit: `b9f32dd` - task-208: add ralph-refine SKILL.md documenting the single-approval refine.sh launch flow, flags, iterations/ outputs, and bundled example role sets

Implemented US-008: added plugins/ralph/skills/ralph-refine/SKILL.md (161 lines). Foreground refine loop (phase-1, no detach) — structure mirrors ralph-run SKILL.md but simpler. Documents ./refine.sh --prompt/--draft/--author/--reviewer, --type/--threshold/--max-iterations + full flag table with defaults matching args.py (FR-5 parity); output files (final.<ext>, summary.md, artifact-v<N>, review-v<N>) in iterations/; exit codes 0/1/130. References bundled examples/{article,drawio,plantuml} with a runnable one-liner. Single-approval invariant: only Step 3 launch prompts (single dangerouslyDisableSandbox:true Bash call); Step 2 locate is read-only sandbox-safe → AC#6 branch-1, no seeded allow rule / no settings-template change. AC#4: plugin.json & marketplace.json carry no skills array (verified) → auto-discovery, no edit; frontmatter name==dir validated across all 11 skills. No R11 obligation (SKILL.md not in R11 table). Gate: ruff clean, 314 pytest pass, bash -n refine.sh OK. task-reviewer: APPROVED. Note: commit-prefix-guard.sh parses only single-line -m "..."; used a single subject-only -m.
<!-- SECTION:NOTES:END -->
