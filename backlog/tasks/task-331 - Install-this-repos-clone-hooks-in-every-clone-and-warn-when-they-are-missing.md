---
id: TASK-331
title: Install this repo's clone hooks in every clone and warn when they are missing
status: To Do
assignee: []
created_date: '2026-11-07T17:25:00Z'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: this repo's release governance relies on two per-clone git hooks that nothing installs. The first is the TASK-214 version-bump wrapper, which execs .claude/hooks/version-bump-guard.sh: the shipped-change bump check plus TASK-319's release-tag check. It sits as .git/hooks/pre-push.local behind the plugin pre-push shim, or as plain .git/hooks/pre-push in a clone that has not moved its pre-push (TASK-328). The second is the bump nudge, .git/hooks/post-commit.local running .claude/hooks/bump-version.sh --nudge. Both were installed by hand on the macOS clone only. The agentbox clone never had them, so its pushes skipped the version-bump guard and the release-tag check; the v0.21.3 tag clash came from that side. Nothing warns about a missing hook, because the guard cannot report that it is not running.

Scope: repo-specific governance under .claude/ only, like bump-version.sh and version-bump-guard.sh. Do NOT mirror any of it into plugins/ralph/skills/ralph-init/templates.

The two files to install, byte for byte:

.git/hooks/pre-push.local (or pre-push in an unmoved clone), mode 755:
```
#!/bin/bash
# pre-push wrapper (TASK-214). Standard hook location, so any other pre-push
# tooling keeps working. Delegates to the tracked, reviewable guard — nothing
# under .git/ is committable, so the guard SOURCE lives in .claude/hooks/ and
# this wrapper is installed once.
exec "$(git rev-parse --show-toplevel)/.claude/hooks/version-bump-guard.sh" "$@"
```

.git/hooks/post-commit.local: copy the macOS clone's file. It runs .claude/hooks/bump-version.sh --nudge || true when that file is executable, then exit 0.

Design: one script, .claude/hooks/install-clone-hooks.sh [--check], resolving the hooks dir with git rev-parse --git-path hooks. Pass rule for pre-push: the plugin shim (cmp with plugins/ralph/skills/ralph-init/templates/shims/git-hook) with the wrapper as pre-push.local, or the wrapper itself as pre-push. A repo-local SessionStart hook in .claude/settings.json runs --check and reports through hookSpecificOutput.additionalContext.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 .claude/hooks/install-clone-hooks.sh installs the TASK-214 wrapper as pre-push.local when the clone's pre-push is the plugin shim, as pre-push when the clone has none, and the bump nudge as post-commit.local when post-commit is the plugin shim (pytest on temporary clones)
- [ ] #2 A second run changes nothing and exits 0; an existing hook file that differs from what it would install is left untouched, named on stderr, and the script exits non-zero (pytest)
- [ ] #3 --check changes nothing, exits 0 when both hooks are in place, and otherwise exits non-zero naming each missing or differing hook (pytest)
- [ ] #4 A repo-local SessionStart hook in .claude/settings.json runs --check and, when it fails, gives the session one line naming the missing hooks and the install command through hookSpecificOutput.additionalContext; it prints nothing when both are in place (pytest feeding the hook)
- [ ] #5 README.md (Releasing plugin updates) and .claude/RELEASING.md tell each clone to run the installer once, after migrate-plugin-hooks.sh clone
- [ ] #6 Nothing new appears under plugins/ralph/skills/ralph-init/templates (git diff --stat shows no path there)
- [ ] #7 bash -n and the bash 3.2 static guard pass on the script; ruff, pytest and bats pass
- [ ] #8 (host) install-clone-hooks.sh --check exits 0 in the macOS clone, and in the agentbox clone after running the installer there
<!-- AC:END -->
