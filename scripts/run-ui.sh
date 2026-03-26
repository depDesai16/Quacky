#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".venv/bin/python" ]; then
  echo "Missing .venv. Run ./scripts/setup.sh first." >&2
  exit 1
fi

exec ".venv/bin/python" scripts/dev.py ui
