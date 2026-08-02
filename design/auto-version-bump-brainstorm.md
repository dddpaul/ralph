# Auto-Bump Plugin Version on Shipped-File Changes

## Architecture decision

Add a **local, per-task auto-bump helper** so an autonomous Ralph loop can change shipped plugin files and push to GitHub with **no human unblocking the version-bump guard**. A shared `bump-version.sh` engine runs as two explicit Task-Lifecycle Merge-step actions: `--auto` (bump the version on the task branch, inferring patch vs minor) before the merge, and `--tag` (annotated `vX.Y.Z` on the merge commit) after it. The existing `version-bump-guard.sh` stays **unchanged** as the origin-based pre-push backstop.

Chosen **Approach B** (explicit lifecycle step) over Approach A (pre-commit hook auto-staging): the project's Task Lifecycle is proven and reliably followed, and an *unconditional* lifecycle step (`bump-version.sh --auto`, where the script itself no-ops when nothing shipped changed) lands B's robustness close to a hook's without auto-staging magic — while degrading safely (a skipped step → a visible guard block, never a silent stale-cache publish). A pre-**push** auto-fix was ruled out on a hard technical fact: by the time `git push` invokes pre-push, the push contents are already computed, so a bump committed in pre-push ships one push late.

## Components / flows

- **`.claude/hooks/bump-version.sh` (new, repo-only)** — modes:
  - `--auto`: if `git diff --name-only master..HEAD` touches no shipped-set path → no-op exit 0. Else infer increment (a newly-added skill dir `plugins/ralph/skills/<new>/` or agent file `plugins/ralph/agents/<new>.md` via `--diff-filter=A` → **minor**; otherwise **patch**; **major** never auto). Compute the target **relative to local `master`'s** version; no-op if HEAD is already ahead (idempotent). Edit `plugin.json` + `marketplace.json` to the same value; commit with a branch-aware `task-N: bump plugin version to X.Y.Z (<increment>)` message (single-line, to satisfy the commit-prefix guard). `patch|minor|major` args override inference; `--no-commit` stages only.
  - `--tag`: read the version at HEAD; if no `vX.Y.Z` tag exists, `git tag -a vX.Y.Z -m "ralph X.Y.Z"` on the current commit (the **merge commit** when run post-merge on master); else no-op.
- **Shared `is_shipped` predicate** — factored into a sourced snippet (e.g. `.claude/hooks/lib/shipped-set.sh`) read by BOTH `bump-version.sh` and `version-bump-guard.sh`, so the shipped-set definition cannot drift.
- **Task Lifecycle Merge step (CLAUDE.md)** — (a) `bump-version.sh --auto` on branch; (b) commit task file; (c) `git checkout master && git merge --no-ff`; (d) `bump-version.sh --tag` on master; (e) `git branch -d`.
- **`post-commit` nudge (interactive)** — extend the existing hook: when a commit touched shipped files and the version isn't yet ahead of `master`, print one non-blocking line (`shipped file changed → run bump-version.sh --auto before pushing (suggested: <patch|minor>)`).
- **`push.followTags=true`** (repo-local git config) — the annotated tag rides the existing autonomous `git push origin master`; **no change** to the generic orchestrator `push.py`.
- **`version-bump-guard.sh`** — unchanged; origin-based pre-push backstop.

## Why local `master`, not `origin/master`

The guard needs only **one** version above origin for the whole unpushed range, and local `master` is always ≥ `origin/master` in the normal flow (git's non-fast-forward rejection stops a behind-push first). So bumping every shipped task against local `master` guarantees `HEAD > master ≥ origin` — the guard passes without the helper ever touching the network. This **deletes** the origin-freshness / `git fetch` / concurrency problem, and gives **per-task** semantic increments (each task classified independently) at the only cost of consuming version numbers faster (free).

## Consistency: helper (local) vs guard (origin)

Helper bumps per-task against local `master`; guard checks per-push against `origin`. Since every shipped task bumps, by push time local master's version is strictly greater than origin's, so the guard passes. The two references never conflict because local `master` ≥ `origin`.

## Scope cuts

- No pre-commit/pre-push auto-fix (pre-push can't add to the in-flight push; pre-commit auto-staging rejected in favor of the explicit, reviewable lifecycle step).
- No `git fetch` / origin read in the helper — fully local.
- No distributed version locking for truly-simultaneous racing pushes — git's non-fast-forward rejection + a re-run handle that.
- No change to the generic `push.py` — tags ride via `push.followTags`.
- No `major` auto-bump — `→ 1.0` stays a deliberate human act.
- Helper + config live under `.claude/` (repo-only, **not** shipped, no R11 template parity — same status as the guard). Nothing added under `plugins/ralph/`.
- The one-time legacy bump that publishes the already-merged TASK-215 change is **separate** (a manual `0.2.1 → 0.2.2` + push), not part of this feature — the helper only covers changes going forward.

## Open questions

- **Cross-batch minor upgrade:** resolved by the merge-step placement — the single `--auto` at merge sees the complete `master..HEAD` diff, so classification is always whole-task; no per-commit misclassification.
- **Concurrent identical tags** (`v0.2.2` from two loops) collide at push — accepted; resolved by the same non-fast-forward re-run as the version itself.

## Hand-off

Single-purpose feature (one auto-bump system; helper + lifecycle wiring + tests, all under `.claude/`), no cross-task invariants → straight to `ralph-task` (rewrite of the existing TASK-217). No PRD needed.

## Distilled for ralph-task

**Direction:** Approach B — a local, per-task auto-bump helper (`.claude/hooks/bump-version.sh`) invoked as two explicit Task-Lifecycle Merge-step actions (`--auto` pre-merge on branch, `--tag` post-merge on master), with the origin-based `version-bump-guard.sh` unchanged as the pre-push backstop. Fully local (no `git fetch`), per-task patch/minor inference, annotated tag on the merge commit carried to origin via `push.followTags`.

**Locked decisions (with rationale):**
- **Explicit lifecycle step, not a hook.** *Rationale:* the proven Task Lifecycle is reliably followed; an unconditional `--auto` step (script self-no-ops) gets hook-like robustness without auto-staging magic.
- **Compare against local `master`, not `origin/master`.** *Rationale:* the guard only needs one bump above origin and local master ≥ origin, so local comparison guarantees the guard passes while eliminating network/staleness/concurrency and giving per-task increments.
- **Bump at the Merge step (final diff).** *Rationale:* the complete `master..HEAD` diff is known, so patch/minor classification is always correct; no per-commit churn.
- **Tag the merge commit, post-merge (`--tag` mode).** *Rationale:* the merge commit is where the version lands on master's permanent first-parent line; the branch (carrying the bump commit) is deleted.
- **Annotated tag + `push.followTags=true`.** *Rationale:* tags reach origin on the normal autonomous push with no change to the generic `push.py`; annotated (not lightweight) so follow-tags sends them.
- **Shared `is_shipped` predicate.** *Rationale:* helper and guard must never drift on what "shipped" means.
- **Guard unchanged as backstop.** *Rationale:* a bypassed/missed bump degrades to a visible block, never a silent stale-cache publish.
- **Everything under `.claude/`, repo-only.** *Rationale:* versioning governance is this-repo-specific (like the guard); not distributed by ralph-init, no R11 parity.

**Scope cuts:**
- No pre-commit/pre-push auto-fix; no `git fetch`; no `push.py` change; no `major` auto; no distributed tag/version locking; no `plugins/ralph/` files; the one-time TASK-215 legacy bump is separate.

**Acceptance criteria (sketch):**
- `.claude/hooks/bump-version.sh` exists, executable, supports `--auto`, `patch|minor|major`, `--tag`, `--no-commit`.
- Shared `is_shipped` snippet sourced by BOTH `bump-version.sh` and `version-bump-guard.sh` (no duplicated inline case-glob).
- `--auto` no-ops when no shipped-set path in `master..HEAD`.
- `--auto` infers minor on a newly-added skill dir/agent file, patch otherwise, never major.
- `--auto` computes vs local master, idempotent when already ahead, edits both JSONs to the same value, commits branch-aware single-line message.
- `--tag` creates annotated `vX.Y.Z` on HEAD if absent, idempotent skip if present; repo config `push.followTags=true` set.
- CLAUDE.md Merge step documents the two actions in order.
- `post-commit` prints a non-blocking nudge on shipped change without a bump.
- `version-bump-guard.sh` behavior unchanged (still blocks a bypassed shipped-change-without-bump).
- bats + `uv run pytest` + `uv run ruff check .` green; all new tooling under `.claude/`, nothing under `plugins/ralph/`.

**Implementation checklist:**
- Factor `is_shipped` into `.claude/hooks/lib/shipped-set.sh`; source it from `version-bump-guard.sh` (behavior-preserving refactor) and the new helper.
- Write `.claude/hooks/bump-version.sh` (`--auto` / explicit increment / `--tag` / `--no-commit`; inference; local-master target; idempotence; branch-aware commit).
- Set repo-local `git config push.followTags true` and document it.
- Extend `post-commit` with the non-blocking nudge.
- Update CLAUDE.md Task Lifecycle Merge step (steps a–e).
- Add `tests/unit/bump-version.bats` mirroring `version-bump-guard.bats` (no-op / patch / minor / idempotent / tag create+skip / branch-aware message).
- Verify: bats, pytest, ruff green; grep confirms nothing added under `plugins/ralph/`.
