#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_command="${PYTHON_COMMAND:-python3.12}"

if ! command -v "$python_command" >/dev/null 2>&1; then
    echo "Python 3.12 is required. On macOS, install it with: brew install python@3.12" >&2
    exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "FFmpeg is required. On macOS, install it with: brew install ffmpeg" >&2
    exit 1
fi

if ! command -v google-chrome >/dev/null 2>&1 \
    && ! command -v google-chrome-stable >/dev/null 2>&1 \
    && [[ ! -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then
    echo "Google Chrome is required to record the map animation." >&2
    exit 1
fi

"$python_command" -m venv --clear "$project_root/venv"
"$project_root/venv/bin/python" -m pip install --upgrade pip setuptools wheel
"$project_root/venv/bin/python" -m pip install -r "$project_root/requirements.txt"

mkdir -p "$project_root/output"

"$project_root/venv/bin/python" -m pip check

echo
echo "CityMaps is ready."
echo "Environment: $project_root/venv"
echo "Run the studio with: ./scripts/run.sh"
