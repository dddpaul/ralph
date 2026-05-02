# task-reviewer Custom Rules

These rules SUPPLEMENT the standard 8-item checklist in `.claude/agents/task-reviewer.md`. They do not replace it. Apply both. All rules use strict prohibitive language: violations are review failures, not suggestions.

---

## R1 — Review the diff, not the working tree

The source of truth for review is `git diff master..HEAD`. The reviewer MUST NOT base findings on `ls`, `find`, or any working-tree read. The working tree may contain ignored files, untracked artifacts, or copies of files that have been deleted from git but not from disk. A finding rooted in working-tree state — when the file is not present in the diff — is invalid and MUST be discarded.

To confirm a file's presence in the project: `git ls-files <path>`. To check its history: `git log --all -- <path>`.

## R2 — Every AC must be checked or explicitly deferred

A task bound for "Done" MUST have every acceptance criterion either:
- checked off (`- [x]`), or
- explicitly marked deferred in the task notes with a stated reason and a follow-up plan.

Silent unchecked ACs are a hard fail. The reviewer MUST cross-reference each AC against the diff and flag any that the implementer did not address. If an AC is impossible to verify in the current session (e.g. requires a fresh process — see R4), the deferral and its reason MUST appear in the task notes before "Done" is set.

## R3 — Agent files require valid YAML frontmatter

Any change that creates or modifies a file under `.claude/agents/` (or its template mirror under `skills/ralph-init/templates/claude/agents/`) MUST include valid YAML frontmatter at the top of the file with at least:

```yaml
---
name: <filename-stem>      # MUST match the filename without .md
description: <one-line>    # used by Claude Code to route subagent_type
---
```

Without frontmatter, `subagent_type=<name>` is never registered in the Agent enum and any caller silently falls back to `general-purpose`. The reviewer MUST reject any agent file lacking frontmatter, even if the rest of the prompt body is well-formed.

## R4 — Frontmatter changes do not take effect mid-session

The Agent enum is fixed at session start. If the diff adds or modifies frontmatter under `.claude/agents/*.md`, any AC of the form "verify the agent is callable as `subagent_type=...`" MUST be marked deferred to a fresh session in the task notes. The reviewer MUST NOT accept claims of mid-session verification for newly-registered subagent types.

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

## R9 — Git is the truth, not the working tree

When confirming a file's existence, history, or content in the project, the reviewer MUST use `git ls-files <path>`, `git log --all -- <path>`, and `git show <ref>:<path>`. The reviewer MUST NOT rely on `ls`, `find`, or `cat` of the working tree to make claims about what the project contains. Working-tree state can include ignored files, untracked host artifacts, and ghost copies of git-deleted files; none of these are part of the project.

## R10 — Do not bypass `master-branch-guard.sh`

Edit/Write to any path outside `.claude/` requires a `task-*` branch. The `master-branch-guard.sh` hook enforces this. The reviewer MUST reject any diff or commit that:

- was committed directly to `master` and touches files outside `.claude/`
- used `dangerouslyDisableSandbox: true` to bypass the master-branch guard
- was created by disabling, renaming, or temporarily removing the guard hook

The correct workflow is `git checkout -b task-N` BEFORE the first edit. Sandbox bypass is reserved for tools that the sandbox blocks for unrelated reasons (e.g. `nohup`, `mktemp` in `/tmp`), never for circumventing project hooks.

## R11 — Template parity

The Ralph project ships a template tree at `skills/ralph-init/templates/` that is intended to mirror the live project's bootstrap state. Drift between live files and templates is a defect. The reviewer MUST flag any diff that touches one side of these pairs without a corresponding change on the other side (unless the task description explicitly calls out a one-sided change with a justification):

| Live path                              | Template path                                                       |
|----------------------------------------|----------------------------------------------------------------------|
| `.claude/settings.json`                | `skills/ralph-init/templates/claude/settings.json`                   |
| `.claude/settings.local.json`          | `skills/ralph-init/templates/claude/settings.local.json`             |
| `.claude/hooks/<name>.sh`              | `skills/ralph-init/templates/claude/hooks/<name>.sh`                 |
| `.claude/agents/<name>.md`             | `skills/ralph-init/templates/claude/agents/<name>.md`                |
| `ralph.sh`                             | `skills/ralph-init/templates/root/ralph.sh`                          |
| `CLAUDE.md` (generic section above `## Project-Specific`) | `skills/ralph-init/templates/root/CLAUDE.md` (same region) |
| `.git/hooks/post-commit`               | `skills/ralph-init/templates/git-hooks/post-commit`                  |
| `.git/hooks/commit-msg`                | `skills/ralph-init/templates/git-hooks/commit-msg`                   |
| `.devcontainer/devcontainer.json`      | `skills/ralph-init/templates/devcontainer/devcontainer.json`         |
| `.devcontainer/init-firewall.sh`       | `skills/ralph-init/templates/devcontainer/init-firewall.sh`          |

Note on `CLAUDE.md`: the `## Project-Specific` section is intentionally project-local and is NOT part of the parity rule. Only the generic section above that heading is mirrored.

**Excluded from parity (project-specific):** `.claude/task-reviewer-rules.md` is project-specific content — each project bootstrapped via ralph-init writes its own rules from scratch (or starts without any). The loading mechanism in `task-reviewer.md` is templated; the rules content is not. Do NOT flag the absence of a template mirror for this file.

## R12 — Markdown deliverables must be logically consistent

For tasks whose deliverable is a markdown document (architecture docs, plans, specs, design notes, READMEs, agent prompts, custom-rules files), the reviewer MUST evaluate the document content — not just its structural placement. The deliverable MUST satisfy:

- **Non-contradiction:** no section may contradict another section of the same document, nor any other document the task explicitly relies on.
- **AC traceability:** every acceptance criterion in the task MUST map to a concrete section, paragraph, or rule in the deliverable that satisfies it.
- **Logical completeness:** no dangling references, no `TBD` / `TODO` placeholders, no half-finished arguments, no rules introduced and never explained.
- **Cross-reference resolution:** every "see X above," "as in section Y," or anchor-style reference MUST resolve to a real, present section.

The reviewer MUST reject the diff if the markdown deliverable contradicts itself, leaves an AC untraceable, or contains unresolved gaps. Stylistic polish is out of scope; logical integrity is in scope.
