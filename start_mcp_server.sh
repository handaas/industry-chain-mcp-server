#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python server/mcp_server.py "${1:-streamable-http}"
