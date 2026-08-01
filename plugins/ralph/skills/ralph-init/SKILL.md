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

Read `templates/git-hooks/pre-commit` → write to `.git/hooks/pre-commit`. Make executable (`chmod +x`). If hook already exists, warn user and ask before overwriting. The hook rejects a commit when a staged path duplicates an existing tree path under a different Unicode normalization (NFD vs NFC) — see TASK-136 for the downstream incident that prompted it.

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
Assemble the Dockerfile from base + language snippets, then write three files:

**Dockerfile assembly:** Read `templates/devcontainer/Dockerfile.base`. Replace `{{LANGUAGE_STAGE}}` with contents of `templates/devcontainer/lang/Dockerfile.lang.<lang>` and `{{LANGUAGE_INSTALL}}` with contents of `templates/devcontainer/lang/Dockerfile.install.<lang>`, where `<lang>` is one of: `node`, `python`, `go`, `docs`. For "Other" languages, use `node` as the base and add a comment for the user to customize. For Documentation projects (0B), use `docs` as the language.

- Assembled Dockerfile → `.devcontainer/Dockerfile`
- `templates/devcontainer/devcontainer.json` → `.devcontainer/devcontainer.json` — update app label and port if specified
- `templates/devcontainer/init-firewall.sh` → `.devcontainer/init-firewall.sh`

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
Read each `templates/claude/hooks/*-guard.sh` and `templates/claude/hooks/task-validator.sh` → write to `.claude/hooks/<name>.sh`. Make executable (`chmod +x`). Create `.claude/hooks/` directory if it does not exist.
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
  .git/hooks/pre-commit  - Unicode NFC/NFD duplicate-path guard
  .gitignore            - Updated with Ralph entries
  backlog/              - Backlog initialized
  .claude/settings.json      - Claude Code hooks (project-wide)
  .claude/hooks/             - Hook scripts referenced by settings.json
  .claude/settings.local.json - Claude Code permissions
  .claude/brainstorm-rules.md - Phase 3/4 brainstorm rules (section-aware merge on upgrade)
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
- ⚠️ **Launch** (`nohup $RALPH_CMD > backlog/.ralph-launch.log 2>&1 & disown`) — **one** prompt. ralph-run Step 4 sets `dangerouslyDisableSandbox: true` on this call so the orchestrator gets full OS access (mktemp, /dev/fd, tee, docker); disabling the sandbox always prompts. This is the expected devcontainer bypass and the only prompt allowed to appear.

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
6. **`.git/hooks/pre-commit`** — exact content match against `templates/git-hooks/pre-commit` (Unicode NFC/NFD duplicate guard, see TASK-136)
7. **`.claude/settings.json`** — exact content match against `templates/claude/settings.json`
8. **`.claude/hooks/`** — each script in `templates/claude/hooks/*-guard.sh` and `templates/claude/hooks/task-validator.sh` must match `.claude/hooks/<name>.sh`
9. **`.claude/settings.local.json`** — exact content match against `templates/claude/settings.local.json`
10. **`.devcontainer/devcontainer.json`** — exact content match against `templates/devcontainer/devcontainer.json`. If `.devcontainer/` directory does not exist, status is **skipped**.
11. **`.devcontainer/init-firewall.sh`** — exact content match against `templates/devcontainer/init-firewall.sh`. If `.devcontainer/` directory does not exist, status is **skipped**.
12. **`.devcontainer/Dockerfile`** — always **skipped** (assembled from fragments, cannot diff meaningfully)
13. **`.gitignore`** — always **skipped** (append-only logic in init flow)
14. **`.claude/brainstorm-rules.md`** — managed via section-aware merge: pre-heading content is regenerated from `templates/claude/brainstorm-rules.md`; the `## Project additions` heading and everything below it are preserved verbatim. Status is **current** when the pre-heading region matches the template byte-for-byte; **outdated** when it differs; **missing** when the file does not exist (would be created from template).

---

### U3: Present Batch Summary

Display the status table to the user:

```
File                              Status
─────────────────────────────────────────
ralph.sh                          outdated
refine.sh                         outdated
CLAUDE.md (generic section)       current
.git/hooks/post-commit            outdated
.git/hooks/commit-msg             outdated
.git/hooks/pre-commit             outdated
.claude/settings.json             current
.claude/hooks/                    current
.claude/settings.local.json       current
.claude/brainstorm-rules.md       outdated
.devcontainer/devcontainer.json   skipped (no .devcontainer/)
.devcontainer/init-firewall.sh    skipped (no .devcontainer/)
.devcontainer/Dockerfile          skipped (assembled)
.gitignore                        skipped (append-only)
```

**For outdated files, show details:**

- **`ralph.sh`**, **`refine.sh`**, **`.git/hooks/post-commit`**, **`.git/hooks/commit-msg`**, and **`.git/hooks/pre-commit`**: show a plain language summary of what changed (e.g. "Template adds --model flag support and fixes timeout handling"). Read both versions and describe the meaningful differences — do not dump raw diffs for these files.
- **`.claude/settings.json`**: show the unified diff (`diff -u`) because the project may have custom hooks the user wants to preserve.
- **`.claude/settings.local.json`**: show the unified diff (`diff -u`) because the project may have custom permissions the user wants to preserve.
- **`CLAUDE.md`**: show a plain language summary of what changed in the generic section (above `## Project-Specific`).
- **`.claude/brainstorm-rules.md`**: show a plain language summary of what changed in the Ralph-managed region (above `## Project additions`).
- **`.devcontainer/devcontainer.json`** and **`.devcontainer/init-firewall.sh`**: show a plain language summary of what changed.

If all files are **current** or **skipped**, print "All Ralph files are up to date." and stop.

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
- **`.git/hooks/pre-commit`**: overwrite from `templates/git-hooks/pre-commit`, then `chmod +x`. Also re-assert `git config --local core.precomposeunicode true` (idempotent — no-op if already set) so the macOS NFD-on-write defense ships alongside the hook.
- **`.claude/settings.json`**: overwrite from `templates/claude/settings.json`.
- **`.claude/hooks/`**: for each `templates/claude/hooks/*-guard.sh` and `templates/claude/hooks/task-validator.sh`, overwrite `.claude/hooks/<name>.sh`, then `chmod +x`. Create directory if needed.
- **`.claude/settings.local.json`**: overwrite from `templates/claude/settings.local.json`. **If the project is Documentation or Mixed** (detect via existing `.obsidian/` directory), run the Step 3.7b pptx merge so the overwrite does not strip the `Bash(python scripts/office/soffice.py:*)` and `Bash(pdftoppm:*)` rules. **Code-only** projects need no post-overwrite merge — the ralph-run and ralph-status helpers are read-only and authorized at run time by `autoAllowBashIfSandboxed`, so no seeded allow-rule is required. User-added custom permissions in the existing `allow` array are preserved by the `+ unique` merge. After any merge, run the Step 3.10 verification block (pptx rules, Documentation / Mixed only) and surface any `WARN` to the user before completing the upgrade.
- **`.devcontainer/devcontainer.json`**: overwrite from `templates/devcontainer/devcontainer.json`.
- **`.devcontainer/init-firewall.sh`**: overwrite from `templates/devcontainer/init-firewall.sh`, then `chmod +x`.
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

**Missing files**: create from template using the same logic as the init flow (copy template, `chmod +x` where applicable).

The Ralph-owned `.devcontainer/devcontainer.json` carries the host MCP gateway slot (`MCP_GATEWAY_HOST` / `MCP_GATEWAY_TOKEN` + the widened `NO_PROXY`), so it upgrades through the normal U2/U4 sync above like any other managed file — no special handling. The per-consumer `.mcp.json` is handled separately in U4.5.

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
