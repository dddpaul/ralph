---
id: TASK-215
title: >-
  Add a generic host MCP gateway slot to the devcontainer template (init +
  upgrade)
status: To Do
assignee: []
created_date: '2026-07-28 17:11'
updated_date: '2026-08-01 13:20'
labels:
  - template
  - 'feature:host-mcp-gateway'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Ralph devcontainers cannot reach host-run HTTP MCP servers: inside the container "localhost:<port>" points at the container itself, so a gateway published on the host (for example a shared-knowledge MCP gateway on :9000) is unreachable, and MCP-dependent phases must run with devcontainer=false, sacrificing sandbox isolation. The host is reachable from the container at host.docker.internal, and init-firewall.sh already permits egress to the host network (HOST_NETWORK /24 + private ranges) — the same path the existing host.docker.internal:3128 Squid proxy uses. So the wiring is small and declarative; no Dockerfile or firewall change is needed.

Rather than bake a specific gateway service into the generic Ralph template (which would couple every ralph-init project to a service most do not use), ship a NEUTRAL, reusable "host MCP gateway" slot: generic env names MCP_GATEWAY_HOST and MCP_GATEWAY_TOKEN that any project can point its own .mcp.json at. The specific service (owner path, port) stays pure per-project .mcp.json config; Ralph never names it. This mirrors the existing CLAUDE_CODE_OAUTH_TOKEN forward (ralph-init SKILL.md around Step 3.6): a ${localEnv:...} containerEnv passthrough plus a host-setup doc note with graceful degradation when the token is unset.

Existing projects must receive this through "ralph-init upgrade", not only new-project init — so BOTH flows are updated. devcontainer.json is Ralph-owned and flows through the normal upgrade file-sync (U2/U4). .mcp.json is per-consumer and NOT Ralph-owned, so upgrade must never silently rewrite it: it uses a detect-and-offer step (show a before/after diff, apply only on user confirm).

## Scope

In scope:
- plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json (and the repo own .devcontainer/devcontainer.json, R11 byte-for-byte parity):
  - containerEnv: "MCP_GATEWAY_HOST": "host.docker.internal" and "MCP_GATEWAY_TOKEN": "${localEnv:MCP_GATEWAY_TOKEN}".
  - Append host.docker.internal to NO_PROXY (currently localhost,127.0.0.1,.local) so the MCP client connects DIRECTLY to the host gateway instead of routing through Squid at :3128 (which is not configured to reach it). The firewall already allows this direct egress.
- plugins/ralph/skills/ralph-init/SKILL.md Init (near the CLAUDE_CODE_OAUTH_TOKEN note, around lines 180-196):
  - document exporting MCP_GATEWAY_TOKEN from ~/.zshenv (NOT ~/.zshrc — interactive-only, so non-interactive Ralph launches would see an empty value; same gotcha as the OAuth token), with graceful degradation when unset.
  - document the consumer .mcp.json convention: "url": "http://${MCP_GATEWAY_HOST:-localhost}:<port>/<path>" with Authorization: Bearer ${MCP_GATEWAY_TOKEN}, so the same file resolves to localhost on the host and host.docker.internal inside the container.
- plugins/ralph/skills/ralph-init/SKILL.md Upgrade Mode (U-flow):
  - devcontainer.json changes flow through the existing U2 status-table and U4 apply (Ralph-owned file).
  - NEW detect-and-offer for .mcp.json: if the project has a .mcp.json containing an http-type MCP server whose url host is localhost or 127.0.0.1, present a before/after diff rewriting the host to ${MCP_GATEWAY_HOST:-localhost} (dual-mode), and apply ONLY on user confirm. Never rewrite silently; do nothing when .mcp.json is absent or already uses the convention.

Out of scope:
- Editing Dockerfile or init-firewall.sh — host-network egress is already permitted; no new firewall rule is required.
- A forwardPorts entry for the gateway port — that publishes a container port to the host (wrong direction); the need is container-to-host egress, which already works.
- Owning or templating .mcp.json as a synced file — it stays per-consumer; upgrade only OFFERS a targeted host-rewrite.
- Naming any specific gateway service (no OKF_ prefix, no hardcoded owner) in the template or the skill — the slot is generic; a concrete service is an example at most.
- Changing any host ~/.zshenv, or runtime setup for host.docker.internal (Docker Desktop maps it automatically; colima needs an explicit host mapping — note this as a doc caveat, not a repo change).

## Files

- plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json (exists) — add the two containerEnv keys + extend NO_PROXY.
- .devcontainer/devcontainer.json (exists) — mirror the same three changes byte-for-byte (R11 parity).
- plugins/ralph/skills/ralph-init/SKILL.md (exists) — Init token/.mcp.json convention note + Upgrade Mode detect-and-offer step.

## Source

Source: /Users/paul/Private/Alfa/Projects/channels@b4c776ce9f8f (derived from a live channels devcontainer/MCP diagnostics session). Reworked 2026-08-01 from an okf-specific wiring to a generic, service-agnostic host MCP gateway slot (MCP_GATEWAY_HOST/MCP_GATEWAY_TOKEN) with ralph-init init + upgrade support and a detect-and-offer .mcp.json migration.

## Before starting (destination validation checklist)

1. Both devcontainer.json files exist and their containerEnv / NO_PROXY blocks still mirror each other (R11 parity target).
2. Each AC is objectively pass/fail (grep over the two JSON files + SKILL.md, JSONC validity, ruff, pytest) — not "works correctly".
3. Dockerfile and init-firewall.sh are genuinely untouched by the final diff, and no forwardPorts entry is added.
4. No service-specific identifier (OKF_, a hardcoded owner, a hardcoded gateway port) is introduced into the template or the skill.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Template devcontainer/devcontainer.json containerEnv contains "MCP_GATEWAY_HOST": "host.docker.internal"
- [ ] #2 Template devcontainer/devcontainer.json containerEnv forwards the token as "MCP_GATEWAY_TOKEN": "${localEnv:MCP_GATEWAY_TOKEN}"
- [ ] #3 Template devcontainer/devcontainer.json NO_PROXY value includes host.docker.internal
- [ ] #4 Repo own .devcontainer/devcontainer.json mirrors all three additions byte-for-byte (R11 parity with the template)
- [ ] #5 Neither devcontainer.json contains a service-specific identifier (grep for OKF, okf, or a hardcoded gateway port such as 9000 is clean) — the slot is generic
- [ ] #6 ralph-init SKILL.md Init documents exporting MCP_GATEWAY_TOKEN from ~/.zshenv (not ~/.zshrc), parallel to the CLAUDE_CODE_OAUTH_TOKEN note, with graceful degradation when unset
- [ ] #7 ralph-init SKILL.md Init documents the .mcp.json url convention http://${MCP_GATEWAY_HOST:-localhost}:<port>/<path> with Authorization: Bearer ${MCP_GATEWAY_TOKEN}
- [ ] #8 ralph-init SKILL.md Upgrade Mode documents a detect-and-offer step: when a project .mcp.json has an http MCP server whose url host is localhost or 127.0.0.1, present a before/after diff rewriting the host to ${MCP_GATEWAY_HOST:-localhost} and apply only on user confirm (never silent; no-op when .mcp.json absent)
- [ ] #9 Both devcontainer.json files are valid JSONC; uv run ruff check . and uv run pytest pass
- [ ] #10 Dockerfile and init-firewall.sh are unchanged in the final diff, and no forwardPorts entry for the gateway port is added
<!-- AC:END -->
