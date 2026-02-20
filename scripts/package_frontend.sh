#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIST="$ROOT_DIR/frontend/dist"
TARGET_DIST="$ROOT_DIR/backend/app/static/dist"

if [[ ! -f "$FRONTEND_DIST/index.html" ]]; then
  echo "Frontend build not found at $FRONTEND_DIST"
  echo "Run: cd frontend && npm install --legacy-peer-deps && npm run build"
  exit 1
fi

rm -rf "$TARGET_DIST"
mkdir -p "$TARGET_DIST"
cp -a "$FRONTEND_DIST"/. "$TARGET_DIST"/

echo "Packaged frontend assets into: $TARGET_DIST"
