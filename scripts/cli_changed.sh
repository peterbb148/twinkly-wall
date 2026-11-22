#!/usr/bin/env bash
# Print whether an automatic CI event changed a CLI source file.
set -euo pipefail

event=$1
base=$2
head=$3

case "$event" in
  pull_request)
    # Compare only the changes introduced by the PR.
    range="$base...$head"
    ;;
  push)
    if [[ $base == 0000000000000000000000000000000000000000 ]]; then
      base=$(git hash-object -w -t tree /dev/null)
    fi
    range="$base..$head"
    ;;
  *)
    printf 'Unsupported event: %s\n' "$event" >&2
    exit 2
    ;;
esac

if git diff --quiet --no-ext-diff --no-renames "$range" -- \
  src/twinkly_wall/command.py src/twinkly_wall/cli.py src/twinkly_wall/daemon.py; then
  echo false
else
  status=$?
  if [[ "$status" != 1 ]]; then
    exit "$status"
  fi
  echo true
fi
