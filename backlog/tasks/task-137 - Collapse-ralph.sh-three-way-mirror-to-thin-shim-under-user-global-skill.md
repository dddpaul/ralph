---
id: TASK-137
title: Collapse ralph.sh three-way mirror to thin shim under user-global skill
status: Done
assignee: []
created_date: '2026-06-12 10:15'
updated_date: '2026-06-12 11:01'
labels:
  - 'feature:ralph-sh-shim'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Why:** drop the R11 burden of keeping three byte-identical copies of `ralph.sh` (canonical at `./ralph.sh`, template at `skills/ralph-init/templates/root/ralph.sh`, user-global at `skills/ralph-run/scripts/ralph.sh`). The shim model collapses the mirror to a single canonical at the user-global skill location, with thin shims at the two project-tree sites that pass the project root through `RALPH_PROJECT_ROOT` before exec. Same change fixes the latent TASK-135 bug where `$SCRIPT_DIR/skills/ralph-run/scripts/usage-check.sh` resolution fails in ralphed projects (the `skills/` tree is not shipped via `ralph-init`).

**Design & decisions:** see `design/ralph-sh-shim-brainstorm.md` — final shim shape, locked decisions for Q1 through Q5, and the audit table of all 9 \$SCRIPT_DIR usages in ralph.sh.

**Shim content (identical at `./ralph.sh` and `skills/ralph-init/templates/root/ralph.sh`):**

\`\`\`bash
#\!/usr/bin/env bash
# Thin shim — the real script lives at ~/.claude/skills/ralph-run/scripts/ralph.sh
# Install/update via /ralph-sync
RALPH_PROJECT_ROOT="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd -P)" \\
  exec "\${CLAUDE_CONFIG_DIR:-\$HOME/.claude}/skills/ralph-run/scripts/ralph.sh" "\$@"
\`\`\`

**Canonical refactor** (in `skills/ralph-run/scripts/ralph.sh`): lines 444, 450, 461, 480, 562, 609, 691, 779 switch from \$SCRIPT_DIR to \${RALPH_PROJECT_ROOT:-\$SCRIPT_DIR}. Line 479 simplifies to \$SCRIPT_DIR/usage-check.sh because the helper now sits alongside the canonical, not under a nested skills/ralph-run/scripts/ tree.

**Bootstrap safeguard:** `ralph-init` verifies the canonical exists at `\${CLAUDE_CONFIG_DIR:-\$HOME/.claude}/skills/ralph-run/scripts/ralph.sh`; hard-stops with "install user-global skills first via /ralph-sync, then re-run ralph-init" if missing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ./ralph.sh and skills/ralph-init/templates/root/ralph.sh are byte-identical 5-line shims (header comment + RALPH_PROJECT_ROOT export + exec); diff of the two produces no output
- [x] #2 skills/ralph-run/scripts/ralph.sh lines 444, 450, 461, 480, 562, 609, 691, 779 reference ${RALPH_PROJECT_ROOT:-$SCRIPT_DIR} instead of bare $SCRIPT_DIR; line 479 simplifies to $SCRIPT_DIR/usage-check.sh
- [x] #3 Path resolution standalone mode: invoking the canonical via absolute path from /tmp (bash <abs>/skills/ralph-run/scripts/ralph.sh) writes backlog/.ralph-status.json next to the canonical script via $SCRIPT_DIR fallback
- [x] #4 Path resolution shim-via-cwd mode: invoking ./ralph.sh from a project root writes backlog/.ralph-status.json in that project root via RALPH_PROJECT_ROOT
- [x] #5 ralph-init verifies ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh exists before writing the shim; hard-stops with 'install user-global skills first via /ralph-sync, then re-run ralph-init' and exits non-zero if missing (verify by temporary rename of the canonical and re-running ralph-init in a temp dir)
- [x] #6 .claude/task-reviewer-rules.md R11 entry for ralph.sh rewritten to require byte-equality between the two shim copies only (canonical at skills/ralph-run/scripts/ralph.sh excluded from the mirror set)
- [x] #7 Full /ralph-run iteration in this repo invokes the shim, execs the canonical, and writes .ralph-status.json to project backlog/ (not under ~/.claude/skills/...)
- [x] #8 Existing tests/unit/usage-check.bats (12 cases) and tests/integration/usage-pause.bats (5 cases) pass without modification
- [x] #9 New shim smoke test asserts ./ralph.sh --help and bash skills/ralph-run/scripts/ralph.sh --help produce identical stdout, stderr, and exit code
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. Refactor canonical at skills/ralph-run/scripts/ralph.sh: replace bare $SCRIPT_DIR with ${RALPH_PROJECT_ROOT:-$SCRIPT_DIR} at lines 444, 450, 461, 480, 562, 609, 691, 779; simplify line 479 to $SCRIPT_DIR/usage-check.sh.
2. Replace ./ralph.sh and skills/ralph-init/templates/root/ralph.sh with the locked 5-line shim (header + RALPH_PROJECT_ROOT export + exec).
3. Add ralph-init bootstrap safeguard: verify canonical exists at ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts/ralph.sh; hard-stop with 'install user-global skills first via /ralph-sync, then re-run ralph-init' and exit non-zero.
4. Rewrite R11 rule in .claude/task-reviewer-rules.md to require byte-equality between the two shim copies only.
5. Add tests/integration/shim.bats — asserts ./ralph.sh --help matches bash skills/ralph-run/scripts/ralph.sh --help in stdout/stderr/exit code.
6. Run existing bats: tests/unit/usage-check.bats (12) + tests/integration/usage-pause.bats (5). Confirm new shim.bats passes.
7. Manually verify path-resolution modes (standalone via /tmp, shim-via-cwd).
8. Task-reviewer agent → APPROVED → merge.

Commit: `f794e6b` - task-137: Collapse ralph.sh three-way mirror to thin shim

Done. task-reviewer APPROVED — all 9 AC verified, R1-R15 pass.
Pre-existing flake: tests/integration/timeout-handling.bats 'Temp file cleaned up on timeout' fails ~50% on both baseline and task-137 branch — unrelated to this change.
<!-- SECTION:NOTES:END -->
