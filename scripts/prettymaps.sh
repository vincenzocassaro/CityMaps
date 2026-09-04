#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
projects_root="$(dirname "$project_root")"
prettymaps_config="$project_root/venv/.prettymaps-dir"

if [[ -n "${PRETTYMAPS_DIR:-}" ]]; then
    prettymaps_dir="$PRETTYMAPS_DIR"
elif [[ -f "$prettymaps_config" ]]; then
    IFS= read -r prettymaps_dir < "$prettymaps_config"
else
    prettymaps_dir="$projects_root/prettymaps"
fi

if [[ ! -f "$prettymaps_dir/app.py" ]]; then
    echo "Prettymaps was not found at $prettymaps_dir." >&2
    echo "Run ./scripts/setup.sh first, or set PRETTYMAPS_DIR to its checkout." >&2
    exit 1
fi

if [[ ! -x "$project_root/venv/bin/streamlit" ]]; then
    echo "The CityMaps environment is missing. Run ./scripts/setup.sh first." >&2
    exit 1
fi

export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
exec "$project_root/venv/bin/streamlit" run \
    "$prettymaps_dir/app.py" \
    --server.headless true \
    "$@"
