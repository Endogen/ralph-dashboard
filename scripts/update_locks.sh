#!/usr/bin/env bash
# Regenerate the hash-pinned dependency locks from backend/pyproject.toml.
# Run this after changing any dependency, and commit the result.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi
# --universal resolves for every supported platform at once, so one lock serves
# the Linux image, the macOS CI leg and local development.
# --no-header keeps the output independent of where it was generated, so CI can
# regenerate and compare byte for byte.
# Run from the repository root with relative paths: uv records the input path in
# its annotations, so the output must not depend on the caller's directory.
cd "$ROOT"
uv pip compile backend/pyproject.toml --universal --generate-hashes --no-header \
  --python-version 3.12 -o backend/requirements.lock
uv pip compile backend/pyproject.toml --extra dev --universal --generate-hashes --no-header \
  --python-version 3.12 -o backend/requirements-dev.lock
echo "Updated backend/requirements.lock and backend/requirements-dev.lock"
