---
export: true
title: 'Brainstorm: ralph-sh-shim'
type: design
---

# Brainstorm: ralph-sh-shim

Collapse the three-way `ralph.sh` mirror to a single canonical copy under `~/.claude/skills/ralph-run/scripts/ralph.sh`. The two remaining copies (`./ralph.sh` in the canonical repo, `skills/ralph-init/templates/root/ralph.sh` shipped to ralphed projects) become thin shims that `exec` the canonical one.

## Trigger

TASK-135 added `usage-check.sh` under `skills/ralph-run/scripts/`, and `ralph.sh:479` resolves it relative to `$SCRIPT_DIR`:

```bash
USAGE_CHECK_SCRIPT="${RALPH_USAGE_CHECK_SCRIPT:-$SCRIPT_DIR/skills/ralph-run/scripts/usage-check.sh}"
```

This resolves cleanly in *this* repo (where `skills/` sits next to `ralph.sh`) but breaks in ralphed projects (ralph-init copies only root-level files, not the `skills/` tree). Default `--block-end-buffer-min 0` hides the bug — the helper is only invoked when the operator opts into the feature, and the helper-missing branch fails open with a warning. But it does mean the time-based-cap feature is shipped half-broken to downstream projects.

The wider observation: R11 parity for `ralph.sh` already costs every change three edits, and the new helper-script coupling makes the "self-contained vendored copy" model partly fictional anyway. If `ralph.sh` is going to depend on the `skills/ralph-run/scripts/` tree, the simplest shape is to have *one* `ralph.sh` that lives in that tree.

## Current state (three-way mirror)

| Path | Role | R11 burden |
|---|---|---|
| `./ralph.sh` | Canonical repo copy; the one run locally during development of this project | mirrored |
| `skills/ralph-init/templates/root/ralph.sh` | Template copied into ralphed projects' repo root at bootstrap | mirrored |
| `skills/ralph-run/scripts/ralph.sh` | User-global copy invoked by `/ralph-run` skill when no project copy exists | mirrored |

The `/ralph-run` skill's `Step 2: Locate ralph.sh` already prefers `./ralph.sh` → `scripts/ralph/ralph.sh` → `~/.claude/skills/ralph-run/scripts/ralph.sh`, so in practice the project copy always wins when present. The user-global copy only runs in fallback. The three copies must stay byte-identical per task-reviewer rule R11.

## Options

### Option A — Full shim collapse (recommended)

Both `./ralph.sh` and `skills/ralph-init/templates/root/ralph.sh` become 3-line shims:

```bash
#!/usr/bin/env bash
exec "$HOME/.claude/skills/ralph-run/scripts/ralph.sh" "$@"
```

Single canonical copy at `~/.claude/skills/ralph-run/scripts/ralph.sh`. R11 burden drops from 3 → 1.

- **Wins**: single source of truth; bug fixes propagate via `/ralph-sync`; the TASK-135 latent bug fixes itself (once `ralph.sh` always runs from the skill dir, `$SCRIPT_DIR/skills/ralph-run/scripts/usage-check.sh` resolves to itself's own directory… *wait — this still doesn't quite work*; see "Open question: $SCRIPT_DIR resolution" below).
- **Losses**: hard dependency on user-global skills install for any ralphed project to function. Bootstrap order matters: `ralph-init` in a fresh project with no user-global skills install yields a shim pointing at nothing.

### Option B — Half-shim (drop template only)

Keep `./ralph.sh` as the canonical in *this* repo (for local development of ralph itself), drop `skills/ralph-init/templates/root/ralph.sh` and replace it with a shim that gets shipped to ralphed projects.

- **Wins**: R11 burden 3 → 2; the new ralphed-project shape matches Option A; *this* repo keeps a full local copy for development convenience.
- **Losses**: still two copies to keep in sync (`./ralph.sh` and `skills/ralph-run/scripts/ralph.sh`); the development-convenience win is marginal — running `./ralph.sh` vs `bash skills/ralph-run/scripts/ralph.sh` is not meaningfully different.

### Option C — Vendor everything via init (more shipping, less coupling)

Keep the three-way mirror AND extend `ralph-init` to also copy the helper scripts (`skills/ralph-run/scripts/*.sh`) into ralphed projects. The bug TASK-135 introduced gets fixed by *shipping more*, not by collapsing.

- **Wins**: ralphed projects fully self-contained; works without user-global skills install; preserves version pinning per-project.
- **Losses**: R11 burden grows (more mirrored paths); ralph-init bootstrap footprint grows; ralphed projects accumulate stale helper scripts unless they re-init.

### Option D — Status quo (do nothing)

Accept that TASK-135's feature is half-shipped to downstream projects until someone files a follow-up.

- **Wins**: zero work.
- **Losses**: `--block-end-buffer-min` silently degrades to fail-open in every ralphed project; R11 burden stays at 3; the architectural question keeps coming back.

## Devcontainer investigation

`.devcontainer/devcontainer.json:43` and the ralph-init template `:43` both have:

```
"source=${localEnv:HOME}/.claude,target=/home/node/.claude,type=bind"
```

Host `~/.claude` is bind-mounted into the container as `/home/node/.claude` (read-write, no `,ro` flag). Inside the container, `$HOME=/home/node`, so the shim's `exec "$HOME/.claude/skills/ralph-run/scripts/ralph.sh"` resolves to `/home/node/.claude/skills/ralph-run/scripts/ralph.sh`, which IS the bind-mounted host script.

The shim works inside the container with no Dockerfile or mount changes.

Confirmed for both this repo and the ralph-init template — R11 parity holds for the devcontainer config too.

## Recommendation

**Option A — Full shim collapse.**

The reasons:

1. R11 burden is the loudest ongoing cost. TASK-135 alone touched all three `ralph.sh` copies for the same 106 lines.
2. The TASK-135 latent bug (helper resolution in ralphed projects) needs *some* fix; Option A's "ralph.sh always runs from `skills/ralph-run/scripts/`" framing is the cleanest answer.
3. Devcontainer is not a blocker.
4. Version pinning loss is theoretical: ralphed projects only sync on explicit `/ralph-sync`, so inaction preserves pinning.

## Open questions / decisions to make

### Bootstrap ordering safeguard

A fresh user who runs `ralph-init` in a new project without first installing user-global skills gets a shim pointing at nothing. Fix shape: `ralph-init` Step X verifies `~/.claude/skills/ralph-run/scripts/ralph.sh` exists, stops with "run /ralph-sync first" if missing.

Decision needed: hard-stop vs warning?

### `$SCRIPT_DIR` resolution after collapse

After Option A, the canonical `ralph.sh` lives at `~/.claude/skills/ralph-run/scripts/ralph.sh`. Its `$SCRIPT_DIR` resolves to `~/.claude/skills/ralph-run/scripts/`, so the line:

```bash
USAGE_CHECK_SCRIPT="${RALPH_USAGE_CHECK_SCRIPT:-$SCRIPT_DIR/skills/ralph-run/scripts/usage-check.sh}"
```

…becomes `~/.claude/skills/ralph-run/scripts/skills/ralph-run/scripts/usage-check.sh` — wrong (double-nested).

The fix is trivial — change the resolution to `$SCRIPT_DIR/usage-check.sh` (helper lives in the same dir). But it has to happen *in the same change* as the shim collapse, otherwise we ship a working shim that breaks the cap feature.

Decision needed: any other `$SCRIPT_DIR`-relative lookups in `ralph.sh` to audit before the shim? (Quick grep: this line is the only one. But the change should re-grep at implementation time.)

### Discoverability comment

Newcomers reading a ralphed project's `ralph.sh` shim should not have to chase. Decision: the shim includes a one-line header comment pointing at the canonical:

```bash
#!/usr/bin/env bash
# Thin shim — the real script lives at ~/.claude/skills/ralph-run/scripts/ralph.sh
# Install/update via `/ralph-sync`.
exec "$HOME/.claude/skills/ralph-run/scripts/ralph.sh" "$@"
```

### task-reviewer R11 rule update

R11 currently enforces three-way parity for `ralph.sh`. After Option A, R11 for `ralph.sh` becomes a one-line shim equivalence check (or simply drops, since there's no longer a "mirror set"). The rules file at `.claude/task-reviewer-rules.md` needs an edit.

Decision: drop the R11 entry for `ralph.sh` entirely, or replace with a shim-equivalence rule?

### `CLAUDE_CONFIG_DIR` corner case

Devcontainer sets `CLAUDE_CONFIG_DIR=/home/node/.claude` as `containerEnv`. The shim uses `$HOME/.claude/...`, not `CLAUDE_CONFIG_DIR`. In the standard devcontainer setup these resolve to the same path. But if a user overrides `CLAUDE_CONFIG_DIR` to point elsewhere, the shim won't follow.

Decision: shim uses `$HOME/.claude/...` (simpler, matches host behavior), or `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/...` (respects override)? Recommend: `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` — three extra characters, handles the corner case for free.

## Out of scope (deliberate)

- **Touching the helper-script vendoring model.** This brainstorm picks shim, not Option C. If we later decide ralphed projects should be fully self-contained, that's a separate redesign.
- **Repointing other R11 mirrors.** The `commit-msg` hook, `task-validator.sh`, etc. have their own parity rules and their own reasons. They're not part of this round.
- **Reworking `/ralph-run`'s `Step 2: Locate ralph.sh`.** Once shim is in place, the skill's resolution order (`./ralph.sh` → `scripts/ralph/ralph.sh` → user-global) still works: `./ralph.sh` is the shim, it execs the user-global. No skill change needed. (Verify at implementation time.)
- **The TASK-136 Unicode NFC normalization task.** Separate concern, separate task.

## Phase 4 — next steps

Decisions above settled → file a backlog task. Likely shape:

- **Title**: `Collapse ralph.sh three-way mirror to thin shim under user-global skill`
- **Label**: `feature:ralph-sh-shim`
- **AC sketch**:
  1. `./ralph.sh` is a ≤5-line shim that `exec`s `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh` with all args
  2. `skills/ralph-init/templates/root/ralph.sh` is the same shim
  3. `skills/ralph-run/scripts/ralph.sh` becomes the canonical full copy (no functional change vs current)
  4. `skills/ralph-run/scripts/ralph.sh:479` (and any other `$SCRIPT_DIR/skills/...` refs) updated to use `$SCRIPT_DIR/usage-check.sh` directly
  5. `ralph-init` Step X verifies `~/.claude/skills/ralph-run/scripts/ralph.sh` exists at bootstrap, errors out with "run /ralph-sync first" if missing
  6. `.claude/task-reviewer-rules.md` R11 entry for `ralph.sh` either dropped or rewritten to "the two project-tree copies are shim-equivalent"
  7. `/ralph-run` skill's `Step 2: Locate ralph.sh` still works (verify by running `/ralph-run` after the change)
  8. Existing `tests/unit/usage-check.bats` and `tests/integration/usage-pause.bats` still pass without modification
  9. README / CLAUDE.md updated if they document the three-way mirror anywhere
  10. New test: `tests/integration/shim.bats` — running the project-root shim produces output indistinguishable from running the canonical script directly

---

## Addendum (2026-06-12): Q2 audit findings + Option A confirmed

### `$SCRIPT_DIR` audit results

`$SCRIPT_DIR` is used for **9 things** in `ralph.sh`. Seven are project-relative paths that must NOT resolve to the user-global skill dir:

| Line | Use | Must resolve to |
|---|---|---|
| 444 | `$SCRIPT_DIR/backlog/.ralph-status.json` | **project** root |
| 450 | `$SCRIPT_DIR/backlog/.ralph-heartbeat` | **project** root |
| 461 | `$SCRIPT_DIR/backlog/.ralph-run.log` | **project** root |
| 480 | `$SCRIPT_DIR/backlog/.ralph-usage-check-disabled` | **project** root |
| 562 | `$SCRIPT_DIR/backlog/.ralph-heartbeat` (dup) | **project** root |
| 609 | `devcontainer up --workspace-folder "$SCRIPT_DIR"` | **project** root |
| 691 | `mkdir -p "$SCRIPT_DIR/backlog"` | **project** root |
| 779 | `devcontainer exec --workspace-folder "$SCRIPT_DIR"` | **project** root |
| 479 | `$SCRIPT_DIR/skills/ralph-run/scripts/usage-check.sh` | helper dir (alongside canonical) |

A naive shim that just `exec`s the canonical from `~/.claude/skills/...` would silently land all 7 project-relative paths under `~/.claude/skills/ralph-run/scripts/backlog/...` — wrong.

The earlier "Open question: $SCRIPT_DIR resolution" section in this brainstorm assumed only one ref existed (line 479). That section is superseded by this addendum.

### Decision: Option A confirmed, with `RALPH_PROJECT_ROOT` env-var override

The shim resolves the project root from its own location and passes it through `RALPH_PROJECT_ROOT`:

```bash
#!/usr/bin/env bash
# Thin shim — the real script lives at ~/.claude/skills/ralph-run/scripts/ralph.sh
# Install/update via /ralph-sync
RALPH_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" \
  exec "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh" "$@"
```

The canonical `ralph.sh` switches the 7 project-artifact paths from `$SCRIPT_DIR` to `${RALPH_PROJECT_ROOT:-$SCRIPT_DIR}`. Line 479 (`usage-check.sh` resolution) simplifies to `$SCRIPT_DIR/usage-check.sh` since the helper now sits alongside the canonical, not under a nested `skills/ralph-run/scripts/` tree.

Standalone mode is preserved: running `bash skills/ralph-run/scripts/ralph.sh` directly (without a shim) keeps `RALPH_PROJECT_ROOT` unset, the fallback `$SCRIPT_DIR` engages, and existing in-repo development continues to work without behavior change.

### What still needs walking

Q1 (bootstrap safeguard), Q3 (shim header comment), Q4 (R11 rule rewrite), Q5 (`CLAUDE_CONFIG_DIR` override — already locked into the shim code above; ratifying via Q5 for the record). Once resolved, the original Phase 4 AC sketch will be rewritten to reflect the env-var-override shape.

---

## Decisions locked (2026-06-12)

- **Q1 — Bootstrap safeguard**: hard-stop. `ralph-init` verifies `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh` exists at bootstrap; errors with "install user-global skills first via /ralph-sync, then re-run ralph-init" and exits non-zero if missing.
- **Q2 — Shape**: env-var override via `RALPH_PROJECT_ROOT`, already specified above.
- **Q3 — Shim header**: short 1-2 line comment pointing at canonical + mentioning `/ralph-sync`.
- **Q4 — R11 rule**: rewrite as shim-equivalence — the two shim copies (`./ralph.sh` and `skills/ralph-init/templates/root/ralph.sh`) must be byte-identical to each other. Canonical `skills/ralph-run/scripts/ralph.sh` excluded from the mirror set.
- **Q5 — `CLAUDE_CONFIG_DIR`**: shim uses `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh` (already in the shim code above).

### Final shim shape

Identical content at `./ralph.sh` and `skills/ralph-init/templates/root/ralph.sh`:

```bash
#!/usr/bin/env bash
# Thin shim — the real script lives at ~/.claude/skills/ralph-run/scripts/ralph.sh
# Install/update via /ralph-sync
RALPH_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" \
  exec "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh" "$@"
```

### Phase 4 — final AC sketch (supersedes the original at top of brainstorm)

For the implementer task. Title: `Collapse ralph.sh three-way mirror to thin shim under user-global skill`. Label: `feature:ralph-sh-shim`.

1. **Shim files**: `./ralph.sh` and `skills/ralph-init/templates/root/ralph.sh` are the exact 5-line shim above (header comment + `RALPH_PROJECT_ROOT` + `exec`). Verifiable: `diff ralph.sh skills/ralph-init/templates/root/ralph.sh` produces no output.
2. **Canonical `ralph.sh` refactor**: in `skills/ralph-run/scripts/ralph.sh`, the 7 project-artifact references (lines 444, 450, 461, 480, 562, 609, 691, 779) switch from `$SCRIPT_DIR` to `${RALPH_PROJECT_ROOT:-$SCRIPT_DIR}`. Line 479's helper-script resolution simplifies to `$SCRIPT_DIR/usage-check.sh`.
3. **Path resolution works in both modes**: standalone (`bash skills/ralph-run/scripts/ralph.sh` from any cwd) writes `backlog/` artifacts next to the canonical via `$SCRIPT_DIR` fallback; shim-via-cwd (`./ralph.sh` from a project root) writes `backlog/` artifacts in that project root via `RALPH_PROJECT_ROOT`. Both verifiable by file-location asserts.
4. **`ralph-init` bootstrap check**: ralph-init verifies `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh` exists before writing the shim; hard-stops with the locked error message if missing. AC pass: simulate the file's absence (temporary rename), run ralph-init in a temp dir, observe stop + exit-nonzero.
5. **R11 rule rewrite**: `.claude/task-reviewer-rules.md` R11 entry for `ralph.sh` rewritten to require byte-equality between the two shim copies only. Canonical excluded.
6. **`/ralph-run` skill works end-to-end**: a full `/ralph-run` iteration in this repo invokes the shim, execs the canonical, and writes `.ralph-status.json` to project `backlog/` (not under `~/.claude/skills/...`). Verifiable post-run.
7. **Existing TASK-135 tests still pass without modification**: `tests/unit/usage-check.bats` (12 cases) and `tests/integration/usage-pause.bats` (5 cases) green.
8. **New shim smoke test**: `tests/integration/shim.bats` — `./ralph.sh --help` and `bash skills/ralph-run/scripts/ralph.sh --help` produce identical stdout/stderr/exit code.
9. **Docs**: README and any CLAUDE.md mention of the "three-way ralph.sh mirror" rewritten to reflect the new shape, including the `/ralph-run` skill's Step 2 if it documents the resolution order.
