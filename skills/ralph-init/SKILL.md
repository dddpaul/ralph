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
[ -s "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh" ] || {
  echo "ERROR: install user-global skills first via /ralph-sync, then re-run ralph-init"
  exit 1
}
```

The project-root `ralph.sh` written in Step 3.1 is a thin shim that `exec`s the canonical script at `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh`. If that canonical is missing, the shim points at nothing and the bootstrap is broken. Hard-stop here and instruct the user to install user-global skills first.

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

### 3.1 `ralph.sh`
Read `templates/root/ralph.sh` → write to project root. Make executable (`chmod +x`).

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

### 3.7a `.claude/hooks/` and `.claude/settings.local.json` (template write)
Read each `templates/claude/hooks/*-guard.sh` and `templates/claude/hooks/task-validator.sh` → write to `.claude/hooks/<name>.sh`. Make executable (`chmod +x`). Create `.claude/hooks/` directory if it does not exist.
Read `templates/claude/settings.local.json` → write to `.claude/settings.local.json` (user permissions).

`.claude/settings.json` (the project-wide file that *registers* the hooks with Claude Code) is deliberately **not** written here. The hook scripts on disk are inert until the registration file lands, so this step leaves them dormant. See Step 3.11 for the deferred activation rationale.

### 3.7b Merge narrow script rules into `settings.local.json` permissions

This sub-step is **required** — the template-written `settings.local.json` does not yet contain narrow rules for the ralph-status helper script, and this merge is what avoids over-broad `Bash(bash:*)` permissions. Step 3.10 verifies the merge landed; skipping 3.7b will trip that check.

The ralph-run skill invokes its preflight and heartbeat-wait helpers as Python modules (`uv run --no-project python -m ralph.preflight` / `ralph.wait_heartbeat`), which the template's blanket `Bash(uv run:*)` rule already covers. The narrow-rule merge below only has to handle the remaining bash-path invocation: `utc-to-moscow.sh`, called by `ralph-status` and `ralph-status-watch`.

**Literal-match gotcha — both forms required for bash-path invocations.** Claude Code's permission matcher compares command strings *literally*. `$HOME` is not expanded before matching. The `utc-to-moscow.sh` resolver block in `ralph-status` / `ralph-status-watch` invokes the script in two distinct shapes:

- `bash /Users/<you>/.claude/skills/ralph-status/scripts/utc-to-moscow.sh` — the absolute-path branch the resolver falls through to.
- `bash $HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh` — the literal `$HOME`-prefixed branch that runs first when the resolved-HOME copy is executable.

Both forms reach the matcher, so we must write **both** rule shapes for `utc-to-moscow.sh` — otherwise a `$HOME`-form call triggers a permission prompt despite a "narrow" absolute rule existing. The `Bash(uv run:*)` rule does not need this dual form: `uv run` is the literal command in every ralph-run invocation, with no `$HOME`/absolute split.

Add these rules if not already present (3 total — 1 `uv run` + 2 `utc-to-moscow.sh` forms):

- `Bash(uv run:*)`
- `Bash(bash <RESOLVED_HOME>/.claude/skills/ralph-status/scripts/utc-to-moscow.sh:*)`
- `Bash(bash $HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh:*)`

Use `jq` for the idempotent merge. Note the deliberate quoting: **double-quoted** strings expand `$HOME` to the absolute path; **single-quoted** strings keep the literal `$HOME` characters intact.
```bash
RULE_UV='Bash(uv run:*)'
RULE_UTC_A="Bash(bash $HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh:*)"
RULE_UTC_B='Bash(bash $HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh:*)'
jq --arg ruv "$RULE_UV" \
   --arg ra "$RULE_UTC_A" --arg rb "$RULE_UTC_B" \
  '.permissions.allow = ((.permissions.allow // []) + [$ruv, $ra, $rb] | unique)' \
  .claude/settings.local.json > .claude/settings.local.json.tmp \
  && mv .claude/settings.local.json.tmp .claude/settings.local.json
```

### 3.7c Merge pptx helper rules into `settings.local.json` (Documentation / Mixed only)

**Gate:** run this sub-step **only when `project_type ∈ {Documentation, Mixed}`** (Q0 answer B or C). For **Code-only** projects (Q0 answer A), skip entirely — print `[skip] 3.7c pptx helper rules (Code-only project)` and proceed to Step 3.8. This gate is what keeps Code-only `settings.local.json` free of pptx rules.

Documentation / Mixed projects provision Obsidian + devcontainer support for presentation work (Step 3.9). The `example-skills:pptx` skill body shells out to two commands not covered by the template allowlist:

- `python scripts/office/soffice.py` — LibreOffice headless conversion
- `pdftoppm` — PDF → image rasterization

Without these rules, every pptx conversion in a Documentation/Mixed project trips a permission prompt. Add these two **narrow-form** rules if not already present. The path-narrowed `python scripts/office/soffice.py` form is deliberate — a blanket `Bash(python:*)` is too broad.

- `Bash(python scripts/office/soffice.py:*)`
- `Bash(pdftoppm:*)`

Use `jq` for the idempotent merge (same `+ unique` pattern as Step 3.7b, so re-running init never duplicates rules):
```bash
PPTX1='Bash(python scripts/office/soffice.py:*)'
PPTX2='Bash(pdftoppm:*)'
jq --arg p1 "$PPTX1" --arg p2 "$PPTX2" \
  '.permissions.allow = ((.permissions.allow // []) + [$p1, $p2] | unique)' \
  .claude/settings.local.json > .claude/settings.local.json.tmp \
  && mv .claude/settings.local.json.tmp .claude/settings.local.json
```

Both rules use single-quoted bash strings: there is no `$HOME` to expand here (unlike Step 3.7b), so the literal characters must be preserved verbatim.

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

### 3.10 Verify `settings.local.json` narrow rules landed

After all Step 3.x writes complete, verify the three narrow rules from Step 3.7b are present — the single `Bash(uv run:*)` rule plus both forms (absolute path and literal `$HOME`) of `utc-to-moscow.sh`. This catches silent omissions of the merge sub-step (e.g. if Step 3.7b was accidentally skipped, or `jq` was missing on the host and the pipeline failed without surfacing). For `utc-to-moscow.sh`, both forms must land; missing either one causes a permission prompt when the corresponding skill invocation shape is used.

For **Documentation / Mixed** projects, the verification additionally checks the two pptx helper rules from Step 3.7c and surfaces a `WARN` naming each missing one. This block is skipped for Code-only projects (where Step 3.7c does not run and the rules are intentionally absent).

```bash
# Each entry pairs a human-readable label with its expected literal string.
# Single-quoted entries keep the literal $HOME characters; double-quoted ones
# expand $HOME to the absolute path.
expected_abs=(
  "$HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh"
)
expected_home=(
  '$HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh'
)
missing=()
grep -q -F 'Bash(uv run:*)' .claude/settings.local.json || missing+=("rule: Bash(uv run:*)")
for p in "${expected_abs[@]}"; do
  grep -q -F "$p" .claude/settings.local.json || missing+=("absolute: $p")
done
for p in "${expected_home[@]}"; do
  grep -q -F "$p" .claude/settings.local.json || missing+=("\$HOME-form: $p")
done
if (( ${#missing[@]} > 0 )); then
  echo "WARN: settings.local.json missing narrow rules:"
  printf '  - %s\n' "${missing[@]}"
  echo "Re-run the jq merge from Step 3.7b to fix."
else
  echo "PASS: all 3 narrow rules (Bash(uv run:*) + utc-to-moscow.sh absolute + \$HOME-form) present in settings.local.json"
fi

# Documentation / Mixed projects only: also verify the two pptx helper rules
# from Step 3.7c. Skip this entire block for Code-only projects — those rules
# are intentionally absent there (Step 3.7c does not run).
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
  echo "Re-run the jq merge from Step 3.7c to fix."
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
2. **`CLAUDE.md`** — compare only lines **above** the `## Project-Specific` heading against the same region in `templates/root/CLAUDE.md`. Everything from `## Project-Specific` down (including conventions) is the project block and must never be touched.
3. **`.git/hooks/post-commit`** — exact content match against `templates/git-hooks/post-commit`
4. **`.git/hooks/commit-msg`** — exact content match against `templates/git-hooks/commit-msg`
5. **`.git/hooks/pre-commit`** — exact content match against `templates/git-hooks/pre-commit` (Unicode NFC/NFD duplicate guard, see TASK-136)
6. **`.claude/settings.json`** — exact content match against `templates/claude/settings.json`
7. **`.claude/hooks/`** — each script in `templates/claude/hooks/*-guard.sh` and `templates/claude/hooks/task-validator.sh` must match `.claude/hooks/<name>.sh`
8. **`.claude/settings.local.json`** — exact content match against `templates/claude/settings.local.json`
9. **`.devcontainer/devcontainer.json`** — exact content match against `templates/devcontainer/devcontainer.json`. If `.devcontainer/` directory does not exist, status is **skipped**.
10. **`.devcontainer/init-firewall.sh`** — exact content match against `templates/devcontainer/init-firewall.sh`. If `.devcontainer/` directory does not exist, status is **skipped**.
11. **`.devcontainer/Dockerfile`** — always **skipped** (assembled from fragments, cannot diff meaningfully)
12. **`.gitignore`** — always **skipped** (append-only logic in init flow)
13. **`.claude/brainstorm-rules.md`** — managed via section-aware merge: pre-heading content is regenerated from `templates/claude/brainstorm-rules.md`; the `## Project additions` heading and everything below it are preserved verbatim. Status is **current** when the pre-heading region matches the template byte-for-byte; **outdated** when it differs; **missing** when the file does not exist (would be created from template).

---

### U3: Present Batch Summary

Display the status table to the user:

```
File                              Status
─────────────────────────────────────────
ralph.sh                          outdated
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

- **`ralph.sh`**, **`.git/hooks/post-commit`**, **`.git/hooks/commit-msg`**, and **`.git/hooks/pre-commit`**: show a plain language summary of what changed (e.g. "Template adds --model flag support and fixes timeout handling"). Read both versions and describe the meaningful differences — do not dump raw diffs for these files.
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
- **`.git/hooks/post-commit`**: overwrite from `templates/git-hooks/post-commit`, then `chmod +x`.
- **`.git/hooks/commit-msg`**: overwrite from `templates/git-hooks/commit-msg`, then `chmod +x`.
- **`.git/hooks/pre-commit`**: overwrite from `templates/git-hooks/pre-commit`, then `chmod +x`. Also re-assert `git config --local core.precomposeunicode true` (idempotent — no-op if already set) so the macOS NFD-on-write defense ships alongside the hook.
- **`.claude/settings.json`**: overwrite from `templates/claude/settings.json`.
- **`.claude/hooks/`**: for each `templates/claude/hooks/*-guard.sh` and `templates/claude/hooks/task-validator.sh`, overwrite `.claude/hooks/<name>.sh`, then `chmod +x`. Create directory if needed.
- **`.claude/settings.local.json`**: overwrite from `templates/claude/settings.local.json`. Then run the same narrow-rule merge as Step 3.7b (writes the single `Bash(uv run:*)` rule plus **both** the absolute-path and literal-`$HOME` forms of the `utc-to-moscow.sh` rule — 3 rules total — via `jq`, idempotent through `unique`). **If the project is Documentation or Mixed** (detect via existing `.obsidian/` directory), also run the Step 3.7c pptx merge so the overwrite does not strip the `Bash(python scripts/office/soffice.py:*)` and `Bash(pdftoppm:*)` rules. User-added custom permissions in the existing `allow` array are preserved by the `+ unique` merge. After the merge(s), run the Step 3.10 verification block to confirm all rules landed; surface any `WARN` to the user before completing the upgrade.
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

---

### U5: Summary

Print which files were updated and their final status:

```
Ralph upgrade complete!

  ralph.sh                          updated
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
