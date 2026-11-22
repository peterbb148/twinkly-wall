#!/usr/bin/env bash
# Package each Ubuntu ARM64 executable with its own checksum.
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
uv run --locked --no-sync pyinstaller --clean --noconfirm packaging/twinklysay.spec
uv run --locked --no-sync pyinstaller --clean --noconfirm --onefile \
  --specpath build --name twinklywall --paths "$PWD/src" "$PWD/packaging/daemon_entrypoint.py"

version="$(uv run --locked --no-sync python -c 'from twinkly_wall import __version__; print(__version__)')"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

for command in twinklywall twinklysay; do
  destination="$stage/$command"
  mkdir -p "$destination/examples" "$destination/assets"
  cp "dist/$command" "$destination/"
  cp config/cards.example.yaml config/settings.example.yaml "$destination/examples/"
  cp assets/carlsberg.png "$destination/assets/"
  archive="$command-$version-ubuntu-arm64.tar.gz"
  tar -czf "dist/$archive" -C "$destination" .
  (
    cd dist
    sha256sum "$archive" > "$archive.sha256"
  )
  echo "Built dist/$archive and dist/$archive.sha256"
done
