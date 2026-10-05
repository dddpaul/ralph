---
id: TASK-263
title: 'Serve shared reviewer rules from the plugin, not per-project copies'
status: Done
assignee: []
created_date: '2026-10-04 18:54'
updated_date: '2026-10-05 06:12'
labels: []
dependencies:
  - TASK-262
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decision: serve the shared reviewer rules from the plugin instead of copying them into each project. Rule distribution is currently a side effect of the ralph-init skill — a human must run the upgrade in every project, an agent performs the copy by reading an English sentence, and nothing detects a project that never did. Concrete skew measured on this machine: the cached 0.9.0 rules template carries 3 R-DOCS rules and 0.9.2 carries 9, so any project last upgraded under 0.9.0 is silently missing six rules.

Mechanism, verified against the plugin manifest reference rather than assumed. The Where-each-variable-resolves table gives "Skill, command, and agent content | Anywhere in the Markdown body | Not applicable", and the prose states the variables are not present in the environment of commands Claude runs through the Bash tool, in the main session or in a subagent, and to write the reference in the Markdown body where Claude Code substitutes the path inline when it loads the content. So the braced token goes literally into the agent Markdown, inside double quotes:

```text
"${CLAUDE_PLUGIN_ROOT}"/skills/ralph-init/rules/task-reviewer-rules.docs.md
```

Do not look the variable up as a shell environment variable — an environment probe will fail misleadingly even though the mechanism works.

Resolve from the agent's own loaded plugin root, never by globbing the newest cached version. The agent version and the rules version must agree, and a glob would pair a new bundle with an old agent.

This REPLACES the per-project copy tier; it does not add a fourth tier. Leaving the project copy loadable means a stale three-rule file keeps applying beside the fresh nine-rule bundle, and the existing override-by-rule-ID precedence does not neutralise a stale copy automatically. After this task the loader no longer reads the project copy, so any file left in a project becomes inert — deleting those files and stopping ralph-init from writing them is the dependent follow-up task, which is why the split is safe here.

Fix the CWD dependency in the same change. The loader in `plugins/ralph/agents/task-reviewer.md` resolves the project tier through a bare relative path, so it depends on the Bash tool's working directory. The same substitution table provides a project-root variable that belongs in the Markdown body for that tier:

```text
"${CLAUDE_PROJECT_DIR}"/.claude/task-reviewer-rules.md
```

Separate two failures the current loop collapses. Its test is a file-exists-and-non-empty check, so a missing bundle is indistinguishable from a tier that does not apply. A bundle that ships with the plugin and is missing or empty is an install error and must be surfaced; an applicability gate evaluating false is simply not-applied and is not an error.

Make applicability explicit rather than inferred. Probing for a vault directory is an imperfect classifier in both directions: a documentation repository without Obsidian would miss the rules, and a code repository that happens to contain a vault would enable them. Give the project an explicit enable or disable choice and document the default when unset.

Preserve the auditability that the in-project copy provided. Dropping the tracked copy means the same project commit can receive a different verdict after a plugin update, and some teams deliberately pin review policy for historical reproducibility. The floor is for the review report to record the plugin version, the resolved bundle path, and any explicitly overridden rule IDs. Per-source content hashes are optional: a hash identifies content without recovering it once caches are pruned, so it only pays off where release artifacts are also retained. Pinning a plugin version stays an optional project policy, separate from tracking the latest shared rules by default.

Test the substitution, not shell expansion. A unit test that extracts the snippet and exports an environment variable proves only that the shell expands a variable; it must model Markdown substitution instead. The end-to-end check is to invoke the real plugin agent and have it print the resolved bundle path.

Framing to retire with the copying: once the rules are no longer copied, the file is a plugin-owned rules bundle rather than a template whose mirror must match. Template-parity checks do not cover runtime distribution, so do not claim they do; cover content, tier selection, load order, overrides and load errors instead.

Provenance: the replace-not-add defect, the same-plugin-root requirement, the error-versus-gate distinction, the classifier weakness and the auditability cost were raised by Codex in peer review; the substitution contract was then verified directly against the documentation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The agent's rule loader resolves the shared rules bundle from a braced CLAUDE_PLUGIN_ROOT reference written literally in the Markdown body and double-quoted, with no shell environment lookup — grep over plugins/ralph/agents/task-reviewer.md shows the braced token and no bare dollar-sign form
- [x] #2 The loader no longer reads the per-project shared-rules copy: grep over plugins/ralph/agents/task-reviewer.md finds no reference to a task-reviewer-rules.docs.md path under .claude, so a file left in a project is inert
- [x] #3 The project rules tier resolves through a braced CLAUDE_PROJECT_DIR reference instead of a working-directory-relative path, verified by running the loader from a subdirectory and seeing the project tier still load
- [x] #4 A missing or empty shipped bundle is surfaced as an error while an applicability gate evaluating false is reported as not-applied, and the two outcomes are distinguishable in the loader output — verified by one fixture of each
- [x] #5 Whether the docs rules apply is decided by an explicit project setting rather than only by probing for a vault directory, and the behaviour when the setting is unset is documented in the agent file
- [x] #6 The review report records the plugin version, the resolved bundle path, and any explicitly overridden rule IDs
- [ ] #7 The test that exercises the extracted loader snippet models Markdown substitution rather than exporting an environment variable, and a smoke check invokes the real plugin agent to print the resolved bundle path with its output recorded in the task notes
- [x] #8 tests cover bundle content, tier selection, load order, override-by-rule-ID and load-error handling, and the bundle is not registered as a template-parity mirror in tests/unit/template-parity.bats
- [x] #9 Gates: uv run ruff check . is clean, uv run pytest passes, and LC_ALL=C node_modules/.bin/bats tests/unit passes with no new failures relative to master
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Execution constraint (R4): AC #7's smoke check must invoke the real plugin agent, but the agent runs from the INSTALLED plugin cache, not this worktree, and the Agent enum is fixed at session start. Inside a Ralph run the installed agent is the pre-change version, so the smoke check cannot be performed honestly before merge. Defer AC #7's smoke-check half explicitly (per R2) with that reason; the Markdown-substitution unit test half is checkable in-run. The smoke check is done post-merge on the host after /plugin update and /reload-plugins, by invoking ralph:task-reviewer and having it print the resolved bundle path.

Plan: git mv the docs rules from templates/claude/ to skills/ralph-init/rules/ (plugin-owned bundle, out of the template tree so it is no mirror); rewrite the agent loader to resolve the bundle via "${CLAUDE_PLUGIN_ROOT}" and project files via "${CLAUDE_PROJECT_DIR}" (Markdown substitution), drop the .claude/ docs-copy tier, gate docs rules on docs_rules=on|off in .claude/task-reviewer.conf (unset -> .obsidian/ probe), print per-tier loaded/absent/not applied/ERROR plus plugin version, bundle path and override references; add a Rules provenance report section; repoint ralph-init's copy source (copying itself stays until TASK-265); rewrite task-reviewer-rules-loading.bats with a substitution model; drop the template registration from template-parity.bats.

Commit: `c5b62d1` - task-263: move the shared docs reviewer rules out of the template tree into a plugin rules bundle

Commit: `ffb53a8` - task-263: load the shared docs reviewer rules from the plugin root with an explicit per-project gate

Implemented: bundle moved (pure git mv, separate commit) to plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.docs.md; agent loader resolves it via "${CLAUDE_PLUGIN_ROOT}" and project files via "${CLAUDE_PROJECT_DIR}"; per-project .claude docs copy no longer read; docs gate = docs_rules=on|off in .claude/task-reviewer.conf (last line wins; unset -> .obsidian/ probe; other value -> load error); per-tier output loaded/absent/not applied/ERROR plus plugin version, docs bundle, project root, override references; new Rules provenance report section. ralph-init SKILL.md only repointed its copy source to rules/ (Init/Upgrade copying itself is TASK-265 scope; SKILL.md 3.7c sentence updated so it no longer claims the agent reads the copy). template-parity.bats: dropped the non_mirrored entry and the template-header test; new test asserts the bundle is outside templates/ and in neither registry list.

AC #7 split: the Markdown-substitution unit test half is done — tests/unit/task-reviewer-rules-loading.bats substitutes the literal braced references in the snippet text and runs it under env -u CLAUDE_PLUGIN_ROOT -u CLAUDE_PROJECT_DIR; a further test proves the raw unsubstituted snippet reports 'project root: ERROR: unresolved'. DEFERRED: the smoke-check half (invoke the real installed ralph:task-reviewer and print the resolved bundle path). Reason: inside this run the installed agent is the pre-change plugin-cache version and the Agent enum is fixed at session start (R4), so it cannot be performed honestly before merge. Follow-up: post-merge on the host, /plugin update + /reload-plugins, invoke ralph:task-reviewer asking it to run its loader and print the 'docs bundle:' line, record the output here, then check AC #7.

Gates: ruff clean; pytest 719 passed; bats tests/unit 137/138 — the one failure (R11 settings.local.json JSON shape) comes from the ignored machine-local .claude/settings.local.json in this checkout; a clean master worktree passes 119/119 and the same test fails at HEAD~ in this checkout, so it is not introduced here. Loader also verified under zsh (the Bash tool shell) from a subdirectory against the real plugin root: version 0.9.3, 9 R-DOCS rules loaded.

Commit: `c33fa94` - task-263: treat every docs_rules value other than on or off as a load error

Review round 1 (CHANGES REQUESTED, 2 blocking): fixed — (1) SKILL.md 3.7c no longer says the copy gives the agent the rules; it is described as a legacy in-project copy; (2) any docs_rules line now counts (last wins) and every value other than on/off, including trailing comments and empty, is a load error instead of a silent .obsidian/ fallback; new bats fixture covers both. bats tests/unit 138/139, same single pre-existing settings.local.json failure.

Review round 2: APPROVED (0 blocking, 1 minor wording remark on SKILL.md:361 appositive, left as is — SKILL.md 3.7c is rewritten by TASK-265). AC #7 smoke-check half remains DEFERRED to post-merge host verification as recorded above.

Commit: `34d2146` - task-263: bump plugin version to 0.9.4 (patch)
<!-- SECTION:NOTES:END -->
