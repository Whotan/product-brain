#!/usr/bin/env bash
# Install the brainify skill so Claude Code / Cowork can discover it.
#
# Usage:
#   bin/install-skill.sh              # personal install: ~/.claude/skills (all your projects)
#   bin/install-skill.sh --project    # project install: ./.claude/skills (this repo, shareable via git)
#   bin/install-skill.sh /custom/dir  # install into a specific skills directory
#
# Claude Code watches these directories, so the skill becomes available in your
# current session without a restart. Then say: "set up product brain".

set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)/skills/brainify"

case "${1:-}" in
  --project) DEST="$(pwd)/.claude/skills" ;;
  "")        DEST="$HOME/.claude/skills" ;;
  *)         DEST="$1" ;;
esac

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "error: can't find the skill at $SRC" >&2
  exit 1
fi

mkdir -p "$DEST"
rm -rf "$DEST/brainify"
cp -R "$SRC" "$DEST/brainify"

echo "✅ Installed brainify → $DEST/brainify"
echo "   Open Claude Code (or Cowork) and say: \"set up product brain\""
