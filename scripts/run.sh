#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

load_keychain_secret() {
    local variable_name="$1"
    local service_name="$2"
    local secret_value

    if [[ -n "${!variable_name:-}" ]]; then
        return
    fi
    if secret_value="$(security find-generic-password -a "$USER" -s "$service_name" -w 2>/dev/null)"; then
        export "$variable_name=$secret_value"
    fi
}

if [[ ! -x "$project_root/venv/bin/streamlit" ]]; then
    echo "The CityMaps environment is missing. Run ./scripts/setup.sh first." >&2
    exit 1
fi

export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
load_keychain_secret BUFFER_API_KEY "CityMaps Buffer API Key"
load_keychain_secret CLOUDINARY_URL "CityMaps Cloudinary URL"
exec "$project_root/venv/bin/streamlit" run \
    "$project_root/app.py" \
    --server.headless true \
    "$@"
