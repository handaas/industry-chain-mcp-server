#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ $# -eq 0 ]]; then
  set -- streamable-http
fi
exec "${PYTHON:-python}" server/mcp_server.py "$@"
