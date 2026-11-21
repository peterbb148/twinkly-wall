#!/usr/bin/env bash
# Install the standalone Apple Silicon CLI from GitHub Releases.
set -euo pipefail

usage() {
  printf '%s\n' 'Usage: install_macos.sh [vVERSION]' \
    'Requires authenticated gh and macOS 15+ on Apple Silicon.' \
    'Set TWINKLYSAY_INSTALL_DIR to override ~/.local/bin.'
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
  printf '%s\n' 'Twinklysay requires macOS 15 or newer.' >&2
  exit 1
fi
if ! command -v gh >/dev/null; then
  printf '%s\n' 'Install the GitHub CLI (gh) and authenticate with gh auth login.' >&2
  exit 1
fi

repo=peterbb148/twinkly-wall
tag=${1:-}
if [[ -z $tag ]]; then
  tag=$(gh release view --repo "$repo" --json tagName --jq .tagName)
fi
if [[ ! $tag =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  printf 'Unexpected release tag: %s\n' "$tag" >&2
  exit 1
fi

archive="twinklysay-${tag#v}-darwin-arm64.tar.gz"
install_dir=${TWINKLYSAY_INSTALL_DIR:-"$HOME/.local/bin"}
download_dir=$(mktemp -d)
trap 'rm -rf -- "$download_dir"' EXIT

gh release download "$tag" --repo "$repo" --dir "$download_dir" \
  --pattern "$archive" --pattern "$archive.sha256"

(
  cd "$download_dir"
  if [[ $(shasum -a 256 "$archive") != "$(cat "$archive.sha256")" ]]; then
    printf 'SHA-256 verification failed for %s\n' "$archive" >&2
    exit 1
  fi
  tar -xzf "$archive" ./twinklysay
  codesign --verify --strict ./twinklysay
)

mkdir -p -- "$install_dir"
install -m 755 "$download_dir/twinklysay" "$install_dir/"
printf 'Installed twinklysay %s at %s/twinklysay\n' "${tag#v}" "$install_dir"
