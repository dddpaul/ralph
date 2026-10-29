---
id: TASK-281
title: Fix two PreToolUse hook guard templates that deny unrelated Bash commands
status: In Progress
assignee: []
created_date: '2026-10-29T07:03:00Z'
updated_date: '2026-10-29T13:05:00Z'
labels:
  - feature:ralph-init
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Two PreToolUse hook guards shipped by ralph-init deny Bash commands they were never registered for. Because they are shipped templates, the defect reaches every project ralph-init touches, and a consuming project cannot fix it locally: U4 overwrites `.claude/hooks/*-guard.sh` on upgrade and `managed-file-drift.sh` flags any local edit as drift on every ralph-run preflight. Observed repeatedly in a consuming project where it blocked `backlog task create`, `backlog task edit --append-notes` and a `python3` heredoc, and made the trailer policy impossible to document through the backlog CLI at all.

Throughout this task `G<SP>C` stands for the two-word phrase "git" and "commit" separated by a space. The literal is elided on purpose: `commit-prefix-guard.sh` denies any command whose text contains it, which is defect 2, and spelling it out makes this task file unwritable through the CLI. That is the clearest available demonstration of the bug.

## Why the two earlier fixes did not cover this

- **TASK-123 (Done)** added the gate `case "$cmd" in *"G<SP>C"*) ;; *) exit 0;; esac` to `commit-prefix-guard.sh`, which is now line 10. It correctly stopped a non-commit command such as `kill 1` from firing the guard. But a free substring test also matches any command that merely *mentions* the phrase, and TASK-123 did not touch the message extraction. So the guard moved from one false-positive class to another. TASK-123's own AC5 asked for a decision on whether the `settings.json` `if:` directive is real filtering or documentation only - that question is still open and is now load-bearing (see AC below).
- **TASK-134 (Done)** fixed `templates/git-hooks/commit-msg`, the **git** hook, by stripping the scissor section. That is a different file from the Claude Code PreToolUse guard `templates/claude/hooks/commit-msg-guard.sh`, whose unconditional grep has never been addressed.

## Defect 1 - commit-msg-guard.sh has no self-gate at all

The script greps the entire `tool_input.command` with nothing narrowing it: the file contains **zero** `case` statements, despite a header comment naming the commit and pull-request-create triggers. Any Bash command whose text contains the forbidden trailer names is denied, whatever the command is.

Relevant: the consuming project registers this script with `if:` conditions for only those two triggers, yet it ran on commands matching neither. Either `if:` does not filter PreToolUse hooks, or it was not applied. Since the sibling guards rely on `if:`, this needs settling rather than assuming.

## Defect 2 - commit-prefix-guard.sh cannot parse a multi-line message

Line 18 is `msg=$(echo "$cmd" | sed -n 's/.*-m[[:space:]]*"\(.*\)".*/\1/p')`. `sed` is line-based, so a message whose opening and closing quotes sit on different lines never matches. The single-quote fallback at line 20 and the heredoc fallback at line 23 miss too, `msg` ends up empty, and the final `grep -qE "^task-N: "` fails on the empty string - so a **correctly prefixed** multi-line message is denied. Reproduced in the consuming project: the identical message was denied as multi-line and accepted when flattened to one line. Combined with line 10's substring gate, a `backlog task edit --append-notes` whose notes quoted that pattern was also denied - exactly the case the comment on line 9 claims to prevent.

## Scope

In scope:
- Gate both guards so `git` is the program and `commit` its subcommand at a command position (start of string, or after `;`, `&&`, `||`, `|` or a newline) rather than a substring anywhere in the text.
- Replace the line-based message extraction with something not line-bound: read the whole command into a variable and match with bash pattern matching or `python3`, handling `-m` with multi-line double and single quotes, `--message=`, `-F`/`--file` (read the named file), and heredoc.
- When the command is a real commit but no message can be extracted, prefer allowing over denying, and record that trade-off in the notes - a false deny blocks legitimate work, which is the whole complaint.
- Keep the repo's own `.claude/hooks/` copies in step with the templates.

Out of scope:
- Changing either policy. The trailer ban and the task-prefix rule both stay and must still fire on real commits.
- `templates/git-hooks/commit-msg`, already handled by TASK-134.
- Repairing this repo's duplicate task IDs, which blocks ID-based backlog commands here - see the note at the end.

## Files

- `plugins/ralph/skills/ralph-init/templates/claude/hooks/commit-msg-guard.sh` (exists) - add the missing gate; currently an unconditional grep.
- `plugins/ralph/skills/ralph-init/templates/claude/hooks/commit-prefix-guard.sh` (exists) - fix the gate on line 10 and the extraction on lines 18-23.
- `.claude/hooks/commit-msg-guard.sh` (exists) - this repo's own copy, keep byte-identical to the template.
- `.claude/hooks/commit-prefix-guard.sh` (exists) - same.
- `tests/` (exists) - add regression tests in the shape TASK-134 used for the git hook.

## Source

Source: /home/paul/src/mycloud@a7366223529e

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior - not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.

## Note on this repo's backlog state

`backlog task list --plain` exits 1 here with "4 duplicate task ID groups affect 9 files" - TASK-77, TASK-101, TASK-102 and TASK-235 each exist in both `backlog/tasks/` and `backlog/archive/tasks/`, and the CLI says ID-based commands are blocked until repaired. This task was created anyway because creation is not ID-based and the highest existing id is 280, so no new collision was introduced. But `backlog task view <this id>` and `backlog task edit <this id>` may refuse until the collision is fixed; `backlog doctor` previews the repair. Worth its own task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 commit-msg-guard.sh exits 0 silently with no output for a command that is not a real commit or pull-request-create, verified by piping a tool_input whose command is a backlog task create carrying the forbidden trailer names in its text
- [x] #2 commit-msg-guard.sh still emits the deny JSON for a real commit whose message contains a forbidden trailer, and for one containing the forbidden heading
- [x] #3 commit-prefix-guard.sh exits 0 silently on a task-N branch for a correctly prefixed message whose -m value spans several lines
- [x] #4 commit-prefix-guard.sh still emits the deny JSON on a task-N branch for an unprefixed and for a wrongly prefixed message, tested both as a single line and as multiple lines
- [x] #5 commit-prefix-guard.sh exits 0 silently for a command that merely mentions the two-word git-commit phrase without being a commit, such as a backlog task edit whose notes quote that pattern
- [x] #6 Message extraction handles -m with multi-line double quotes, -m with multi-line single quotes, --message=, -F and --file reading the named file, and a heredoc; the chosen behaviour when no message can be extracted is recorded in the task notes with its rationale
- [x] #7 Regression tests under tests/ cover each case above and pass with uv run pytest, and this repo's .claude/hooks copies of both scripts are byte-identical to the templates
- [x] #8 Both scripts pass bash -n and satisfy R-INFRA-3 GNU and BSD userland plus bash 3.2 portability, and the notes settle TASK-123's open AC5 question by recording with evidence whether PreToolUse if: conditions filter hook invocations
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: self-gate both guards on a real commit (and gh pr create for the msg guard) at a command position, using an awk pass that drops quoted text and heredoc bodies so mentions never match; replace the sed extraction in the prefix guard with bash [[ =~ ]] matching (not line-bound) over -m/--message (double, single, unquoted, $(cat <<EOF) wrapper), -F/--file (named file or - heredoc) and a bare heredoc; pytest regression tests in tests/python/test_commit_guards.py; sync .claude/hooks copies.

No-extractable-message decision: when the command is a real commit but no message can be extracted (editor, --amend --no-edit, -C, -m "$MSG", -F naming a file not present yet), the prefix guard ALLOWS. Rationale: a false deny blocks legitimate work (the complaint this task fixes), while the git commit-msg hook still sees the final message. Old behaviour denied these on task-* branches.

if: question (TASK-123 AC5), settled with evidence on Claude Code 2.1.283 in this repo, whose live commit-msg-guard was still the unconditional grep: echo / python3 heredoc / && compound / quoted $(...) commands carrying the trailer name were NOT denied, so if: Bash(git commit *) does filter them. But 'X=1; echo ... Co-Authored-By $X $(date +%s)' WAS denied by the commit-msg guard. The hooks docs (code.claude.com/docs/en/hooks) say the filter is best-effort: patterns that specify more than the command name run the hook anyway on $(), backticks or $VAR, and so does any command Claude Code cannot parse. So if: is real filtering but not a reliable gate, and each guard must gate itself. The same probe also hit the old prefix guard: a python3 heredoc command in this session whose text contained the phrase was denied on task-281.

Portability: awk program uses POSIX features only (verified under mawk here); bash uses [[ =~ ]] with regex in a variable, $'\n', BASH_REMATCH and parameter expansion, all bash 3.2. No GNU-only flags added. Gate limits: options between git and commit are recognised (-C path, -c k=v, other -flags); env-prefix forms (FOO=1 git commit) and sudo/env wrappers are not gated and are allowed. Pre-existing: uv run ruff check . reports 43 errors on master too (none in touched files); bats is not installed in this container so tests/unit/pretools-hooks.bats was not run, and its guard cases are covered again by the new pytest file.
<!-- SECTION:NOTES:END -->
