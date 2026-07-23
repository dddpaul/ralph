---
name: ralph-refine
description: "Run the ralph-refine adversarial author-reviewer refinement loop over a digital artifact (markdown / draw.io / PlantUML) until a reviewer quality score meets a threshold. Foreground sibling of ralph-run: loops an author→reviewer pair via ./refine.sh instead of a coder over backlog tasks. Launches with a single permission prompt. Triggers on: ralph refine, run refine, refine, refine loop, author reviewer loop, refine article, refine diagram, refine artifact, adversarial refinement."
---

# Ralph Refine

Run the adversarial **author → reviewer** refinement loop: an *author* role
drafts an artifact, a *reviewer* role scores it `1–10` and writes feedback, and
the author revises — iterating until the score meets a threshold or the
iteration cap is hit. It is Ralph's non-code sibling loop: where `ralph-run`
loops a *coder* over backlog tasks, `ralph-refine` loops an *author-reviewer*
over one digital artifact (`md` / `drawio` / `puml`).

Refine runs in the **foreground** — the launch blocks until the loop converges,
then prints where the results landed. (Detached / watch execution is phase-2 and
not part of this skill.)

---

## Step 1: Parse Arguments

The user may pass overrides as skill arguments — space-separated `key=value`
pairs. Each maps to a `refine.sh` flag; defaults below **match `refine.sh`**.

| Parameter        | Default          | Flag               | Notes |
|------------------|------------------|--------------------|-------|
| `prompt`         | (none)           | `--prompt`         | Path to a task-prompt file. **Exactly one of `prompt` or `draft` is required.** |
| `draft`          | (none)           | `--draft`          | Path to an existing draft to revise instead of starting from a prompt. Mutually exclusive with `prompt`. |
| `author`         | (none)           | `--author`         | **Required.** Path to the author role file. |
| `reviewer`       | (none)           | `--reviewer`       | **Required.** Path to the reviewer role file. |
| `type`           | `md`             | `--type`           | Artifact type: `md`, `drawio`, or `puml`. Sets the `final.<ext>` extension. |
| `threshold`      | `8`              | `--threshold`      | Stop once the reviewer score `≥` this (`1–10`). |
| `max_iterations` | `10`             | `--max-iterations` | Hard cap on author→reviewer rounds. |
| `output_dir`     | `iterations/`    | `--output-dir`     | Where per-iteration and final files land. |
| `tool`           | `claude`         | `--tool`           | `claude` or `opencode`. |
| `model`          | `claude-opus-4-8`| `--model`          | Model id passed to the tool. |
| `effort`         | `medium`         | `--effort`         | `low`, `medium`, `high`, or `max`. |
| `timeout`        | `15`             | `--timeout`        | Per-call timeout in minutes. |
| `on_error`       | `stop`           | `--on-error`       | `stop`, `continue`, or `retry` on a failed LLM call. |
| `retry_count`    | `2`              | `--retry-count`    | Retries when `on_error=retry`. |
| `devcontainer`   | `false`          | `--devcontainer`   | Run the tool inside the project devcontainer. |
| `resume`         | `false`          | `--resume`         | Continue an interrupted run from the last artifact in `output_dir`. |
| `verbose`        | `false`          | `--verbose`        | Print each composed prompt before its call. |
| `dry_run`        | `false`          | `--dry-run`        | Print the iteration-1 prompts and exit `0` — no LLM call. |

Add a flag to the launch command only when its value differs from the default.
Boolean flags (`devcontainer`, `resume`, `verbose`, `dry_run`) are appended bare
(e.g. `--verbose`) only when set to `true`.

**Example invocations:**
- `/ralph-refine prompt=spec.md author=roles/author.md reviewer=roles/reviewer.md`
- `/ralph-refine draft=draft.md author=a.md reviewer=r.md type=md threshold=9`
- `/ralph-refine prompt=diagram.md author=a.md reviewer=r.md type=drawio max_iterations=5`
- `/ralph-refine prompt=p.md author=a.md reviewer=r.md dry_run=true` — preview prompts only

Do **not** pre-validate the file paths or flag values in the skill — `refine.sh`
performs the same checks the CLI does (exactly-one-of `prompt`/`draft`, `author`
and `reviewer` readable, enumerated/range checks) and prints a parity
`Error: …` on stderr, exiting `1`. Relay that error verbatim if the launch
fails on it.

---

## Step 2: Locate refine.sh

`refine.sh` is the thin project shim that resolves and execs the installed
plugin's `refine_orchestrator.py` (5-tier resolver, mirroring `ralph.sh`). This
is a **read-only** check — the sandbox auto-allows it, so it never prompts.
Check for `./refine.sh` at the project root.

If it is missing, report and stop:

```
Error: refine.sh not found at the project root. Run /ralph-init to seed it, or install the Ralph plugin (/plugin marketplace add dddpaul/ralph && /plugin install ralph@dddpaul-ralph).
```

---

## Step 3: Launch (single approval)

Build the launch command from the parsed arguments:

```bash
./refine.sh --prompt <prompt> --author <author> --reviewer <reviewer> [--type <type>] [--threshold <n>] [--max-iterations <n>] [<other flags>]
```

Use `--draft <draft>` in place of `--prompt <prompt>` when `draft` was given.

Issue this as a **single Bash tool call** with **`dangerouslyDisableSandbox: true`**.
This is the **one and only** permission prompt of the whole flow — it mirrors the
`ralph-run` launch UX. The bypass is required because the orchestrator needs full
OS access (`mktemp`, `/dev/fd`, `tee`, and — when `devcontainer=true` — `docker`)
that the sandbox blocks; the refine run itself, not just docker, needs it.

Refine is foreground, so this call blocks until the loop finishes. Relay the
command's stdout/stderr to the user.

---

## Step 4: Report

Use the exit code and the orchestrator's own output:

- **`0` — threshold met.** The orchestrator prints
  `Threshold <t> reached at iteration <n> (score <s>). Wrote <output_dir>/final.<ext>`.
- **`1` — max iterations (or a validation / stopped-call error).** On a
  completed-but-below-threshold run it prints a `WARNING: reached max
  iterations …` line and still writes `final.<ext>`. On a bad invocation it
  prints a single `Error: …` line — relay it verbatim.
- **`130` — interrupted** (SIGINT/SIGTERM); the child process group is cleaned
  up.

Outputs land in `output_dir` (default `iterations/`):

| File                     | Contents |
|--------------------------|----------|
| `final.<ext>`            | The winning artifact (`.md` / `.drawio` / `.puml`). |
| `summary.md`             | Score history and the reviewer's final `<summary>`. |
| `artifact-v<N>.<ext>`    | The artifact from each iteration `N`. |
| `review-v<N>.md`         | The reviewer's full feedback for iteration `N`. |

Point the user at `final.<ext>` and `summary.md`.

---

## Example role sets

Three ready-to-run author/reviewer/prompt sets ship with this skill under
`${CLAUDE_PLUGIN_ROOT}/skills/ralph-refine/examples/` (the harness renders
`${CLAUDE_PLUGIN_ROOT}` to the installed plugin directory):

| Directory   | Type     | Artifact |
|-------------|----------|----------|
| `article/`  | `md`     | A markdown article. |
| `drawio/`   | `drawio` | A draw.io architecture diagram (reviewer references the `arch-draw` skill). |
| `plantuml/` | `puml`   | A PlantUML sequence diagram. |

Each set contains `prompt.md` (the seed task), `author.md` (author role, with the
`<artifact>…</artifact>` output protocol), and `reviewer.md` (reviewer role, with
the `SCORE: N` line and `<summary>…</summary>` protocol). Run one out of the box:

```bash
./refine.sh \
  --prompt   ${CLAUDE_PLUGIN_ROOT}/skills/ralph-refine/examples/article/prompt.md \
  --author   ${CLAUDE_PLUGIN_ROOT}/skills/ralph-refine/examples/article/author.md \
  --reviewer ${CLAUDE_PLUGIN_ROOT}/skills/ralph-refine/examples/article/reviewer.md \
  --type md --threshold 8
```

---

## Single-approval invariant

When this skill launches refine on the user's behalf, **exactly one permission
prompt fires** — the sandbox-bypass launch of `refine.sh` in Step 3. Every other
step is read-only and sandbox-safe (locating `refine.sh`, reading role files),
so it runs without prompting. There is no helper shim that needs its own
`Bash(bash <abs-path>:*)` allow rule, and no `plugin.json` edit is required —
this skill is auto-discovered by the plugin loader from its `SKILL.md`. This
matches the `ralph-run` launch UX and doc-4 invariant 4.
