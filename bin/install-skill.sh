#!/usr/bin/env bash
# Install the brainify skill and the pb CLI.
#
# Usage:
#   bin/install-skill.sh                    # install both skill + pb (recommended)
#   bin/install-skill.sh --project          # skill into ./.claude/skills (shareable via git)
#   bin/install-skill.sh --link             # symlink the skill too (always up to date)
#   bin/install-skill.sh --no-pb            # skill only, skip pb
#   bin/install-skill.sh --pb-dir DIR       # install pb into DIR instead of ~/.local/bin
#   bin/install-skill.sh /custom/skills/dir # skill into a specific skills directory
#
# Skill: copy (default) = snapshot; re-run this script after pulling updates.
#        --link = always reflects the repo — nothing to re-run.
# pb:    always installed as a symlink so it stays current automatically.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/skills/brainify"
PB_SRC="$ROOT/bin/pb"
VER="$( [ -f "$ROOT/VERSION" ] && cat "$ROOT/VERSION" || echo "?" )"

LINK=0
SKILL_DEST="$HOME/.claude/skills"
PB_DEST="$HOME/.local/bin"
INSTALL_PB=1
NEXT_IS_PB_DIR=0

for arg in "$@"; do
  if [ "$NEXT_IS_PB_DIR" -eq 1 ]; then
    PB_DEST="$arg"
    NEXT_IS_PB_DIR=0
    continue
  fi
  case "$arg" in
    --link)     LINK=1 ;;
    --project)  SKILL_DEST="$(pwd)/.claude/skills" ;;
    --no-pb)    INSTALL_PB=0 ;;
    --pb-dir)   NEXT_IS_PB_DIR=1 ;;
    --*)        echo "unknown option: $arg" >&2; exit 2 ;;
    *)          SKILL_DEST="$arg" ;;
  esac
done

# ── 1. Skill ─────────────────────────────────────────────────────────────────
if [ ! -f "$SRC/SKILL.md" ]; then
  echo "error: can't find the skill at $SRC" >&2; exit 1
fi

mkdir -p "$SKILL_DEST"
rm -rf "$SKILL_DEST/brainify"

if [ "$LINK" -eq 1 ]; then
  ln -s "$SRC" "$SKILL_DEST/brainify"
  echo "🔗 Skill linked  → $SKILL_DEST/brainify  (always reflects this repo)"
else
  cp -R "$SRC" "$SKILL_DEST/brainify"
  echo "✅ Skill copied  → $SKILL_DEST/brainify  (snapshot — re-run to update)"
fi

# ── 2. pb CLI ─────────────────────────────────────────────────────────────────
if [ "$INSTALL_PB" -eq 1 ]; then
  mkdir -p "$PB_DEST"
  ln -sf "$PB_SRC" "$PB_DEST/pb"
  echo "🔗 pb linked     → $PB_DEST/pb  (always reflects this repo)"

  # Warn if the destination isn't on PATH yet.
  case ":$PATH:" in
    *":$PB_DEST:"*) ;;
    *)
      echo ""
      echo "   ⚠️  $PB_DEST is not on your PATH."
      echo "   Add this to your shell profile (~/.zshrc, ~/.bashrc, etc.) and reload:"
      echo ""
      echo "      export PATH=\"$PB_DEST:\$PATH\""
      ;;
  esac
fi

echo ""
echo "   Check anytime:    pb version"
echo "   Start using it:   open Claude Code and say \"set up product brain\""
