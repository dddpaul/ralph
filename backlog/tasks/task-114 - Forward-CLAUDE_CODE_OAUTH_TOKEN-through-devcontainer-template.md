---
id: TASK-114
title: Forward CLAUDE_CODE_OAUTH_TOKEN through devcontainer (template + this project)
status: Done
assignee: []
created_date: '2026-05-10 13:07'
updated_date: '2026-05-10 17:03'
labels:
  - devcontainer
  - template
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Inside a devcontainer started by macOS hosts, `claude` fails authentication. The macOS host stores OAuth credentials in the system Keychain (not on disk), so the bind-mounted host Claude credentials file is empty and the container has no working auth path. Ralph cannot run inside the devcontainer until this is fixed.

The Anthropic-documented way out is `claude setup-token` (host-only, valid for 1 year). The host then exports `CLAUDE_CODE_OAUTH_TOKEN`. Forwarding that variable into the container via `containerEnv` + `${localEnv:...}` substitution lets `claude` inside auth without touching Keychain.

This was already done by hand in the `channels` project (its TASK-15). The fix needs to live in BOTH:

- this repo's live devcontainer config (so devcontainer auth works on this Ralph project today after merge), AND
- the ralph-init template (so every future Ralph-bootstrapped project gets it for free).

R11 parity: both files mirror byte-for-byte on the new entry — same key, same value, same first-key position.

Reference: https://code.claude.com/docs/en/authentication.md#generate-a-long-lived-token

## What

1. Edit the ralph-init template at:

   ```
   skills/ralph-init/templates/devcontainer/devcontainer.json
   ```

   Inside the existing `containerEnv` block, add one entry as the FIRST key (before `NODE_OPTIONS`):

   ```jsonc
   "CLAUDE_CODE_OAUTH_TOKEN": "${localEnv:CLAUDE_CODE_OAUTH_TOKEN}",
   ```

   Keep all other keys (`NODE_OPTIONS`, `CLAUDE_CONFIG_DIR`, `POWERLEVEL9K_DISABLE_GITSTATUS`, `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, `TZ`) verbatim and in the same relative order.

2. Apply the SAME edit to this repo's live devcontainer config at:

   ```
   .devcontainer/devcontainer.json
   ```

   Mirror the template byte-for-byte for the new entry: same key, same value, same first-key position.

3. Add a short host-side prerequisites note. Choose one of:
   - Append a section to `skills/ralph-init/SKILL.md` near Step 3.6 (devcontainer setup) documenting the host-side requirement, OR
   - Append a section to `README.md` if there is a "Devcontainer auth" or "Setup" section.

   The note must include four concrete steps:
   - Run `claude setup-token` once to mint a long-lived host token.
   - Export `CLAUDE_CODE_OAUTH_TOKEN` from the shell's always-sourced env file (zsh users: the `.zshenv` file; bash users: equivalent), so it propagates to non-interactive subshells launched by GUI apps. macOS Keychain users can pull the token from Keychain inside that env file:

     ```sh
     export CLAUDE_CODE_OAUTH_TOKEN="$(security find-generic-password -a "$USER" -s "claude-code-oauth-token" -w 2>/dev/null)"
     ```

   - Address the GUI-app caveat: VS Code launched from Dock/Spotlight does **not** source the shell's env file. Either (a) restart VS Code from a shell that has the token, or (b) run `launchctl setenv CLAUDE_CODE_OAUTH_TOKEN <value>` for a launchd-domain export visible to all GUI apps.
   - Note `launchctl setenv` does not persist across reboots — either re-run after each reboot, or persist via a launchd plist in `~/Library/LaunchAgents/`.

4. **Do not** commit any token value anywhere. Both files only contain the env var name and the `${localEnv:...}` substitution.

5. **Graceful degradation:** when the host shell does not export the token, `${localEnv:CLAUDE_CODE_OAUTH_TOKEN}` resolves to empty string and the container starts unaffected (existing host Keychain auth path stays intact).

## Verification (manual smoke test, after merge)

Not an AC because Ralph cannot run this autonomously from inside the very container being tested. Implementer should manually verify after merge by rebuilding the devcontainer, confirming the env var is visible inside, then running `claude --version` and `claude doctor` to confirm no "Not logged in" error.

## Out of scope

- Modifying `Dockerfile` or the firewall init script.
- Changing how `claude` itself reads `CLAUDE_CODE_OAUTH_TOKEN` — that's an upstream Claude Code feature, already working.
- Migrating other already-bootstrapped projects' devcontainer configs (besides this one) — that's `ralph-init upgrade` flow's job.
- Adding a `.devcontainer/` to projects that don't already have one.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Inside the existing `containerEnv` block in `skills/ralph-init/templates/devcontainer/devcontainer.json`, the entry `"CLAUDE_CODE_OAUTH_TOKEN": "${localEnv:CLAUDE_CODE_OAUTH_TOKEN}"` is present
- [x] #2 The new entry is the first key in the `containerEnv` block (placed before `NODE_OPTIONS`)
- [x] #3 All other keys in containerEnv (NODE_OPTIONS, CLAUDE_CONFIG_DIR, POWERLEVEL9K_DISABLE_GITSTATUS, HTTP_PROXY, HTTPS_PROXY, NO_PROXY, TZ) keep their existing values and relative order
- [x] #4 Template file `skills/ralph-init/templates/devcontainer/devcontainer.json` parses as valid JSONC (a URL-aware comment-stripper followed by `json.loads` succeeds — the naive `re.sub(r"//[^\n]*", "", ...)` regex must NOT be used to validate, because it eats `//` inside URL string values)
- [x] #5 Either `skills/ralph-init/SKILL.md` or `README.md` gains a host-side prerequisites note covering: (a) `claude setup-token`, (b) export from the shell's always-sourced env file with the optional Keychain helper one-liner, (c) the GUI-app caveat (VS Code launched from Dock/Spotlight does not source the shell env file; restart from shell or use `launchctl setenv`), (d) `launchctl setenv` does not persist across reboots (re-run on reboot, or persist via a launchd plist)
- [x] #6 No occurrence of an actual OAuth token value (no string starting with `sk-ant-` or similar) appears anywhere in the diff
- [x] #7 task-reviewer agent verdict on `git diff master..HEAD` is APPROVED
- [x] #8 Inside this repo's live .devcontainer/devcontainer.json containerEnv block, the entry "CLAUDE_CODE_OAUTH_TOKEN": "${localEnv:CLAUDE_CODE_OAUTH_TOKEN}" is present as the FIRST key (before NODE_OPTIONS), and the file parses as valid JSONC
- [x] #9 Live .devcontainer/devcontainer.json and skills/ralph-init/templates/devcontainer/devcontainer.json mirror byte-for-byte for the new entry: same key, same value, same first-key position (R11 parity)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Add CLAUDE_CODE_OAUTH_TOKEN as the FIRST key in containerEnv block of skills/ralph-init/templates/devcontainer/devcontainer.json. (2) Mirror byte-for-byte to .devcontainer/devcontainer.json. (3) Validate both files parse as JSONC (URL-aware comment stripper, NOT naive regex). (4) Append host-side prerequisites note to skills/ralph-init/SKILL.md near Step 3.6 covering claude setup-token, .zshenv export with optional Keychain helper, GUI-app caveat, and launchctl persistence note. (5) Verify diff has no real token values. (6) task-reviewer agent on master..HEAD. (7) Done + merge.

Commit: `822e1ff` - task-114: forward CLAUDE_CODE_OAUTH_TOKEN through devcontainer

Implementation: added CLAUDE_CODE_OAUTH_TOKEN as the first containerEnv key in both skills/ralph-init/templates/devcontainer/devcontainer.json and .devcontainer/devcontainer.json (byte-for-byte parity at line 51). Added host-side prerequisites section to skills/ralph-init/SKILL.md just inside Step 3.6 covering: claude setup-token, .zshenv export with optional Keychain helper, GUI-app caveat with launchctl setenv, and reboot-persistence note via launchd plist. Both files validated as JSONC via URL-aware comment stripper (/tmp/claude/validate_jsonc.py), key order preserved. task-reviewer agent verdict: APPROVED (9/9 ACs met, all standard checklist items clean, R7/R10/R11/R12 custom rules pass). Manual smoke test deferred per task description (Ralph cannot self-verify from inside the container being tested).
<!-- SECTION:NOTES:END -->
