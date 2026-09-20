#!/usr/bin/env bash
# Refresh dependency locks, or verify them without upgrading existing pins.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:-update}"
case "$mode" in
  update|--check|--upgrade) ;;
  *) echo "Usage: $0 [--check|--upgrade]" >&2; exit 2 ;;
esac
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi
cd "$ROOT"
lock_tmp="$(mktemp -d)"
trap 'rm -rf "$lock_tmp"' EXIT
for flavor in runtime dev; do
  extra=(--universal --generate-hashes --no-header --python-version 3.12)
  lock=backend/requirements.lock
  if [[ "$flavor" == dev ]]; then
    extra+=(--extra dev)
    lock=backend/requirements-dev.lock
  fi
  output="$lock"
  if [[ "$mode" == --check ]]; then
    output="$lock_tmp/$(basename "$lock")"
    # uv treats an existing output as preferred versions. Fresh resolution
    # would incorrectly fail whenever an unrelated upstream release appears.
    cp "$lock" "$output"
  elif [[ "$mode" == --upgrade ]]; then
    extra+=(--upgrade)
  fi
  uv pip compile backend/pyproject.toml "${extra[@]}" -o "$output" --quiet
  if [[ "$mode" == --check ]]; then diff -u "$lock" "$output"; fi
done
