#!/usr/bin/env bash
set -euo pipefail
G="\033[0;32m"; R="\033[0;31m"; N="\033[0m"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIM_PYTHON="$PROJECT_DIR/.venv/bin/python"
MANIM_EXECUTABLE="$PROJECT_DIR/.venv/bin/manim"
ok() { echo -e "  ${G}+${N} $1"; }
fail() { echo -e "  ${R}x${N} $1"; }
echo ""; echo "Manim Video Skill — Setup Check"; echo ""
errors=0
if [ -x "$MANIM_PYTHON" ] && [ "$("$MANIM_PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" = "3.11" ]; then
  ok "Isolated Python $("$MANIM_PYTHON" --version 2>&1 | awk '{print $2}')"
else
  fail "Locked Python 3.11 environment missing; run: uv sync --project '$PROJECT_DIR' --frozen"
  errors=$((errors+1))
fi
if [ -x "$MANIM_EXECUTABLE" ] && "$MANIM_PYTHON" -c "import manim; assert manim.__version__ == '0.20.1'" 2>/dev/null; then
  ok "Manim $($MANIM_EXECUTABLE --version 2>&1 | head -1)"
else
  fail "Locked Manim 0.20.1 missing; run: uv sync --project '$PROJECT_DIR' --frozen"
  errors=$((errors+1))
fi
command -v pdflatex &>/dev/null && ok "LaTeX (pdflatex)" || { fail "LaTeX not found (macOS: brew install --cask mactex-no-gui)"; errors=$((errors+1)); }
command -v ffmpeg &>/dev/null && ok "ffmpeg" || { fail "ffmpeg not found"; errors=$((errors+1)); }
echo ""
[ $errors -eq 0 ] && echo -e "${G}All prerequisites satisfied.${N}" || echo -e "${R}$errors prerequisite(s) missing.${N}"
echo ""
