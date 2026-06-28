#!/usr/bin/env bash
# Install the brainify skill so Claude Code / Cowork can discover it.
#
# Usage:
#   bin/install-skill.sh                # copy into ~/.claude/skills (all your projects)
#   bin/install-skill.sh --project      # copy into ./.claude/skills (this repo, shareable via git)
#   bin/install-skill.sh --link         # SYMLINK ~/.claude/skills -> this repo (always up to date)
#   bin/install-skill.sh --link --project
#   bin/install-skill.sh /custom/dir    # install into a specific skills directory
#
# Copy vs link:
#   - copy  (default): a snapshot. Re-run this script after you change/pull the skill to refresh it.
#   - --link         : a symlink. The installed skill always reflects this repo — no re-running.
#
# Claude Code watches these directories, so the skill becomes available in your
# current session without a restart. Then say: "set up product brain".

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/skills/brainify"
VER="$( [ -f "$ROOT/VERSION" ] && cat "$ROOT/VERSION" || echo "?" )"

LINK=0
DEST="$HOME/.claude/skills"
for arg in "$@"; do
  case "$arg" in
    --link)    LINK=1 ;;
    --project) DEST="$(pwd)/.claude/skills" ;;
    --*)       echo "unknown option: $arg" >&2; exit 2 ;;
    *)         DEST="$arg" ;;
  esac
done

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "error: can't find the skill at $SRC" >&2
  exit 1
fi

mkdir -p "$DEST"
rm -rf "$DEST/brainify"

if [ "$LINK" -eq 1 ]; then
  ln -s "$SRC" "$DEST/brainify"
  echo "🔗 Linked brainify v$VER → $DEST/brainify  (always reflects this repo)"
else
  cp -R "$SRC" "$DEST/brainify"
  echo "✅ Copied brainify v$VER → $DEST/brainify  (snapshot — re-run to update)"
fi
echo "   Check anytime with: pb version"
echo "   Open Claude Code (or Cowork) and say: \"set up product brain\""
