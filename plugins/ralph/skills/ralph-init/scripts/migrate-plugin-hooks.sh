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
#   migrate-plugin-hooks.sh clone [<project-dir>]
#       Migrates this clone, once per clone on each host; on the second host,
#       run it after the git pull that brings the tracked part. It commits
#       nothing and never sets ralph.sharedBacklog (that is an explicit step).
#   Exit 0 = migrated or nothing to change, 1 = clone refused (a hook it would
#   have to overwrite or drop; the message says which), 2 = usage error,
#   unreadable or malformed input, or jq not found.
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
#                  runs a managed guard copy that is not in localGuards, in
#                  any form ralph-init has shipped ("$CLAUDE_PROJECT_DIR"/,
#                  quoted whole, or relative .claude/hooks/<guard>.sh); every
#                  other entry and key stays. The file is deleted only when
#                  nothing is left in it.
#   4. hooks     — the managed guard copies in .claude/hooks/ that are not in
#                  localGuards are deleted, one by one. A copy that a remaining
#                  settings.json command still names is kept, with a warning,
#                  so no entry is left calling a missing script.
#
# Managed guards are the six Claude guards older ralph-init versions copied
# into .claude/hooks/ and registered in .claude/settings.json. Every other file
# in .claude/hooks/ is the project's own and is never touched. filename-length-guard.sh is kept too: it is a git
# hook helper, not a Claude guard, and a clone whose .git/hooks/pre-commit is
# still the legacy copy falls back to it until that clone runs the plugin shim.
# A second run changes nothing. RALPH_MIGRATE_STOP_AFTER=<step> (marker,
# gitignore, settings or hooks:<guard>) exits 3 right after that step; the
# tests use it to stop the run at every interruption point.
#
# clone checks every git hook before it writes anything, then:
#
#   1. config   — saves git config ralph.jq (the jq it found), ralph.projectPath
#                 (the canonical main worktree root, the identity the plugin
#                 resolver matches) and, when the Claude config dir is not
#                 $HOME/.claude, ralph.claudeConfigDir.
#   2. shims    — installs the plugin shim (templates/shims/git-hook) as
#                 pre-commit, commit-msg and post-commit in the directory
#                 `git rev-parse --git-path hooks` returns. A hook that is
#                 absent or a legacy copy of the plugin's hook body
#                 (git-hooks/<name>) is replaced. A hook that
#                 differs and that .claude/managed-file-drift.accept lists for
#                 .git/hooks/<name> is kept as <name>.local, which the shim runs
#                 first. Any other differing hook, or an existing <name>.local
#                 with other content, stops the run before anything is written:
#                 a <name>.local is never overwritten.
#   3. switch   — sets git config ralph.pluginHooks true, so pre-commit and
#                 commit-msg block when the plugin cannot be resolved.
#   4. allow    — removes from .claude/settings.local.json each entry of the
#                 plugin's user-settings.json fragment that the user settings
#                 file already holds with the same value, and reports the
#                 entries it kept because the user settings lack them. The file
#                 is deleted only when nothing is left in it.
#
# A second clone run changes nothing. RALPH_MIGRATE_STOP_AFTER also takes the
# clone steps config, shim:<name> and switch.
set -euo pipefail
unset CDPATH

MANAGED="commit-msg-guard commit-prefix-guard master-branch-guard naming-guard notes-guard task-validator"
EXCEPTION='!.claude/ralph.json'

usage() {
  echo "usage: migrate-plugin-hooks.sh tracked [--local-guards <name>[,<name>...]] [<project-dir>]" >&2
  echo "       migrate-plugin-hooks.sh clone [<project-dir>]" >&2
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
# reader never sees a half-written file. An existing file keeps its mode; a new
# one gets 0644 rather than mktemp's 0600.
write_file() {
  local tmp
  tmp=$(mktemp "$(dirname "$1")/.migrate.XXXXXX")
  if [ -e "$1" ]; then cp -p "$1" "$tmp"; else chmod 644 "$tmp"; fi
  cat >"$tmp"
  mv -f "$tmp" "$1"
}

# Succeed when JSON files/strings $1 and $2 hold the same value.
same_json() {
  "$jq" -en --argjson a "$1" --argjson b "$2" '$a == $b' >/dev/null
}

SHIMMED="pre-commit commit-msg post-commit"

refuse() {
  echo "migrate-plugin-hooks: $*" >&2
  exit 1
}

# SHA-256 of stdin, hex only: shasum on macOS, sha256sum on GNU systems.
sha256() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | cut -d' ' -f1
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum | cut -d' ' -f1
  else
    die "neither shasum nor sha256sum is on PATH"
  fi
}

# Print the canonical path of directory $1, or $1 itself when it is no directory.
canonical() {
  (cd "$1" 2>/dev/null && pwd -P) || printf '%s\n' "$1"
}

# Set git config key $1 to $2 in the clone unless it already holds that value.
set_config() {
  if [ "$(git -C "$root" config --get "$1" 2>/dev/null || true)" != "$2" ]; then
    git -C "$root" config "$1" "$2"
    echo "set git config $1 $2"
    changed=1
  fi
}

# Succeed when .claude/managed-file-drift.accept lists hook $1 with its current
# content against template $2, in the line managed-file-drift.sh accept prints.
accepted_hook() {
  local file=$root/.claude/managed-file-drift.accept line
  [ -r "$file" ] && [ -r "$2" ] || return 1
  line=".git/hooks/${1##*/} template=$(sha256 <"$2") project=$(sha256 <"$1")"
  grep -Fxq -- "$line" "$file"
}

# Copy file $1 to $2 through a temporary file in $2's directory, keeping $1's
# mode, or setting mode $3 when given, before the file appears under its name.
copy_into() {
  local tmp
  tmp=$(mktemp "$(dirname "$2")/.migrate.XXXXXX")
  cp -p "$1" "$tmp"
  [ -z "${3:-}" ] || chmod "$3" "$tmp"
  mv -f "$tmp" "$2"
}

# Decide what clone does with each git hook; print "<name>:<action>" lines.
# Exits 1, before anything is written, on a hook it may not replace.
plan_hooks() {
  local name hook loc tmpl
  for name in $SHIMMED; do
    hook=$hooks/$name loc=$hooks/$name.local tmpl=$plugin_root/git-hooks/$name
    if [ ! -e "$hook" ] && [ ! -L "$hook" ]; then
      echo "$name:install"
    elif cmp -s "$hook" "$shim"; then
      echo "$name:keep"
    elif [ -r "$tmpl" ] && cmp -s "$hook" "$tmpl"; then
      echo "$name:replace"
    elif accepted_hook "$hook" "$tmpl"; then
      if { [ -e "$loc" ] || [ -L "$loc" ]; } && ! cmp -s "$hook" "$loc"; then
        refuse "$loc already exists and differs from the accepted $hook; it is never overwritten: merge the two into $name.local by hand, delete $hook, and rerun"
      fi
      echo "$name:local"
    else
      refuse "$hook differs from the plugin's $name hook body and .claude/managed-file-drift.accept does not list it; to keep it as $name.local, accept it (managed-file-drift.sh accept . .git/hooks/$name) and rerun, else delete it and rerun"
    fi
  done
}

# jq program for the allow step: reads .claude/settings.local.json, takes the
# fragment as $f and the user settings as $u, and prints {doc, removed, kept}.
# shellcheck disable=SC2016  # $-names belong to jq, not the shell
TRIM='
  def at($p): try getpath($p) catch null;
  def has_item($a; $i): ($a | type) == "array" and any($a[]; . == $i);
  def entry_label($p; $v): ($p | join(".")) as $k
    | if ($v | type) == "string" and $k == "permissions.allow" then "\($k): \($v)" else "\($k)=\($v | tojson)" end;
  def prune($p): if ($p | length) == 0 then .
    else at($p) as $v | if $v == null or $v == [] or $v == {} then delpaths([$p]) | prune($p[:-1]) else . end end;
  [$f | paths(type != "object") | select(all(.[]; type == "string"))] as $ps
  | reduce $ps[] as $p ({doc: ., rm: [], kept: []};
      ($f | getpath($p)) as $fv | (.doc | at($p)) as $lv | ($u | at($p)) as $uv
      | if ($fv | type) == "array" then
          if ($lv | type) == "array" then
            [$lv[] | select(has_item($fv; .))] as $common
            | [$common[] | select(has_item($uv; .))] as $gone
            | .doc |= setpath($p; [$lv[] | select(has_item($gone; .) | not)])
            | .rm += [$gone[] | {p: $p, l: entry_label($p; .)}]
            | .kept += [$common[] | select(has_item($gone; .) | not) | entry_label($p; .)]
          else . end
        elif $lv == $fv then
          if $uv == $fv then .doc |= delpaths([$p]) | .rm += [{p: $p, l: entry_label($p; $fv)}]
          else .kept += [entry_label($p; $fv)] end
        else . end)
  | .doc = (reduce ([.rm[].p] | unique)[] as $p (.doc; prune($p)))
  | {doc, removed: [.rm[].l], kept}
'

clone_main() {
  local project="" common main hooks plugin_root templates shim fragment cfg user local_settings plan name action out kept
  while [ $# -gt 0 ]; do
    case $1 in
      -*) usage ;;
      *)
        [ -z "$project" ] || usage
        project=$1
        shift
        ;;
    esac
  done
  root=$(cd "${project:-.}" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null) ||
    die "${project:-.} is not inside a git repository"
  root=$(cd "$root" && pwd -P)
  common=$(cd "$root" && c=$(git rev-parse --git-common-dir) && cd "$c" && pwd -P) ||
    die "cannot find the git common dir of $root"
  case $common in
    */.git) main=${common%/.git} ;;
    *) die "separate git dir layout is not supported (git common dir $common is not <root>/.git)" ;;
  esac
  [ -n "$main" ] || main=/
  hooks=$(cd "$root" && git rev-parse --git-path hooks) || die "cannot find the git hooks directory of $root"
  case $hooks in /*) ;; *) hooks=$root/$hooks ;; esac

  here=$(cd "$(dirname "$0")" && pwd -P)
  plugin_root=$(canonical "${CLAUDE_PLUGIN_ROOT:-$here/../../..}")
  templates=$plugin_root/skills/ralph-init/templates
  shim=$templates/shims/git-hook
  fragment=$plugin_root/user-settings.json
  [ -r "$shim" ] || die "cannot read the plugin shim $shim"
  [ -r "$fragment" ] || die "cannot read the plugin fragment $fragment"

  jq=$(command -v jq 2>/dev/null) || jq=$(git -C "$root" config ralph.jq 2>/dev/null) || jq=
  [ -n "$jq" ] && [ -x "$jq" ] || die "jq not found (PATH or git config ralph.jq)"
  case $jq in /*) ;; *) jq=$(cd "$(dirname "$jq")" && pwd -P)/${jq##*/} ;; esac

  cfg=${CLAUDE_CONFIG_DIR:-}
  [ -n "$cfg" ] || cfg=$(git -C "$root" config ralph.claudeConfigDir 2>/dev/null) || true
  [ -n "$cfg" ] || cfg=$HOME/.claude
  user=$cfg/settings.json
  local_settings=$root/.claude/settings.local.json

  # Check everything before writing anything.
  "$jq" -e 'type == "object"' "$fragment" >/dev/null 2>&1 || die "$fragment is not a JSON object"
  if [ -e "$local_settings" ]; then
    "$jq" -e 'type == "object"' "$local_settings" >/dev/null 2>&1 || die "$local_settings is not a JSON object; fix it by hand"
  fi
  if [ -e "$user" ]; then
    "$jq" -e 'type == "object"' "$user" >/dev/null 2>&1 || die "$user is not a JSON object; fix it by hand"
  fi
  plan=$(plan_hooks) || exit $?
  changed=0

  # 1. config
  set_config ralph.jq "$jq"
  set_config ralph.projectPath "$main"
  if [ -n "${CLAUDE_CONFIG_DIR:-}" ] && [ "$(canonical "$CLAUDE_CONFIG_DIR")" != "$(canonical "$HOME/.claude")" ]; then
    set_config ralph.claudeConfigDir "$(canonical "$CLAUDE_CONFIG_DIR")"
  fi
  stop_after config

  # 2. shims
  mkdir -p "$hooks"
  for line in $plan; do
    name=${line%%:*} action=${line#*:}
    [ "$action" != keep ] || continue
    if [ "$action" = local ] && ! [ -e "$hooks/$name.local" ]; then
      copy_into "$hooks/$name" "$hooks/$name.local"
      echo "kept the accepted $name hook as $name.local"
    fi
    copy_into "$shim" "$hooks/$name" 755
    echo "installed the plugin shim as $name"
    changed=1
    stop_after "shim:$name"
  done

  # 3. switch
  set_config ralph.pluginHooks true
  stop_after switch

  # 4. allow
  if [ -f "$local_settings" ]; then
    out=$("$jq" --slurpfile f "$fragment" --argjson u "$(if [ -f "$user" ]; then cat "$user"; else echo '{}'; fi)" \
      '$f[0] as $f | '"$TRIM" "$local_settings")
    if [ "$(printf '%s\n' "$out" | "$jq" '.removed | length')" -gt 0 ]; then
      if [ "$(printf '%s\n' "$out" | "$jq" -c .doc)" = '{}' ]; then
        rm -f "$local_settings"
        echo "removed every entry from .claude/settings.local.json ($user already holds them) and deleted it"
      else
        printf '%s\n' "$out" | "$jq" .doc | write_file "$local_settings"
        echo "removed $(printf '%s\n' "$out" | "$jq" '.removed | length') entries from .claude/settings.local.json that $user already holds"
      fi
      changed=1
    fi
    kept=$(printf '%s\n' "$out" | "$jq" -r '.kept[]')
    if [ -n "$kept" ]; then
      printf '%s\n' "$kept" | while IFS= read -r line; do
        echo "kept in .claude/settings.local.json, not yet in $user: $line"
      done
      echo "  (add them to $user, e.g. with bash $plugin_root/skills/ralph-run/scripts/merge-user-settings.sh $user, then rerun clone to drop them here)"
    fi
  fi

  if ! "$jq" -e '.pluginHooks == true' "$root/.claude/ralph.json" >/dev/null 2>&1; then
    echo "migrate-plugin-hooks: warning: .claude/ralph.json does not set pluginHooks true; run the tracked part (on one host) and commit it" >&2
  fi
  # shellcheck source=../templates/shims/resolve-plugin.sh
  . "$templates/shims/resolve-plugin.sh"
  if ! ralph_resolve_plugin "$root" git-hooks/pre-commit >/dev/null; then
    echo "migrate-plugin-hooks: warning: the plugin cannot be resolved from this clone (reason above); with ralph.pluginHooks true, commits block until it can (bypass once with git commit --no-verify)" >&2
  fi
  echo "note: the plugin's Claude guard hooks are best effort: a guard hook that cannot start does not block the command; the git hooks still block on ralph.pluginHooks"
  if [ "$changed" -eq 0 ]; then
    echo "clone: nothing to change"
  else
    echo "clone: done; nothing was committed"
  fi
}

[ $# -ge 1 ] || usage
if [ "$1" = clone ]; then
  shift
  clone_main "$@"
  exit 0
fi
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
    | any($drop[]; . as $g | $c | test("(^|[^A-Za-z0-9_.-])\\.claude/hooks/" + $g + "\\.sh([^A-Za-z0-9_.-]|$)"));
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
still=""
if [ -f "$settings" ]; then
  still=$("$jq" -r '.hooks[]? | arrays | .[] | objects | .hooks? | arrays | .[] | .command? | strings' "$settings")
fi

# 4. hooks
for name in $drop; do
  copy=$hooks_dir/$name.sh
  if printf '%s\n' "$still" | grep -Fq -- ".claude/hooks/$name.sh"; then
    echo "migrate-plugin-hooks: warning: kept .claude/hooks/$name.sh: a .claude/settings.json entry still calls it; remove that entry by hand and rerun" >&2
  elif [ -e "$copy" ] || [ -L "$copy" ]; then
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
