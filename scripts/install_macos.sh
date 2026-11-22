#!/usr/bin/env bash
# Install the standalone Apple Silicon CLI from GitHub Releases.
set -euo pipefail

usage() {
  printf '%s\n' 'Usage: install_macos.sh [vVERSION]' \
    'Requires authenticated gh and macOS 15+ on Apple Silicon.' \
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

if [[ $(uname -s) != Darwin || $(uname -m) != arm64 ]]; then
  printf '%s\n' 'Run this installer in a native Apple Silicon macOS shell.' >&2
  exit 1
fi
macos_version=$(sw_vers -productVersion)
if (( ${macos_version%%.*} < 15 )); then
  printf '%s\n' 'Twinkly CLI requires macOS 15 or newer.' >&2
  exit 1
fi
# shellcheck source=scripts/install_release_binary.sh
source "$(dirname "${BASH_SOURCE[0]}")/install_release_binary.sh"
install_release_binary twinkly-cli darwin-arm64 "${1:-}" "${TWINKLY_INSTALL_DIR:-$HOME/.local/bin}"
