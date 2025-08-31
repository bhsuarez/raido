#!/usr/bin/env bash
set -euo pipefail

# Raido cleanup utility
# - Cleans caches, logs, TTS, node_modules, and virtualenvs (opt-in)
# - Dry by default unless --yes or FORCE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

YES=${FORCE:-0}
DO_CACHES=0
DO_LOGS=0
DO_TTS=0
DO_NODE=0
DO_VENV=0
DO_DOCKER=0
SHOW_REPORT=0

usage() {
  cat <<EOF
Usage: scripts/cleanup.sh [options]

Options:
  --caches        Remove Python caches, test caches, build artifacts
  --logs          Remove logs under ./logs and ./shared/logs (if present)
  --tts           Remove generated TTS under ./shared/tts (if present)
  --node          Remove web/node_modules (frontend deps)
  --venv          Remove Python virtualenvs (e.g., kokoro-tts/.venv)
  --docker        Run docker prune commands (containers/images/networks)
  --report        Show disk usage before and after
  --all           Shorthand for: --caches --logs --tts
  --yes           Non-interactive (skip confirmation)
  -h, --help      Show this help

Examples:
  bash scripts/cleanup.sh --all --report
  FORCE=1 bash scripts/cleanup.sh --node --venv
EOF
}

confirm() {
  if [[ "$YES" == "1" ]]; then return 0; fi
  read -r -p "$1 [y/N] " ans || true
  [[ "$ans" =~ ^[Yy]$ ]]
}

report() {
  echo "---- Disk usage (top-level) ----"
  du -sh . .git 2>/dev/null || true
  du -sh * .[^.]* 2>/dev/null | sort -hr | head -n 15 || true
}

rm_path() {
  local path="$1"
  if [[ -e "$path" || -d "$path" ]]; then
    echo "Removing: $path"
    rm -rf -- "$path"
  fi
}

find_and_delete() {
  local name="$1"
  echo "Deleting all $name ..."
  find . -type d -name "$name" -prune -exec rm -rf {} + 2>/dev/null || true
}

delete_files_by_glob() {
  local pattern="$1"
  shopt -s nullglob dotglob
  local matches=( $pattern )
  if ((${#matches[@]})); then
    echo "Deleting files: $pattern"
    rm -f -- "${matches[@]}"
  fi
  shopt -u nullglob dotglob
}

if [[ $# -eq 0 ]]; then usage; exit 0; fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --caches) DO_CACHES=1; shift;;
    --logs) DO_LOGS=1; shift;;
    --tts) DO_TTS=1; shift;;
    --node) DO_NODE=1; shift;;
    --venv) DO_VENV=1; shift;;
    --docker) DO_DOCKER=1; shift;;
    --report) SHOW_REPORT=1; shift;;
    --all) DO_CACHES=1; DO_LOGS=1; DO_TTS=1; shift;;
    --yes) YES=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown option: $1"; usage; exit 1;;
  esac
done

if (( SHOW_REPORT )); then report; fi

echo "\nPlanned actions:"
(( DO_CACHES )) && echo " - Remove caches and build artifacts"
(( DO_LOGS ))   && echo " - Remove logs under ./logs and ./shared/logs"
(( DO_TTS ))    && echo " - Remove generated TTS under ./shared/tts"
(( DO_NODE ))   && echo " - Remove web/node_modules"
(( DO_VENV ))   && echo " - Remove Python virtualenvs (e.g., kokoro-tts/.venv)"
(( DO_DOCKER )) && echo " - Docker prune (containers/images/networks)"

if ! confirm "Proceed?"; then
  echo "Aborted."
  exit 1
fi

if (( DO_CACHES )); then
  # Python caches
  find_and_delete "__pycache__"
  find_and_delete ".pytest_cache"
  delete_files_by_glob "**/*.pyc"
  delete_files_by_glob "**/*.pyo"
  # mypy/ruff caches if present
  find_and_delete ".mypy_cache"
  rm_path ".ruff_cache"
  # Frontend build artifacts
  rm_path "web/dist"
  rm_path "web/.vite"
  rm_path "web/.turbo"
fi

if (( DO_LOGS )); then
  rm_path "logs/*"
  rm_path "shared/logs/*"
fi

if (( DO_TTS )); then
  rm_path "shared/tts/*"
fi

if (( DO_NODE )); then
  rm_path "web/node_modules"
fi

if (( DO_VENV )); then
  # Common virtualenv locations
  rm_path "kokoro-tts/.venv"
  # Any other .venv in the repo root
  find . -maxdepth 3 -type d -name ".venv" -prune -exec rm -rf {} + 2>/dev/null || true
fi

if (( DO_DOCKER )); then
  echo "Pruning Docker (requires Docker installed)..."
  docker system prune -f || true
  docker image prune -f || true
fi

if (( SHOW_REPORT )); then echo; report; fi

echo "Done."

