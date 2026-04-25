#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

load_env
require_stack

cd "${APP_DIR}"
PYTHONPATH="${APP_DIR}/python_tools" \
XDG_CACHE_HOME="${XDG_CACHE_HOME}" \
"${PYTHON_SIM_BIN}" python_tools/cadquery_env.py preprocess-reference "$@"
