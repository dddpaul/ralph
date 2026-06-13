#!/bin/bash
# master-branch-guard.sh — Block file edits on master branch within the project tree
#   (except .claude/, design/, .obsidian/, .vscode/, .idea/, .cursor/, .zed/, .fleet/,
#   .gitignore). Paths outside the project root pass through.
# Trigger: Edit|Write (all)
# Action: deny JSON (PreToolUse)
# Input: tool_input JSON on stdin

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)
if [ "$branch" != "master" ]; then exit 0; fi

path=$(jq -r '.tool_input.file_path // empty')
[ -z "$path" ] && exit 0

# Resolve relative paths against the current working directory so the prefix check is meaningful.
case "$path" in
  /*) abs_path="$path" ;;
  *)  abs_path="$PWD/$path" ;;
esac

# Outside the project tree → not our concern. (Includes /tmp, $TMPDIR, $HOME/Downloads, sibling repos.)
project_root=$(git rev-parse --show-toplevel 2>/dev/null)
[ -z "$project_root" ] && exit 0
case "$abs_path" in
  "$project_root"|"$project_root"/*) ;;
  *) exit 0 ;;
esac

# Inside the project tree: apply existing in-tree exemptions.
case "$path" in */.claude/*|.claude/*) exit 0;; esac
case "$path" in */design/*|design/*) exit 0;; esac
case "$path" in */.obsidian/*|.obsidian/*) exit 0;; esac
case "$path" in */.vscode/*|.vscode/*) exit 0;; esac
case "$path" in */.idea/*|.idea/*) exit 0;; esac
case "$path" in */.cursor/*|.cursor/*) exit 0;; esac
case "$path" in */.zed/*|.zed/*) exit 0;; esac
case "$path" in */.fleet/*|.fleet/*) exit 0;; esac
if [ "$(basename "$path")" = ".gitignore" ]; then exit 0; fi

echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED: no active task branch. Create a backlog task and `git checkout -b task-<id>-<desc> master` first."}}'
