#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_dir"
checker_python="${CHECKER_PYTHON:-$repo_dir/.venv-gui/bin/python}"
if [ ! -x "$checker_python" ]; then checker_python="$repo_dir/.venv/bin/python"; fi
"$checker_python" -c "from gui.fonts import prepare_fonts; prepare_fonts()"
export FONTCONFIG_FILE="$repo_dir/.local/fonts.conf"
if [ -n "${DISPLAY:-}" ]; then
  exec "$checker_python" -m unittest discover -s tests -v
fi
xvfb_path="$(command -v Xvfb || true)"
if [ -z "$xvfb_path" ]; then xvfb_path="$repo_dir/.local/xvfb/usr/bin/Xvfb"; fi
if [ ! -x "$xvfb_path" ]; then
  echo 'Run bash tools/setup_headless.sh first.' >&2
  exit 1
fi
# Allocate a display automatically; do not terminate any pre-existing server.
run_dir="$(mktemp -d)"
"$xvfb_path" -displayfd 3 -screen 0 1440x1000x24 -nolisten tcp 3>"$run_dir/display" >"$run_dir/server.log" 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true; rm -rf "$run_dir"' EXIT
for attempt in $(seq 1 50); do
  if [ -s "$run_dir/display" ]; then break; fi
  if ! kill -0 "$server_pid" 2>/dev/null; then cat "$run_dir/server.log" >&2; exit 1; fi
  sleep 0.1
done
if [ ! -s "$run_dir/display" ]; then echo 'Display startup timed out.' >&2; exit 1; fi
export DISPLAY=":$(cat "$run_dir/display")"
"$checker_python" -m unittest discover -s tests -v
