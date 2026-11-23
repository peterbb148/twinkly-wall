#!/usr/bin/env bash
# Build the archive on native ARM64 with the Trixie runtime ABI.
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck source=scripts/check_raspberry_pi.sh
source scripts/check_raspberry_pi.sh
require_raspberry_pi_userspace

UV_PYTHON=/usr/bin/python3 bash scripts/build_linux_binary.sh raspberry-pi-arm64 --no-install-project
