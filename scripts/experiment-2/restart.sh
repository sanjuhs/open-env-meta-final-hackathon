#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PORT="${PORT:-}" VITE_PORT="${VITE_PORT:-}" "${SCRIPT_DIR}/stop.sh"
sleep 1
PORT="${PORT:-}" VITE_PORT="${VITE_PORT:-}" "${SCRIPT_DIR}/start.sh"
