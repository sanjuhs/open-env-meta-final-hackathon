#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

load_env
ensure_dirs

echo "Experiment 2 status"
echo "  app:      ${APP_DIR}"
echo "  venv:     ${PYTHON_SIM_BIN}"
echo "  backend:  http://localhost:${PORT}"
echo "  frontend: http://localhost:${VITE_PORT}"
print_process_status backend "${PORT}"
print_process_status frontend "${VITE_PORT}"
