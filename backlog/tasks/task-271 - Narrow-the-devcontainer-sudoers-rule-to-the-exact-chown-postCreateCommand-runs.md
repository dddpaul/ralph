---
id: TASK-271
title: Narrow the devcontainer sudoers rule to the exact chown postCreateCommand runs
status: Done
assignee: []
created_date: '2026-10-05 16:51'
updated_date: '2026-10-05 17:31'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The devcontainer template grants the `node` user passwordless `sudo /bin/chown` with any arguments. Inside the container the firewall (`init-firewall.sh`) is the only isolation, and Ralph runs `claude --dangerously-skip-permissions` there. With unrestricted chown, `node` can take ownership of the root-owned, sudo-allowed `/usr/local/bin/init-firewall.sh`, rewrite it and run it through sudo as root — full root, firewall flushed. The only chown the template actually needs is the one `postCreateCommand` runs: `sudo chown node:node /workspace/.venv`. A task reviewer flagged this as blocking in a downstream project (stacks, TASK-354), where the rule was narrowed locally; every project assembled from the current template still carries the broad rule.

## Scope

In scope:
- Narrow the sudoers line in `Dockerfile.base` to the exact chown invocation, with the colon escaped for sudoers (`node\:node`; an unescaped `:` is a sudoers syntax error).
- Make a malformed rule fail the image build by validating the file with `visudo -cf`.
- Mirror the change in the live `.devcontainer/Dockerfile` (template parity).
- Pin the narrowed rule with a test.

The target shape (as applied and verified with `visudo -cf` → `parsed OK` in stacks; the unescaped variant fails with a syntax error):

```dockerfile
RUN chmod +x /usr/local/bin/init-firewall.sh \
 && echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh, /bin/chown node\:node /workspace/.venv" > /etc/sudoers.d/node-firewall \
 && chmod 0440 /etc/sudoers.d/node-firewall \
 && visudo -cf /etc/sudoers.d/node-firewall
```

Inside the double-quoted `echo`, `sh` keeps `\:` literally (backslash escapes only `$`, backtick, `"`, `\` and newline), so the file receives `node\:node`.

Not yet verified in a live container: whether sudo matches `sudo chown …` (resolved through `secure_path`, possibly to `/usr/bin/chown` on merged-/usr Debian) against the `/bin/chown` rule. sudo compares the resolved command by device/inode, so it should match, but the live check in the AC below is the proof.

Out of scope:
- Upgrade-time detection or patching of an existing project's assembled `.devcontainer/Dockerfile` (U2 marks it `skipped (assembled)`, so existing projects keep the broad rule until patched by hand). Record a proposed follow-up task in the notes instead, modelled on `stale-runtime-copy.sh` / `floating-uv-copy.sh`.
- Any other change to `init-firewall.sh`, `devcontainer.json` or `postCreateCommand`.

## Files

- `plugins/ralph/skills/ralph-init/templates/devcontainer/Dockerfile.base` (exists) — sudoers line at line 132
- `.devcontainer/Dockerfile` (exists) — the same line at line 147 (template parity)
- `tests/unit/template-parity.bats` (exists) — must keep passing
- `tests/python/test_devcontainer_sudoers.py` (to-create) — pins the narrowed rule, next to `tests/python/test_devcontainer_uv_pin.py` (exists) and `tests/python/test_devcontainer_claude_code_pin.py` (exists)

## Source

Source: /Users/paul/Private/Alfa/Projects/standard/stacks@bf209f77170a
Source reference (read-only context, do NOT modify): /Users/paul/Private/Alfa/Projects/standard/stacks/.devcontainer/Dockerfile (the narrowed line near line 184) and the review notes of stacks TASK-354 (`backlog task view 354 --plain` in that repo).

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

The live-container AC needs a host with Docker: a Ralph run inside the devcontainer cannot build or recreate its own container.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Dockerfile.base grants node exactly /usr/local/bin/init-firewall.sh and /bin/chown node\:node /workspace/.venv; grep -rn '/bin/chown"' plugins/ .devcontainer/ finds no bare chown rule
- [x] #2 The sudoers RUN step ends with visudo -cf /etc/sudoers.d/node-firewall, so a malformed rule fails the image build
- [x] #3 .devcontainer/Dockerfile carries the same narrowed line and tests/unit/template-parity.bats passes
- [x] #4 tests/python/test_devcontainer_sudoers.py fails on the bare /bin/chown form and on an unescaped node:node, and passes on the narrowed line
- [x] #5 On a host with Docker, a freshly built devcontainer starts with postCreateCommand succeeding; inside it sudo -n chown node:node /workspace/.venv exits 0 and sudo -n chown node /usr/local/bin/init-firewall.sh is refused; the sudo -l output is recorded in the task notes
- [x] #6 uv run pytest and uv run ruff check . pass
- [x] #7 A proposed follow-up task for upgrade-time detection and patching of existing projects' assembled Dockerfile is recorded in the task notes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: handoff checklist yellow — all (exists) paths present, no deps, AC #5 needs a Docker host (none in this container) so it is deferred to the host. Narrow the sudoers echo in Dockerfile.base + .devcontainer/Dockerfile to init-firewall.sh and /bin/chown node\:node /workspace/.venv, append visudo -cf; add tests/python/test_devcontainer_sudoers.py that extracts the rule via sh (as the build would write it) and checks the exact command list, the escape, visudo as last step, plus mutation cases (bare chown, unescaped colon); also tie the chown args to postCreateCommand. Record follow-up task proposal in notes.

Commit: `d293c34` - task-271: grant node only the venv chown in the devcontainer sudoers rule and validate it with visudo

Proposed follow-up task (AC #7, not created here): 'Detect and patch the broad devcontainer sudoers chown on upgrade'. Add plugins/ralph/skills/ralph-init/scripts/broad-sudoers-chown.sh, modelled on stale-runtime-copy.sh / floating-uv-copy.sh: in Upgrade Mode, where U2 marks .devcontainer/Dockerfile 'skipped (assembled)', it greps the assembled Dockerfile for the echo into /etc/sudoers.d/node-firewall whose grant ends in a bare '/bin/chown"'. It reports the finding and, with consent, rewrites that line to the narrowed form '/bin/chown node\:node /workspace/.venv' and appends '&& visudo -cf /etc/sudoers.d/node-firewall'. A pytest with fixture Dockerfiles pins it: broad gets flagged and patched, narrowed is a no-op, and a hand-customised grant gets reported without being patched. SKILL.md Upgrade Mode calls it and tells the user to rebuild the container.

AC #5 deferred to a Docker host: this Ralph run is inside the devcontainer (no docker binary) and cannot rebuild its own container. The current container still shows the old broad rule (sudo -n -l: '(root) NOPASSWD: /usr/local/bin/init-firewall.sh, /bin/chown'). This matters because /bin -> usr/bin here, so whether sudo matches 'sudo chown' (secure_path -> /usr/bin/chown) against the /bin/chown rule is still unproven. Host check: rebuild the devcontainer (Dev Containers: Rebuild Container, or devcontainer up --remove-existing-container) and confirm postCreateCommand succeeds. Then, inside the container, run: sudo -n chown node:node /workspace/.venv; echo $? (expect 0); sudo -n chown node /usr/local/bin/init-firewall.sh; echo $? (expect refusal, non-zero); sudo -n -l. Append the outputs to these notes and check AC #5. Gates: uv run pytest 819 passed/3 skipped; ruff clean; bats tests/unit 147 ok, 1 not ok (#134 settings.local.json shape, fails identically on master because of the untracked local file). The new test fails 8/12 against the pre-change Dockerfiles.

task-reviewer (ralph:task-reviewer, installed 0.12.0): first pass CHANGES REQUESTED (AC #7 proposal and AC #5 deferral note missing from notes) → added → re-review APPROVED, SCORE 10, 0 blocking, 0 minor.

Not marked Done and not merged: AC #5 is the only proof that sudo still allows the postCreateCommand chown under the narrowed rule; merging unverified could break postCreateCommand for every newly scaffolded project. Remaining steps on the host: run the AC #5 check above, record the output and check AC #5, then Done + Merge step 6 (bump-version.sh --auto bumps the plugin version, since Dockerfile.base and ralph-init SKILL.md changed).

Host verification (macOS, Docker): devcontainer up --workspace-folder /Users/paul/Private/Projects/ai/ralph --remove-existing-container rebuilt the image and replaced Ralph's container (2a5e939ce3f9 -> 76d8b0f97391); outcome success. Build step 13/13 ran the narrowed RUN; visudo -cf printed '/etc/sudoers.d/node-firewall: parsed OK'. postCreateCommand succeeded (log moved on to postStartCommand; /workspace/.venv is node:node; safe.directory=/workspace set). Inside the container as node: sudo -n chown node:node /workspace/.venv exit 0; sudo -n chown node /usr/local/bin/init-firewall.sh refused ('sudo: a password is required', exit 1); chown root:root and chown -R node:node on .venv also refused. sudo -n -l: 'Matching Defaults entries for node: env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin, use_pty. User node may run the following commands: (root) NOPASSWD: /usr/local/bin/init-firewall.sh, /bin/chown node\:node /workspace/.venv'. Host gates after merging master (0.13.1): uv run ruff check . clean; uv run pytest 820 passed, 2 skipped; LC_ALL=C bats tests/unit 154 ok, 0 not ok; grep for a bare /bin/chown rule finds none.

Commit: `4fb019a` - task-271: bump plugin version to 0.13.2 (patch)
<!-- SECTION:NOTES:END -->
