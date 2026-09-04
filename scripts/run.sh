#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -x "$project_root/venv/bin/streamlit" ]]; then
    echo "The CityMaps environment is missing. Run ./scripts/setup.sh first." >&2
    exit 1
fi

export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
exec "$project_root/venv/bin/streamlit" run \
    "$project_root/app.py" \
    --server.headless true \
    "$@"
