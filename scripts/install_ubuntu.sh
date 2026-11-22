#!/usr/bin/env bash
# Install the standalone Ubuntu ARM64 executable from GitHub Releases.
set -euo pipefail

usage() {
  printf '%s\n' 'Usage: install_ubuntu.sh [vVERSION]' \
    'Requires authenticated gh and Ubuntu 24.04 or 26.04 LTS on ARM64.' \
    'Set TWINKLY_INSTALL_DIR to override ~/.local/bin.'
}

if [[ ${1:-} == --help || ${1:-} == -h ]]; then
  usage
  exit 0
fi
if (( $# > 1 )) || [[ $# == 1 && ! $1 =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  usage >&2
  exit 2
fi

if [[ $(uname -s) != Linux || $(uname -m) != aarch64 ]]; then
  printf '%s\n' 'Run this installer in a native Ubuntu ARM64 shell.' >&2
  exit 1
fi
# shellcheck source=/dev/null
source /etc/os-release
if [[ ${ID:-} != ubuntu || ( ${VERSION_ID:-} != 24.04 && ${VERSION_ID:-} != 26.04 ) ]]; then
  printf '%s\n' 'This installer supports Ubuntu 24.04 and 26.04 LTS.' >&2
  exit 1
fi

# shellcheck source=scripts/install_release_binary.sh
source "$(dirname "${BASH_SOURCE[0]}")/install_release_binary.sh"
install_release_binary twinkly-cli ubuntu-arm64 "${1:-}" "${TWINKLY_INSTALL_DIR:-$HOME/.local/bin}"
