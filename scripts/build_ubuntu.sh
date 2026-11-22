#!/usr/bin/env bash
# Package the Ubuntu ARM64 executable with its own checksum.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "$(uname -s)" != Linux || "$(uname -m)" != aarch64 ]]; then
  echo 'Build requires native Ubuntu ARM64.' >&2
  exit 1
fi
# shellcheck source=/dev/null
source /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 24.04 ]]; then
  echo 'Build requires Ubuntu 24.04 to set the minimum runtime ABI.' >&2
  exit 1
fi

uv sync --locked --no-dev --group build
uv run --locked --no-sync pyinstaller --clean --noconfirm packaging/twinkly-cli.spec

version="$(uv run --locked --no-sync python -c 'from twinkly_wall import __version__; print(__version__)')"
archive="twinkly-cli-$version-ubuntu-arm64.tar.gz"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

mkdir -p "$stage/examples" "$stage/assets"
cp dist/twinkly-cli "$stage/"
cp config/cards.example.yaml config/settings.example.yaml "$stage/examples/"
cp assets/carlsberg.png "$stage/assets/"
tar -czf "dist/$archive" -C "$stage" .
(
  cd dist
  sha256sum "$archive" > "$archive.sha256"
)
echo "Built dist/$archive and dist/$archive.sha256"
