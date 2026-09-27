---
name: ralph-init
description: "Bootstrap Ralph autonomous agent infrastructure in a new project. Sets up ralph.sh, CLAUDE.md, git hooks, backlog, .devcontainer, .gitignore, and skills. Triggers on: ralph init, bootstrap ralph, setup ralph, init ralph, initialize ralph, upgrade ralph, ralph upgrade, update ralph files."
---

# Ralph Project Bootstrapper

Set up Ralph autonomous agent infrastructure in an existing git repository.

All template files are in the `templates/` directory next to this SKILL.md. Read each template, customize as needed, and write to the target project.

**Important:** Do NOT start implementing features or creating tasks. Just set up the infrastructure.

---

## Prerequisites

Ralph's orchestrator is Python. It runs via `uv` with PEP 723 inline metadata that pins Python 3.14 + `pydantic>=2.5`.

- **DevContainer projects** (Step 2 Q3 answer A): `uv` and Python 3.14 are baked into the container by Step 3.6 — no host install needed.
- **Host-mode projects** (Step 2 Q3 answer B): install `uv` on the host using your OS package manager. Common forms:

  - macOS: `brew install uv`
  - Arch Linux: `pacman -S uv`
  - Fedora: `dnf install uv`
  - Cross-platform (already have Python + pipx): `pipx install uv`

  Last-resort fallback, only if no package manager ships `uv` for your distro: `curl -LsSf https://astral.sh/uv/install.sh | sh` (review the script first).

  Python 3.14 is fetched lazily on first `uv run`, or you can pre-install with `uv python install 3.14`.

---

## Step 1: Preflight Checks

```bash
git rev-parse --git-dir    # Must be a git repo
command -v backlog          # Must have backlog CLI
```

If `backlog` is missing: `npm install -g backlog.md`
If not a git repo: `git init -b master`

```bash
[ -s "$HOME/.claude/agents/task-reviewer.md" ] || {
  echo "ERROR: ~/.claude/agents/task-reviewer.md missing. Copy it from the Ralph repo:"
  echo "  cp <ralph-repo>/agents/task-reviewer.md ~/.claude/agents/"
  exit 1
}
```

If the user-global agent file is missing, print the error and **abort** — do NOT proceed to Step 2 or write any project files.

```bash
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
find "$CLAUDE_DIR/plugins/cache" -type f \
  -path '*/ralph/*/skills/ralph-run/scripts/ralph_orchestrator.py' 2>/dev/null \
  | grep -q . || {
  echo "ERROR: the ralph plugin is not installed. Install it first, then re-run ralph-init:"
  echo "  /plugin marketplace add dddpaul/ralph"
  echo "  /plugin install ralph@dddpaul-ralph"
  exit 1
}
```

The project-root `ralph.sh` written in Step 3.1 is a thin shim that resolves the Ralph orchestrator wherever the plugin is installed — by precedence (`$RALPH_ORCHESTRATOR` explicit override, then the newest plugin-cache install, else error) — and `exec`s it via `uv run`. Absent an override, the orchestrator comes from the installed plugin cache; if the ralph plugin is not installed the shim has nothing to exec and the bootstrap is broken. Hard-stop here and instruct the user to install the plugin first.

---

## Step 2: Clarifying Questions

Ask with lettered options for quick answers (e.g. "0A, 1A, 2C, 3B, 4A"):

```
0. What type of project?
   A. Code — software project with build/lint/test pipeline
   B. Documentation — Obsidian vault, architecture docs, presentations
   C. Mixed — code + documentation

1. What is your primary language/runtime?
   A. TypeScript / Node.js
   B. Python
   C. Go
   D. Other: [please specify]

2. What are your quality check commands?
   A. npm run build && npm run lint && npm test
   B. pytest && mypy . && ruff check .
   C. go build ./... && go vet ./... && go test ./...
   D. Other: [please specify]

3. Do you need the DevContainer (sandboxed execution with firewall)?
   A. Yes — I want isolated autonomous runs
   B. No — I'll run Ralph directly on my machine

4. Which AI tool will you use with Ralph?
   A. Claude Code
   B. opencode
```

**Project type behavior:**
- **Code (0A):** All questions apply as normal.
- **Documentation (0B):** Skip Q1 and Q2. Language defaults to `docs` (Python + Node.js runtime). Quality checks are N/A — leave Build/Lint/Test empty or mark as N/A in CLAUDE.md.
- **Mixed (0C):** All questions apply. In step 3.6, use the language from Q1 for Dockerfile assembly. Obsidian config (step 3.8) is also generated.

---

## Step 3: Generate Files

**Skip any file that already exists** unless the user says `--force`. For skipped files, print `[skip] <file> already exists`.

### 3.1 `ralph.sh` and `refine.sh`
Read `templates/root/ralph.sh` → write to project root. Make executable (`chmod +x`).

Read `templates/root/refine.sh` → write to project root. Make executable (`chmod +x`). Seed it unconditionally, alongside `ralph.sh`: both are thin shims that resolve their orchestrator (`ralph_orchestrator.py` / `refine_orchestrator.py`) from the installed plugin cache when no explicit override is set, so the same plugin-not-installed hard-stop below applies to `refine.sh`.

### 3.2 `CLAUDE.md`
Read `templates/root/CLAUDE.md` → replace ALL `<FILL IN ...>` placeholders in `## Project-Specific` with actual values from the user's answers. Parse quality commands (Q2) into separate build, lint, and test entries.

**Documentation projects (0B):** Set Language to `Markdown / Python`, and set Build, Lint, and Test to `N/A`. Use `docs` as the `<lang>` for conventions lookup.

**Language conventions:** If `templates/root/CLAUDE.conventions.<lang>.md` exists for the chosen language (e.g. `python`, `docs`), read it and append its contents after the `### Conventions` section. This adds language-specific rules (package management, code style, etc.).

Write to project root.

### 3.3 `.git/hooks/post-commit`, `.git/hooks/commit-msg`, `.git/hooks/pre-commit`, and Unicode normalization
Read `templates/git-hooks/post-commit` → write to `.git/hooks/post-commit`. Make executable (`chmod +x`). If hook already exists, warn user and ask before overwriting.

Read `templates/git-hooks/commit-msg` → write to `.git/hooks/commit-msg`. Make executable (`chmod +x`). If hook already exists, warn user and ask before overwriting.

Read `templates/git-hooks/pre-commit` → write to `.git/hooks/pre-commit`. Make executable (`chmod +x`). If hook already exists, warn user and ask before overwriting. The hook rejects a commit when a staged path duplicates an existing tree path under a different Unicode normalization (NFD vs NFC) — see TASK-136 for the downstream incident that prompted it. It also delegates to `.claude/hooks/filename-length-guard.sh` (written in Step 3.7a), which rejects any staged path whose name components exceed 125 bytes — the cap that keeps names inside the ~140-byte ecryptfs/Syncthing budget, Windows MAX_PATH, and archive round-trips. The delegation is guarded by `[ -x ]`, so the hook degrades to the NFC check alone in a project that predates the guard script.

Then bootstrap git's Unicode normalization so working-tree paths are recorded in NFC even on macOS APFS, which hands filenames back in NFD:

```bash
git config --local core.precomposeunicode true
```

This setting plus the pre-commit guard form a belt-and-suspenders defense: the config catches new files written via macOS, the hook catches NFD bytes that slip in via patch import, `git mv`, or a foreign filesystem.

### 3.4 `.gitignore`
Append missing entries (don't duplicate existing lines):
```
# Ralph working files (generated during runs)
backlog/.ralph-status.json
backlog/.ralph-run.log
backlog/.ralph-launch.log
backlog/.ralph-heartbeat

# OS files
.DS_Store

# Claude Code (ignore local overrides, track project config)
.claude/*
!.claude/settings.json
!.claude/task-reviewer-rules.md
!.claude/brainstorm-rules.md
!.claude/hooks/

# Python virtualenv (also the devcontainer .venv volume mountpoint)
.venv/
```
Do NOT add `backlog/` — task files should be committed.

### 3.5 Backlog
Skip if `backlog/` directory already exists. Otherwise run non-interactively using the repo directory name as the project name:
```bash
backlog init <project-name> --defaults --agent-instructions none
backlog config set remoteOperations false       # avoids SSH passphrase prompts on every CLI call
backlog config set checkActiveBranches false    # avoids backlog CLI stalls in offline / restricted-git envs
```
Use `--agent-instructions none` because CLAUDE.md is already generated by this skill.

### 3.6 `.devcontainer/` (only if user said Yes to Q3)
Assemble the Dockerfile from base + language snippets, then write four files:

**Dockerfile assembly:** Read `templates/devcontainer/Dockerfile.base`. Replace `{{LANGUAGE_STAGE}}` with contents of `templates/devcontainer/lang/Dockerfile.lang.<lang>` and `{{LANGUAGE_INSTALL}}` with contents of `templates/devcontainer/lang/Dockerfile.install.<lang>`, where `<lang>` is one of: `node`, `python`, `go`, `docs`. For "Other" languages, use `node` as the base and add a comment for the user to customize. For Documentation projects (0B), use `docs` as the language.

- Assembled Dockerfile → `.devcontainer/Dockerfile`. Then run `bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-init/scripts/stale-runtime-copy.sh check .devcontainer/Dockerfile`; it must exit 0 with no output. It flags any `COPY --from=<stage or image>` of `/usr/local`, `/usr/local/bin` or `/usr/local/lib` whose image does not pin the same Debian suite as the devcontainer base (the last `FROM`) — the rule `tests/python/test_devcontainer_python_runtime.py` pins on the fragments. The shipped fragments pass; a hand-written stage for an "Other" language may not, and Upgrade Mode runs the same check (see "Stale language-runtime copy on upgrade" in U4).
- `templates/devcontainer/devcontainer.json` → `.devcontainer/devcontainer.json` — update app label and port if specified
- `templates/devcontainer/init-firewall.sh` → `.devcontainer/init-firewall.sh`
- `templates/devcontainer/container-settings.local.json` → `.devcontainer/container-settings.local.json` — copy verbatim; it is the container's `.claude/settings.local.json` (see the "shared `.claude`" note below)

**Host-side prerequisites for devcontainer auth (macOS):** the template forwards `CLAUDE_CODE_OAUTH_TOKEN` from the host into the container via `containerEnv` + `${localEnv:...}`. macOS hosts store Claude OAuth credentials in the system Keychain (not on disk), so the bind-mounted host credentials file is empty inside the container. Without the env-var forward, `claude` inside the container fails auth. After running `ralph-init`, tell the user to do the following on the host (one-time setup, token is valid for ~1 year):

1. **Mint a long-lived token** by running `claude setup-token` once on the host. Reference: https://code.claude.com/docs/en/authentication.md#generate-a-long-lived-token

2. **Export the token from the shell's always-sourced env file** so it propagates to non-interactive subshells. zsh users: add the export to `~/.zshenv` (NOT `~/.zshrc` — the latter is interactive-only). bash users: the equivalent always-sourced env file. macOS Keychain users can pull the token from Keychain inside that env file:

   ```sh
   export CLAUDE_CODE_OAUTH_TOKEN="$(security find-generic-password -a "$USER" -s "claude-code-oauth-token" -w 2>/dev/null)"
   ```

3. **GUI-app caveat:** VS Code launched from Dock/Spotlight does **not** source the shell's env file, so `${localEnv:CLAUDE_CODE_OAUTH_TOKEN}` resolves to empty when VS Code starts the devcontainer. Either (a) restart VS Code from a terminal that has the token in its environment, or (b) run `launchctl setenv CLAUDE_CODE_OAUTH_TOKEN <value>` once for a launchd-domain export visible to all GUI apps.

4. **`launchctl setenv` does not persist across reboots.** Either re-run it after each reboot, or persist via a launchd plist (e.g. `~/Library/LaunchAgents/com.user.claude-oauth.plist` with a `RunAtLoad` `launchctl setenv` invocation).

**Graceful degradation:** when the host shell does not export the token, `${localEnv:CLAUDE_CODE_OAUTH_TOKEN}` resolves to empty string and the container starts unaffected. The existing host Keychain auth path stays intact for non-devcontainer use.

**Do not** commit the token value anywhere — only the env var name and the `${localEnv:...}` substitution belong in `devcontainer.json`.

**Shared `.claude`, with one file overridden (keeps host and container in sync):** `workspaceMount` bind-mounts the host project folder at `/workspace`, so the container sees the project's own `.claude/` directly — `.claude/skills/**`, `.claude/hooks/**`, and `CLAUDE.md` are the same bytes on both sides, host edits are visible to the container immediately, and a container-side commit can never carry a stale copy back into git. Exactly one file has to differ: `bwrap` cannot create mount namespaces on Docker Desktop macOS, so Claude Code's sandbox must be **off** inside the container while the host keeps it **on**. The template therefore binds a single container-specific file over that one path:

```
"source=${localWorkspaceFolder}/.devcontainer/container-settings.local.json,target=/workspace/.claude/settings.local.json,type=bind"
```

`.devcontainer/container-settings.local.json` carries only the sandbox switch:

```json
{
  "sandbox": {
    "enabled": false
  }
}
```

No permission allowlist belongs in it — Ralph launches `claude` with `--dangerously-skip-permissions` inside the container, so the allowlist is never consulted there. The override wins over the user-level `${localEnv:HOME}/.claude` bind above it, and the host's own project `.claude/settings.local.json` (sandbox enabled, `autoAllowBashIfSandboxed`) is untouched because nothing is mounted over the directory any more.

Two lifecycle hooks go with it:

```
"initializeCommand": "sh -c 'mkdir -p .claude && { [ -s .claude/settings.local.json ] || echo {} > .claude/settings.local.json; }'",
"postCreateCommand": "sudo chown node:node /workspace/.venv && git config --global --add safe.directory /workspace",
```

- `initializeCommand` runs **on the host** before the container starts, with its working directory pinned to the workspace folder (so the relative path is correct and `${localWorkspaceFolder}` is unnecessary). Without it, a fresh clone with no `.claude/settings.local.json` lets Docker create the bind destination as a 0-byte file that the host's own Claude Code cannot parse. `[ -s ]` makes it idempotent and leaves a real file alone. `mkdir -p .claude` runs first because a fresh clone may have no `.claude` at all (gitignored or never committed): the redirect would then fail, `sh -c` would exit non-zero, and the devcontainer CLI aborts container creation.
- `safe.directory` is not optional. `/workspace` presents as root-owned inside the container (that is how Docker Desktop's file-sharing layer maps the workspace bind) while the container user is `node`, so git refuses the repository with `fatal: detected dubious ownership` and Ralph gets no `status` and no `commit`. The container user can already write to both the worktree and `.git`; only the permission is missing. Do **not** rely on a long-lived container where someone set this by hand — recreating the container loses it.

The single-file bind is deliberately **not** `readonly`: a container-side write to a tracked file is cosmetic and visible in review, whereas a read-only mount would break every run if any startup path wrote that file.

**Second bind of the user `~/.claude` at its own host path (makes plugin agents resolve):** the template binds the host `~/.claude` **twice** — once at `/home/node/.claude`, and once at the literal host path:

```
"source=${localEnv:HOME}/.claude,target=/home/node/.claude,type=bind",
"source=${localEnv:HOME}/.claude,target=${localEnv:HOME}/.claude,type=bind",
```

and points the config root at the second one:

```
"CLAUDE_CONFIG_DIR": "${localEnv:HOME}/.claude",
```

It looks like a duplicate and it is not. A skills directory is merely scanned, but a **plugin** is resolved through an absolute path recorded in a registry: `~/.claude/plugins/known_marketplaces.json` stores `installLocation` and `plugins/installed_plugins.json` stores `installPath`, both as **host** paths (e.g. `/Users/<user>/.claude/plugins/marketplaces/<name>`). With only the `/home/node/.claude` bind the same directory is present under a different name, which is exactly what the registry cannot follow, so every user plugin fails with `Marketplace <name> failed to load: cache-miss`. The consequence is silent and severe: the `task-reviewer` agent shipped by `ralph@dddpaul-ralph` never registers, so the Review step of the Task Lifecycle degrades to a plain agent reading a rules file — and still reports APPROVED. The second bind makes the recorded path resolve to the same bytes.

`CLAUDE_CONFIG_DIR` points at that same host path — `"CLAUDE_CONFIG_DIR": "${localEnv:HOME}/.claude"`, **not** `/home/node/.claude`. The two names are binds of one directory, so the choice changes nothing about *which bytes* are read; it changes the root Claude Code **writes** into the registries. Rooted at `/home/node` a container run records `installLocation` / `installPath` values that do not exist on the host, and the host then refuses each one — `Marketplace <name> has a corrupted installLocation (/home/node/...) — expected a path inside <config>/plugins/marketplaces` — for every marketplace in the file, not just ralph's; `/plugin marketplace update` cannot repair it either, because the directory it wants to pull is absent on that machine. Rooted at the host path both machines record and resolve the same shape. The `/home/node/.claude` bind stays as the `$HOME` alias so anything that ignores `CLAUDE_CONFIG_DIR` still lands on the shared directory. Never "fix" cache-miss by editing those two registry JSON files instead: `/home/node/.claude` is a read-write bind of the host's real `~/.claude`, so rewriting a path there breaks the host. Registering the marketplace through `extraKnownMarketplaces` in project settings does not work either — the stale `known_marketplaces.json` entry wins and cache-miss persists.

Verify it **inside the container** after a recreate:

```bash
claude plugin list                             # ralph@dddpaul-ralph -> enabled, not "cache-miss"
claude plugin details ralph@dddpaul-ralph      # Agents (2)  task-reviewer, ralph-reviewer
```

Both commands work without auth, so they are usable even where `claude -p` in the container is not logged in. On a host whose `$HOME` is literally `/home/node` the two binds collapse to the same target; the second one can be dropped there, since the first already puts the directory at the recorded path — but note that U4 rewrites this file from the template, so such a local edit does not survive an upgrade and has to be reapplied (or better, raised as a template change).

**`.venv` volume overlay (keeps the container virtualenv off the host):** `workspaceMount` bind-mounts the host project folder at `/workspace`, so anything the container writes under it lands on the host. For a Python project that includes `.venv/` — `uv sync` inside the container rewrites `.venv/pyvenv.cfg` to a container-only interpreter home (`/home/node/.local/share/uv/python/cpython-<ver>-linux-<arch>-gnu/bin`) and repoints `.venv/bin/python` at it. Back on the host that symlink dangles, so `uv run ...` and the ralph-run preflight fail until the user does `rm -rf .venv && uv sync`. The template therefore mounts a named volume over that one path:

```
"source=claude-code-project-venv-${devcontainerId},target=/workspace/.venv,type=volume"
```

This is the **only** remaining volume overlay under `/workspace` — the `.claude` directory is a plain shared bind, per the note directly above. `postCreateCommand` chowns the volume because Docker creates a fresh named volume root-owned, so `sudo chown node:node /workspace/.venv` must run before `uv` writes there as `node`. The container gets its own Linux virtualenv, the host keeps its own, and neither sees the other. Nothing needs to seed the volume: `uv` builds the environment on first use, and it repairs a stale one by itself after an image rebuild (`Ignoring existing virtual environment linked to non-existent Python interpreter` → `Removed virtual environment` → recreate). For non-Python projects the overlay is inert — an empty volume, plus an empty `.venv/` mountpoint directory in the project root, which is why Step 3.4 gitignores `.venv/` for every language.

To confirm both overlays are live, run this **inside the container** after a rebuild — each one shows up as its own mount nested inside the host bind mount:

```bash
awk '$5 == "/workspace" || $5 ~ /^\/workspace\// { print $5, $(NF-2) }' /proc/self/mountinfo
# /workspace                            virtiofs   <- host bind mount (Docker Desktop macOS)
# /workspace/.claude/settings.local.json virtiofs   <- container settings bind; absent means it did not apply
# /workspace/.venv                      ext4       <- .venv volume; absent means it did not apply
```

`/workspace/.claude` itself must **not** appear as its own filesystem — if it does, the container is still running the old whole-directory volume and needs a recreate. Two more checks for the shared bind: `md5sum .claude/settings.json` must match on host and in the container, and `git status` must work as `node` with no manual config.

A `mounts` or lifecycle-hook change needs **Dev Containers: Rebuild Container** (or `--rebuild` / `/ralph-run rebuild=true`) — a restart will not pick it up, because `mounts`, `initializeCommand`, and `postCreateCommand` are all read only when the container is created.

**Claude Code version pin (the image must not freeze an old CLI):** `devcontainer.json` passes `CLAUDE_CODE_VERSION` as a concrete `X.Y.Z` build arg, never `latest`. The Dockerfile installs it with `npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}`, and because that `RUN` line never changes, Docker caches the layer: a floating tag is resolved once, at the first build, and every later build silently reuses it. A container 24 releases behind npm then fails every Ralph iteration with `Claude Code X.Y.Z does not support this model; version … or newer is required`, while the image looks freshly rebuilt. With a pin, the version is in the diff, and bumping it changes the layer's cache key, so the next build reinstalls. `Dockerfile.base` declares the `ARG` with **no default** and its npm step fails the build on anything that is not `X.Y.Z` (empty, `latest`, `next`), then checks `claude --version` against the pin; it also stamps the pin as the image label `dev.ralph.claude-code-version`.

- **Bump:** set the value to `npm view @anthropic-ai/claude-code version`, commit, then rebuild the image — a plain build (`devcontainer build --workspace-folder .`, or recreating the container with `--rebuild` / `rebuild=true`) is enough, because the new value already misses the cache; `--no-cache` is only for forcing a refresh without an input change.
- **What the next build installs** (no container needed): `grep '"CLAUDE_CODE_VERSION"' .devcontainer/devcontainer.json`
- **What a built image carries** (no container needed): `docker image inspect --format '{{ index .Config.Labels "dev.ralph.claude-code-version" }}' <image>` — devcontainer images are named `vsc-<folder>-<hash>`; list them with `docker images 'vsc-*'`.
- **`--remove-existing-container` does NOT refresh the image.** It (like `--rebuild`, `/ralph-run rebuild=true`, and "Rebuild Container") recreates the *container*; the image layers come from the build cache, and any layer whose inputs did not change is reused as-is. To force a fresh image regardless of inputs, run `devcontainer build --workspace-folder . --no-cache`, then recreate the container.

**uv version pin (the orchestrator's own toolchain must not freeze):** `devcontainer.json` also passes `UV_VERSION` as a concrete `X.Y.Z` build arg. uv is what runs the orchestrator (`ralph.sh` ends in `exec uv run …`), what installs the interpreter (`uv python install 3.14`), and what executes every PEP 723 script, so a frozen copy surfaces as a confusing resolver or interpreter-download error rather than as an obvious stale-tool message. `COPY --from` **cannot** expand a build arg — Docker fails with `variable expansion is not supported for --from` — so `Dockerfile.base` declares `ARG UV_VERSION` before the first `FROM` (it has to be global: `Dockerfile.lang.go` contributes its own `FROM`), pulls the binary through `FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv-bin`, and copies it once with `COPY --from=uv-bin /uv /usr/local/bin/uv`. uv is copied in the base for **every** language, so no `Dockerfile.install.*` fragment may add a second one. The `ARG` has **no default** on purpose: an unset value makes the stage reference invalid and the build fails at stage 0, which is louder and earlier than a floating tag. BuildKit warns `InvalidDefaultArgInFrom` because of that missing default — the warning is expected; do not silence it by adding one, which would reintroduce the silent float and put the pin in a second place that drifts.

- **Bump:** set the value to a uv release, commit, then rebuild the image — the changed value points the `uv-bin` stage at a different image, so the copy layer misses the cache.
- **What the next build installs** (no container needed): `grep '"UV_VERSION"' .devcontainer/devcontainer.json`
- **What a built image carries** (no container needed): `docker image inspect --format '{{ index .Config.Labels "dev.ralph.uv-version" }}' <image>`
- **A plain `docker build` now needs the arg.** Without `--build-arg UV_VERSION=<X.Y.Z>` the stage reference is `ghcr.io/astral-sh/uv:` and Docker fails with an opaque `invalid reference format`. The `devcontainer` CLI supplies it from `devcontainer.json`, so the normal path is unaffected.

**Host MCP gateway slot (optional):** the template also ships a neutral, service-agnostic "host MCP gateway" slot so MCP-dependent phases can run with `devcontainer=true` (sandbox isolation intact) instead of falling back to `devcontainer=false`. Inside the container `localhost` points at the container, so a gateway published on the host is unreachable by that name; the host is reachable at `host.docker.internal`, and `init-firewall.sh` already permits that container→host egress (same path as the `host.docker.internal:3128` Squid proxy). The template forwards two neutral vars — `MCP_GATEWAY_HOST` (fixed to `host.docker.internal`) and `MCP_GATEWAY_TOKEN` (a `${localEnv:MCP_GATEWAY_TOKEN}` passthrough) — and appends `host.docker.internal` to `NO_PROXY` so the MCP client connects **directly** to the host gateway instead of routing through Squid (which is not configured to reach it). Ralph ships only this reachability plumbing; the specific gateway (its port and path) stays in the project's own `.mcp.json`. Ralph never names the service. If the project has no host MCP gateway, ignore this — the vars resolve empty and nothing else changes. Tell the user:

1. **Export the gateway token from the shell's always-sourced env file** (same gotcha as the OAuth token above): zsh users add the export to `~/.zshenv` — NOT `~/.zshrc`, which is interactive-only, so non-interactive Ralph launches would see an empty value. bash users use the equivalent always-sourced env file.

   ```sh
   export MCP_GATEWAY_TOKEN="<your host gateway token>"
   ```

2. **Point `.mcp.json` at the slot** so a single file resolves correctly both on the host and inside the container. Use `${MCP_GATEWAY_HOST:-localhost}` for the host (→ `localhost` on the host, `host.docker.internal` in-container) and `Bearer ${MCP_GATEWAY_TOKEN}` for auth:

   ```json
   {
     "mcpServers": {
       "<name>": {
         "type": "http",
         "url": "http://${MCP_GATEWAY_HOST:-localhost}:<port>/<path>",
         "headers": { "Authorization": "Bearer ${MCP_GATEWAY_TOKEN}" }
       }
     }
   }
   ```

**Graceful degradation:** when the host shell does not export `MCP_GATEWAY_TOKEN`, `${localEnv:MCP_GATEWAY_TOKEN}` resolves to empty string and the container starts unaffected — a server that needs the token simply fails to authenticate, exactly like the OAuth-token path. `MCP_GATEWAY_HOST` is a constant, so the reachability wiring is inert until a `.mcp.json` actually references it.

> **colima caveat:** Docker Desktop maps `host.docker.internal` automatically; colima may need an explicit host mapping for it to resolve in-container. This is a host runtime prerequisite, not a repo change.

### 3.7a `.claude/hooks/` and `.claude/settings.local.json` (template write)
Read each `templates/claude/hooks/*-guard.sh` and `templates/claude/hooks/task-validator.sh` → write to `.claude/hooks/<name>.sh`. Make executable (`chmod +x`). Create `.claude/hooks/` directory if it does not exist. The `*-guard.sh` glob includes `filename-length-guard.sh`, which is not a PreToolUse hook — it is the tracked implementation that `.git/hooks/pre-commit` (Step 3.3) invokes, so it must be executable even though `settings.json` never references it.
Read `templates/claude/settings.local.json` → write to `.claude/settings.local.json` (user permissions).

`.claude/settings.json` (the project-wide file that *registers* the hooks with Claude Code) is deliberately **not** written here. The hook scripts on disk are inert until the registration file lands, so this step leaves them dormant. See Step 3.11 for the deferred activation rationale.

### 3.7b Merge pptx helper rules into `settings.local.json` (Documentation / Mixed only)

**Gate:** run this sub-step **only when `project_type ∈ {Documentation, Mixed}`** (Q0 answer B or C). For **Code-only** projects (Q0 answer A), skip entirely — print `[skip] 3.7b pptx helper rules (Code-only project)` and proceed to Step 3.8. This gate is what keeps Code-only `settings.local.json` free of pptx rules.

Documentation / Mixed projects provision Obsidian + devcontainer support for presentation work (Step 3.9). The `example-skills:pptx` skill body shells out to two commands not covered by the template allowlist:

- `python scripts/office/soffice.py` — LibreOffice headless conversion
- `pdftoppm` — PDF → image rasterization

Without these rules, every pptx conversion in a Documentation/Mixed project trips a permission prompt. Add these two **narrow-form** rules if not already present. The path-narrowed `python scripts/office/soffice.py` form is deliberate — a blanket `Bash(python:*)` is too broad.

- `Bash(python scripts/office/soffice.py:*)`
- `Bash(pdftoppm:*)`

Use `jq` for the idempotent merge (the `+ unique` pattern means re-running init never duplicates rules):
```bash
PPTX1='Bash(python scripts/office/soffice.py:*)'
PPTX2='Bash(pdftoppm:*)'
jq --arg p1 "$PPTX1" --arg p2 "$PPTX2" \
  '.permissions.allow = ((.permissions.allow // []) + [$p1, $p2] | unique)' \
  .claude/settings.local.json > .claude/settings.local.json.tmp \
  && mv .claude/settings.local.json.tmp .claude/settings.local.json
```

Both rules use single-quoted bash strings: there is no `$HOME` to expand, so the literal characters must be preserved verbatim.

### 3.7c Write docs reviewer rules to `.claude/task-reviewer-rules.md` (Documentation / Mixed only)

**Gate:** run this sub-step **only when `project_type ∈ {Documentation, Mixed}`** (Q0 answer B or C). For **Code-only** projects (Q0 answer A), skip entirely — print `[skip] 3.7c docs reviewer rules (Code-only project)` and proceed to Step 3.8. This gate is what keeps Code-only projects free of the docs reviewer rule (Code-only vaults have no `[[…]]` links, so the rule would be noise).

Documentation / Mixed projects keep their canonical `.md` documents in an Obsidian vault (Step 3.9), so wiki-links between them must resolve. Read `templates/claude/task-reviewer-rules.docs.md` → write to `.claude/task-reviewer-rules.md` (create the `.claude/` directory if it does not exist). This gives the `task-reviewer` agent rule `R-DOCS-1`, whose source of truth is the "Obsidian cross-link convention" section that Step 3.2 appended to `CLAUDE.md` (from `CLAUDE.conventions.docs.md`) — the rule points at that section rather than restating it, so the two never drift.

Skip if `.claude/task-reviewer-rules.md` already exists (same skip-if-exists policy as other Step 3 files) — print `[skip] .claude/task-reviewer-rules.md already exists`. A project may maintain its own reviewer rules there; never overwrite them.

### 3.8 `.claude/brainstorm-rules.md`
Read `templates/claude/brainstorm-rules.md` → write to `.claude/brainstorm-rules.md`. Skip if file already exists (same skip-if-exists policy as other init files in Step 3).

The template ships with Ralph-managed sections (Save Design Conclusions Case A/B + Phase 4 Override) above a literal `## Project additions` heading. On upgrade, content above the heading is regenerated from the template; content from `## Project additions` onward is preserved verbatim (see U4 special-merge for the algorithm).

### 3.9 `.obsidian/` config (only if project type is Documentation or Mixed)
Copy Obsidian configuration from templates:

- `templates/obsidian/app.json` → `.obsidian/app.json`
- `templates/obsidian/hotkeys.json` → `.obsidian/hotkeys.json`
- `templates/obsidian/snippets/wide-tables.css` → `.obsidian/snippets/wide-tables.css`

Also append these entries to `.gitignore` (don't duplicate existing lines):
```
# Obsidian (vault-local state — not shared)
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/plugins/
.obsidian/community-plugins.json
```

### 3.10 Verify `settings.local.json` pptx helper rules landed (Documentation / Mixed only)

The ralph-run preflight / heartbeat-wait helpers and the ralph-status `utc-to-moscow.sh` helper are all read-only and invoked as `bash ${CLAUDE_PLUGIN_ROOT}/...`, so `autoAllowBashIfSandboxed` (set in the template `settings.local.json`) authorizes them at run time by what they touch — no seeded allow-rule is required, and there is nothing to verify for them here.

The only rules this step checks are the two **pptx helper** rules from Step 3.7b, which apply to **Documentation / Mixed** projects. Verify they are present and surface a `WARN` naming each missing one — this catches a silently-skipped 3.7b merge (e.g. if `jq` was missing on the host and the pipeline failed without surfacing). For **Code-only** projects the rules are intentionally absent (Step 3.7b does not run), so skip this step entirely.

```bash
# Documentation / Mixed projects only. Code-only projects skip this step —
# the pptx rules are intentionally absent there (Step 3.7b does not run).
pptx_expected=(
  'Bash(python scripts/office/soffice.py:*)'
  'Bash(pdftoppm:*)'
)
pptx_missing=()
for p in "${pptx_expected[@]}"; do
  grep -q -F "$p" .claude/settings.local.json || pptx_missing+=("$p")
done
if (( ${#pptx_missing[@]} > 0 )); then
  echo "WARN: settings.local.json missing pptx helper rules (Documentation/Mixed):"
  printf '  - %s\n' "${pptx_missing[@]}"
  echo "Re-run the jq merge from Step 3.7b to fix."
else
  echo "PASS: both pptx helper rules present in settings.local.json"
fi
```

`grep -F` matches the literal string so paths containing regex-special characters (e.g. `.`, `+`, `$`) do not cause false negatives.

### 3.11 `.claude/settings.json` (hook activation — last act of init)
Read `templates/claude/settings.json` → write to `.claude/settings.json` (project-wide hooks).

This is the file that *registers* the hook scripts written in Step 3.7a with Claude Code, so writing it activates `master-branch-guard.sh` and the other PreToolUse hooks mid-session. Deferring it until after every other Step 3.x template write means subsequent steps (including 3.9's `.obsidian/*` writes on `master`) cannot self-block on a hook this same `/ralph-init` invocation just installed. The invariant for future template-write steps is durable: **hook activation is the last act of init.** Rationale walked end-to-end in `design/ralph-init-hook-ordering-brainstorm.md` (Options A–E, Q1–Q5, addendum 2026-06-13).

---

## Step 4: Summary

```
Ralph initialized successfully!

Files created:
  ralph.sh              - Main autonomous loop script (supports claude, opencode)
  refine.sh             - Adversarial author-reviewer refinement loop (ralph-refine)
  CLAUDE.md             - Agent instructions for Claude Code
  .git/hooks/post-commit - Commit hash tracking for tasks
  .git/hooks/commit-msg  - Forbidden trailer/heading guard
  .git/hooks/pre-commit  - Filename-length (125-byte) + Unicode NFC/NFD guards
  .gitignore            - Updated with Ralph entries
  backlog/              - Backlog initialized
  .claude/settings.json      - Claude Code hooks (project-wide)
  .claude/hooks/             - Hook scripts referenced by settings.json
  .claude/settings.local.json - Claude Code permissions
  .claude/brainstorm-rules.md - Phase 3/4 brainstorm rules (section-aware merge on upgrade)
  .claude/task-reviewer-rules.md - (if Documentation/Mixed) task-reviewer rules (Obsidian cross-links)
  .devcontainer/        - (if applicable) Sandboxed execution environment
  .obsidian/            - (if Documentation/Mixed) Obsidian vault configuration

Usage:
  ./ralph.sh --tool claude       # Run with Claude Code (default)
  ./ralph.sh --tool opencode     # Run with opencode

Error handling options:
  --on-error stop|continue|retry  # Error behavior (default: stop)
  --retry-count N                 # Retries for --on-error=retry (default: 2)
  --log-file path                 # Log errors to file

Next steps:
  1. Review and customize CLAUDE.md (especially ## Project-Specific)
  2. Create a PRD:  /ralph-prd
  3. Convert to tasks:  /ralph-backlog
  4. Run Ralph:  ./ralph.sh --tool claude
                 ./ralph.sh --tool opencode
  5. Receive a planned task from another Ralph project: have the source
     project run /ralph-handoff against this project's path. The handoff
     drops a self-contained task in this repo's backlog/ (status To Do)
     with a Source: line and a Before-starting validation checklist. To
     accept, type in this session: "check new task TASK-NNN — do you
     understand, can you run it?"
```

---

## Verification: zero-prompt smoke test

Run this manual smoke test once after any change to the init permission flow. It confirms a fresh scaffold launches Ralph with **zero permission prompts except the single devcontainer sandbox bypass** — the property this init flow exists to guarantee. It exercises the real Claude Code permission matcher, which the Python unit tests cannot.

**Why zero seeded rules suffice:** the scaffolded `.claude/settings.local.json` sets `sandbox.enabled: true` and `autoAllowBashIfSandboxed: true`. Under a devcontainer run, sandbox auto-allow authorizes a command by **what it touches, not the script path** — so the ralph-run / ralph-status helpers need no seeded allow-rule. There are no `Bash(bash $HOME/.claude/skills/...:*)` narrow rules to seed or verify; that subsystem was removed.

**Setup — scaffold a throwaway project:**

1. In an empty git repo (`git init`), install the ralph plugin, then run `/ralph-init` and answer **Code-only** (Q0 → A) with the devcontainer **enabled**. Code-only skips Step 3.7b, so the scaffold carries **no** pptx rules and **no** `.claude/skills` narrow rules — only the template allowlist plus the two sandbox keys.
2. Confirm the scaffold is clean:
   ```bash
   # Expect NO output: no seeded narrow skills rules should exist.
   grep -n '\.claude/skills/ralph' .claude/settings.local.json
   # Expect { "enabled": true, "autoAllowBashIfSandboxed": true }.
   jq -c '.sandbox' .claude/settings.local.json
   ```
3. Create one trivial task so `/ralph-run` has something to launch: `backlog task create "smoke" -d "noop"`.

**Exercise — from an interactive Claude Code session in that project, run:**

```
/ralph-run tasks=1 watch=5m devcontainer=true
```

**Expected result — exactly one prompt:**

- ✅ **Preflight** (`bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-run/scripts/preflight.sh …`) — no prompt. Read-only, so sandbox auto-allow covers it.
- ✅ **Heartbeat wait** (`bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-run/scripts/wait-heartbeat.sh && rm -f backlog/.ralph-launch.log`) — no prompt. The shim is read-only (TASK-192) and the trailing `rm` only touches `backlog/.ralph-launch.log` inside the workspace, so the whole command stays sandbox-covered.
- ✅ **ralph-status `utc-to-moscow.sh`** (fired by `watch`) — no prompt. Read-only helper, sandbox-covered.
- ✅ **backlog / git / jq** helpers — no prompt. Covered by the template allowlist.
- ⚠️ **Launch** (`nohup "${RALPH_CMD[@]}" > backlog/.ralph-launch.log 2>&1 & disown`) — **one** prompt. ralph-run Step 4 sets `dangerouslyDisableSandbox: true` on this call so the orchestrator gets full OS access (mktemp, /dev/fd, tee, docker); disabling the sandbox always prompts. This is the expected devcontainer bypass and the only prompt allowed to appear.

If any command other than the launch prompts, a seeded-rule regression has crept back in — a helper is no longer read-only or workspace-confined, or its invocation no longer leads with `bash ${CLAUDE_PLUGIN_ROOT}/…`. Fix the helper or skill, not the allowlist: re-adding a narrow rule is exactly the regression this flow removed.

---

## Upgrade Mode

Activated when the user says `upgrade ralph`, `ralph upgrade`, `update ralph files`, or passes `--upgrade`. This flow updates existing Ralph infrastructure files to the latest template versions without losing project-specific customizations.

**This is a separate flow from init.** Do not run init steps. Do not ask clarifying questions (Q0–Q4). The upgrade flow reads existing files, compares them against templates, and offers to update outdated ones.

---

### U1: Preflight

Run the same checks as Step 1:

```bash
git rev-parse --git-dir    # Must be a git repo
command -v backlog          # Must have backlog CLI
```

**Additionally verify** that Ralph was previously initialized — at least one of these must exist:
- `ralph.sh` in the project root
- `CLAUDE.md` in the project root

If neither exists, tell the user: "Ralph has not been initialized in this project. Run `/ralph-init` first." and stop.

---

### U1.5: Branch Safety

Refuse to proceed with the upgrade flow when the user is on `master` (or a detached HEAD). Upgrade-mode U4 overwrites root-level files — `ralph.sh`, `CLAUDE.md`, `.git/hooks/*`, `.devcontainer/*` — none of which are in the master-branch-guard exempt list. If the hook is already installed (which it will be after a prior init), every U4 write is denied. The fix is to require a task branch before upgrade can begin.

Run:

```bash
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
```

- **If `branch` is `master` or `HEAD`** (the latter indicates detached HEAD): print the refusal message verbatim and **stop**. Do NOT read any files, do NOT proceed to U1.6 or U2.

  ```
  BLOCKED: ralph upgrade refuses to run on master (or detached HEAD).
  Upgrade overwrites root-level files (ralph.sh, CLAUDE.md, .git/hooks/*,
  .devcontainer/*) that master-branch-guard denies on master.
  Create a task branch first, then re-invoke upgrade:

    git checkout -b task-<id>-ralph-upgrade master

  See design/ralph-init-hook-ordering-brainstorm.md (Q4) for rationale.
  ```

- **Otherwise** (any non-master, non-detached branch): proceed silently to U1.6.

This step fires before any file reads, so a refusal has no side effects.

---

### U1.6: Legacy File Migration

Detect PRD and brainstorm files created before the `design/` convention (TASK-102) and offer to relocate them.

**This step is silent when no legacy files exist** — print nothing, proceed directly to U2.

1. Glob for `tasks/prd-*.md` and `tasks/brainstorm-*.md`.
2. If no matches, skip silently to U2.
3. If matches exist, ensure `design/` directory exists (`mkdir -p design`).
4. For each matched file, extract `<name>` from the filename pattern and propose the move:

   - `tasks/prd-<name>.md` → `design/<name>-prd.md`
   - `tasks/brainstorm-<name>.md` → `design/<name>-brainstorm.md`

   Print:
   ```
   Detected legacy PRD at tasks/prd-<name>.md. Move to design/<name>-prd.md? [y/N]
   ```
   (or the brainstorm equivalent)

   - On **y**: run `git mv tasks/prd-<name>.md design/<name>-prd.md`, print `  moved`.
   - On **N** (default): leave the file alone, print `  skipped (user)`.

5. After processing all files, print a one-line summary: `Legacy migration: <moved> moved, <skipped> skipped.`

---

### U2: Build File Status Table

Compare each managed file against its current template. Assign one status per file:

| Status | Meaning |
|---|---|
| **current** | File exists and matches the template |
| **outdated** | File exists but differs from the template |
| **missing** | File does not exist (would be created) |
| **skipped** | File is excluded from upgrade checks |

**Files to check:**

1. **`ralph.sh`** — exact content match against `templates/root/ralph.sh`
2. **`refine.sh`** — exact content match against `templates/root/refine.sh`
3. **`CLAUDE.md`** — compare only lines **above** the `## Project-Specific` heading against the same region in `templates/root/CLAUDE.md`. Everything from `## Project-Specific` down (including conventions) is the project block and must never be touched.
4. **`.git/hooks/post-commit`** — exact content match against `templates/git-hooks/post-commit`
5. **`.git/hooks/commit-msg`** — exact content match against `templates/git-hooks/commit-msg`
6. **`.git/hooks/pre-commit`** — exact content match against `templates/git-hooks/pre-commit` (125-byte filename-length guard + Unicode NFC/NFD duplicate guard, see TASK-136)
7. **`.claude/settings.json`** — exact content match against `templates/claude/settings.json`
8. **`.claude/hooks/`** — each script in `templates/claude/hooks/*-guard.sh` and `templates/claude/hooks/task-validator.sh` must match `.claude/hooks/<name>.sh`. A project that predates `filename-length-guard.sh` reports it **missing**; U4 creates it, which is what arms the pre-commit length check.
9. **`.claude/settings.local.json`** — exact content match against `templates/claude/settings.local.json`
10. **`.devcontainer/devcontainer.json`** — exact content match against `templates/devcontainer/devcontainer.json`. If `.devcontainer/` directory does not exist, status is **skipped**.
11. **`.devcontainer/init-firewall.sh`** — exact content match against `templates/devcontainer/init-firewall.sh`. If `.devcontainer/` directory does not exist, status is **skipped**.
12. **`.devcontainer/Dockerfile`** — always **skipped** (assembled from fragments, cannot diff meaningfully). It is still **checked**, not silently passed over: run `bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-init/scripts/stale-runtime-copy.sh check .devcontainer/Dockerfile`. Exit 0 keeps the plain `skipped (assembled)`; exit 1 means the file still copies a foreign interpreter over `/usr/local` — status **skipped (assembled; stale runtime copy)**, and U4 offers the in-place patch. The file is never added to the mirror registry: it is patched in place, not re-synced.
13. **`.gitignore`** — always **skipped** (append-only logic in init flow)
14. **`.claude/brainstorm-rules.md`** — managed via section-aware merge: pre-heading content is regenerated from `templates/claude/brainstorm-rules.md`; the `## Project additions` heading and everything below it are preserved verbatim. Status is **current** when the pre-heading region matches the template byte-for-byte; **outdated** when it differs; **missing** when the file does not exist (would be created from template).
15. **`.claude/task-reviewer-rules.md`** — Documentation / Mixed only (detect via an existing `.obsidian/` directory). This file may hold a project's own reviewer rules, so upgrade treats it as **create-if-missing** and never overwrites it: status is **missing** (would be created from `templates/claude/task-reviewer-rules.docs.md`) when a Documentation / Mixed project lacks it; **skipped (present, project-owned)** when it already exists; **skipped (Code-only)** when no `.obsidian/` directory is present.
16. **`.devcontainer/container-settings.local.json`** — exact content match against `templates/devcontainer/container-settings.local.json`. If `.devcontainer/` directory does not exist, status is **skipped**; if the directory exists but the file does not (every project that predates this scheme), status is **missing** and U4 creates it. It must be created whenever `.devcontainer/devcontainer.json` is updated: the new mount binds this file, and a missing bind source makes Docker materialize a directory at the source path, breaking container creation.

---

### U3: Present Batch Summary

Display the status table to the user:

```
File                                         Status
────────────────────────────────────────────────────────────────────────
ralph.sh                                     outdated
refine.sh                                    outdated
CLAUDE.md (generic section)                  current
.git/hooks/post-commit                       outdated
.git/hooks/commit-msg                        outdated
.git/hooks/pre-commit                        outdated
.claude/settings.json                        current
.claude/hooks/                               current
.claude/settings.local.json                  current
.claude/brainstorm-rules.md                  outdated
.claude/task-reviewer-rules.md               skipped (Code-only)
.devcontainer/devcontainer.json              skipped (no .devcontainer/)
.devcontainer/init-firewall.sh               skipped (no .devcontainer/)
.devcontainer/container-settings.local.json  skipped (no .devcontainer/)
.devcontainer/Dockerfile                     skipped (assembled)
.gitignore                                   skipped (append-only)
```

**For outdated files, show details:**

- **`ralph.sh`**, **`refine.sh`**, **`.git/hooks/post-commit`**, **`.git/hooks/commit-msg`**, and **`.git/hooks/pre-commit`**: show a plain language summary of what changed (e.g. "Template adds --model flag support and fixes timeout handling"). Read both versions and describe the meaningful differences — do not dump raw diffs for these files.
- **`.claude/settings.json`**: show the unified diff (`diff -u`) because the project may have custom hooks the user wants to preserve.
- **`.claude/settings.local.json`**: show the unified diff (`diff -u`) because the project may have custom permissions the user wants to preserve.
- **`CLAUDE.md`**: show a plain language summary of what changed in the generic section (above `## Project-Specific`).
- **`.claude/brainstorm-rules.md`**: show a plain language summary of what changed in the Ralph-managed region (above `## Project additions`).
- **`.devcontainer/devcontainer.json`** and **`.devcontainer/init-firewall.sh`**: show a plain language summary of what changed.
- **`.devcontainer/container-settings.local.json`**: show the unified diff (`diff -u`) — it is three lines, and it is the file that decides whether the container runs with the sandbox off.
- **`.devcontainer/Dockerfile`** when U2 marked it `skipped (assembled; stale runtime copy)`: print the `check` output line and say that `python3` in the image cannot start. The patch itself is offered separately in U4 ("Stale language-runtime copy on upgrade"). A stale Dockerfile counts as pending work: when every other file is **current** or **skipped**, do not print "All Ralph files are up to date." and stop — skip the batch question and go straight to that U4 offer.

If all files are **current** or **skipped** — except a Dockerfile marked `skipped (assembled; stale runtime copy)`, which is pending work (see the bullet above) — print "All Ralph files are up to date." and stop.

**Then ask:**
```
Update all outdated files? Or name files to skip.
  - yes / all — update everything
  - skip <file> [<file> ...] — update all except named files
  - none / cancel — do nothing
```

---

### U4: Apply Updates

For each file the user approved:

- **`ralph.sh`**: overwrite from `templates/root/ralph.sh`, then `chmod +x`.
- **`refine.sh`**: overwrite from `templates/root/refine.sh`, then `chmod +x`.
- **`.git/hooks/post-commit`**: overwrite from `templates/git-hooks/post-commit`, then `chmod +x`.
- **`.git/hooks/commit-msg`**: overwrite from `templates/git-hooks/commit-msg`, then `chmod +x`.
- **`.git/hooks/pre-commit`**: overwrite from `templates/git-hooks/pre-commit`, then `chmod +x`. Also re-assert `git config --local core.precomposeunicode true` (idempotent — no-op if already set) so the macOS NFD-on-write defense ships alongside the hook. The overwritten hook calls `.claude/hooks/filename-length-guard.sh`; if the user skipped the `.claude/hooks/` update the `[ -x ]` guard makes the call a silent no-op rather than a broken hook, so the two files may be updated in either order.
- **`.claude/settings.json`**: overwrite from `templates/claude/settings.json`.
- **`.claude/hooks/`**: for each `templates/claude/hooks/*-guard.sh` and `templates/claude/hooks/task-validator.sh`, overwrite `.claude/hooks/<name>.sh`, then `chmod +x`. Create directory if needed. This is how an existing project picks up `filename-length-guard.sh`; `chmod +x` is not optional for it, since pre-commit tests `[ -x ]` before calling it.
- **`.claude/settings.local.json`**: overwrite from `templates/claude/settings.local.json`. **If the project is Documentation or Mixed** (detect via existing `.obsidian/` directory), run the Step 3.7b pptx merge so the overwrite does not strip the `Bash(python scripts/office/soffice.py:*)` and `Bash(pdftoppm:*)` rules. **Code-only** projects need no post-overwrite merge — the ralph-run and ralph-status helpers are read-only and authorized at run time by `autoAllowBashIfSandboxed`, so no seeded allow-rule is required. User-added custom permissions in the existing `allow` array are preserved by the `+ unique` merge. After any merge, run the Step 3.10 verification block (pptx rules, Documentation / Mixed only) and surface any `WARN` to the user before completing the upgrade.
- **`.devcontainer/devcontainer.json`**: overwrite from `templates/devcontainer/devcontainer.json`.
- **`.devcontainer/init-firewall.sh`**: overwrite from `templates/devcontainer/init-firewall.sh`, then `chmod +x`.
- **`.devcontainer/container-settings.local.json`**: overwrite from `templates/devcontainer/container-settings.local.json`. Not executable, and it must stay at the sandbox switch alone — never merge project permissions into it (see the Init "shared `.claude`" note).
- **`CLAUDE.md` (special merge)**:
  1. Read the existing `CLAUDE.md`
  2. Find the line `## Project-Specific`
  3. Extract from that line to EOF — this is the **project block**
  4. Read `templates/root/CLAUDE.md`
  5. Take everything **above** `## Project-Specific` from the template — this is the **generic block**
  6. Write: generic block + project block (concatenated, no extra blank lines between them)
- **`.claude/brainstorm-rules.md` (special merge — section-aware)**:
  1. Read the existing `.claude/brainstorm-rules.md`.
  2. Locate the first line that exactly equals `## Project additions` (line-level exact match).
  3. **If the heading is present:** split the existing file at that line. The heading + everything below is the **user block** (preserved verbatim). Read `templates/claude/brainstorm-rules.md` and take everything **above** the same `## Project additions` heading — this is the **template block**. Write: template block + user block (concatenated, no extra blank lines between them).
  4. **If the heading is absent** (legacy file lacking the convention): one-time migration. Treat the entire existing file as user content. Write: template block (everything above `## Project additions` in the template) + the template's `## Project additions` heading + HTML comment + the existing file content appended verbatim below the heading.
  5. Write the merged result back to `.claude/brainstorm-rules.md`.
- **`.claude/task-reviewer-rules.md`** (Documentation / Mixed only — detect via an existing `.obsidian/` directory): **create-if-missing only.** If the file is absent, create it from `templates/claude/task-reviewer-rules.docs.md`; this is how existing docs/mixed projects pick up the `R-DOCS-1` rule on upgrade. If it already exists, leave it untouched — it may hold the project's own reviewer rules, so never overwrite it. Code-only projects have no `.obsidian/` directory and are skipped.

**Missing files**: create from template using the same logic as the init flow (copy template, `chmod +x` where applicable).

The Ralph-owned `.devcontainer/devcontainer.json` carries the host MCP gateway slot (`MCP_GATEWAY_HOST` / `MCP_GATEWAY_TOKEN` + the widened `NO_PROXY`), so it upgrades through the normal U2/U4 sync above like any other managed file — no special handling. The per-consumer `.mcp.json` is handled separately in U4.5.

The same file also carries the `.venv` volume overlay, the shared-`.claude` scheme — the single-file bind of `.devcontainer/container-settings.local.json` over `/workspace/.claude/settings.local.json`, the `initializeCommand` that seeds the host file (creating `.claude` first with `mkdir -p`, so a clone without the directory no longer aborts container creation — projects scaffolded before this fix only get it through U4), and the `postCreateCommand` that grants git `safe.directory` — and the second bind of the user `~/.claude` at its own host path, `source=${localEnv:HOME}/.claude,target=${localEnv:HOME}/.claude,type=bind`, which is what makes plugin-provided agents (`task-reviewer`) resolve instead of failing with `cache-miss`, together with `"CLAUDE_CONFIG_DIR": "${localEnv:HOME}/.claude"`, which keeps what the container *writes* into the shared plugin registries readable on the host (see all three Init notes). They sync the same way — but `mounts`, `containerEnv`, `initializeCommand`, and `postCreateCommand` are read **only when the container is created**, so a change to any of them takes effect on a **recreate**, never on a restart. So whenever U4 rewrites `.devcontainer/devcontainer.json`, add this to the U5 summary:

```
.devcontainer/devcontainer.json changed — run "Dev Containers: Rebuild Container"
(a restart will not pick up mount or lifecycle-hook changes). The project .claude
is now shared with the container instead of copied into a volume, so host edits
reach the container and container commits no longer revert .claude files; only
.claude/settings.local.json is overridden, from
.devcontainer/container-settings.local.json. The host ~/.claude is now bound a
second time at its own host path, and CLAUDE_CONFIG_DIR now points there
instead of at /home/node/.claude, so plugin marketplaces resolve inside the
container, the task-reviewer agent registers, and a container run no longer
writes container-only paths into the shared registries; until the container is
recreated, `claude plugin list` still reports cache-miss and Review silently
runs without the real reviewer. If an earlier container run already relocated
them, repair the host's ~/.claude/plugins/known_marketplaces.json and
installed_plugins.json once by rewriting every /home/node/.claude prefix back
to your own $HOME/.claude (the clones themselves are intact, so no re-add is
needed). If your host .venv was already clobbered by an
earlier container run, repair it once on the host with:
  rm -rf .venv && uv sync
```

**Claude Code version pin on upgrade:** the template's `devcontainer.json` pins `CLAUDE_CODE_VERSION` to a concrete `X.Y.Z` (see the Init "Claude Code version pin" note). Two rules apply when U4 rewrites the file:

1. **Never downgrade.** If the project's existing `CLAUDE_CODE_VERSION` is a concrete version **newer** than the template's, keep the project's value in the rewritten file and say so in the U5 summary. An older project value or `latest` takes the template's pin.
2. **Patch the Dockerfile in place (confirm first).** `.devcontainer/Dockerfile` is skipped by the U2 table (assembled), so it keeps `ARG CLAUDE_CODE_VERSION=latest` and the bare npm `RUN`. The pinned build arg already overrides that default, so the freeze is fixed by `devcontainer.json` alone; still offer to replace those two instructions with the `Dockerfile.base` versions (the default-less `ARG`, the `LABEL dev.ralph.claude-code-version`, and the guarded npm `RUN`) so a lost build arg fails the build instead of quietly installing `latest`. Show the diff, apply only on a yes, and label the file `skipped (assembled; version pin patched)` in U5 when it fires.

Whenever the pin changed, add to the U5 summary:

```
CLAUDE_CODE_VERSION is now pinned to <X.Y.Z> — the image needs a rebuild to pick
it up. --remove-existing-container / "Rebuild Container" recreates the container
but does NOT refresh cached image layers; the changed pin invalidates the npm
layer on the next build, and `devcontainer build --workspace-folder . --no-cache`
forces a fresh image. Check what a built image carries with:
  docker image inspect --format '{{ index .Config.Labels "dev.ralph.claude-code-version" }}' <image>
```

**uv version pin on upgrade (here the Dockerfile patch is NOT optional):** the template's `devcontainer.json` also pins `UV_VERSION` (see the Init "uv version pin" note), and the never-downgrade rule above applies to its value too. What differs from `CLAUDE_CODE_VERSION` is the consequence of leaving the Dockerfile alone.

`COPY --from` cannot expand a build arg, so the pin only works through a named stage: a global `ARG UV_VERSION` before the first `FROM`, then `FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv-bin`. A project bootstrapped before the pin has neither — its `.devcontainer/Dockerfile` still says `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv`. U4 rewrites `devcontainer.json`, so the project **gains** `"UV_VERSION"`, but Docker has nothing to apply it to: it reports the arg as unused, uv stays frozen on `latest` in the layer cache, and no `dev.ralph.uv-version` label appears. The project then *looks* pinned to a `grep` while nothing has changed. With `CLAUDE_CODE_VERSION` a pre-existing `ARG …=latest` absorbs the build arg, so that Dockerfile patch is hardening; **for uv there is no fallback at all, so the patch is required for the pin to have any effect.**

So whenever U4 adds or changes `UV_VERSION` in a project whose `.devcontainer/Dockerfile` still copies uv from a floating tag, offer the in-place patch — confirm-only, the same shape as the version-pin patch above:

1. Build the patched text without writing it: add a global `ARG UV_VERSION` and the `FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv-bin` stage above the project's first `FROM`, and replace the floating `COPY --from=ghcr.io/astral-sh/uv:…` line with the `Dockerfile.base` block — the in-stage `ARG UV_VERSION`, `LABEL dev.ralph.uv-version`, `COPY --from=uv-bin /uv /usr/local/bin/uv`, and the guarded `RUN` that rejects a non-`X.Y.Z` value and checks `uv --version` against the pin.
2. Show `diff -u` of the current and patched files and ask:

   ```
   .devcontainer/Dockerfile still copies uv from a floating tag, so the UV_VERSION pin
   just added to devcontainer.json has no effect. Patch the Dockerfile to use it? [y/N]
   ```

3. **On a yes:** write it and label the file `skipped (assembled; uv pin patched)` in U5. **On N:** leave it and say plainly in the U5 summary that `UV_VERSION` is inert until the Dockerfile is patched, so the project is not pinned despite the value being present. Do not let the summary imply otherwise.

When both this and the Claude Code patch fire, join the outcomes in one label, version pin first — e.g. `skipped (assembled; version pin patched; uv pin patched)`. A project that predates TASK-242 can fire all three (Claude Code pin, uv pin, stale runtime copy); the `; `-joined pattern extends the same way, in that order — e.g. `skipped (assembled; version pin patched; uv pin patched; runtime copy patched)`.

**Stale language-runtime copy on upgrade:** projects bootstrapped as Python or Documentation / Mixed before TASK-242 still carry `FROM python:3.14 AS python-runtime` and `COPY --from=python-runtime /usr/local /usr/local` in `.devcontainer/Dockerfile`. `python:3.14` is built on a newer Debian than the `node:20` (bookworm) base, so that copy puts an interpreter linked against a glibc the image lacks first in `PATH`, and `python3 -c ''` cannot start. The upgraded pre-commit hook already skips a `python3` that cannot run, so commits still work; the image is degraded, not broken. When U2 marked the Dockerfile `skipped (assembled; stale runtime copy)`, offer the in-place patch — confirm-only, the same shape as the version-pin patches above:

1. Run `bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-init/scripts/stale-runtime-copy.sh patch .devcontainer/Dockerfile > .devcontainer/Dockerfile.patched`. The script only prints; it never writes the Dockerfile. It replaces the stale stage (the `FROM … AS <stage>` line and the `###` banner above it) with the current `templates/devcontainer/lang/Dockerfile.lang.<flavour>`, and the paragraph holding the `COPY` with the first paragraph of the current `Dockerfile.install.<flavour>`; every other line is kept. The flavour comes from the file itself — `docs` when it carries `# ---- Documentation Tools ----`, `python` when the stage image is `python:*` — so a Mixed project gets the fragments it was assembled from.
2. **Any exit other than 0** — 3 (more than one stale copy, a stage no current fragment replaces, or a copy paragraph that also holds other instructions), 2 (a fragment could not be read), or anything else: delete `.devcontainer/Dockerfile.patched`, show the script's stderr and the `check` output, tell the user to fix the file by hand, and label it `skipped (assembled; stale runtime copy, patch by hand)` in U5.
3. **Exit 0:** show `diff -u .devcontainer/Dockerfile .devcontainer/Dockerfile.patched` and ask:

   ```
   .devcontainer/Dockerfile still copies a foreign python over /usr/local, so python3 in the
   image cannot start. Replace the stale stage and copy with the current language fragment? [y/N]
   ```

4. On **y**: `mv .devcontainer/Dockerfile.patched .devcontainer/Dockerfile` and label the file `skipped (assembled; runtime copy patched)` in U5. On **N** (default) or an empty answer: delete `.devcontainer/Dockerfile.patched`, leave the Dockerfile untouched, and label it `skipped (assembled; stale runtime copy, user declined)`. Never write the Dockerfile without the explicit yes.

A project that deliberately re-pinned the stage and the base to the **same** Debian suite (for example `python:3.14-bookworm` over `node:20-bookworm`) passes `check`, so none of this fires for it. When the patch was applied, add to the U5 summary that the image needs a rebuild to drop the copied interpreter. When either version-pin patch also fired, join the outcomes in one label, version pin first — e.g. `skipped (assembled; version pin patched; runtime copy patched)` or `skipped (assembled; version pin patched; stale runtime copy, user declined)`.

**If the project already applied this fix by hand**, U4's overwrite is still the right outcome — the template is the canonical shape — but say so explicitly in the U5 summary rather than letting the rewrite look like a surprise, and check that `.devcontainer/container-settings.local.json` survived with the sandbox switch intact.

In the same case — and only then, since a project without `.devcontainer/` never gets the mountpoint — append `.venv/` to `.gitignore` if absent: the overlay creates an empty `.venv/` directory in the project root even for non-Python projects. `.gitignore` is skipped by the U2 status table (append-only, never diffed), so this step is the one place the entry gets added on upgrade; when it fires, label the file `skipped (append-only; .venv/ appended)` in the U5 summary instead of the plain `skipped (append-only)`.

---

### U4.5: Offer `.mcp.json` host-rewrite (per-consumer, confirm-only)

`.mcp.json` is **per-consumer and not Ralph-owned**, so it is deliberately absent from the U2 status table and the U4 sync — upgrade must **never silently rewrite it**. This step only *offers* a targeted host-rewrite so an existing `.mcp.json` can use the `MCP_GATEWAY_HOST` slot the updated `devcontainer.json` now provides (see the Init "Host MCP gateway slot" note for the convention).

**This step is silent when it does not apply** — print nothing and proceed to U5 when `.mcp.json` is absent, contains no http-type MCP server, or every http server already uses `${MCP_GATEWAY_HOST...}`.

1. If `.mcp.json` does not exist in the project root, skip silently to U5.
2. Read `.mcp.json`. For each server under `mcpServers` whose `type` is `http` (or that carries a `url`), inspect the URL host.
3. Collect only servers whose URL host is exactly `localhost` or `127.0.0.1`. Ignore any URL that already contains `${MCP_GATEWAY_HOST`, a non-loopback host, or a non-http server. If none remain, skip silently to U5.
4. For each collected server, compute the rewrite that substitutes **only the host** with `${MCP_GATEWAY_HOST:-localhost}` — scheme, port, path, headers, and everything else unchanged:
   - `http://localhost:<port>/<path>` → `http://${MCP_GATEWAY_HOST:-localhost}:<port>/<path>`
   - `http://127.0.0.1:<port>/<path>` → `http://${MCP_GATEWAY_HOST:-localhost}:<port>/<path>`
5. Present a **before/after unified diff** of the proposed change and ask:

   ```
   Rewrite <n> .mcp.json server url(s) to ${MCP_GATEWAY_HOST:-localhost} so they resolve to the
   host gateway inside the devcontainer (and stay localhost on the host)? This edits your
   (non-Ralph) .mcp.json. [y/N]
   ```

6. On **y**: apply the host substring rewrite only (do not reformat or re-key the rest of the file) and print `  .mcp.json rewritten (<n> url(s))`. On **N** (default) or an empty answer: leave the file untouched and print `  .mcp.json skipped (user)`.

Never rewrite silently and never touch anything but the loopback host substring. When in doubt, leave the entry and let the user decide.

---

### U5: Summary

Print which files were updated and their final status:

```
Ralph upgrade complete!

  ralph.sh                          updated
  refine.sh                         updated
  CLAUDE.md (generic section)       current
  .git/hooks/post-commit            updated
  .git/hooks/commit-msg             updated
  .git/hooks/pre-commit             updated
  .claude/settings.json             current
  .claude/hooks/                    current
  .claude/settings.local.json       current
  .claude/brainstorm-rules.md       updated
  .claude/task-reviewer-rules.md    skipped (Code-only)
  .devcontainer/devcontainer.json   skipped (no .devcontainer/)
  .devcontainer/init-firewall.sh    skipped (no .devcontainer/)
  .devcontainer/Dockerfile          skipped (assembled)
  .gitignore                        skipped (append-only)
```

Use these labels:
- **updated** — file was overwritten with the latest template
- **created** — file was missing and has been created
- **current** — file already matched the template
- **skipped (reason)** — file was excluded from checks, with reason in parentheses
- **skipped (user)** — user chose to skip this file
- **skipped (assembled; runtime copy patched)** / **skipped (assembled; stale runtime copy, user declined)** / **skipped (assembled; stale runtime copy, patch by hand)** — `.devcontainer/Dockerfile` only: the outcome of the U4 "Stale language-runtime copy on upgrade" offer. A declined or by-hand result means `python3` in the image still cannot start.
