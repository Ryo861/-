#!/usr/bin/env bash
# Debian-only cloud test helper. Signed APT indices and checksums remain enabled.
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
local_dir="$repo_dir/.local"
mkdir -p "$local_dir/apt/lists/partial" "$local_dir/apt/archives/partial" "$local_dir/xvfb"
if ! command -v Xvfb >/dev/null && [ ! -x "$local_dir/xvfb/usr/bin/Xvfb" ]; then
  test -f /usr/share/keyrings/debian-archive-keyring.gpg
  cat > "$local_dir/apt/apt.conf" <<CONFIG
Dir::Etc::Parts "-";
Dir::Etc::main "-";
Dir::Etc::sourcelist "$local_dir/apt/sources.list";
Dir::Etc::sourceparts "-";
Dir::State::lists "$local_dir/apt/lists";
Dir::Cache::archives "$local_dir/apt/archives";
Dir::Cache::pkgcache "";
Dir::Cache::srcpkgcache "";
CONFIG
  printf '%s\n' 'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main' > "$local_dir/apt/sources.list"
  APT_CONFIG="$local_dir/apt/apt.conf" apt-get update
  (cd "$local_dir" && APT_CONFIG="$local_dir/apt/apt.conf" apt-get download xvfb)
  for package in "$local_dir"/xvfb_*.deb; do dpkg-deb -x "$package" "$local_dir/xvfb"; done
fi
