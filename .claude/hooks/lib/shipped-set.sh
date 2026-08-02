# shipped-set.sh — the single definition of the "shipped-and-executed plugin
# surface" for THIS repo. Sourced by BOTH version-bump-guard.sh (the pre-push
# backstop, TASK-214) and bump-version.sh (the auto-bump helper, TASK-217) so
# the two can never drift on what "shipped" means.
#
# A change to any of these paths requires a strictly-greater plugin version in
# plugins/ralph/.claude-plugin/plugin.json AND .claude-plugin/marketplace.json,
# because Claude Code's on-disk plugin cache rebuilds ONLY on a version increase
# (a stale cache silently runs old skill/agent code otherwise):
#   plugins/ralph/skills/**                     plugins/ralph/agents/**
#   plugins/ralph/.claude-plugin/plugin.json    .claude-plugin/marketplace.json
# Excluded (docs & tooling, not shipped-and-executed): README, design/,
# backlog/, .claude/, tests/.
#
# Sourced, not executed: no shebang, no `set`. Portability (R5): POSIX
# case-glob only.

# Is a repo-relative path part of the shipped-and-executed plugin surface?
is_shipped() {
  case "$1" in
    plugins/ralph/skills/*) return 0 ;;
    plugins/ralph/agents/*) return 0 ;;
    plugins/ralph/.claude-plugin/plugin.json) return 0 ;;
    .claude-plugin/marketplace.json) return 0 ;;
    *) return 1 ;;
  esac
}
