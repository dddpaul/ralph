# task-reviewer Custom Rules

These rules SUPPLEMENT the standard 8-item checklist in the task-reviewer agent (`plugins/ralph/agents/task-reviewer.md` or `~/.claude/agents/task-reviewer.md`). They do not replace it. Apply both. All rules use strict prohibitive language: violations are review failures, not suggestions.

The review-conduct rules that used to be R1, R2, R9, R13, R14, R16 and R17 now ship as built-in rules in the agent itself, so they apply in every project — in `plugins/ralph/agents/task-reviewer.md`: R1 and R9 → `R-CORE-1`, R2 → `R-CORE-2`, R13 → `R-CORE-3`, R14 → `R-CORE-4`, R16 → `R-CORE-5`, R17 → `R-CORE-6`. The infrastructure rules that used to be R3, R4, R5, R6, R8, R10 and R15 cover files ralph-init installs in every project, so they now ship as the plugin's shared infra bundle — `plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md`, which the agent loads here because this repository has `ralph.sh` at its root: R3 → `R-INFRA-1`, R4 → `R-INFRA-2`, R5 → `R-INFRA-3`, R6 → `R-INFRA-4`, R8 → `R-INFRA-5`, R10 → `R-INFRA-6`, R15 → `R-INFRA-7`.

Their numbers are retired, not reused: the remaining rules keep their IDs, because task notes and docs cite them.

---

## R7 — No AI-attribution trailers in commits

Commit messages, PR bodies, and any template that generates commit messages MUST NOT contain:

- `Co-Authored-By: Claude` (or any AI-attributed `Co-Authored-By:`)
- `Co-Authored-By: Happy`
- `Generated with [Claude Code]` / `Generated with Claude Code`
- `via [Happy]` / `via Happy`
- `🤖 Generated with` or any emoji-prefixed AI attribution

The `commit-msg-guard.sh` hook is the first line of defense. The reviewer is the second: any diff that introduces such a trailer (in a script, prompt, or template) MUST be rejected.

## R11 — Template parity

The Ralph project ships a template tree at `plugins/ralph/skills/ralph-init/templates/` that is intended to mirror the live project's bootstrap state. Drift between live files and templates is a defect. The reviewer MUST flag any diff that touches one side of these pairs without a corresponding change on the other side (unless the task description explicitly calls out a one-sided change with a justification):

| Live path                              | Template path                                                       |
|----------------------------------------|----------------------------------------------------------------------|
| `.claude/settings.json`                | `plugins/ralph/skills/ralph-init/templates/claude/settings.json`                   |
| `.claude/settings.local.json`          | `plugins/ralph/skills/ralph-init/templates/claude/settings.local.json`             |
| `.claude/hooks/<name>.sh`              | `plugins/ralph/skills/ralph-init/templates/claude/hooks/<name>.sh`                 |
| `ralph.sh` (thin shim)                 | `plugins/ralph/skills/ralph-init/templates/root/ralph.sh` (thin shim)              |
| `refine.sh` (thin shim)                | `plugins/ralph/skills/ralph-init/templates/root/refine.sh` (thin shim)             |
| `CLAUDE.md` (generic section above `## Project-Specific`) | `plugins/ralph/skills/ralph-init/templates/root/CLAUDE.md` (same region) |
| `.git/hooks/post-commit`               | `plugins/ralph/skills/ralph-init/templates/git-hooks/post-commit`                  |
| `.git/hooks/commit-msg`                | `plugins/ralph/skills/ralph-init/templates/git-hooks/commit-msg`                   |
| `.devcontainer/devcontainer.json`      | `plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json`         |
| `.devcontainer/container-settings.local.json` | `plugins/ralph/skills/ralph-init/templates/devcontainer/container-settings.local.json` |
| `.devcontainer/init-firewall.sh`       | `plugins/ralph/skills/ralph-init/templates/devcontainer/init-firewall.sh`          |

Note on `ralph.sh` and `refine.sh`: the parity rule covers only the thin shim copies above, which each carry an orchestrator resolver (`ralph.sh`: `$RALPH_ORCHESTRATOR` override or the newest installed plugin-cache copy, simplified from five tiers in TASK-212; `refine.sh`: a 5-tier resolver — see `design/ralph-marketplace-prd.md` US-004 and `design/ralph-refine-prd.md` US-006) and exec the resolved orchestrator via `uv run "$ORCHESTRATOR"`. `ralph.sh` resolves `ralph_orchestrator.py`; `refine.sh` resolves `refine_orchestrator.py`. The canonical orchestrators at `plugins/ralph/skills/ralph-run/scripts/{ralph,refine}_orchestrator.py` (plus the `ralph/` package) are the single source of truth and are intentionally excluded from this mirror set — the two copies of each shim must remain byte-identical to their own template (a `diff` of the two MUST produce no output), but neither needs to match the canonical, and the two shims (`ralph.sh` vs `refine.sh`) are NOT required to match each other. Because the resolver logic lives in each shim itself, any change to it MUST land in both copies of that shim (keeping them byte-identical); a change to a canonical orchestrator does NOT trigger a parity finding.

Note on `CLAUDE.md`: the `## Project-Specific` section is intentionally project-local and is NOT part of the parity rule. Only the generic section above that heading is mirrored.

**Excluded from parity (project-specific):** `.claude/task-reviewer-rules.md` is project-specific content — each project bootstrapped via ralph-init writes its own rules from scratch (or starts without any). The loading mechanism in the task-reviewer agent is templated; the rules content is not. Do NOT flag the absence of a template mirror for this file.

**Excluded from parity (plugin-bundled distribution):** the two agents under `plugins/ralph/agents/` ship inside the `ralph` plugin and are distributed via `/plugin install`, not copied into a project. ralph-init does NOT mirror them into project-local `.claude/agents/` and there is NO template under `plugins/ralph/skills/ralph-init/templates/claude/agents/`. Do NOT flag the absence of a template mirror for agent files.

## R12 — Markdown deliverables must be logically consistent

For tasks whose deliverable is a markdown document (architecture docs, plans, specs, design notes, READMEs, agent prompts, custom-rules files), the reviewer MUST evaluate the document content — not just its structural placement. The deliverable MUST satisfy:

- **Non-contradiction:** no section may contradict another section of the same document, nor any other document the task explicitly relies on.
- **AC traceability:** every acceptance criterion in the task MUST map to a concrete section, paragraph, or rule in the deliverable that satisfies it.
- **Logical completeness:** no dangling references, no `TBD` / `TODO` placeholders, no half-finished arguments, no rules introduced and never explained.
- **Cross-reference resolution:** every "see X above," "as in section Y," or anchor-style reference MUST resolve to a real, present section.

The reviewer MUST reject the diff if the markdown deliverable contradicts itself, leaves an AC untraceable, or contains unresolved gaps. Stylistic polish is out of scope; logical integrity is in scope.

