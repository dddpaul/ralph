---
id: TASK-215
title: >-
  Wire devcontainer template to reach host okf-mcp-gateway (:9000) so
  MCP-dependent phases can run with devcontainer=true
status: To Do
assignee: []
created_date: '2026-07-28 17:11'
labels:
  - template
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Ralph projects that consume shared knowledge register the okf-mcp-gateway as an
**HTTP** MCP server at `http://localhost:9000/<owner>/mcp` (Bearer token). That works
on the host, but inside the Ralph devcontainer `localhost:9000` points at the
container itself, so every MCP resource is unreachable — MCP-dependent phases must be
run with `devcontainer=false`, sacrificing sandbox isolation. The gateway is
reachable from the container at `host.docker.internal:9000` (Docker Desktop maps it),
and `init-firewall.sh` already permits egress to the host network (HOST_NETWORK /24 +
private ranges) — the same path the existing `host.docker.internal:3128` proxy uses.
So only three declarative wires are missing in the devcontainer template; no Dockerfile
or firewall change is needed. This mirrors TASK-114 (CLAUDE_CODE_OAUTH_TOKEN forward)
in shape and applies to both the template and this repo's own `.devcontainer` (R11
byte-for-byte parity).

## Scope

In scope:
- Add to `containerEnv` in the devcontainer template (and mirror in this repo's own
  `.devcontainer/devcontainer.json`, R11 parity):
  - `"OKF_GATEWAY_HOST": "host.docker.internal"` — so a consumer `.mcp.json` can point
    the gateway URL at the host from inside the container.
  - `"OKF_GATEWAY_TOKEN": "${localEnv:OKF_GATEWAY_TOKEN}"` — forward the gateway Bearer
    token (same forwarding shape as CLAUDE_CODE_OAUTH_TOKEN).
  - Append `host.docker.internal` to `NO_PROXY` (currently
    `localhost,127.0.0.1,.local`) so the MCP client connects DIRECTLY to
    host.docker.internal:9000 instead of routing through the Squid proxy at :3128
    (which is not configured to reach :9000). The firewall already allows this direct
    egress.
- Document in `ralph-init` SKILL.md, parallel to the existing CLAUDE_CODE_OAUTH_TOKEN
  host-setup note (~lines 180-196):
  - export `OKF_GATEWAY_TOKEN` from `~/.zshenv` (NOT `~/.zshrc` — interactive-only, so
    non-interactive Ralph launches would see an empty value; same gotcha as the OAuth
    token), with graceful degradation when unset.
  - the consumer-side `.mcp.json` convention: use
    `"url": "http://${OKF_GATEWAY_HOST:-localhost}:9000/<owner>/mcp"` so the same file
    resolves to `localhost` on the host and `host.docker.internal` inside the container.

The additions are safe as unconditional template defaults: a project that does not set
`OKF_GATEWAY_TOKEN` on the host gets an empty `${localEnv:...}` (graceful, like OAuth),
an unused `OKF_GATEWAY_HOST` is inert, and a wider `NO_PROXY` is harmless.

Out of scope:
- Editing `Dockerfile` or `init-firewall.sh` — egress to the host network is already
  permitted; no new firewall rule is required.
- Adding a `forwardPorts` entry for 9000 — that publishes a CONTAINER port to the host
  (wrong direction); the need here is container→host egress, which already works.
- Creating or templating a `.mcp.json` — ralph-init does not own it; it is per-consumer.
  Only DOCUMENT the URL convention.
- Changing the host `~/.zshenv` on any machine — that is a per-user manual step the doc
  describes, not a repo edit.

## Files

- `plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json` (exists) —
  add the two containerEnv keys + extend NO_PROXY.
- `.devcontainer/devcontainer.json` (exists) — mirror the same three changes byte-for-
  byte (R11 parity with the template, per TASK-114 precedent).
- `plugins/ralph/skills/ralph-init/SKILL.md` (exists) — add the OKF_GATEWAY_TOKEN host
  note (~near the CLAUDE_CODE_OAUTH_TOKEN section, lines ~180-196) + the `.mcp.json`
  `${OKF_GATEWAY_HOST:-localhost}` convention.

## Source

Source: /Users/paul/Private/Alfa/Projects/channels@b4c776ce9f8f
No source design doc — derived from a live channels devcontainer/MCP diagnostics
session: channels `.mcp.json` registers the gateway over HTTP at `localhost:9000`
(type=http, Bearer `${OKF_GATEWAY_TOKEN}`); the gateway container publishes
`0.0.0.0:9000->8080/tcp`; channels `.devcontainer/init-firewall.sh` already ACCEPTs
egress to HOST_NETWORK (lines ~116-117) and private ranges (~46-48); channels
devcontainer.json already reaches the host via `host.docker.internal` for HTTP_PROXY
(:3128). These are seeded from this repo's devcontainer template, hence the fix belongs
upstream here.

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. Both devcontainer.json files exist and their `containerEnv` blocks still mirror each
   other (R11 parity target).
2. Each AC is objectively pass/fail (grep over the two JSON files + the SKILL.md, plus
   `uv run pytest`) — not "works correctly".
3. Dockerfile and init-firewall.sh are genuinely untouched by the final diff.
4. No `forwardPorts` 9000 entry is introduced.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Template devcontainer.json containerEnv contains "OKF_GATEWAY_HOST": "host.docker.internal"
- [ ] #2 Template devcontainer.json containerEnv forwards the token as "OKF_GATEWAY_TOKEN": "${localEnv:OKF_GATEWAY_TOKEN}"
- [ ] #3 Template devcontainer.json NO_PROXY value includes host.docker.internal
- [ ] #4 Repo own .devcontainer/devcontainer.json mirrors all three additions byte-for-byte (R11 parity with the template)
- [ ] #5 Both devcontainer.json files remain valid JSONC and uv run pytest passes
- [ ] #6 ralph-init SKILL.md documents (a) exporting OKF_GATEWAY_TOKEN from ~/.zshenv not ~/.zshrc, parallel to the CLAUDE_CODE_OAUTH_TOKEN note, and (b) the .mcp.json url convention http://${OKF_GATEWAY_HOST:-localhost}:9000/<owner>/mcp
- [ ] #7 Dockerfile and init-firewall.sh are unchanged in the final diff, and no forwardPorts entry for 9000 is added
<!-- AC:END -->
