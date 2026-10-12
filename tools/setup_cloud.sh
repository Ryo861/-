#!/usr/bin/env bash
# Reusable setup for this Debian Codex machine. Windows uses setup_windows.bat.
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_dir"
command -v uv >/dev/null
/usr/bin/python3 -c 'import tkinter; assert tkinter.TkVersion >= 8.6'
mkdir -p .local/uv-cache .local/pip-cache
export UV_CACHE_DIR="$repo_dir/.local/uv-cache"
export PIP_CACHE_DIR="$repo_dir/.local/pip-cache"
# Use system Tk (Xft enabled), rather than the platform Tk9 without Japanese fonts.
if [ ! -x .venv-gui/bin/python ]; then
  uv venv --python /usr/bin/python3 --seed --system-certs .venv-gui
fi
uv pip install --python .venv-gui/bin/python --system-certs -r requirements.txt
.venv-gui/bin/python -c 'from gui.fonts import prepare_fonts; prepare_fonts()'
bash tools/setup_headless.sh
.venv-gui/bin/python -m pip check
