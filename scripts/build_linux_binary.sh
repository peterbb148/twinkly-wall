#!/usr/bin/env bash
# Package a Linux executable after the platform entry point has checked the host.
set -euo pipefail

platform="${1:?Expected the release platform}"
shift
uv sync --locked --no-dev --group build "$@"
uv run --locked --no-sync pyinstaller --clean --noconfirm packaging/twinkly-cli.spec

version="$(PYTHONPATH=src uv run --locked --no-sync python -c 'from twinkly_wall import __version__; print(__version__)')"
archive="twinkly-cli-$version-$platform.tar.gz"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

mkdir -p "$stage/examples"
cp dist/twinkly-cli "$stage/"
cp config/cards.example.yaml config/settings.example.yaml "$stage/examples/"
tar -czf "dist/$archive" -C "$stage" .
(
  cd dist
  sha256sum "$archive" > "$archive.sha256"
)
echo "Built dist/$archive and dist/$archive.sha256"
