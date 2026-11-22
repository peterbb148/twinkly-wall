# shellcheck shell=bash
# Shared GitHub Releases installer for the platform-specific entry points.
install_release_binary() (
  local binary="$1" platform="$2" tag="$3" install_dir="$4"
  local repo=peterbb148/twinkly-wall
  local archive download_dir actual
  local checksum=(sha256sum)

  if ! command -v gh >/dev/null; then
    printf '%s\n' 'Install the GitHub CLI (gh) and authenticate with gh auth login.' >&2
    exit 1
  fi
  if [[ -z $tag ]]; then
    tag=$(gh release view --repo "$repo" --json tagName --jq .tagName)
  fi
  if [[ ! $tag =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    printf 'Unexpected release tag: %s\n' "$tag" >&2
    exit 1
  fi

  archive="$binary-${tag#v}-$platform.tar.gz"
  download_dir=$(mktemp -d)
  trap 'rm -rf -- "$download_dir"' EXIT
  gh release download "$tag" --repo "$repo" --dir "$download_dir" \
    --pattern "$archive" --pattern "$archive.sha256"

  if [[ $platform == darwin-arm64 ]]; then
    checksum=(shasum -a 256)
  fi
  (
    cd "$download_dir" || exit
    if [[ ! -f "$archive" || ! -f "$archive.sha256" ]]; then
      printf 'Release %s is missing %s or its SHA-256 checksum.\n' "$tag" "$archive" >&2
      exit 1
    fi
    actual=$("${checksum[@]}" "$archive")
    if [[ $actual != "$(cat "$archive.sha256")" ]]; then
      printf 'SHA-256 verification failed for %s\n' "$archive" >&2
      exit 1
    fi
    tar -xzf "$archive" "./$binary"
    if [[ $platform == darwin-arm64 ]]; then
      codesign --verify --strict "./$binary"
    fi
  )

  mkdir -p -- "$install_dir"
  install -m 755 "$download_dir/$binary" "$install_dir/"
  printf 'Installed %s %s at %s/%s\n' "$binary" "${tag#v}" "$install_dir" "$binary"
)
