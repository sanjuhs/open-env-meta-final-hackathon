#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

load_env
ensure_dirs
require_stack
install_node_deps_if_missing

if port_is_busy "${PORT}"; then
  echo "Backend port ${PORT} is already in use."
  echo "Run scripts/experiment-2/stop.sh first, or choose another PORT."
  exit 1
fi

if port_is_busy "${VITE_PORT}"; then
  echo "Frontend port ${VITE_PORT} is already in use."
  echo "Run scripts/experiment-2/stop.sh first, or choose another VITE_PORT."
  exit 1
fi

echo "Starting Experiment 2 backend on http://localhost:${PORT}"
(
  cd "${APP_DIR}"
  nohup env \
    PORT="${PORT}" \
    PYTHON_SIM_BIN="${PYTHON_SIM_BIN}" \
    UV_CACHE_DIR="${UV_CACHE_DIR}" \
    XDG_CACHE_HOME="${XDG_CACHE_HOME}" \
    node server/index.js > "${LOG_DIR}/backend.log" 2>&1 &
  echo "$!" > "$(pid_file_for backend)"
)

echo "Starting Experiment 2 frontend on http://localhost:${VITE_PORT}"
(
  cd "${APP_DIR}"
  nohup env \
    PORT="${PORT}" \
    VITE_PORT="${VITE_PORT}" \
    npm exec -- vite --host 0.0.0.0 --port "${VITE_PORT}" > "${LOG_DIR}/frontend.log" 2>&1 &
  echo "$!" > "$(pid_file_for frontend)"
)

sleep 1
PORT="${PORT}" VITE_PORT="${VITE_PORT}" "${SCRIPT_DIR}/status.sh"

echo
echo "Logs:"
echo "  backend:  ${LOG_DIR}/backend.log"
echo "  frontend: ${LOG_DIR}/frontend.log"
