---
name: ralph-sync
description: "Sync agents/ and skills/ from Ralph repo to ~/.claude/. Classifies items as unchanged/updated/new/orphan, shows summary, applies with one confirmation. Triggers on: ralph sync, sync agents, sync skills, ralph-sync."
---

# Ralph Sync

Sync `agents/` and `skills/` from the Ralph repo to `~/.claude/agents/` and `~/.claude/skills/`.

---

## Step 1: Classify

Run the sync script in classify mode to see what needs updating:

```bash
bash .claude/skills/ralph-sync/sync.sh classify
```

Capture the exit code:
- Exit 0: everything is in sync. Output the result and **stop** (do not prompt).
- Exit 1: there are items to sync. Continue to Step 2.

---

## Step 2: Show Summary and Prompt

Display the classify output to the user, then ask:

```
Apply N updates? [y/N/diff]
```

Where N is the count of `[new]` + `[updated]` items from the output.

Wait for the user's response:
- **y** -> proceed to Step 3 (Apply)
- **diff** -> proceed to Step 2b (Diff), then re-prompt
- **n** or anything else -> output "No changes applied." and **stop**

---

## Step 2b: Diff

For each `[updated]` item in the classify output, run the diff mode:

```bash
bash .claude/skills/ralph-sync/sync.sh diff agent/<name>
bash .claude/skills/ralph-sync/sync.sh diff skill/<name>
```

Display the diff output, then re-prompt with `Apply N updates? [y/N]` (the `diff` option is not re-offered since diffs were just shown).

---

## Step 3: Apply

Run the sync script in apply mode:

```bash
bash .claude/skills/ralph-sync/sync.sh apply
```

Display the output. This is the ONE moment that requires sandbox-bypass approval (writing to `~/.claude/`).

After apply, check if any `[applied] agent` lines appeared in the output. If so, append this warning:

```
Warning: Agent files were updated. Restart your Claude Code session for frontmatter changes to take effect.
```

---

## Important Notes

- **Orphans are never deleted** -- only reported. The user decides whether to manually remove them.
- The classify and diff modes are read-only. Only the apply step writes to `~/.claude/`.
- This skill is project-local to the Ralph repo (lives under `.claude/skills/`). It is NOT distributed via ralph-init.
- Invocations use a relative path (`.claude/skills/ralph-sync/sync.sh`). This works because Claude Code's cwd equals the repo root when project-local skills load. Invoking from a subdirectory will fail; `cd` to the repo root first.
