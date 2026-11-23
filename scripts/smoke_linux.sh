#!/usr/bin/env bash
# Run on native ARM64 with the downloaded release assets and a runtime-only PATH.
set -euo pipefail
export LC_ALL=C.UTF-8
export TERM=dumb

if [[ "$(uname -m)" != aarch64 ]]; then
  echo 'Smoke tests require ARM64.' >&2
  exit 1
fi
for tool in python python3 uv; do
  if command -v "$tool" >/dev/null; then
    echo "Smoke environment unexpectedly contains $tool." >&2
    exit 1
  fi
done

scripts_dir="$(cd "$(dirname "$0")" && pwd)"
downloads="${1:?Expected the directory containing downloaded artifacts}"
version="${2:?Expected the package version}"
platform="${3:?Expected the release platform}"
work="$(mktemp -d)"
daemon_pid=
cleanup() {
  if [[ -n "$daemon_pid" ]]; then
    kill -KILL "$daemon_pid" 2>/dev/null || true
    wait "$daemon_pid" 2>/dev/null || true
  fi
  rm -rf "$work"
}
trap cleanup EXIT

artifact="twinkly-cli-$version-$platform"
archive="$artifact.tar.gz"
(
  cd "$downloads/$artifact"
  sha256sum --strict --check "$archive.sha256"
  tar -xzf "$archive" -C "$work"
)
binary="$work/twinkly-cli"
read -r elf_format < <(od -An -tx1 -N6 "$binary")
read -r elf_machine < <(od -An -tx1 -j18 -N2 "$binary")
[[ "$elf_format" == "7f 45 4c 46 02 01" && "$elf_machine" == "b7 00" ]]

cd "$work"
export HOME="$work"
cat > settings.yaml <<'YAML'
twinkly: {orientation: vertical_left}
YAML
cat > cards.yaml <<'YAML'
cards:
  - type: clock
    duration: 10
YAML

[[ "$("$binary" --version)" == "twinkly-cli $version" ]]
"$binary" say --help > help.log
grep -Fq 'Usage:' help.log
"$binary" say text Hello --no-color > text.log
grep -Eq '[░▒▓█]' text.log
"$binary" say list --playlist cards.yaml > list.log
grep -Fq '[1] clock' list.log
"$binary" say preview --id 1 --playlist cards.yaml --settings settings.yaml \
  --duration 0.1 --no-color > preview.log
grep -Eq '[░▒▓█]' preview.log
cat > image-cards.yaml <<YAML
cards:
  - type: image
    path: $work/assets/carlsberg.png
    duration: 0.1
YAML
"$binary" say preview --id 1 --playlist image-cards.yaml --no-color > image.log 2>&1
grep -Eq '[░▒▓█]' image.log
if grep -Fq 'Failed to load image' image.log; then
  cat image.log >&2
  exit 1
fi

catalog="$work/card-definitions"
mkdir "$catalog"
export TWINKLY_CARD_DIR="$catalog"
cat > "$catalog/party-flame.yaml" <<'YAML'
type: image
layout: portrait
path: flame.ppm
scroll: false
YAML
{
  printf 'P6\n10 50\n255\n'
  head -c 1500 /dev/zero
} > "$catalog/flame.ppm"
"$binary" say list > catalog.log
grep -Fq "party-flame ($catalog/party-flame.yaml)" catalog.log
"$binary" say preview party-flame --settings settings.yaml --duration 0.1 --no-color > flame.log
if grep -Fq '█' flame.log; then
  echo 'The initial external image should be black.' >&2
  exit 1
fi
{
  printf 'P6\n10 50\n255\n'
  head -c 1500 /dev/zero | tr '\000' '\377'
} > "$catalog/flame.ppm"
"$binary" say preview party-flame --settings settings.yaml --duration 0.1 --no-color > flame.log
grep -Fq '██████████' flame.log

"$binary" wall --help > help.log
grep -Fq 'usage: twinkly-cli wall ' help.log
"$binary" wall --terminal --settings settings.yaml --cards cards.yaml > wall.log 2>&1 &
daemon_pid=$!
for _ in {1..100}; do
  if grep -Fq '▀' wall.log; then
    break
  fi
  if ! kill -0 "$daemon_pid" 2>/dev/null; then
    break
  fi
  sleep 0.1
done

if ! grep -Fq 'Playing card: clock' wall.log || ! grep -Fq '▀' wall.log; then
  cat wall.log >&2
  exit 1
fi
kill -TERM "$daemon_pid"
for _ in {1..100}; do
  if ! kill -0 "$daemon_pid" 2>/dev/null; then
    break
  fi
  sleep 0.1
done
if kill -0 "$daemon_pid" 2>/dev/null; then
  echo 'Daemon did not stop after SIGTERM.' >&2
  exit 1
fi
wait "$daemon_pid"
daemon_pid=
grep -Fq 'Daemon stopped' wall.log
echo "Both modes of the $platform binary passed smoke tests."

bash "$scripts_dir/smoke_installer.sh" "$platform" "$downloads/$artifact/$archive"
