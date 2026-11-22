#!/usr/bin/env bash
# Build, verify, and package the native macOS Apple Silicon CLI.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
  echo 'Build requires native Apple Silicon macOS; cross-compilation is not supported.' >&2
  exit 1
fi

uv sync --locked --no-dev --group build
uv run --locked --no-sync pyinstaller --clean --noconfirm packaging/twinkly-cli.spec
test "$(lipo -archs dist/twinkly-cli)" = arm64
codesign --verify --strict dist/twinkly-cli
uv run --locked --no-sync python scripts/smoke_binary.py dist/twinkly-cli

version="$(uv run --locked --no-sync python -c 'from twinkly_wall import __version__; print(__version__)')"
archive="twinkly-cli-${version}-darwin-arm64.tar.gz"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
cp dist/twinkly-cli "$stage/twinkly-cli"
mkdir -p "$stage/examples" "$stage/assets" "$stage/checks"
cp config/cards.example.yaml config/settings.example.yaml "$stage/examples/"
cp assets/carlsberg.png "$stage/assets/"
cp scripts/smoke_binary.py "$stage/checks/"
tar -czf "dist/$archive" -C "$stage" .
(
  cd dist
  shasum -a 256 "$archive" > "$archive.sha256"
)
echo "Built dist/$archive and dist/$archive.sha256"
