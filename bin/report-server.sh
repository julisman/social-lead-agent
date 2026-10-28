#!/usr/bin/env bash
# Serves reports/*.md as readable HTML at http://127.0.0.1:8787
# Local-only — reports contain customer names and phone numbers.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-${REPORT_SERVER_PORT:-8787}}"

exec python3 "$DIR/report-server.py" "$PORT"
