---
id: TASK-290
title: >-
  Keep devcontainer secrets off host argv: skip the exec env probe and forward
  MCP_GATEWAY_TOKEN by name
status: Done
assignee: []
created_date: '2026-11-03T17:32:00Z'
updated_date: '2026-11-03T18:00:00Z'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

TASK-282 moved CLAUDE_CODE_OAUTH_TOKEN off the long-lived `docker run` command line. Its macOS host verification found two secret values that still reach the host's process list (`ps -eo args`, readable by any process that can list processes):

1. **Every `devcontainer exec`.** The devcontainer CLI runs its user-env probe (`userEnvProbe`, default `loginInteractiveShell`) and re-sends the probed container environment as `docker exec -e NAME=value` flags. The container env holds CLAUDE_CODE_OAUTH_TOKEN and MCP_GATEWAY_TOKEN, so both values sit on the host's `ps` for the life of each exec. Every Ralph iteration is one such exec (the orchestrator builds `devcontainer exec --workspace-folder <path> claude ...` in `plugins/ralph/skills/ralph-run/scripts/ralph/tools/claude.py`, and the same in `tools/opencode.py`), and an iteration lasts up to the timeout (60 min by default).
2. **MCP_GATEWAY_TOKEN on `docker run`.** It is still forwarded through `containerEnv` (`"MCP_GATEWAY_TOKEN": "${localEnv:MCP_GATEWAY_TOKEN}"`), so its value sits on the long-lived `docker run` command line exactly as the OAuth token did before TASK-282. It is set on the owner's host (length 64).

Measured on the macOS host (devcontainer CLI 0.90.0, colima):

- During `devcontainer exec --workspace-folder . sleep 6`, the `docker exec` line carried 36 `-e` flags, among them `-eCLAUDE_CODE_OAUTH_TOKEN=<value>` and `-eMCP_GATEWAY_TOKEN=<value>`.
- With `--default-user-env-probe none` the same line carried only `-eVSCODE_REMOTE_CONTAINERS_SESSION=`. Inside the container both tokens were still present (a docker exec process inherits the container's env), `claude` and `uv` resolved, and PATH was identical.
- What the probe supplies besides secrets: LANG, LC_ALL and LANGUAGE (`en_US.UTF-8`), TERM (`xterm`), and shell cosmetics (ZSH, PAGER, LESS, LSCOLORS, LS_COLORS, PROMPT_COMMAND, HISTFILE, SHLVL, LOGNAME, OLDPWD, `_`, P9K_*). The locale has to be kept.

## Recommended fix

- Both devcontainer.json copies: set `"userEnvProbe": "none"`. devcontainer.json takes precedence over the CLI's `--default-user-env-probe`, and the setting also covers manual `devcontainer exec`. Then supply the locale the probe used to supply through `remoteEnv` (not a secret, so its `-e` flags are harmless). First confirm with `locale -a` in the container that `en_US.utf8` exists:

```jsonc
"userEnvProbe": "none",
"remoteEnv": { "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8" },
```

- Forward MCP_GATEWAY_TOKEN by name, as TASK-282 did for the OAuth token: drop the containerEnv entry and add the single runArgs element `"--env=MCP_GATEWAY_TOKEN"`. Keep it one element, not the pair `"-e", "NAME"`, because Upgrade U4's `merge-runargs.sh` drops project elements the template already has. runArgs stays on its single line.
- ralph-init SKILL.md: rewrite the host MCP gateway passage for the name-only forward (graceful degradation when unset still holds). Add a note on `userEnvProbe: none` and why. Make sure the Upgrade Mode U5 recreate note covers the change; U4's devcontainer.json overwrite already carries the file.

## Scope

Out of scope:
- other containerEnv entries;
- `docker inspect` showing Config.Env to anyone with docker access;
- other projects, which pick the change up through the ralph-init upgrade;
- changing the orchestrator's exec argv, unless devcontainer.json alone cannot do it (then record why).

## Files

- `.devcontainer/devcontainer.json` (exists)
- `plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json` (exists)
- `plugins/ralph/skills/ralph-init/SKILL.md` (exists)
- `tests/python/test_devcontainer_oauth_token_forward.py` (exists): extend it, or add a sibling test
- `tests/unit/template-parity.bats` (exists): must keep passing
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Neither .devcontainer/devcontainer.json nor the ralph-init template devcontainer.json has an MCP_GATEWAY_TOKEN key in containerEnv, and both list "--env=MCP_GATEWAY_TOKEN" as one element in their single-line runArgs next to "--env=CLAUDE_CODE_OAUTH_TOKEN"
- [x] #2 Both devcontainer.json copies set "userEnvProbe": "none" and set LANG and LC_ALL to en_US.UTF-8 through remoteEnv (or the notes record why another place was used)
- [x] #3 A test pins the template's MCP_GATEWAY_TOKEN name-only forward, the absent containerEnv entry, userEnvProbe none and the locale entries; uv run pytest, uv run ruff check . and tests/unit/template-parity.bats pass
- [x] #4 plugins/ralph/skills/ralph-init/SKILL.md describes the name-only MCP_GATEWAY_TOKEN forward and the userEnvProbe none setting with its reason (the probe re-sends the container env as docker exec -e NAME=value, visible in the host's ps for each exec's lifetime), and the Upgrade Mode U5 recreate note covers the change
- [ ] #5 On the macOS host after the merge and a container recreate: ps -ww -eo args, grepped with each token read via -f from a umask 077 mktemp file, counts 0 lines for this repo's docker run and 0 lines while devcontainer exec --workspace-folder . sleep 8 is running; the counts are recorded in the task notes
- [ ] #6 On the macOS host, in that container: both token lengths printed by devcontainer exec equal the host's, LANG and LC_ALL print en_US.UTF-8, and devcontainer exec --workspace-folder . claude -p 'Reply with the single word OK' prints OK
- [ ] #7 On the macOS host: devcontainer exec --workspace-folder . uv run pytest -q passes in the recreated container
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: in both devcontainer.json copies move MCP_GATEWAY_TOKEN from containerEnv to the single runArgs element --env=MCP_GATEWAY_TOKEN, add userEnvProbe none + remoteEnv LANG/LC_ALL; extend tests/python/test_devcontainer_oauth_token_forward.py to pin both; rewrite SKILL.md host MCP gateway passage, add a userEnvProbe note, extend the U5 recreate note. Precondition check: locale -a in this container lists only C, C.utf8, POSIX — en_US.utf8 is NOT installed; the probe's en_US.UTF-8 comes from ~/.zshrc (zsh-in-docker), so the value is already a non-installed locale today. Keeping en_US.UTF-8 per AC #2 preserves the status quo exactly; a follow-up task covers installing the locale or switching to C.UTF-8.

Commit: `72f7a0d` - task-290: forward MCP_GATEWAY_TOKEN by name and skip the devcontainer exec env probe

Deferred: AC #5, #6 and #7 need the macOS host after the merge and a container recreate (host ps -ww -eo args grepped with each token via -f from a umask 077 mktemp file, for docker run and during devcontainer exec --workspace-folder . sleep 8; token lengths, LANG/LC_ALL and claude -p 'Reply with the single word OK' via devcontainer exec; devcontainer exec --workspace-folder . uv run pytest -q). The owner runs them and records the counts and results here. They cannot run from inside the container.

Commit: `28a455b` - task-290: say the gateway token is unset, not empty, when the host lacks it

Commit: `4dd092b` - task-290: drop a stray blank line in the token-forward test

Done: MCP_GATEWAY_TOKEN moved from containerEnv to the single runArgs element --env=MCP_GATEWAY_TOKEN, next to --env=CLAUDE_CODE_OAUTH_TOKEN. Both devcontainer.json copies (byte-identical) set userEnvProbe none and remoteEnv LANG/LC_ALL en_US.UTF-8. The orchestrator's exec argv is unchanged, since devcontainer.json is enough. The token-forward test is parametrised over both secrets and pins the probe and locale. SKILL.md has a new userEnvProbe note, the host MCP gateway passage now describes the name-only forward, and runArgs plus the secrets are in the U5 recreate note. pytest 1011 passed, ruff clean. template-parity.bats: 11/12, and test 5 fails the same way on master in the container (.claude/settings.local.json is the container overlay). task-reviewer APPROVED on the second pass. Follow-up: TASK-293 (en_US.UTF-8 is not a generated locale in the image).
<!-- SECTION:NOTES:END -->
