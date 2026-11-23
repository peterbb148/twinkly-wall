#!/usr/bin/env bash
# Install the standalone Raspberry Pi ARM64 executable from GitHub Releases.
set -euo pipefail

usage() {
  printf '%s\n' 'Usage: install_raspberry_pi.sh [vVERSION]' \
    'Requires authenticated gh and 64-bit Raspberry Pi OS (Trixie) or Debian 13 ARM64.' \
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

scripts_dir="$(dirname "${BASH_SOURCE[0]}")"
# shellcheck source=scripts/check_raspberry_pi.sh
source "$scripts_dir/check_raspberry_pi.sh"
require_raspberry_pi_userspace

# shellcheck source=scripts/install_release_binary.sh
source "$scripts_dir/install_release_binary.sh"
install_release_binary twinkly-cli raspberry-pi-arm64 "${1:-}" "${TWINKLY_INSTALL_DIR:-$HOME/.local/bin}"
