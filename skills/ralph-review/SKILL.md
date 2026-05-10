---
name: ralph-review
description: "Orchestrate a cumulative cross-task feature review against design intent. Gathers PRD, brainstorm, task summaries, and git diff, then spawns the ralph-reviewer agent. Triggers on: ralph review, cumulative review, review feature, ralph-review, feature review."
---

# Ralph Review

Orchestrate a cumulative feature review by gathering design docs, resolved tasks, and the cumulative diff, then spawning the `ralph-reviewer` agent to evaluate alignment.

---

## Step 1: Parse Arguments

Parse space-separated `key=value` pairs from the skill arguments.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `name`    | **yes**  | Feature slug — matches `design/<name>-prd.md`, `design/<name>-brainstorm.md`, and backlog label `feature:<name>` |
| `tasks`   | no       | Comma-separated numeric task IDs (e.g. `62,64,65`). Overrides label-based resolution |

If `name` is missing, output and stop:

```
BLOCKED: name= is required. Usage: /ralph-review name=<feature-slug> [tasks=N,M,K]
```

Validate `tasks` (if provided) contains only comma-separated integers. Reject `TASK-` prefix or non-numeric values:

```
BLOCKED: tasks= must be comma-separated numeric IDs (e.g. tasks=62,64,65).
```

---

## Step 2: Pre-conditions

### 2a: Design documents

Check for existence of `design/<name>-prd.md` and `design/<name>-brainstorm.md` using the Glob tool.

If **neither** file exists, output and stop:

```
BLOCKED: No design documents found. Expected at least one of design/<name>-prd.md or design/<name>-brainstorm.md.
```

Record which documents exist for later steps. Read each existing document with the Read tool.

### 2b: In-scope tasks

Resolve in-scope tasks using one of two approaches:

**If `tasks=` was provided (Approach D override):**

For each ID in the comma-separated list, run:

```bash
backlog task view <id> --plain
```

Collect all tasks regardless of status (the user explicitly chose them).

**If `tasks=` was NOT provided (label-based default):**

Resolve Done tasks for the feature by grepping `backlog/tasks/*.md` directly. The `backlog` CLI (v1.44.0) has no `-l/--label` filter on `task list`, so we read task files instead. The regex anchors on the YAML list-item form `^\s*-\s*['"]?feature:<name>['"]?\s*$` to avoid false positives from description prose; `^status:\s*Done\s*$` filters to completed tasks; `sort -V` gives natural numeric ordering.

```bash
name=<feature-slug>
grep -rl --include="*.md" -E "^\s*-\s*['\"]?feature:${name}['\"]?\s*\$" backlog/tasks/ \
  | while IFS= read -r f; do
      grep -qE "^status:\s*Done\s*\$" "$f" \
        && grep -m1 -E "^id:\s*TASK-" "$f" | sed -E 's/^id:[[:space:]]*TASK-//'
    done | sort -V
```

The pipeline emits one numeric task ID per line. For each ID, run `backlog task view <id> --plain` to load the full task for downstream steps.

If no tasks are returned, output and stop:

```
BLOCKED: No completed tasks found for feature:<name>. Complete at least one task before running a review.
```

### 2c: Diff range

Walk the in-scope task files and collect all `Commit:` hash lines. These are appended by the post-commit hook.

For each task, read its file path (shown in `backlog task view` output) and grep for lines matching `` ^Commit: `[0-9a-f]+` ``. The post-commit hook writes hashes wrapped in backticks (e.g. `` Commit: `94b6e69` - task-16: ... ``). Strip the backticks to extract the raw hash.

Collect all hashes into a list. If no commit hashes are found across any task file, output and stop:

```
BLOCKED: No Commit: hashes found in task files. The post-commit hook may not have run for these tasks.
```

Find the earliest commit by sorting the collected hashes by commit date:

```bash
for h in <hash1> <hash2> ...; do echo "$(git log -1 --format=%ct $h) $h"; done | sort -n | head -1 | awk '{print $2}'
```

Then derive `<base>` as the parent of that earliest commit:

```bash
git rev-parse <earliest>~1
```

Verify the diff range is non-empty:

```bash
git diff --stat <base>..HEAD
```

If empty, output and stop:

```
BLOCKED: Diff range <base>..HEAD is empty. Nothing to review.
```

---

## Step 3: Build Agent Input Bundle

Construct a Markdown bundle document to pass to the ralph-reviewer agent. The bundle has these sections:

### 3a: Design Documents

Include each existing design doc verbatim, wrapped in a header:

```markdown
# Design: <name>-brainstorm.md

<contents of design/<name>-brainstorm.md>

# Design: <name>-prd.md

<contents of design/<name>-prd.md>
```

Omit any document that doesn't exist.

### 3b: Task Summaries

For each in-scope task, include a summary block:

```markdown
## TASK-<id>: <title>

**Status:** <status>
**Acceptance Criteria:**
<AC list with check states>

**Notes:**
<implementation notes from the task, if any>
```

### 3c: Cumulative Diff

Run `git diff <base>..HEAD` and include it. If the diff exceeds 50,000 characters, truncate and append:

```
[WARN: Diff truncated at 50,000 chars. Review may be incomplete.]
```

---

## Step 4: Spawn Ralph-Reviewer Agent

Spawn the `ralph-reviewer` agent in foreground with `subagent_type: ralph-reviewer`.

The prompt must include:

1. The full bundle from Step 3
2. The feature name
3. Instruction to produce the review output in the format specified in the ralph-reviewer agent definition

**Critical:** Use `subagent_type: "ralph-reviewer"` — do NOT fall back to `general-purpose` or any other agent type.

If the agent returns an error or empty response, output:

```
Review failed: <reason from agent or "agent returned empty response">
```

Do not fabricate a verdict. Stop here.

---

## Step 5: Save Review Output

Save the full review output from the agent to `design/<name>-review-<YYYY-MM-DD>.md`.

### Collision handling

Check if the target filename already exists using Glob:

```
design/<name>-review-<YYYY-MM-DD>*.md
```

If collisions exist, append a two-digit suffix: `-01`, `-02`, etc. Pick the next available number. Never overwrite an existing file.

Write the file using the Write tool.

---

## Step 6: Report to Chat

Extract from the review output:
- The **verdict line** (`Verdict: Aligned | Partial | Drifted`)
- The **drift list** section (or "No drift detected")

Output to chat:

```
## Feature Review: <name>

**<verdict line>**

### Drift
<drift list items, or "No drift detected">

Full review saved to design/<name>-review-<YYYY-MM-DD>.md
```

Do not print the full intent-to-implementation matrix or other sections in chat — those belong in the saved file only.
