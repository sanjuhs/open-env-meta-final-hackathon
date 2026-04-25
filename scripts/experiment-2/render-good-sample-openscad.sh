#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SOURCE_MD="${ROOT_DIR}/3d-models/good-sample-cad-code.md"
OUT_DIR="${ROOT_DIR}/.run/experiment-2/openscad"
SCAD_OUT="${OUT_DIR}/good-sample-cad-code.scad"
STL_OUT="${OUT_DIR}/good-sample-cad-code.stl"
PNG_OUT="${OUT_DIR}/good-sample-cad-code.png"

find_openscad() {
  if [[ -n "${OPENSCAD_BIN:-}" && -x "${OPENSCAD_BIN}" ]]; then
    echo "${OPENSCAD_BIN}"
    return 0
  fi

  local path_bin
  path_bin="$(command -v openscad || true)"
  if [[ -n "${path_bin}" ]]; then
    echo "${path_bin}"
    return 0
  fi

  local candidates=(
    "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
    "/Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD"
    "/opt/homebrew/Caskroom/openscad/latest/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD"
    "/opt/homebrew/Caskroom/openscad@snapshot/latest/OpenSCAD.app/Contents/MacOS/OpenSCAD"
    "/usr/local/Caskroom/openscad/latest/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD"
    "/usr/local/Caskroom/openscad@snapshot/latest/OpenSCAD.app/Contents/MacOS/OpenSCAD"
  )

  for candidate in "${candidates[@]}"; do
    if [[ -x "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done

  return 1
}

extract_scad() {
  mkdir -p "${OUT_DIR}"
  awk '
    /^```scad[[:space:]]*$/ { inside = 1; next }
    /^```[[:space:]]*$/ && inside { exit }
    inside { print }
  ' "${SOURCE_MD}" > "${SCAD_OUT}"

  if [[ ! -s "${SCAD_OUT}" ]]; then
    echo "Could not extract a SCAD code fence from ${SOURCE_MD}" >&2
    exit 1
  fi
}

main() {
  if [[ ! -f "${SOURCE_MD}" ]]; then
    echo "Sample markdown not found: ${SOURCE_MD}" >&2
    exit 1
  fi

  local openscad_bin
  if ! openscad_bin="$(find_openscad)"; then
    cat >&2 <<'MSG'
OpenSCAD is not installed or not visible on PATH.

Install one of these, then rerun this script:
  brew install --cask openscad@snapshot

or the stable cask:
  brew install --cask openscad

You can also set OPENSCAD_BIN=/path/to/OpenSCAD if the app is installed somewhere else.
MSG
    exit 127
  fi

  extract_scad

  echo "Using OpenSCAD: ${openscad_bin}"
  echo "Extracted SCAD: ${SCAD_OUT}"
  echo "Compiling STL..."
  "${openscad_bin}" -o "${STL_OUT}" "${SCAD_OUT}"
  echo "Wrote STL: ${STL_OUT}"

  echo "Rendering PNG preview..."
  if "${openscad_bin}" -o "${PNG_OUT}" --imgsize=1400,1000 --viewall --autocenter "${SCAD_OUT}"; then
    echo "Wrote PNG: ${PNG_OUT}"
  else
    echo "PNG preview failed, but STL compilation completed." >&2
  fi
}

main "$@"
