---
id: TASK-143
title: Remove unused git-delta install from devcontainer Dockerfile
status: Done
assignee: []
created_date: '2026-06-20 18:11'
updated_date: '2026-06-20 18:37'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
git-delta is installed in .devcontainer/Dockerfile but never wired up. There is no `core.pager = delta`, no `interactiveDiffFilter`, no gitconfig that activates it. `grep -rn delta agents/ skills/ ralph.sh` returns nothing. Ralph reads `git diff` as plain text; delta would only matter for a human SSHing into the container, and no one does. The package is dead weight inherited from upstream Claude Code's reference devcontainer image.

**Concrete failure that motivated this** — TASK-142 launch on 2026-06-20 died because `docker buildx build` ran:

```
wget https://github.com/dandavison/delta/releases/download/0.18.2/git-delta_0.18.2_arm64.deb
```

and got exit code 4 (network failure). Buildx has no retry; one CDN blip = full container build aborted. Removing the install block eliminates the single point of failure for a dependency we don't use, and drops ~5 MB from the image.

**Files to touch (R11 parity pair, both pairs in this task per rule 3):**

1. `.devcontainer/Dockerfile` — delete the `# ---- git-delta ----` block at lines 73-78 (ARG GIT_DELTA_VERSION + RUN wget/dpkg/rm)
2. `.devcontainer/devcontainer.json` — remove the `"GIT_DELTA_VERSION": "0.18.2"` entry from `build.args`
3. `skills/ralph-init/templates/devcontainer/Dockerfile.base` — delete the matching git-delta block at lines 60-66
4. `skills/ralph-init/templates/devcontainer/devcontainer.json` — remove the matching GIT_DELTA_VERSION build arg

**Verification path:** after edits, run `docker buildx build .devcontainer/` end-to-end and confirm the wget step is gone from the build trace. Then test `./ralph.sh --tool claude --devcontainer 1 --tasks <some-test-task-id>` to confirm container-up still works.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Live .devcontainer/Dockerfile contains no git-delta references (grep -i delta .devcontainer/Dockerfile returns empty)
- [x] #2 Live .devcontainer/devcontainer.json contains no GIT_DELTA_VERSION (grep GIT_DELTA .devcontainer/devcontainer.json returns empty)
- [x] #3 Template skills/ralph-init/templates/devcontainer/Dockerfile.base contains no git-delta references
- [x] #4 Template skills/ralph-init/templates/devcontainer/devcontainer.json contains no GIT_DELTA_VERSION
- [x] #5 docker buildx build .devcontainer/ completes end-to-end with no wget-against-github.com step in the trace
- [ ] #6 After successful build: ./ralph.sh --tool claude --devcontainer 1 --tasks <id> launches and the container reaches the heartbeat-emitting state
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 4 edits in one branch.
1. .devcontainer/Dockerfile: delete lines 73-78 (git-delta block).
2. .devcontainer/devcontainer.json: remove GIT_DELTA_VERSION arg from build.args.
3. skills/ralph-init/templates/devcontainer/Dockerfile.base: delete lines 61-66 (same block).
4. skills/ralph-init/templates/devcontainer/devcontainer.json: remove GIT_DELTA_VERSION arg.
Verify: grep delta returns empty in all 4 files; docker buildx build .devcontainer/ succeeds end-to-end; ./ralph.sh --devcontainer 1 launches and heartbeats.

Implementation: removed git-delta install block from .devcontainer/Dockerfile (8 lines incl. ARG + RUN) and skills/ralph-init/templates/devcontainer/Dockerfile.base (same 8 lines). Removed GIT_DELTA_VERSION build arg from both devcontainer.json files. Both R11 mirror pairs stayed identical.

Verification (interactive run):
- AC #1-4 PASS: grep delta / grep GIT_DELTA returned empty in all four target files.
- AC #5 PASS: docker buildx build .devcontainer/ completed end-to-end (19 steps DONE, no ERROR, no delta/git-delta in trace, image ralph-test-task143 loaded). Log saved at /tmp/claude/build-task143.log during test.
- AC #5 supplement: devcontainer up --workspace-folder ... returned {outcome:success,containerId:cee68a59...}, firewall verification passed both inverse (example.com blocked) and positive (api.github.com via proxy reachable).

AC #6 deferred to next natural Ralph launch (R2 explicit deferral). Reason: this task changed only Dockerfile content (removed an unused install block); the ralph.sh launch path and in-container heartbeat-emit logic are unchanged. AC #5 already proves the image builds + container starts, which is the only mechanism this task could break. Follow-up: next /ralph-run invocation (e.g., TASK-142 retry) will exercise the full ralph.sh -> container -> heartbeat path; if heartbeat appears, AC #6 is retroactively satisfied. No code path needs separate test.

task-reviewer APPROVED. R2 deferral of AC #6 accepted (Dockerfile-only change; launch path unchanged; AC #5 covers build+up). R11 parity verified in both pairs.

Commit: `c39a741` - task-143: Remove unused git-delta install from devcontainer
<!-- SECTION:NOTES:END -->
