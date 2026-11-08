# Releasing the ralph plugin (this repo only)

Repo-specific tooling under `.claude/`; not shipped in the plugin and not mirrored to the `ralph-init` templates.

## Once per clone

The pre-push guard and the post-commit bump nudge live in `.git/hooks/`, which is not committed. In every clone, after `migrate-plugin-hooks.sh clone`, run once:

```bash
.claude/hooks/install-clone-hooks.sh
```

It installs the version-bump wrapper (`pre-push.local` behind the plugin shim, or `pre-push` in a clone without one) and the nudge (`post-commit.local`). It never overwrites a differing hook: it names it and exits non-zero. `.claude/hooks/install-clone-hooks.sh --check` only reports, and the repo's SessionStart hook runs it to warn a session in a clone that lacks the hooks. Without them, pushes from that clone skip the guard below.

## Normal release

1. On the task branch, `.claude/hooks/bump-version.sh --auto` sets both manifests (`plugins/ralph/.claude-plugin/plugin.json` `version` and `.claude-plugin/marketplace.json` `metadata.version`) to the next version and commits, iff a shipped file changed.
2. Merge the branch into `master` with `--no-ff`.
3. On `master`, `.claude/hooks/bump-version.sh --tag` creates the annotated tag `vX.Y.Z` on the merge commit.
4. `git push origin master` — `push.followTags` carries the tag.

## The release commit rule

The release commit of `vX.Y.Z` is the first commit, along origin's `master` first-parent history, where both manifests read `X.Y.Z`. The tag, peeled for annotated tags, must point at that commit. Commits after the release that keep the same version do not move the release commit. When that first commit is a merge that brings `X.Y.Z` in from another parent — a merge pull of another host's release — the release commit of that parent's line also counts, so pulling a release by merge or by rebase both pass.

The pre-push guard `.claude/hooks/version-bump-guard.sh` checks this on every push of `master`. It runs `git ls-remote origin 'refs/tags/vX.Y.Z' 'refs/tags/vX.Y.Z^{}'` with a deadline of `VERSION_GUARD_LS_REMOTE_TIMEOUT` seconds (default 20) and refuses the push when:

- origin already has `vX.Y.Z` peeled to a commit other than the pushed tip's release commit (another host released the same version with different content);
- the two manifests disagree on the pushed tip;
- origin cannot be reached within the deadline.

A tag absent from origin passes; the push itself delivers it.

## Resolving a version conflict

A tag on origin is never moved, deleted or force-pushed. Whatever origin tagged as `vX.Y.Z` is what consumers may already have cached under that version.

When the guard reports `version conflict on vX.Y.Z`:

1. Delete only your local, never-pushed tag: `git tag -d vX.Y.Z`. Then `git fetch origin --tags` to get origin's.
2. Bring `master` up to date by merging `origin/master` into it. Never rebase: a rebase rewrites your reviewed commits, so they no longer match the SHAs in their `Review: APPROVED <sha>` notes and R-INFRA-6 flags them (the shared-backlog protocol never rebases either).
3. Re-bump both manifests to a version above `X.Y.Z`, e.g. `.claude/hooks/bump-version.sh patch` on a task branch, then merge it into `master` as usual.
4. On `master`, `.claude/hooks/bump-version.sh --tag` tags the new version; push again.

When origin is unreachable, retry the push once it is. Do not bypass the guard with `--no-verify` to publish a version tag.
