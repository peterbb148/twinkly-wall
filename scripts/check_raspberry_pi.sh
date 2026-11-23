# shellcheck shell=bash
# Raspberry Pi OS Trixie and its Debian base both identify as Debian 13.
require_raspberry_pi_userspace() (
  if [[ $(uname -s) == Linux && $(uname -m) == aarch64 ]] &&
    [[ $(dpkg --print-architecture 2>/dev/null) == arm64 ]]; then
    # shellcheck source=/dev/null
    source /etc/os-release
    if [[ ${ID:-} == debian && ${VERSION_ID:-} == 13 ]]; then
      return 0
    fi
  fi
  printf '%s\n' 'Requires 64-bit Raspberry Pi OS (Trixie) or Debian 13 ARM64.' >&2
  return 1
)
