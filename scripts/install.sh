#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
WRAPPER_DIR="${HOME}/.local/bin"
WRAPPER_PATH="$WRAPPER_DIR/ralph-dashboard"

CLI_PYTHON_BIN=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--python)
      shift
      if [[ $# -eq 0 ]]; then
        echo "Missing value for --python"
        exit 1
      fi
      CLI_PYTHON_BIN="$1"
      ;;
    -h|--help)
      cat <<'EOF_HELP'
Usage: ./scripts/install.sh [--python <executable>]

Options:
  -p, --python   Python interpreter to use (must be Python 3.12+)
  -h, --help     Show this help message

You can also set PYTHON_BIN (or PYTHON) instead of passing --python.
EOF_HELP
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Run ./scripts/install.sh --help for usage."
      exit 1
      ;;
  esac
  shift
done

is_python_312_plus() {
  local candidate="$1"
  "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
}

python_version() {
  local candidate="$1"
  "$candidate" - <<'PY'
import sys
print(".".join(map(str, sys.version_info[:3])))
PY
}

PYTHON_BIN="${CLI_PYTHON_BIN:-${PYTHON_BIN:-${PYTHON:-}}}"

if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in python3.12 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && is_python_312_plus "$candidate"; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if [[ -n "${CLI_PYTHON_BIN:-}" ]]; then
    echo "Python executable not found: $PYTHON_BIN"
  else
    echo "No suitable Python interpreter found."
    echo "Install Python 3.12+ and rerun, or pass --python <executable>."
  fi
  exit 1
fi

if ! is_python_312_plus "$PYTHON_BIN"; then
  actual_version="$(python_version "$PYTHON_BIN")"
  echo "Python 3.12+ is required, but '$PYTHON_BIN' is $actual_version."
  echo "Use --python python3.12 (or set PYTHON_BIN=python3.12)."
  exit 1
fi

echo "==> Using Python: $PYTHON_BIN ($(python_version "$PYTHON_BIN"))"

echo "==> Ensuring backend virtualenv"
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

echo "==> Installing backend package"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -e "$BACKEND_DIR"

echo "==> Installing CLI wrapper to $WRAPPER_PATH"
mkdir -p "$WRAPPER_DIR"
cat > "$WRAPPER_PATH" <<EOF_WRAPPER
#!/usr/bin/env bash
exec "$VENV_DIR/bin/ralph-dashboard" "\$@"
EOF_WRAPPER
chmod +x "$WRAPPER_PATH"

PACKAGED_DIST="$BACKEND_DIR/app/static/dist"
FRONTEND_DIST="$FRONTEND_DIR/dist"

echo "==> Preparing frontend assets"
if [[ -f "$FRONTEND_DIST/index.html" ]]; then
  "$ROOT_DIR/scripts/package_frontend.sh"
elif [[ -f "$PACKAGED_DIST/index.html" ]]; then
  echo "Using packaged frontend assets at $PACKAGED_DIST"
elif command -v npm >/dev/null 2>&1 && [[ -f "$FRONTEND_DIR/package.json" ]]; then
  echo "No built frontend assets found; building with npm"
  (
    cd "$FRONTEND_DIR"
    npm install --legacy-peer-deps
    npm run build
  )
  "$ROOT_DIR/scripts/package_frontend.sh"
else
  echo "Warning: frontend assets are missing and npm is unavailable."
  echo "The API will run, but the web UI cannot be served until assets are provided."
fi

echo ""
echo "Install complete."
echo "Next steps:"
echo "1. Ensure $WRAPPER_DIR is on your PATH"
echo "2. Run: ralph-dashboard init"
echo "   (auto-creates ~/.config/ralph-dashboard/env and credentials.yaml)"
echo "3. Run: ralph-dashboard doctor"
if [[ "$(uname -s)" == "Linux" ]]; then
  echo "4. Run: ralph-dashboard service install --user --start"
else
  echo "4. Start manually:"
  echo '   set -a'
  echo '   source ~/.config/ralph-dashboard/env'
  echo '   set +a'
  echo '   cd backend'
  echo '   .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$RALPH_PORT"'
fi
