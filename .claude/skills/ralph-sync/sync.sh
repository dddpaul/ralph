#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AGENTS_SRC="$REPO_ROOT/agents"
SKILLS_SRC="$REPO_ROOT/skills"
AGENTS_DST="$HOME/.claude/agents"
SKILLS_DST="$HOME/.claude/skills"

MODE="${1:-classify}"
DIFF_PATH="${2:-}"

classify_agents() {
  if [ ! -d "$AGENTS_SRC" ]; then return; fi
  for src_file in "$AGENTS_SRC"/*.md; do
    [ -f "$src_file" ] || continue
    name="$(basename "$src_file")"
    dst_file="$AGENTS_DST/$name"
    if [ ! -f "$dst_file" ]; then
      echo "[new] agent $name"
    elif diff -q "$src_file" "$dst_file" >/dev/null 2>&1; then
      echo "[unchanged] agent $name"
    else
      echo "[updated] agent $name"
    fi
  done

  if [ -d "$AGENTS_DST" ]; then
    for dst_file in "$AGENTS_DST"/*.md; do
      [ -f "$dst_file" ] || continue
      name="$(basename "$dst_file")"
      if [ ! -f "$AGENTS_SRC/$name" ]; then
        echo "[orphan] agent $name"
      fi
    done
  fi
}

classify_skills() {
  if [ ! -d "$SKILLS_SRC" ]; then return; fi
  for src_dir in "$SKILLS_SRC"/*/; do
    [ -d "$src_dir" ] || continue
    name="$(basename "$src_dir")"
    dst_dir="$SKILLS_DST/$name"
    if [ ! -d "$dst_dir" ]; then
      echo "[new] skill $name"
    elif diff -rq "$src_dir" "$dst_dir" >/dev/null 2>&1; then
      echo "[unchanged] skill $name"
    else
      echo "[updated] skill $name"
    fi
  done

  if [ -d "$SKILLS_DST" ]; then
    for dst_dir in "$SKILLS_DST"/*/; do
      [ -d "$dst_dir" ] || continue
      name="$(basename "$dst_dir")"
      if [ ! -d "$SKILLS_SRC/$name" ]; then
        echo "[orphan] skill $name"
      fi
    done
  fi
}

do_classify() {
  local has_changes=0
  local output
  output="$(classify_agents; classify_skills)"

  if [ -z "$output" ]; then
    echo "Nothing to sync (no agents/ or skills/ in repo)."
    exit 0
  fi

  echo "$output" | sort -t' ' -k2,2 -k3,3

  if echo "$output" | grep -qE '^\[(new|updated)\]'; then
    has_changes=1
  else
    echo ""
    echo "Already in sync."
  fi

  exit $has_changes
}

do_apply() {
  local applied=0

  if [ -d "$AGENTS_SRC" ]; then
    mkdir -p "$AGENTS_DST"
    for src_file in "$AGENTS_SRC"/*.md; do
      [ -f "$src_file" ] || continue
      name="$(basename "$src_file")"
      dst_file="$AGENTS_DST/$name"
      if [ ! -f "$dst_file" ]; then
        cp "$src_file" "$dst_file"
        echo "[applied] agent $name (new)"
        applied=$((applied + 1))
      elif ! diff -q "$src_file" "$dst_file" >/dev/null 2>&1; then
        cp "$src_file" "$dst_file"
        echo "[applied] agent $name (updated)"
        applied=$((applied + 1))
      fi
    done
  fi

  if [ -d "$SKILLS_SRC" ]; then
    mkdir -p "$SKILLS_DST"
    for src_dir in "$SKILLS_SRC"/*/; do
      [ -d "$src_dir" ] || continue
      name="$(basename "$src_dir")"
      dst_dir="$SKILLS_DST/$name"
      if [ ! -d "$dst_dir" ]; then
        cp -r "$src_dir" "$dst_dir"
        echo "[applied] skill $name (new)"
        applied=$((applied + 1))
      elif ! diff -rq "$src_dir" "$dst_dir" >/dev/null 2>&1; then
        rm -rf "$dst_dir"
        cp -r "$src_dir" "$dst_dir"
        echo "[applied] skill $name (updated)"
        applied=$((applied + 1))
      fi
    done
  fi

  echo ""
  echo "Applied $applied item(s)."
}

do_diff() {
  if [ -z "$DIFF_PATH" ]; then
    echo "Usage: sync.sh diff <type/name>"
    echo "  e.g. sync.sh diff agent/task-reviewer.md"
    echo "       sync.sh diff skill/ralph-run"
    exit 1
  fi

  local item_type="${DIFF_PATH%%/*}"
  local item_name="${DIFF_PATH#*/}"

  case "$item_type" in
    agent)
      local src="$AGENTS_SRC/$item_name"
      local dst="$AGENTS_DST/$item_name"
      if [ ! -f "$src" ]; then
        echo "Source not found: $src"
        exit 1
      fi
      if [ ! -f "$dst" ]; then
        echo "$item_name is [new] -- no destination file to diff against."
        exit 0
      fi
      diff -ru "$dst" "$src" || true
      ;;
    skill)
      local src="$SKILLS_SRC/$item_name"
      local dst="$SKILLS_DST/$item_name"
      if [ ! -d "$src" ]; then
        echo "Source not found: $src"
        exit 1
      fi
      if [ ! -d "$dst" ]; then
        echo "$item_name is [new] -- no destination directory to diff against."
        exit 0
      fi
      diff -ru "$dst" "$src" || true
      ;;
    *)
      echo "Unknown type: $item_type (expected 'agent' or 'skill')"
      exit 1
      ;;
  esac
}

case "$MODE" in
  classify) do_classify ;;
  apply)    do_apply ;;
  diff)     do_diff ;;
  *)
    echo "Usage: sync.sh <classify|apply|diff> [path]"
    exit 1
    ;;
esac
