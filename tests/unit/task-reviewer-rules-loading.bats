#!/usr/bin/env bats
# task-reviewer rule tiers: the agent loads user-global, the shared docs and
# infra bundles shipped in the plugin, and project rules additively in that
# order; ralph-init upgrade hints at project-file headings that duplicate the
# shipped docs rules.
#
# Both snippets are extracted from the shipped files and run as-is against
# fixtures, so the test follows the documented code rather than a copy of it.
# The loader's plugin-root and project-root references are substituted in the
# snippet TEXT, the way Claude Code substitutes them when it loads the agent
# Markdown, and the snippet then runs with those names absent from the
# environment: exporting them would only prove that the shell expands them.

PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
AGENT="$PROJECT_ROOT/plugins/ralph/agents/task-reviewer.md"
SKILL="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/SKILL.md"

load '../helpers/common'

# Print the first ```bash fence that follows the first line matching $2 in $1.
# The fence may be indented (as inside a markdown list item); the indent is
# stripped.
extract_snippet() {
  awk -v anchor="$2" '
    !found && index($0, anchor) { found = 1; next }
    found && !in_block && $0 ~ /^[ \t]*```bash[ \t]*$/ {
      in_block = 1; match($0, /^[ \t]*/); indent = RLENGTH; next
    }
    in_block && $0 ~ /^[ \t]*```[ \t]*$/ { exit }
    in_block { print substr($0, indent + 1) }
  ' "$1"
}

setup() {
  WORK="$(make_temp_dir)"
  FAKE_HOME="$(make_temp_dir)"
  PLUGIN="$(make_temp_dir)"
  mkdir -p "$WORK/.claude" "$FAKE_HOME/.claude" \
    "$PLUGIN/.claude-plugin" "$PLUGIN/skills/ralph-init/rules"
  printf '{\n  "name": "ralph",\n  "version": "7.8.9"\n}\n' > "$PLUGIN/.claude-plugin/plugin.json"
  BUNDLE="$PLUGIN/skills/ralph-init/rules/task-reviewer-rules.docs.md"
  printf '<!-- header: for example "replaces R-DOCS-3" -->\n\nDOCS-RULE\n' > "$BUNDLE"
  INFRA="$PLUGIN/skills/ralph-init/rules/task-reviewer-rules.infra.md"
  printf '<!-- header: for example "replaces R-INFRA-3" -->\n\n## R-INFRA-3: INFRA-RULE\n' > "$INFRA"
  RAW_LOADER="$WORK/loader.raw.sh"
  extract_snippet "$AGENT" "## Custom Rules Loading" > "$RAW_LOADER"
  HINTER="$WORK/hinter.sh"
  extract_snippet "$SKILL" '- **`.claude/task-reviewer-rules.md`** — project-owned' > "$WORK/hinter.raw.sh"
  hinter="$(cat "$WORK/hinter.raw.sh")"
  printf '%s\n' "${hinter//'${CLAUDE_PLUGIN_ROOT}'/$PLUGIN}" > "$HINTER"
}

# Model Claude Code's Markdown substitution: replace the literal braced
# references in the snippet text with the plugin root $1 and project root $2.
substitute() {
  local text
  text="$(cat "$RAW_LOADER")"
  text="${text//'${CLAUDE_PLUGIN_ROOT}'/$1}"
  text="${text//'${CLAUDE_PROJECT_DIR}'/$2}"
  printf '%s\n' "$text"
}

# Run the loader substituted for plugin root $1 (default: fixture plugin) from
# working directory $2 (default: the project root).
run_loader() {
  substitute "${1:-$PLUGIN}" "$WORK" > "$WORK/loader.sh"
  run env -u CLAUDE_PLUGIN_ROOT -u CLAUDE_PROJECT_DIR HOME="$FAKE_HOME" \
    bash -c 'cd "$1" && bash "$2"' _ "${2:-$WORK}" "$WORK/loader.sh"
}

@test "loader resolves the bundle and project files through quoted braced references" {
  [ -s "$RAW_LOADER" ]
  grep -qF '"${CLAUDE_PLUGIN_ROOT}"/skills/ralph-init/rules/task-reviewer-rules.docs.md' "$RAW_LOADER"
  grep -qF '"${CLAUDE_PROJECT_DIR}"/.claude/task-reviewer-rules.md' "$RAW_LOADER"
  # No bare-dollar (environment) form anywhere in the agent file.
  run grep -nE '\$CLAUDE_(PLUGIN_ROOT|PROJECT_DIR)' "$AGENT"
  [ "$status" -eq 1 ]
}

@test "agent no longer reads a per-project copy of the shared docs rules" {
  run grep -n '\.claude/task-reviewer-rules\.docs\.md' "$AGENT"
  [ "$status" -eq 1 ]
}

@test "substitution leaves no plugin-root or project-root reference in the snippet" {
  substitute "$PLUGIN" "$WORK" > "$WORK/loader.sh"
  run grep -nE 'CLAUDE_(PLUGIN_ROOT|PROJECT_DIR)' "$WORK/loader.sh"
  [ "$status" -eq 1 ]
}

@test "all three tiers load additively in order user-global, shared docs, project" {
  echo "GLOBAL-RULE" > "$FAKE_HOME/.claude/task-reviewer-rules.md"
  echo "docs_rules=on" > "$WORK/.claude/task-reviewer.conf"
  echo "PROJECT-RULE" > "$WORK/.claude/task-reviewer-rules.md"
  run_loader
  [ "$status" -eq 0 ]
  [[ "$output" == *GLOBAL-RULE*DOCS-RULE*PROJECT-RULE* ]]
  [[ "$output" == *"tier user-global: loaded"*"tier shared docs: loaded ($BUNDLE)"*"tier project: loaded ($WORK/.claude/task-reviewer-rules.md)"* ]]
  [[ "$output" != *ERROR* ]]
}

@test "project tier loads when the loader runs from a subdirectory" {
  echo "PROJECT-RULE" > "$WORK/.claude/task-reviewer-rules.md"
  mkdir -p "$WORK/deep/sub"
  run_loader "$PLUGIN" "$WORK/deep/sub"
  [ "$status" -eq 0 ]
  [[ "$output" == *"tier project: loaded ($WORK/.claude/task-reviewer-rules.md)"* ]]
  [[ "$output" == *PROJECT-RULE* ]]
}

@test "a shared docs copy left in the project is inert" {
  # An un-upgraded Documentation / Mixed project: vault, legacy copy, no conf.
  mkdir "$WORK/.obsidian"
  echo "STALE-COPY" > "$WORK/.claude/task-reviewer-rules.docs.md"
  run_loader
  [ "$status" -eq 0 ]
  [[ "$output" != *ERROR:* ]]
  [[ "$output" == *DOCS-RULE* ]]
  [[ "$output" != *STALE-COPY* ]]
}

@test "docs_rules=off excludes the bundle even in a vault project" {
  mkdir "$WORK/.obsidian"
  echo "docs_rules=off" > "$WORK/.claude/task-reviewer.conf"
  run_loader
  [[ "$output" == *"tier shared docs: not applied (docs_rules=off in $WORK/.claude/task-reviewer.conf)"* ]]
  [[ "$output" != *DOCS-RULE* ]]
}

@test "docs_rules=on applies the bundle without a vault, and the last line wins" {
  printf 'docs_rules=off\n docs_rules = on \n' > "$WORK/.claude/task-reviewer.conf"
  run_loader
  [[ "$output" == *"tier shared docs: loaded"* ]]
  [[ "$output" == *DOCS-RULE* ]]
}

@test "unset docs_rules falls back to the .obsidian/ check" {
  run_loader
  [[ "$output" == *"tier shared docs: not applied (docs_rules unset, no $WORK/.obsidian)"* ]]
  [[ "$output" != *DOCS-RULE* ]]
  mkdir "$WORK/.obsidian"
  run_loader
  [[ "$output" == *"tier shared docs: loaded"* ]]
  [[ "$output" == *DOCS-RULE* ]]
}

@test "a docs_rules line with a trailing comment or an empty value is a load error, not a fallback" {
  mkdir "$WORK/.obsidian"
  echo "docs_rules=off # pinned" > "$WORK/.claude/task-reviewer.conf"
  run_loader
  [[ "$output" == *'tier shared docs: ERROR: invalid docs_rules value "off # pinned"'* ]]
  [[ "$output" != *DOCS-RULE* ]]
  echo "docs_rules=" > "$WORK/.claude/task-reviewer.conf"
  run_loader
  [[ "$output" == *'tier shared docs: ERROR: invalid docs_rules value ""'* ]]
  [[ "$output" != *DOCS-RULE* ]]
}

@test "agent documents the docs_rules setting and its unset default" {
  grep -q 'a line `docs_rules=on` or `docs_rules=off` in `.claude/task-reviewer.conf`' "$AGENT"
  grep -q 'When the setting is unset' "$AGENT"
}

@test "a missing shipped bundle is a load error, not a skipped tier" {
  echo "docs_rules=on" > "$WORK/.claude/task-reviewer.conf"
  rm "$BUNDLE"
  run_loader
  [ "$status" -eq 0 ]
  [[ "$output" == *"tier shared docs: ERROR: shipped bundle missing or empty ($BUNDLE)"* ]]
  [[ "$output" != *"tier shared docs: not applied"* ]]
}

@test "an empty shipped bundle is a load error" {
  mkdir "$WORK/.obsidian"
  : > "$BUNDLE"
  run_loader
  [[ "$output" == *"tier shared docs: ERROR: shipped bundle missing or empty"* ]]
}

@test "a gate evaluating false never reports an error, even without a bundle" {
  rm "$BUNDLE"
  run_loader
  [[ "$output" == *"tier shared docs: not applied ("* ]]
  [[ "$output" != *ERROR* ]]
}

@test "an invalid docs_rules value is a load error" {
  echo "docs_rules=yes" > "$WORK/.claude/task-reviewer.conf"
  run_loader
  [[ "$output" == *'tier shared docs: ERROR: invalid docs_rules value "yes"'* ]]
  [[ "$output" != *DOCS-RULE* ]]
}

@test "an unsubstituted project root is reported, not silently skipped" {
  # Running the raw snippet with the names absent from the environment is what
  # happens if the Markdown is not substituted: the loader must say so.
  run env -u CLAUDE_PLUGIN_ROOT -u CLAUDE_PROJECT_DIR HOME="$FAKE_HOME" \
    bash -c 'cd "$1" && bash "$2"' _ "$WORK" "$RAW_LOADER"
  [[ "$output" == *"project root: ERROR: unresolved"* ]]
  [[ "$output" == *"plugin version: ERROR: unreadable"* ]]
}

@test "provenance lines record plugin version and resolved bundle path" {
  run_loader
  [ "${lines[0]}" = "plugin version: 7.8.9" ]
  [ "${lines[1]}" = "docs bundle: $BUNDLE" ]
  [ "${lines[2]}" = "infra bundle: $INFRA" ]
  [ "${lines[3]}" = "project root: $WORK" ]
}

@test "override references list rule IDs a loaded rule replaces, skipping HTML comments" {
  echo "docs_rules=on" > "$WORK/.claude/task-reviewer.conf"
  printf '## R-LOCAL-1: x (replaces R-DOCS-4)\n\n## R-LOCAL-2: y, replaces R5\n' \
    > "$WORK/.claude/task-reviewer-rules.md"
  run_loader
  # R-DOCS-3 appears only inside the bundle's HTML-comment header.
  [[ "$output" == *"override references: R-DOCS-4, R5"* ]]
}

@test "no override reference prints none" {
  run_loader
  [[ "$output" == *"override references: none"* ]]
}

@test "empty and missing optional tiers are skipped without masking the others" {
  : > "$FAKE_HOME/.claude/task-reviewer-rules.md"
  echo "PROJECT-RULE" > "$WORK/.claude/task-reviewer-rules.md"
  run_loader
  [ "$status" -eq 0 ]
  [[ "$output" == *"tier user-global: absent"* ]]
  [[ "$output" == *"tier project: loaded"* ]]
  [[ "$output" == *PROJECT-RULE* ]]
}

@test "a project rules file does not hide the user-global tier" {
  echo "GLOBAL-RULE" > "$FAKE_HOME/.claude/task-reviewer-rules.md"
  echo "PROJECT-RULE" > "$WORK/.claude/task-reviewer-rules.md"
  run_loader
  [[ "$output" == *GLOBAL-RULE*PROJECT-RULE* ]]
}

@test "no tier at all loads nothing and reports no error" {
  run_loader
  [ "$status" -eq 0 ]
  [[ "$output" != *"loaded ("* ]]
  [[ "$output" != *ERROR* ]]
  [ "${lines[${#lines[@]}-1]}" = "----- rules -----" ]
}

@test "shipped bundle carries R-DOCS-1..9 once each, behind an HTML-comment header" {
  real="$PROJECT_ROOT/plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.docs.md"
  [ "$(grep -c '^## R-DOCS-' "$real")" -eq 9 ]
  for n in 1 2 3 4 5 6 7 8 9; do
    [ "$(grep -c "^## R-DOCS-$n: " "$real")" -eq 1 ]
  done
  run head -n 5 "$real"
  [[ "$output" == *"<!--"*"project rules belong in .claude/task-reviewer-rules.md"*"-->"* ]]
  [[ "$output" != *overwritten* ]]
}

@test "loader against the real plugin root loads the shipped bundle and its version" {
  echo "docs_rules=on" > "$WORK/.claude/task-reviewer.conf"
  run_loader "$PROJECT_ROOT/plugins/ralph"
  version="$(sed -n 's/.*"version": "\(.*\)".*/\1/p' "$PROJECT_ROOT/plugins/ralph/.claude-plugin/plugin.json")"
  [ "${lines[0]}" = "plugin version: $version" ]
  [[ "$output" == *"tier shared docs: loaded ($PROJECT_ROOT/plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.docs.md)"* ]]
  [ "$(printf '%s\n' "$output" | grep -c '^## R-DOCS-')" -eq 9 ]
  [[ "$output" == *"override references: none"* ]]
}

@test "agent states that an explicit project override of a named shared rule wins" {
  grep -q 'project rule explicitly names a rule ID' "$AGENT"
  grep -q 'the project rule wins' "$AGENT"
}

@test "report format records plugin version, bundle path and overridden rule IDs" {
  grep -q '1. \*\*Rules provenance\*\* — always: the plugin version, the resolved shared docs bundle path' "$AGENT"
  grep -q 'the rule IDs explicitly overridden by a loaded rule' "$AGENT"
}

@test "upgrade hint names each project heading duplicated in the shipped docs rules" {
  [ -s "$HINTER" ]
  grep -qF '"${CLAUDE_PLUGIN_ROOT}"/skills/ralph-init/rules/task-reviewer-rules.docs.md' "$WORK/hinter.raw.sh"
  printf '# T\n\n## R-DOCS-1: A\n\n## R-DOCS-2: B\n' > "$BUNDLE"
  # A legacy project copy is not what the hint reads.
  printf '## R-LOCAL-1: mine\n' > "$WORK/.claude/task-reviewer-rules.docs.md"
  printf '# P\n\n## R-DOCS-1: A\n\n## R-LOCAL-1: mine\n' > "$WORK/.claude/task-reviewer-rules.md"
  run bash -c 'cd "$1" && bash "$2"' _ "$WORK" "$HINTER"
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 1 ]
  [[ "${lines[0]}" == 'hint: .claude/task-reviewer-rules.md repeats "## R-DOCS-1: A"'* ]]
}

@test "upgrade hint is silent without overlap or without a project file" {
  printf '## R-DOCS-1: A\n' > "$BUNDLE"
  run bash -c 'cd "$1" && bash "$2"' _ "$WORK" "$HINTER"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  printf '## R-LOCAL-1: mine\n' > "$WORK/.claude/task-reviewer-rules.md"
  run bash -c 'cd "$1" && bash "$2"' _ "$WORK" "$HINTER"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "loader reads the infra bundle through the quoted braced plugin-root reference" {
  grep -qF '"${CLAUDE_PLUGIN_ROOT}"/skills/ralph-init/rules/task-reviewer-rules.infra.md' "$RAW_LOADER"
}

@test "infra_rules=on loads the infra bundle between the docs and project tiers" {
  printf 'docs_rules=on\ninfra_rules=on\n' > "$WORK/.claude/task-reviewer.conf"
  echo "PROJECT-RULE" > "$WORK/.claude/task-reviewer-rules.md"
  run_loader
  [ "$status" -eq 0 ]
  [[ "$output" == *"tier shared docs: loaded"*"tier shared infra: loaded ($INFRA)"*"tier project: loaded"* ]]
  [[ "$output" == *DOCS-RULE*INFRA-RULE*PROJECT-RULE* ]]
  [[ "$output" != *ERROR* ]]
}

@test "infra_rules=off excludes the infra bundle even with a ralph.sh shim" {
  : > "$WORK/ralph.sh"
  printf 'infra_rules=on\ninfra_rules=off\n' > "$WORK/.claude/task-reviewer.conf"
  run_loader
  [[ "$output" == *"tier shared infra: not applied (infra_rules=off in $WORK/.claude/task-reviewer.conf)"* ]]
  [[ "$output" != *INFRA-RULE* ]]
}

@test "unset infra_rules applies the bundle iff a ralph.sh shim is at the root or scripts/ralph/" {
  run_loader
  [[ "$output" == *"tier shared infra: not applied (infra_rules unset, no $WORK/ralph.sh or $WORK/scripts/ralph/ralph.sh)"* ]]
  [[ "$output" != *INFRA-RULE* ]]
  : > "$WORK/ralph.sh"
  run_loader
  [[ "$output" == *"tier shared infra: loaded ($INFRA)"* ]]
  [[ "$output" == *INFRA-RULE* ]]
  rm "$WORK/ralph.sh"
  mkdir -p "$WORK/scripts/ralph"
  : > "$WORK/scripts/ralph/ralph.sh"
  run_loader
  [[ "$output" == *"tier shared infra: loaded ($INFRA)"* ]]
  [[ "$output" == *INFRA-RULE* ]]
}

@test "an invalid infra_rules value is a load error, not a fallback to the shim check" {
  : > "$WORK/ralph.sh"
  echo "infra_rules=yes" > "$WORK/.claude/task-reviewer.conf"
  run_loader
  [[ "$output" == *'tier shared infra: ERROR: invalid infra_rules value "yes"'* ]]
  [[ "$output" != *INFRA-RULE* ]]
  echo "infra_rules=on # pinned" > "$WORK/.claude/task-reviewer.conf"
  run_loader
  [[ "$output" == *'tier shared infra: ERROR: invalid infra_rules value "on # pinned"'* ]]
}

@test "a missing or empty infra bundle that applies is a load error" {
  : > "$WORK/ralph.sh"
  rm "$INFRA"
  run_loader
  [ "$status" -eq 0 ]
  [[ "$output" == *"tier shared infra: ERROR: shipped bundle missing or empty ($INFRA); applies by infra_rules unset, $WORK/ralph.sh exists"* ]]
  : > "$INFRA"
  echo "infra_rules=on" > "$WORK/.claude/task-reviewer.conf"
  run_loader
  [[ "$output" == *"tier shared infra: ERROR: shipped bundle missing or empty ($INFRA); applies by infra_rules=on"* ]]
}

@test "the infra setting does not leak into the docs gate" {
  printf 'infra_rules=on\n' > "$WORK/.claude/task-reviewer.conf"
  run_loader
  [[ "$output" == *"tier shared docs: not applied (docs_rules unset, no $WORK/.obsidian)"* ]]
  [[ "$output" == *"tier shared infra: loaded"* ]]
}

@test "a project rule replacing an R-INFRA rule is reported under override references" {
  echo "infra_rules=on" > "$WORK/.claude/task-reviewer.conf"
  printf '## R-LOCAL-1: hooks may be inline (replaces R-INFRA-5)\n' > "$WORK/.claude/task-reviewer-rules.md"
  run_loader
  # The bundle header names R-INFRA-3 inside an HTML comment; only the project rule counts.
  [ "$(printf '%s\n' "$output" | grep '^override references:')" = "override references: R-INFRA-5" ]
  [[ "$output" == *"tier shared infra: loaded"* ]]
}

@test "agent documents the infra_rules setting and its unset default" {
  grep -q 'a line `infra_rules=on` or `infra_rules=off` in `.claude/task-reviewer.conf`' "$AGENT"
  grep -q 'a `ralph.sh` shim at the project root or at `scripts/ralph/ralph.sh`' "$AGENT"
}

@test "loader against the real plugin root loads the shipped infra bundle" {
  echo "infra_rules=on" > "$WORK/.claude/task-reviewer.conf"
  run_loader "$PROJECT_ROOT/plugins/ralph"
  [[ "$output" == *"tier shared infra: loaded ($PROJECT_ROOT/plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md)"* ]]
  [ "$(printf '%s\n' "$output" | grep -c '^## R-INFRA-')" -eq 7 ]
  [[ "$output" == *"override references: none"* ]]
}
