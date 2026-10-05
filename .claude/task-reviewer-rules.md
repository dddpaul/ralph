# task-reviewer Custom Rules

These rules SUPPLEMENT the standard 8-item checklist in the task-reviewer agent (`plugins/ralph/agents/task-reviewer.md` or `~/.claude/agents/task-reviewer.md`). They do not replace it. Apply both. All rules use strict prohibitive language: violations are review failures, not suggestions.

The review-conduct rules that used to be R1, R2, R9, R13, R14, R16 and R17 now ship as built-in rules in the agent itself, so they apply in every project — in `plugins/ralph/agents/task-reviewer.md`: R1 and R9 → `R-CORE-1`, R2 → `R-CORE-2`, R13 → `R-CORE-3`, R14 → `R-CORE-4`, R16 → `R-CORE-5`, R17 → `R-CORE-6`. Their numbers are retired, not reused: the remaining rules keep their IDs, because task notes and docs cite them.

---

## R3 — Agent files require valid YAML frontmatter

Any change that creates or modifies a file under `agents/` (top-level), `.claude/agents/` (project-local), or `~/.claude/agents/` (user-global) MUST include valid YAML frontmatter at the top of the file with at least:

```yaml
---
name: <filename-stem>      # MUST match the filename without .md
description: <one-line>    # used by Claude Code to route subagent_type
---
```

Without frontmatter, `subagent_type=<name>` is never registered in the Agent enum and any caller silently falls back to `general-purpose`. The reviewer MUST reject any agent file lacking frontmatter, even if the rest of the prompt body is well-formed.

**No exception applies for files being moved, renamed, or refactored** — `git mv` preserves content, and the post-move file is still an agent file under R3's scope. Task notes, commit messages, or design narrative claiming *"frontmatter added by user later"*, *"intentional omission"*, *"frontmatter optional in distribution form"*, or similar MUST NOT be accepted as exceptions. The frontmatter MUST be present in the post-diff file, period. (TASK-92 shipped without frontmatter behind the rationale "users add frontmatter when copying" — that is exactly the kind of post-hoc excuse this clause forbids.)

## R4 — Frontmatter changes do not take effect mid-session

The Agent enum is fixed at session start. If the diff adds or modifies frontmatter under `agents/*.md`, `.claude/agents/*.md`, or `~/.claude/agents/*.md`, any AC of the form "verify the agent is callable as `subagent_type=...`" MUST be marked deferred to a fresh session in the task notes. The reviewer MUST NOT accept claims of mid-session verification for newly-registered subagent types.

## R5 — Shell scripts must work on both GNU and BSD tools

Scripts under `.claude/hooks/`, `scripts/`, `skills/*/scripts/`, and `ralph.sh` run on both macOS (BSD coreutils) and Linux/devcontainer (GNU coreutils). The reviewer MUST flag known incompatibilities, including but not limited to:

- BRE-vs-ERE alternation in `sed` / `grep` without `-E`
- `sed -i` without an empty-string argument (BSD requires `sed -i ''`, GNU requires `sed -i`)
- `date -d ...` (GNU only) or `date -j ...` (BSD only) without a portable fallback
- `grep -P` / PCRE features (not available on BSD)
- `mktemp` template differences (`-t` semantics differ)
- `find -regex` argument ordering (BSD silently skips longer alternatives placed second; longest must come first)
- `readlink -f` (GNU only)
- `xargs -r` (GNU only)

When in doubt, prefer POSIX-compliant constructs.

## R6 — No over-broad shell permission rules

`.claude/settings.local.json` MUST NOT grant broad shell permissions. The following patterns are forbidden:

- `Bash(bash:*)`
- `Bash(sh:*)`
- `Bash(*)`
- Any rule of the form `Bash(<interpreter>:*)` where `<interpreter>` can execute arbitrary code

The reviewer MUST require narrow rules of the form `Bash(bash <absolute-script-path>:*)`. If a single permission prompt is annoying, the fix is to extract the inline blob into a script and add a narrow allowlist entry — NOT to widen the allowlist.

## R7 — No AI-attribution trailers in commits

Commit messages, PR bodies, and any template that generates commit messages MUST NOT contain:

- `Co-Authored-By: Claude` (or any AI-attributed `Co-Authored-By:`)
- `Co-Authored-By: Happy`
- `Generated with [Claude Code]` / `Generated with Claude Code`
- `via [Happy]` / `via Happy`
- `🤖 Generated with` or any emoji-prefixed AI attribution

The `commit-msg-guard.sh` hook is the first line of defense. The reviewer is the second: any diff that introduces such a trailer (in a script, prompt, or template) MUST be rejected.

## R8 — Hook commands reference scripts, not inline bash

Entries in `.claude/settings.json` under `hooks.<event>.<n>.hooks[].command` MUST point to a `.claude/hooks/<name>.sh` script. Inline bash blobs (multi-line strings, `bash -c "..."`, piped one-liners) are forbidden. The `if:` clause is the gate; the script is the implementation. One approach throughout the file. The reviewer MUST flag any inline command longer than a single script path.

## R10 — Do not bypass `master-branch-guard.sh`

Edit/Write to any path outside `.claude/` requires a `task-*` branch. The `master-branch-guard.sh` hook enforces this. The reviewer MUST reject any diff or commit that:

- was committed directly to `master` and touches files outside `.claude/`
- used `dangerouslyDisableSandbox: true` to bypass the master-branch guard
- was created by disabling, renaming, or temporarily removing the guard hook

The correct workflow is `git checkout -b task-N` BEFORE the first edit. Sandbox bypass is reserved for tools that the sandbox blocks for unrelated reasons (e.g. `nohup`, `mktemp` in `/tmp`), never for circumventing project hooks.

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

## R15 — PostToolUse hooks must emit JSON via hookSpecificOutput

Hooks registered under `PostToolUse` in `.claude/settings.json` that need to deliver model-visible feedback MUST emit a single JSON object on stdout with the structure:

```json
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"<text>"}}
```

Raw stdout text — including text wrapped in `<system-reminder>` tags — is silently dropped by the Claude Code harness and never reaches the model. The reviewer MUST reject any PostToolUse hook that uses `printf`, `echo`, or any other mechanism to emit raw text intended for the model, even if the text is correctly formatted as XML tags.

When a hook has multiple feedback sections (e.g. deterministic issues AND an LLM rubric), it MUST combine them into a single `additionalContext` string separated by blank lines — not emit multiple JSON objects. The harness parses exactly one JSON object per hook invocation.

This rule exists because TASK-100 wrapped validator output in `<system-reminder>` tags (correct format) but emitted them as raw stdout (wrong protocol). The model never received the feedback, and the smoke test only verified the script's stdout — not model receipt.
