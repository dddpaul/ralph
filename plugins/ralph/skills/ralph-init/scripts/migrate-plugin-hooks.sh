#!/usr/bin/env bash
# Migrate a project from the legacy copied guard hooks to the ralph plugin's
# hooks.
#
#   migrate-plugin-hooks.sh tracked [--local-guards <name>[,<name>...]] [<project-dir>]
#       Migrates the project's tracked files, once per project, on one host.
#       <project-dir> defaults to the current directory; its git root is
#       migrated. --local-guards (repeatable; commas or spaces) names guards the
#       project keeps as its own copies. It commits nothing: review the result
#       and commit it once, then push; the other host pulls it.
#   Exit 0 = migrated or nothing to change, 2 = usage error, unreadable or
#   malformed input, or jq not found.
#
# The steps run in this order, so an interrupted run never leaves a guard that
# neither the plugin nor a legacy copy enforces:
#
#   1. marker    — .claude/ralph.json gets "pluginHooks": true, keeping every
#                  existing key; --local-guards names are added to
#                  "localGuards". From here on the plugin enforces every guard
#                  not in localGuards (run.sh), so the legacy wiring that is
#                  still present only checks a second time.
#   2. gitignore — .gitignore gets the !.claude/ralph.json exception, so the
#                  marker can be committed.
#   3. settings  — .claude/settings.json loses the hook entries whose command
#                  runs a managed guard copy that is not in localGuards; every
#                  other entry and key stays. The file is deleted only when
#                  nothing is left in it.
#   4. hooks     — the managed guard copies in .claude/hooks/ that are not in
#                  localGuards are deleted, one by one.
#
# Managed guards are the six Claude guards the ralph-init template
# settings.json registers. Every other file in .claude/hooks/ is the project's
# own and is never touched. filename-length-guard.sh is kept too: it is a git
# hook helper, not a Claude guard, and a clone whose .git/hooks/pre-commit is
# still the legacy copy falls back to it until that clone runs the plugin shim.
# A second run changes nothing. RALPH_MIGRATE_STOP_AFTER=<step> (marker,
# gitignore, settings or hooks:<guard>) exits 3 right after that step; the
# tests use it to stop the run at every interruption point.
set -euo pipefail
unset CDPATH

MANAGED="commit-msg-guard commit-prefix-guard master-branch-guard naming-guard notes-guard task-validator"
EXCEPTION='!.claude/ralph.json'

usage() {
  echo "usage: migrate-plugin-hooks.sh tracked [--local-guards <name>[,<name>...]] [<project-dir>]" >&2
  exit 2
}

die() {
  echo "migrate-plugin-hooks: $*" >&2
  exit 2
}

stop_after() {
  if [ "${RALPH_MIGRATE_STOP_AFTER:-}" = "$1" ]; then
    echo "migrate-plugin-hooks: stopped after $1 (RALPH_MIGRATE_STOP_AFTER)" >&2
    exit 3
  fi
}

is_managed() {
  case " $MANAGED " in *" $1 "*) return 0 ;; *) return 1 ;; esac
}

# Write stdin to file $1 through a temporary file in the same directory, so a
# reader never sees a half-written file.
write_file() {
  local tmp
  tmp=$(mktemp "$(dirname "$1")/.migrate.XXXXXX")
  cat >"$tmp"
  mv -f "$tmp" "$1"
}

# Succeed when JSON files/strings $1 and $2 hold the same value.
same_json() {
  "$jq" -en --argjson a "$1" --argjson b "$2" '$a == $b' >/dev/null
}

[ $# -ge 1 ] || usage
[ "$1" = tracked ] || usage
shift
requested=""
project=""
while [ $# -gt 0 ]; do
  case $1 in
    --local-guards)
      [ $# -ge 2 ] || usage
      requested="$requested,$2"
      shift 2
      ;;
    --local-guards=*)
      requested="$requested,${1#--local-guards=}"
      shift
      ;;
    -*) usage ;;
    *)
      [ -z "$project" ] || usage
      project=$1
      shift
      ;;
  esac
done
requested=$(printf '%s\n' "$requested" | tr ', ' '\n\n' | awk 'NF && !seen[$0]++')
for name in $requested; do
  is_managed "$name" || die "unknown guard '$name' in --local-guards (managed guards: $MANAGED)"
done

root=$(cd "${project:-.}" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null) ||
  die "${project:-.} is not inside a git repository"
root=$(cd "$root" && pwd -P)
here=$(cd "$(dirname "$0")" && pwd -P)
plugin_hooks=${CLAUDE_PLUGIN_ROOT:-$here/../../..}/hooks

jq=$(command -v jq 2>/dev/null) || jq=$(git -C "$root" config ralph.jq 2>/dev/null) || jq=
[ -n "$jq" ] && [ -x "$jq" ] || die "jq not found (PATH or git config ralph.jq)"

marker=$root/.claude/ralph.json
gitignore=$root/.gitignore
settings=$root/.claude/settings.json
hooks_dir=$root/.claude/hooks
changed=0

# Read both JSON inputs before writing anything, so a malformed file stops the
# run with the project untouched.
current='{}'
if [ -e "$marker" ]; then
  current=$(cat "$marker") || die "cannot read $marker"
  "$jq" -en --argjson m "$current" '($m | type) == "object" and ($m.localGuards == null or ($m.localGuards | type) == "array")' >/dev/null 2>&1 ||
    die "$marker is not a JSON object with an array localGuards; fix it by hand"
fi
if [ -e "$settings" ]; then
  "$jq" -e 'type == "object"' "$settings" >/dev/null 2>&1 || die "$settings is not a JSON object; fix it by hand"
fi

# 1. marker
add=$(printf '%s\n' "$requested" | "$jq" -Rnc '[inputs | select(length > 0)]')
merged=$("$jq" -n --argjson m "$current" --argjson add "$add" '
  $m | .pluginHooks = true
  | if ($add | length) > 0 then .localGuards = ((.localGuards // []) + ($add - (.localGuards // []))) else . end')
if [ ! -e "$marker" ] || ! same_json "$current" "$merged"; then
  mkdir -p "$root/.claude"
  printf '%s\n' "$merged" | "$jq" . | write_file "$marker"
  echo "wrote .claude/ralph.json (pluginHooks true)"
  changed=1
fi
stop_after marker
locals=$("$jq" -r '.localGuards // [] | .[] | strings' "$marker")

# 2. gitignore
if ! { [ -f "$gitignore" ] && grep -Fxq -- "$EXCEPTION" "$gitignore"; }; then
  if [ -s "$gitignore" ] && [ -n "$(tail -c 1 "$gitignore")" ]; then
    printf '\n' >>"$gitignore"
  fi
  printf '%s\n' "$EXCEPTION" >>"$gitignore"
  echo "added $EXCEPTION to .gitignore"
  changed=1
fi
if git -C "$root" check-ignore -q .claude/ralph.json 2>/dev/null; then
  echo "migrate-plugin-hooks: warning: .claude/ralph.json is still ignored; fix .gitignore so it can be committed" >&2
fi
stop_after gitignore

drop=""
for name in $MANAGED; do
  printf '%s\n' "$locals" | grep -Fxq -- "$name" || drop="$drop $name"
done

# 3. settings
# shellcheck disable=SC2016  # $-names belong to jq, not the shell
defs='
  def runs_dropped: (.command? // "") as $c
    | any($drop[]; . as $g | $c | test("^\"?\\$\\{?CLAUDE_PROJECT_DIR\\}?\"?/\\.claude/hooks/" + $g + "\\.sh$"));
  def group_has: (.hooks | type) == "array" and any(.hooks[]; runs_dropped);
  def event_has: type == "array" and any(.[]; group_has);
  def has_dropped: (.hooks | type) == "object" and any(.hooks[]; event_has);
'
if [ -f "$settings" ]; then
  drop_json=$(printf '%s\n' $drop | "$jq" -Rnc '[inputs | select(length > 0)]')
  removed=$("$jq" --argjson drop "$drop_json" "$defs"'[.hooks[]? | arrays | .[] | objects | .hooks? | arrays | .[] | select(runs_dropped)] | length' "$settings")
  if [ "$removed" -gt 0 ]; then
    stripped=$("$jq" --argjson drop "$drop_json" "$defs"'
      if has_dropped then
        .hooks |= (to_entries
          | map(if (.value | event_has) then
                  .value |= map(if group_has then (.hooks |= map(select(runs_dropped | not))) | select(.hooks != []) else . end)
                  | select(.value != [])
                else . end)
          | from_entries)
        | if .hooks == {} then del(.hooks) else . end
      else . end' "$settings")
    if [ "$stripped" = '{}' ]; then
      rm -f "$settings"
      echo "removed $removed managed hook entries from .claude/settings.json and deleted it (nothing left)"
    else
      printf '%s\n' "$stripped" | write_file "$settings"
      echo "removed $removed managed hook entries from .claude/settings.json"
    fi
    changed=1
  fi
fi
stop_after settings

# 4. hooks
for name in $drop; do
  copy=$hooks_dir/$name.sh
  if [ -e "$copy" ] || [ -L "$copy" ]; then
    note=""
    if [ -r "$plugin_hooks/$name.sh" ] && ! cmp -s "$copy" "$plugin_hooks/$name.sh"; then
      note=" (it differed from the plugin's copy; restore it from git and rerun with --local-guards $name to keep it)"
    fi
    rm -f "$copy"
    echo "deleted .claude/hooks/$name.sh$note"
    changed=1
  fi
  stop_after "hooks:$name"
done
[ ! -d "$hooks_dir" ] || rmdir "$hooks_dir" 2>/dev/null || true

for name in $locals; do
  is_managed "$name" || continue
  [ -f "$hooks_dir/$name.sh" ] ||
    echo "migrate-plugin-hooks: warning: local guard $name has no .claude/hooks/$name.sh copy; nothing enforces it" >&2
done

if [ "$changed" -eq 0 ]; then
  echo "tracked: nothing to change"
else
  echo "tracked: done; review the result and commit it once, on one host (this script commits nothing)"
fi
