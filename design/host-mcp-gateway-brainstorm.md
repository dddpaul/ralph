# Host MCP Gateway Slot for the Ralph Devcontainer

## Architecture decision

Give the Ralph devcontainer a **generic, service-agnostic "host MCP gateway" slot** so MCP-dependent phases can run with `devcontainer=true` instead of falling back to `devcontainer=false` (which sacrifices sandbox isolation). The template forwards **neutral** env vars — `MCP_GATEWAY_HOST=host.docker.internal` and `MCP_GATEWAY_TOKEN=${localEnv:MCP_GATEWAY_TOKEN}` — and widens `NO_PROXY`. The specific gateway (okf-mcp-gateway, its owner path, its port) stays **pure per-project `.mcp.json` config**. Chosen (Option C) over baking `OKF_`-specific vars into the template (Option B), which would couple every `ralph-init` project to a service most do not use.

The guiding split: **reachability is generic, service identity is specific.** Ralph ships only the reachability plumbing; each consumer names its own gateway.

## Components / flows

- **Reachability (generic):** the container reaches the host at `host.docker.internal`; `init-firewall.sh` already permits host-network egress (HOST_NETWORK /24 + private ranges) — the same path the existing `host.docker.internal:3128` Squid proxy uses. `NO_PROXY += host.docker.internal` so the MCP client connects **directly** to the gateway instead of routing through Squid (which is not configured to reach it).
- **Template slot (Ralph-owned):** `devcontainer.json` `containerEnv` carries `MCP_GATEWAY_HOST` + `MCP_GATEWAY_TOKEN` (a `${localEnv:...}` passthrough, graceful/empty when unset) — mirrors the existing `CLAUDE_CODE_OAUTH_TOKEN` precedent. Mirrored byte-for-byte into this repo's own `.devcontainer/devcontainer.json` (R11 parity).
- **Consumer `.mcp.json` convention (per-project):** `url: http://${MCP_GATEWAY_HOST:-localhost}:<port>/<path>` + `Authorization: Bearer ${MCP_GATEWAY_TOKEN}`. One file resolves to `localhost` on the host and `host.docker.internal` inside the container — dual-mode by a shell default.
- **ralph-init dual flow:** **Init** (Step 3.x) seeds the template and documents the convention; **Upgrade Mode** (U1–U5) syncs the Ralph-owned `devcontainer.json` through the normal file-sync AND runs a **detect-and-offer** migration for the per-consumer `.mcp.json` (show a before/after diff, apply only on confirm — never silent, no-op when absent).

## Scope cuts

- No `Dockerfile` / `init-firewall.sh` change — host-network egress is already permitted.
- No `forwardPorts` for the gateway port — that publishes container→host (wrong direction); the need is container→host egress, which already works.
- `.mcp.json` is **not** owned or templated by Ralph — upgrade only *offers* a targeted host-rewrite on confirm.
- No service identity in the template or skill (no `OKF_` prefix, no hardcoded owner, no hardcoded port) — the slot is generic; a concrete service is an example at most.
- No host `~/.zshenv` edits — documented per-user manual step.

## Open questions

- **colima `host.docker.internal`:** Docker Desktop maps it automatically; **colima** (the user's runtime) may need an explicit host mapping (`extra_hosts` / `--network-address`). Verify it resolves in-container on colima, or document the mapping as a prerequisite. Non-blocking for the repo change — a doc caveat.
- **Token var naming:** standardized on `MCP_GATEWAY_TOKEN`; existing consumers exporting `OKF_GATEWAY_TOKEN` must re-export (or alias) `MCP_GATEWAY_TOKEN`. The detect-and-offer migration rewrites the URL host; the token-var rename is a doc note, not a forced rewrite.

## Hand-off

Single-task feature (one `devcontainer` + `ralph-init` deliverable, no cross-task invariants), so straight to `ralph-task` — already captured as **TASK-215** (`feature:host-mcp-gateway`). No PRD needed.

## Distilled for ralph-task

**Direction:** Option C — a generic, service-agnostic "host MCP gateway" slot in the Ralph devcontainer template (neutral `MCP_GATEWAY_HOST` / `MCP_GATEWAY_TOKEN`), with `ralph-init` init + upgrade support and a detect-and-offer `.mcp.json` migration. Not okf-specific.

**Locked decisions (with rationale):**
- **Neutral env names in the template** (`MCP_GATEWAY_HOST` / `MCP_GATEWAY_TOKEN`, not `OKF_GATEWAY_*`). *Rationale:* Ralph is a generic framework; naming a specific service couples every `ralph-init` project to a service most do not use.
- **Slot lives in the Ralph-owned template `devcontainer.json`, not per-project additions.** *Rationale:* `devcontainer.json` is synced by the upgrade U-flow, so per-project `containerEnv` additions would be clobbered on upgrade; owning the neutral slot avoids needing section-aware merge machinery.
- **Service identity confined to per-consumer `.mcp.json`** (`${MCP_GATEWAY_HOST:-localhost}` + `Bearer ${MCP_GATEWAY_TOKEN}`). *Rationale:* one file resolves correctly on host and in-container; Ralph never names the service.
- **`NO_PROXY += host.docker.internal`.** *Rationale:* direct container→host egress bypasses the Squid proxy, which cannot reach the gateway; the firewall already permits it.
- **Update BOTH init and upgrade sections.** *Rationale:* existing projects receive changes only via `ralph-init upgrade`; an init-only change reaches zero existing repos.
- **`.mcp.json` migration is detect-and-offer, never silent.** *Rationale:* `.mcp.json` is per-consumer and not Ralph-owned; silently rewriting an unowned file is unsafe and heuristic — show a diff, apply on confirm.

**Scope cuts:**
- No `Dockerfile` / `init-firewall.sh` change; no `forwardPorts`; no `.mcp.json` templating/ownership; no service identity in template/skill; no host `~/.zshenv` edits.

**Acceptance criteria (sketch):** (TASK-215 carries the 10 verifiable ACs)
- Template + repo `devcontainer.json` carry `MCP_GATEWAY_HOST` / `MCP_GATEWAY_TOKEN` + `NO_PROXY host.docker.internal` (R11 byte-for-byte).
- No `OKF`/`okf`/hardcoded-port in either `devcontainer.json`.
- `ralph-init` Init documents the `~/.zshenv` token export + the `.mcp.json` `${MCP_GATEWAY_HOST:-localhost}` convention.
- `ralph-init` Upgrade documents the detect-and-offer `.mcp.json` migration (confirm-only).
- JSONC valid; `ruff` + `pytest` green; `Dockerfile`/firewall unchanged; no `forwardPorts`.

**Implementation checklist:**
- Add the two `containerEnv` keys + extend `NO_PROXY` in `templates/devcontainer/devcontainer.json`; mirror byte-for-byte into `.devcontainer/devcontainer.json` (R11).
- Add the Init doc note (token export + `.mcp.json` convention) near the `CLAUDE_CODE_OAUTH_TOKEN` section.
- Add the Upgrade Mode detect-and-offer `.mcp.json` step to the U-flow.
- Verify: grep decoupling (no `OKF`/`9000`), JSONC validity, `ruff`, `pytest`, `Dockerfile`/firewall unchanged, no `forwardPorts`.
