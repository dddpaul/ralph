---
name: ralph-handoff
description: "Hand off an epic or task from this project to another Ralph project by creating a self-contained backlog task in the destination repo. Destination's backlog CLI allocates the task ID. Triggers on: ralph handoff, handoff task, cross-project task, send task to other project, create task in other ralph project, передать задачу в другой проект."
---

# Ralph Handoff

Deposit a self-contained backlog task into a **destination** Ralph project so its Ralph loop can pick the work up after a human confirmation gate. Invoked from the **source** project where the epic was planned.

The skill is one-way: source → destination. There is no sync of completed status back to source.

---

## What this skill does NOT do

- Run the task. The destination Ralph loop (or destination Claude) runs it after the user confirms.
- Commit the new task file. The user decides whether to `git add`/`git commit` in the destination repo.
- Write a source-side audit doc. The git history of source + the `Source:` line in the destination task are the audit trail.
- Copy source files into destination. Reference them by absolute path in `Source:` and inline only the snippets the destination Claude needs verbatim.

---

## Step 1: Validate Destination

The user must provide an absolute path to the destination project (e.g. `/Users/<user>/Projects/project-b`). If they did not, ask once before continuing.

Run a single combined preflight check:

```bash
DEST="<destination-abs-path>"
[ -d "$DEST/backlog" ] && echo "backlog-dir: ok" || echo "backlog-dir: MISSING"
[ -d "$DEST/.git" ] && echo "git-repo: ok" || echo "git-repo: MISSING"
(cd "$DEST" && command -v backlog >/dev/null && backlog task list --plain >/dev/null 2>&1) && echo "backlog-cli: ok" || echo "backlog-cli: MISSING"
```

If any line ends in `MISSING`, stop and tell the user. Example failure responses:

- `backlog-dir: MISSING` — destination has no `backlog/` directory; run `/ralph-init` there first.
- `git-repo: MISSING` — destination is not a git repository; cannot record commits/branches.
- `backlog-cli: MISSING` — `backlog` CLI is missing or fails in that directory; cannot allocate a task ID.

---

## Step 2: Recon Destination Conventions

Read these from destination (skip silently if any are missing):

```bash
DEST="<destination-abs-path>"
[ -f "$DEST/README.md" ] && cat "$DEST/README.md"
[ -f "$DEST/CLAUDE.md" ] && cat "$DEST/CLAUDE.md"
[ -f "$DEST/AGENTS.md" ] && cat "$DEST/AGENTS.md"
```

Note from the output:
- **Build/lint/test commands** — so the AC can reference the right verification command.
- **Label vocabulary** — does the destination use `feature:<slug>`, `bug`, `chore`? Mirror it.
- **AC style** — terse imperative vs. user-story format? Mirror.
- **Existing tasks** (`(cd "$DEST" && backlog task list --plain | head -40)`) — to scan for naming patterns and check whether the proposed work is already tracked (avoid duplicate handoffs).

Do NOT modify any destination file at this step. Read-only recon.

---

## Step 3: Gather Task Fields

Required fields:

1. **Title** (English — the CLI uses it for the filename)
2. **Why** — business/product motivation. Destination Claude has zero memory of the source conversation, so this is essential.
3. **Acceptance criteria** — 3–8 atomic, verifiable outcomes (objective pass/fail), written in **destination's** frame of reference (paths that exist in destination, commands that work there).
4. **Destination-frame file paths** — concrete paths/modules to touch. Verify they exist (or flag as "destination Claude to create").
5. **Out-of-scope** — what NOT to do. One task per iteration; scope creep is the enemy.
6. **Dependencies** — other destination tasks (by ID) that must be Done first.
7. **Labels** — using destination's label vocabulary discovered in Step 2.
8. **Priority** — high / medium / low.

### Derivation rule

Derive as many fields as possible from the **source conversation** (current chat context, design docs in source under `design/`, recent commits). Only invoke `AskUserQuestion` for fields that are genuinely ambiguous after derivation.

Cap each `AskUserQuestion` call at 4 fields. If more than 4 are ambiguous, prioritize: title and AC first, then why and file paths, then out-of-scope and deps, then labels and priority. Spread across multiple `AskUserQuestion` rounds if necessary.

### Path verification

For each destination-frame file path:

```bash
[ -e "$DEST/<path>" ] && echo "exists: <path>" || echo "to-create: <path>"
```

Annotate paths in the composed body as `(exists)` or `(to-create)` so destination Claude knows immediately whether to read or generate.

---

## Step 4: Compose Task Body

Build the description body. The body lives in the `-d` flag of `backlog task create`; AC are passed via `--ac` (repeat per criterion — never comma-join).

### Body template

```
## Why

<2–4 sentence motivation: what user-visible problem this solves, what constraint
or stakeholder drove it. No source-conversation snippets — paraphrase.>

## Scope

In scope:
- <destination-frame deliverable bullet>
- <destination-frame deliverable bullet>

Out of scope:
- <thing not to do>
- <thing not to do>

## Files

- `<path>` (exists) — <one-line note on what touches it>
- `<path>` (to-create) — <one-line note on shape/purpose>

## Source

Source: <abs-path-to-source-repo>@<commit-sha-or-uncommitted>
Source design doc (read-only context, do NOT modify): <abs-path-to-source/design/foo.md>

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
```

### Source line construction

Build the `Source:` line from source's CWD:

```bash
SOURCE_REPO=$(pwd)
SOURCE_REF=$(git describe --always --dirty --abbrev=12 2>/dev/null || echo "not-a-git-repo")
echo "Source: $SOURCE_REPO@$SOURCE_REF"
```

The `--dirty` suffix appears if source has uncommitted changes — a signal that the SHA does not fully reflect the planning state.

If source is not a git repo, the line reads `Source: <abs-path>@not-a-git-repo`.

### AC list construction

Each AC is its own `--ac` flag. Never comma-join. Each AC ends with a verifiable check — a command name, file path, or observable behavior.

---

## Step 5: Create the Task in Destination

Run `backlog task create` with destination as CWD. The destination's `backlog` CLI allocates the next available task ID locally — source's IDs are irrelevant.

```bash
DEST="<destination-abs-path>"
(cd "$DEST" && backlog task create "<English title>" \
  -d "<composed body from Step 4>" \
  --ac "<atomic outcome 1>" \
  --ac "<atomic outcome 2>" \
  --ac "<atomic outcome 3>" \
  --priority <high|medium|low> \
  --status "To Do")
```

If labels were chosen, add `-l "<label>"` per label (repeat the flag — do not comma-join).

If dependencies were specified, add `--dep task-<id>` per dep.

Status is explicitly `To Do`, not `Draft`. The user's workflow assumes they will type `check new task TASK-NNN — do you understand, can you run it?` in destination Claude **before** launching Ralph there, so the human confirmation gate is in their hands, not in the status field.

### Mandatory self-check

After create succeeds, verify ACs landed as separate items:

```bash
(cd "$DEST" && backlog task view <new-id> --plain | grep -A 30 "Acceptance")
```

If a single AC line contains commas joining what should be separate outcomes, fix:

```bash
(cd "$DEST" && backlog task edit <new-id> --remove-ac N --ac "<outcome 1>" --ac "<outcome 2>")
```

### Do NOT commit

The new task file appears as untracked in destination's `git status`. Do NOT run `git add` or `git commit` in destination — the user decides whether and when to commit (they may want to inspect first, or batch multiple handoffs).

Print a one-line reminder in the final summary (Step 6).

---

## Step 6: Print Handoff Confirmation

Output exactly this block (substituting real values for `<...>`):

```
Handoff complete.

Created TASK-<NNN> in <destination-abs-path>
Title:    <task title>
Status:   To Do
ACs:      <count>
Source:   <abs-path-to-source-repo>@<sha-or-uncommitted>

Next step — in your destination Claude session:
  check new task TASK-<NNN> — do you understand, can you run it?

Note: the new task file is uncommitted in <destination>. Commit it yourself
when ready (e.g., `cd <destination> && git add backlog/tasks/task-<NNN>*.md && git commit -m "Handoff task TASK-<NNN>"`).
```

The verbatim phrase `check new task TASK-<NNN> — do you understand, can you run it?` is the user's contract with destination Claude. Do not paraphrase it in the output — destination Claude can be primed to look for that exact phrasing.

---

## Failure modes and what to do

| Symptom | Cause | Fix |
|---|---|---|
| `backlog task create` exits non-zero | CLI syntax error or destination has uncommitted backlog config | Print the exact command + stderr; ask the user to inspect destination state |
| Self-check shows comma-joined AC | `--ac "a,b,c"` mistake | Fix with `--remove-ac N --ac "..." --ac "..."` |
| `Source:` line missing SHA | Source is not a git repo or has no commits | The fallback `not-a-git-repo` is fine — leave as is |
| Destination path does not exist | Typo or wrong project | Stop. Re-ask for destination path |
| User wants two destinations | Two different destination projects | Run the skill twice; each invocation handles one destination |

---

## Checklist before stopping

- [ ] Step 1 preflight passed for destination (backlog dir, git repo, backlog CLI all OK)
- [ ] Step 2 recon: destination's README/CLAUDE.md were read (or confirmed absent)
- [ ] Step 3: every required field has a value (derived or asked)
- [ ] Step 4: `Source:` line built from source's `git describe --always --dirty`
- [ ] Step 4: Before-starting checklist included verbatim in the body
- [ ] Step 5: `backlog task create` ran with destination as CWD (via `cd "$DEST" && ...`)
- [ ] Step 5: self-check confirmed no comma-joined ACs
- [ ] Step 5: did NOT run `git add`/`git commit` in destination
- [ ] Step 6: handoff confirmation block printed with verbatim magic phrase
