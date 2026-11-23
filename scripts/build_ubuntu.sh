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

bash scripts/build_linux_binary.sh ubuntu-arm64
