#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
projects_root="$(dirname "$project_root")"
prettymaps_dir="${PRETTYMAPS_DIR:-$projects_root/prettymaps}"
python_command="${PYTHON_COMMAND:-python3.12}"

if ! command -v "$python_command" >/dev/null 2>&1; then
    echo "Python 3.12 is required. On macOS, install it with: brew install python@3.12" >&2
    exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "FFmpeg is required. On macOS, install it with: brew install ffmpeg" >&2
    exit 1
fi

if [[ ! -d "$prettymaps_dir/.git" ]]; then
    mkdir -p "$(dirname "$prettymaps_dir")"
    git clone https://github.com/marceloprates/prettymaps.git "$prettymaps_dir"
fi

"$python_command" -m venv --clear "$project_root/venv"
"$project_root/venv/bin/python" -m pip install --upgrade pip setuptools wheel
"$project_root/venv/bin/python" -m pip install \
    -r "$project_root/requirements.txt" \
    -e "$prettymaps_dir"

printf '%s\n' "$prettymaps_dir" > "$project_root/venv/.prettymaps-dir"

mkdir -p \
    "$project_root/src/images" \
    "$project_root/src/videos/first" \
    "$project_root/src/videos/second" \
    "$project_root/src/videos/final"

"$project_root/venv/bin/python" -m pip check

echo
echo "CityMaps is ready."
echo "Prettymaps: $prettymaps_dir"
echo "Environment: $project_root/venv"
echo "Run the map editor with: PRETTYMAPS_DIR=\"$prettymaps_dir\" ./scripts/prettymaps.sh"
