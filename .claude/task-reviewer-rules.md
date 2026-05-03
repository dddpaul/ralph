# task-reviewer Custom Rules

These rules SUPPLEMENT the standard 8-item checklist in the task-reviewer agent (`agents/task-reviewer.md` or `~/.claude/agents/task-reviewer.md`). They do not replace it. Apply both. All rules use strict prohibitive language: violations are review failures, not suggestions.

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
| `ralph.sh`                             | `skills/ralph-init/templates/root/ralph.sh`                          |
| `CLAUDE.md` (generic section above `## Project-Specific`) | `skills/ralph-init/templates/root/CLAUDE.md` (same region) |
| `.git/hooks/post-commit`               | `skills/ralph-init/templates/git-hooks/post-commit`                  |
| `.git/hooks/commit-msg`                | `skills/ralph-init/templates/git-hooks/commit-msg`                   |
| `.devcontainer/devcontainer.json`      | `skills/ralph-init/templates/devcontainer/devcontainer.json`         |
| `.devcontainer/init-firewall.sh`       | `skills/ralph-init/templates/devcontainer/init-firewall.sh`          |

Note on `CLAUDE.md`: the `## Project-Specific` section is intentionally project-local and is NOT part of the parity rule. Only the generic section above that heading is mirrored.

**Excluded from parity (project-specific):** `.claude/task-reviewer-rules.md` is project-specific content — each project bootstrapped via ralph-init writes its own rules from scratch (or starts without any). The loading mechanism in the task-reviewer agent is templated; the rules content is not. Do NOT flag the absence of a template mirror for this file.

**Excluded from parity (user-global distribution):** files under `agents/` are user-global content distributed manually; the user copies them to `~/.claude/agents/`, the same way they copy `skills/*` to `~/.claude/skills/`. ralph-init does NOT mirror these into project-local `.claude/agents/` and there is NO template under `skills/ralph-init/templates/claude/agents/`. Do NOT flag the absence of a template mirror for agent files.

## R12 — Markdown deliverables must be logically consistent

For tasks whose deliverable is a markdown document (architecture docs, plans, specs, design notes, READMEs, agent prompts, custom-rules files), the reviewer MUST evaluate the document content — not just its structural placement. The deliverable MUST satisfy:

- **Non-contradiction:** no section may contradict another section of the same document, nor any other document the task explicitly relies on.
- **AC traceability:** every acceptance criterion in the task MUST map to a concrete section, paragraph, or rule in the deliverable that satisfies it.
- **Logical completeness:** no dangling references, no `TBD` / `TODO` placeholders, no half-finished arguments, no rules introduced and never explained.
- **Cross-reference resolution:** every "see X above," "as in section Y," or anchor-style reference MUST resolve to a real, present section.

The reviewer MUST reject the diff if the markdown deliverable contradicts itself, leaves an AC untraceable, or contains unresolved gaps. Stylistic polish is out of scope; logical integrity is in scope.

## R13 — Rationalization is not exemption

The reviewer MUST apply rules R1–R14 strictly. Task description, implementation notes, commit messages, and design narrative MUST NOT be treated as overriding a rule violation. If the diff violates a rule, the diff is rejected — even when the implementer claims the violation is intentional, by design, or pre-approved.

The following excuses are **automatically rejected** when invoked to justify a rule violation:

- *"intentional per design"*
- *"pre-existing, not a new change"* (a file being modified is in scope; staleness inherited from prior commits is the right thing to fix during the modification)
- *"users will fix when copying"* / *"users add it manually later"*
- *"not in scope for this task"* (if the diff touches the file, the file's compliance is in scope)
- *"by convention"* / *"matches existing pattern"* (a violation propagated by prior commits is still a violation)
- *"the prior reviewer accepted this"*

The ONLY legitimate way to relax a rule is to amend `.claude/task-reviewer-rules.md` itself via a separate task with explicit user approval. Until the rules file changes, the rules apply as written.

This rule exists because TASK-92 shipped two defects that the reviewer waved through after accepting Ralph's post-hoc rationalizations — both verbatim from the above list. Future reviewers MUST apply the rules first and read narrative second.

## R14 — Content preservation during moves

When a file is moved or renamed via `git mv`, its content MUST be preserved verbatim unless the task explicitly authorizes content changes in its description or acceptance criteria. The reviewer MUST verify rename diffs show `similarity index 100%` (or near-100% with the deviation explicitly authorized by an AC).

Forbidden during a move (without explicit AC authorization):

- Stripping frontmatter
- Adding frontmatter
- Updating import paths or `cat`/`source` references
- Fixing typos
- Reformatting whitespace
- Renaming internal symbols
- Updating cross-references in the file's body
- Any other in-flight content edit "while we're at it"

If both a move AND content changes are needed, the task SHOULD describe both in its description and ACs (e.g. "AC #N: agents/foo.md uses the new path X for the user-global fallback"). Otherwise, the move is one commit and the content change is a separate commit on the same branch — never bundled silently. The reviewer MUST reject any rename diff with content drift that is not explicitly authorized.

This rule exists because TASK-92's `git mv .claude/agents/task-reviewer.md → agents/task-reviewer.md` silently stripped the frontmatter and left a stale path inside the file. A 100%-similarity move would have caught both.
