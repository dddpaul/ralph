---
id: TASK-341
title: Move git hook chaining into a plugin dispatcher and thin the shim
status: In Progress
assignee: []
created_date: '2026-11-08T09:41:00Z'
updated_date: '2026-11-08T09:45:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-335
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: the git hook shim, plugins/ralph/skills/ralph-init/templates/shims/git-hook, is the same 138-line file in every clone, installed as pre-commit, commit-msg, post-commit and pre-push. Besides the embedded plugin resolver, it chains <name>.local and copies pre-push's stdin through two descriptors on an unlinked temp file (3<&- and exec 0<&3). That copy is hard to read, and it covers post-rewrite and reference-transaction, names no clone installs. This logic is the part most likely to change, and every change to it means refreshing the shim in every clone, while the hook bodies arrive with a plugin update.

Direction: move the .local chaining and the stdin copy into a plugin-shipped dispatcher, plugins/ralph/git-hooks/run, the way plugins/ralph/hooks/run.sh serves the Claude-side guards. The shim keeps only what must run before the plugin is found:
- the resolver block, left byte-identical, so ralph.sh, refine.sh and the shared-backlog shim do not change;
- exec of git-hooks/run;
- the fallback for a missing plugin.

Locked decisions:
- The resolver stays embedded and unchanged. Git hooks run outside Claude Code, with no CLAUDE_PLUGIN_ROOT, and the resolver is what finds the plugin. Compacting it would change every project's ralph.sh and refine.sh; it is out of scope.
- No pointer file and no SessionStart hook (PRD non-goals). No resolved path cached in git config, because it goes stale after /plugin update.
- Only pre-push gets a stdin copy, read once into a variable with no temp file.
- On the fallback path stdin is still unread, so <name>.local gets git's own stdin.
- Behaviour kept: the same arguments reach both hooks, both get identical pre-push stdin, a failing .local stops the hook with its status, the per-switch fail-closed table is unchanged, and core.hooksPath and linked worktrees keep working.
- Accepted differences: on the blocked path .local no longer runs first (still exit 1); on the warn path the warning prints before .local; the bypass hint just says --no-verify.

Prototype, tested with real git commit and git push under /bin/bash 3.2.57 (9/9). plugins/ralph/git-hooks/run:

```bash
#!/usr/bin/env bash
# Ralph git hook dispatcher. The per-clone shim (templates/shims/git-hook) finds
# the installed plugin and execs this file as: run <hook> [git's arguments].
# It runs the clone's own <hook>.local first, then the plugin's <hook> body next
# to this file. Both get git's arguments, and for pre-push the same ref list on
# stdin.
name="$1"
shift
body="$(dirname "$0")/$name"
local_hook="$(git rev-parse --git-path hooks)/$name.local" || exit 1

# git writes pre-push's ref list to stdin once; keep a copy so that both hooks
# read all of it. The trailing x keeps the final newline through $(...).
if [ "$name" = pre-push ]; then
  input="$(cat; echo x)"
  input="${input%x}"
fi

# feed CMD ARGS... — run CMD with git's stdin, or with the copy for pre-push.
feed() {
  if [ "$name" = pre-push ]; then printf '%s' "$input" | "$@"; else "$@"; fi
}

if [ -x "$local_hook" ]; then
  feed "$local_hook" "$@" || exit $?
fi
if [ ! -x "$body" ]; then
  echo "ralph: warning: the ralph plugin ships no $name hook; ran only $name.local" >&2
  exit 0
fi
feed "$body" "$@"
```

Shim: the header comment, the unchanged resolver block, then:

```bash

name="${0##*/}"
if run="$(ralph_resolve_plugin "$PWD" git-hooks/run)"; then
  exec "$run" "$name" "$@"
fi

case "$name" in
  pre-commit | commit-msg) switches="ralph.pluginHooks" ;;
  pre-push) switches="ralph.pluginHooks ralph.sharedBacklog" ;;
  *) switches="" ;;
esac
for switch in $switches; do
  if [ "$(git config --bool "$switch" 2>/dev/null)" = true ]; then
    echo "ralph: $name hook blocked: the ralph plugin cannot be found (reason above) and $switch is true." >&2
    echo "ralph: install or update the ralph plugin, or bypass this once with --no-verify" >&2
    exit 1
  fi
done
echo "ralph: warning: $name hook ran without the ralph plugin, which cannot be found (reason above)" >&2
local_hook="$(git rev-parse --git-path hooks)/$name.local" || exit 1
if [ -x "$local_hook" ]; then
  exec "$local_hook" "$@"
fi
exit 0
```

Migration: this is the first shim change since 777119a. TASK-335's shipped-git-hooks.sha256 'shim <sha256>' lines must then hold both versions; test_shipped_git_hooks.py generates them from git history. With both recorded, clone replaces the old shim in place, preflight reports it as outdated, and enable replaces an old pre-push shim. Old shims keep working until a clone is refreshed, because the bodies stay at git-hooks/<name>. A clone gets the new shim only through migrate-plugin-hooks.sh clone run from an installed plugin, which then ships git-hooks/run. If a new shim meets an older plugin without run, the resolver names git-hooks/run as missing, and the fallback blocks or warns as usual. Order on each host: /plugin update, then clone in each clone.

This repo: .claude/hooks/install-clone-hooks.sh --check compares pre-push byte for byte with the checkout's template, so right after the merge it would report a not-yet-refreshed clone's old shim as differing. Make it accept any shim version recorded in shipped-git-hooks.sha256.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 plugins/ralph/git-hooks/run runs <name>.local, then the plugin's <name> body, with the same arguments and identical pre-push stdin; a failing .local stops the hook with its status; a name with no body warns and exits 0 after .local (pytest)
- [ ] #2 The shim only resolves git-hooks/run and execs it, or falls back; grep -n -E 'exec 3|0<&3' on the shim finds nothing, and its resolver block still matches resolve-plugin.sh (test_resolve_plugin.py passes)
- [ ] #3 When the plugin cannot be found, the shim blocks per switch as before, and otherwise warns and execs <name>.local with git's stdin (pytest)
- [ ] #4 The existing test_git_hook_shim.py cases pass, adapted where needed (core.hooksPath, linked worktree, merge message); the shipped-bodies test allows run, and run gets no hook line in shipped-git-hooks.sha256
- [ ] #5 shipped-git-hooks.sha256 lists both shim versions; clone replaces the old shim in place and preflight reports it as outdated, tested with the real old shim (pytest)
- [ ] #6 .claude/hooks/install-clone-hooks.sh --check accepts a pre-push equal to any shim version recorded in shipped-git-hooks.sha256 (pytest)
- [ ] #7 README.md and .claude/RELEASING.md say to run /plugin update first, then migrate-plugin-hooks.sh clone in each clone
- [ ] #8 bash -n, the bash 3.2 static guard, ruff, pytest and bats pass
- [ ] #9 (host) Both clones are refreshed with clone after /plugin update, and a live commit and push through the new shim are recorded in the notes
<!-- AC:END -->
