#!/usr/bin/env bash
# Exercise the installer with the exact assets downloaded by CI.
set -euo pipefail
scripts_dir="$(cd "$(dirname "$0")" && pwd)"
platform="${1:?Expected the release platform}"
archive_path="${2:?Expected the downloaded archive}"
archive="$(basename "$archive_path")"
version="${archive#twinkly-cli-}"
version="${version%-"$platform".tar.gz}"
installer="$scripts_dir/install_${platform%%-*}.sh"
if [[ "$platform" == darwin-arm64 ]]; then
  installer="$scripts_dir/install_macos.sh"
fi
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir "$work/bin" "$work/release"
cp "$archive_path" "$archive_path.sha256" "$work/release/"
export PATH="$work/bin:$PATH"
export TWINKLY_INSTALL_DIR="$work/install dir"
export FIXTURE_RELEASE="$work/release" FIXTURE_TAG="v$version" FIXTURE_ARCHIVE="$archive"

cat > "$work/bin/gh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == 'release view --repo peterbb148/twinkly-wall --json tagName --jq .tagName' ]]; then
  printf '%s\n' "$FIXTURE_TAG"
else
  [[ $# == 11 && "$1 $2 $3 $4 $5 $6" == "release download $FIXTURE_TAG --repo peterbb148/twinkly-wall --dir" ]]
  [[ "$8 $9 ${10} ${11}" == "--pattern $FIXTURE_ARCHIVE --pattern $FIXTURE_ARCHIVE.sha256" ]]
  cp "$FIXTURE_RELEASE/$9" "$FIXTURE_RELEASE/${11}" "$7/"
fi
SH
chmod +x "$work/bin/gh"

bash "$installer" --help
bash "$installer"
[[ "$("$TWINKLY_INSTALL_DIR/twinkly-cli" --version)" == "twinkly-cli $version" ]]
bash "$installer" "$FIXTURE_TAG"
cp "$TWINKLY_INSTALL_DIR/twinkly-cli" "$work/installed"
printf 'corrupt asset\n' >> "$FIXTURE_RELEASE/$archive"
if bash "$installer" "$FIXTURE_TAG" > "$work/rejected" 2>&1; then
  echo 'The installer accepted a corrupt download.' >&2
  exit 1
fi
grep -Fq 'SHA-256 verification failed' "$work/rejected"
cmp "$work/installed" "$TWINKLY_INSTALL_DIR/twinkly-cli"
echo "Installer passed verification on $platform."
