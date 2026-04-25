#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

load_env
ensure_dirs

stop_pid frontend || true
stop_pid backend || true

stop_port_processes frontend "${VITE_PORT}"
stop_port_processes backend "${PORT}"

rm -f "$(pid_file_for frontend)" "$(pid_file_for backend)"

echo "Experiment 2 stop requested."
"${SCRIPT_DIR}/status.sh"
