# Task reviewer rules (ralph-init infrastructure)

<!-- Shipped with the ralph plugin: the task-reviewer agent reads these rules from the plugin and ralph-init does not copy them into projects; project rules belong in .claude/task-reviewer-rules.md, which ralph-init never touches. They cover the files ralph-init installs in every project it scaffolds: agents, hooks, settings and shell scripts. A project rule that names a rule ID from this file (for example "replaces R-INFRA-3") overrides that rule. -->

## R-INFRA-1: Agent files require valid YAML frontmatter

Any change that creates or modifies a file under `agents/` (top-level or inside a plugin), `.claude/agents/` (project-local), or `~/.claude/agents/` (user-global) MUST include valid YAML frontmatter at the top of the file with at least:

```yaml
---
name: <filename-stem>      # MUST match the filename without .md
description: <one-line>    # used by Claude Code to route subagent_type
---
```

Without frontmatter, `subagent_type=<name>` is never registered in the Agent enum and any caller silently falls back to `general-purpose`. The reviewer MUST reject any agent file lacking frontmatter, even if the rest of the prompt body is well-formed.

**No exception applies for files being moved, renamed, or refactored** — `git mv` preserves content, and the post-move file is still an agent file under this rule's scope. Task notes, commit messages, or design narrative claiming *"frontmatter added by user later"*, *"intentional omission"*, *"frontmatter optional in distribution form"*, *"users add frontmatter when copying"*, or similar MUST NOT be accepted as exceptions. The frontmatter MUST be present in the post-diff file, period.

## R-INFRA-2: Frontmatter changes do not take effect mid-session

The Agent enum is fixed at session start. If the diff adds or modifies frontmatter under `agents/*.md`, `.claude/agents/*.md`, or `~/.claude/agents/*.md`, any AC of the form "verify the agent is callable as `subagent_type=...`" MUST be marked deferred to a fresh session in the task notes. The reviewer MUST NOT accept claims of mid-session verification for newly-registered subagent types.

## R-INFRA-3: Shell scripts must work on both GNU and BSD tools and parse under bash 3.2

Scripts under `.claude/hooks/`, `scripts/`, `skills/*/scripts/`, and `ralph.sh` run on both macOS (BSD userland) and Linux/devcontainer (GNU userland). The reviewer MUST flag known incompatibilities, including but not limited to:

- BRE-vs-ERE alternation in `sed` / `grep` without `-E`
- `sed -i` without an empty-string argument (BSD requires `sed -i ''`, GNU requires `sed -i`)
- `date -d ...` (GNU only) or `date -j ...` (BSD only) without a portable fallback
- `grep -P` / PCRE features (not available on BSD)
- `mktemp` template differences (`-t` semantics differ)
- `find -regex` argument ordering (BSD silently skips longer alternatives placed second; longest must come first)
- `readlink -f` (GNU only)
- `xargs -r` (GNU only)

macOS system bash is GNU bash 3.2 (`/bin/bash`), and a `bash` resolved through PATH on a default Mac is that 3.2, so every script MUST also parse under it. The Linux devcontainer runs bash 5 and cannot see a 3.2-only syntax error, so the reviewer MUST flag bash 4+ syntax, including but not limited to:

- a case pattern without the leading `(` inside `$( ... )` — bash 3.2 reads its `)` as the end of the substitution; write `(pattern)` or move the loop into a function
- associative arrays (`declare -A`), `mapfile` / `readarray`, `${var,,}` / `${var^^}` case conversion, `;&` / `;;&` case fall-through, `|&`, `&>>`, and `coproc`

On a Mac, `/bin/bash -n <script>` checks a script against bash 3.2.

When in doubt, prefer POSIX-compliant constructs.

## R-INFRA-4: No over-broad shell permission rules

`.claude/settings.local.json` MUST NOT grant broad shell permissions. The following patterns are forbidden:

- `Bash(bash:*)`
- `Bash(sh:*)`
- `Bash(*)`
- Any rule of the form `Bash(<interpreter>:*)` where `<interpreter>` can execute arbitrary code

The reviewer MUST require narrow rules of the form `Bash(bash <absolute-script-path>:*)`. If a single permission prompt is annoying, the fix is to extract the inline blob into a script and add a narrow allowlist entry — NOT to widen the allowlist.

## R-INFRA-5: Hook commands reference scripts, not inline bash

Entries in `.claude/settings.json` under `hooks.<event>.<n>.hooks[].command` MUST point to a `.claude/hooks/<name>.sh` script. Inline bash blobs (multi-line strings, `bash -c "..."`, piped one-liners) are forbidden. The `if:` clause is the gate; the script is the implementation. One approach throughout the file. The reviewer MUST flag any inline command longer than a single script path.

## R-INFRA-6: Do not bypass `master-branch-guard.sh`

Edit/Write to any path outside the guard's allowlist requires a `task-*` branch. The `master-branch-guard.sh` hook enforces this. The reviewer MUST reject any diff or commit that:

- used `dangerouslyDisableSandbox: true` to bypass the master-branch guard
- was created by disabling, renaming, or temporarily removing the guard hook
- landed on `master` in any way other than those listed below

Only these commits are allowed on `master`:

- **Guard allowlist paths.** A commit that changes only paths the guard lets through: `.claude/`, `design/`, `.obsidian/`, `.vscode/`, `.idea/`, `.cursor/`, `.zed/`, `.fleet/` and `.gitignore` files.
- **Task-file commits.** A `task-N: ` commit that changes only files under `backlog/{tasks,drafts,archive,completed}/`.
- **Reviewed task-branch work.** The Review step records the verdict with the commit the reviewer saw, as `Review: APPROVED <sha>` in the task's notes, where `<sha>` is the task branch tip. A merge is allowed when its second parent equals such a SHA of the task its subject names, or follows it with only bookkeeping commits in between. A fast-forward landing is allowed when every landed `task-N` commit is equal to or an ancestor of such a SHA on master's first-parent line, or follows it with only bookkeeping commits in between. Bookkeeping commits are `task-N: ` commits that change task files, guard allowlist paths, or the paths a project lists in `master_bookkeeping_paths` (for example a version bump). No branch ref needs to survive. A verdict recorded for an earlier SHA does not approve any other commit made after it. A fast-forward cannot show where the reviewed range began, so a code commit made on `master` before the task branch forked from it passes as reviewed work; the guard hook is what stops that commit, and a `--no-ff` merge lets the checker flag it.
- **Integration merges.** A merge whose `Integrated-Origin: <sha>` trailer, written by `shared-backlog.sh integrate`, names its second parent, where that SHA is reachable from origin's base branch.

Every merge, of either kind, must also have the tree `git merge-tree --write-tree` makes of its parents. That equality only shows nothing was resolved by hand; it is not proof of approval. A merge whose tree differs is allowed only when a task's notes record `Integration review: APPROVED <merge-sha>` for exactly that merge.

The reviewer MUST check this by running the plugin's checker, `scripts/master-provenance.sh` in the plugin root this bundle was read from (the directory that holds `skills/`), from the project root with no arguments. It walks the first-parent commits master has that origin lacks (all of master when there is no remote-tracking branch for it, such as before a project's first push) and prints `ok <sha> <reason>` or `FLAG <sha> <reason>` per commit. Every `FLAG` line is a blocking R-INFRA-6 finding; exit status 2 (a usage or git error) is reported as a load error, not as a pass. A project sets `master_bookkeeping_paths=` (space-separated path prefixes) and `master_provenance_since=<commit>` (leave out that commit and its history, from before the project recorded `Review: APPROVED` notes) in `.claude/task-reviewer.conf`.

The correct workflow is `git checkout -b task-N` BEFORE the first edit. Sandbox bypass is reserved for tools that the sandbox blocks for unrelated reasons (e.g. `nohup`, `mktemp` in `/tmp`), never for circumventing project hooks.

## R-INFRA-7: PostToolUse hooks must emit JSON via hookSpecificOutput

Hooks registered under `PostToolUse` in `.claude/settings.json` that need to deliver model-visible feedback MUST emit a single JSON object on stdout with the structure:

```json
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"<text>"}}
```

Raw stdout text — including text wrapped in `<system-reminder>` tags — is silently dropped by the Claude Code harness and never reaches the model. The reviewer MUST reject any PostToolUse hook that uses `printf`, `echo`, or any other mechanism to emit raw text intended for the model, even if the text is correctly formatted as XML tags.

When a hook has multiple feedback sections (e.g. deterministic issues AND an LLM rubric), it MUST combine them into a single `additionalContext` string separated by blank lines — not emit multiple JSON objects. The harness parses exactly one JSON object per hook invocation.

A smoke test that only checks the hook script's stdout does not prove the model received the feedback: a hook that wraps its output in `<system-reminder>` tags but prints it as raw stdout passes such a test and still reaches nobody.
