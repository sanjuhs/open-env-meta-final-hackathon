#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
APP_DIR="${ROOT_DIR}/experiment-2-cadforge"
RUN_DIR="${ROOT_DIR}/.run/experiment-2"
PID_DIR="${RUN_DIR}/pids"
LOG_DIR="${RUN_DIR}/logs"

load_env() {
  set -a
  if [[ -f "${ROOT_DIR}/.env" ]]; then
    # shellcheck disable=SC1091
    source "${ROOT_DIR}/.env"
  fi
  if [[ -f "${APP_DIR}/.env" ]]; then
    # shellcheck disable=SC1091
    source "${APP_DIR}/.env"
  fi
  set +a

  export PORT="${PORT:-8791}"
  export VITE_PORT="${VITE_PORT:-5177}"
  export PYTHON_SIM_BIN="${PYTHON_SIM_BIN:-${ROOT_DIR}/.venv/bin/python}"
  export UV_CACHE_DIR="${UV_CACHE_DIR:-${ROOT_DIR}/.uv-cache}"
  export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${APP_DIR}/.cache}"
  export PATH="${ROOT_DIR}/.venv/bin:${PATH}"
}

ensure_dirs() {
  mkdir -p "${PID_DIR}" "${LOG_DIR}"
}

require_stack() {
  if [[ ! -d "${APP_DIR}" ]]; then
    echo "Experiment 2 app directory not found: ${APP_DIR}" >&2
    exit 1
  fi

  if [[ ! -x "${PYTHON_SIM_BIN}" ]]; then
    echo "Global Python venv not found at ${PYTHON_SIM_BIN}" >&2
    echo "Create it from the repo root with: UV_CACHE_DIR=.uv-cache uv venv --python python3.12 .venv" >&2
    exit 1
  fi

  if ! command -v node >/dev/null 2>&1; then
    echo "Node.js is required for Experiment 2." >&2
    exit 1
  fi

  if ! command -v npm >/dev/null 2>&1; then
    echo "npm is required for Experiment 2." >&2
    exit 1
  fi
}

install_node_deps_if_missing() {
  if [[ ! -d "${APP_DIR}/node_modules" ]]; then
    echo "Installing Experiment 2 Node dependencies..."
    (cd "${APP_DIR}" && npm install --cache .npm-cache)
  fi
}

pid_file_for() {
  echo "${PID_DIR}/$1.pid"
}

pid_is_running() {
  local pid="$1"
  [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1
}

read_pid() {
  local name="$1"
  local file
  file="$(pid_file_for "${name}")"
  if [[ -f "${file}" ]]; then
    tr -d '[:space:]' < "${file}"
  fi
}

pids_on_port() {
  local port="$1"
  lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
}

port_is_busy() {
  local port="$1"
  [[ -n "$(pids_on_port "${port}")" ]]
}

print_process_status() {
  local name="$1"
  local port="$2"
  local pid
  pid="$(read_pid "${name}")"

  if pid_is_running "${pid:-}"; then
    echo "${name}: running with pid ${pid} on expected port ${port}"
    return
  fi

  local port_pids
  port_pids="$(pids_on_port "${port}")"
  if [[ -n "${port_pids}" ]]; then
    echo "${name}: port ${port} is occupied by pid(s): ${port_pids//$'\n'/ }"
  else
    echo "${name}: stopped"
  fi
}

stop_pid() {
  local name="$1"
  local pid
  pid="$(read_pid "${name}")"

  if ! pid_is_running "${pid:-}"; then
    rm -f "$(pid_file_for "${name}")"
    return 0
  fi

  echo "Stopping ${name} pid ${pid}..."
  kill "${pid}" 2>/dev/null || {
    echo "Could not stop ${name} pid ${pid}. You may need to stop it from the owning terminal." >&2
    return 1
  }

  for _ in {1..30}; do
    if ! pid_is_running "${pid}"; then
      rm -f "$(pid_file_for "${name}")"
      return 0
    fi
    sleep 0.2
  done

  echo "${name} did not stop after SIGTERM; sending SIGKILL..."
  kill -9 "${pid}" 2>/dev/null || true
  rm -f "$(pid_file_for "${name}")"
}

stop_port_processes() {
  local label="$1"
  local port="$2"
  local pids
  pids="$(pids_on_port "${port}")"

  if [[ -z "${pids}" ]]; then
    return 0
  fi

  while IFS= read -r pid; do
    [[ -z "${pid}" ]] && continue
    echo "Stopping ${label} process on port ${port}: pid ${pid}"
    kill "${pid}" 2>/dev/null || {
      echo "Could not stop pid ${pid} on port ${port}. You may need to stop it from the owning terminal." >&2
    }
  done <<< "${pids}"
}
