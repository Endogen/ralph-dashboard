#!/usr/bin/env bash
# Repository entry point. Installed distributions also provide `ralph-loop`.
set -euo pipefail
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -x "$REPO_ROOT/backend/.venv/bin/python" ]]; then
  PYTHON="$REPO_ROOT/backend/.venv/bin/python"
else
  PYTHON="${RALPH_PYTHON:-python3}"
fi
export PYTHONPATH="$REPO_ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" -m app.runner "$@"
