#!/usr/bin/env bash
#
# Scaffold a strategy Play.
#
# This used to copy `plays/route-experiment.example.play.ts` plus the
# route-experiment helpers. That worked example and the route-card ceremony
# around it are gone; `scaffold-search-experiment.py` is the strategy scaffold
# now, and it copies the template plus every shared helper it imports and
# rewrites the Play identity. This entry point stays so the documented command
# keeps working, and forwards to it.
set -euo pipefail

if [[ $# -ne 1 || "$1" != *.play.ts ]]; then
  echo "usage: init-strategy-play.sh <target.play.ts>" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target="$1"
target_dir="$(dirname "$target")"
target_name="$(basename "$target" .play.ts)"

if [[ -e "$target" ]]; then
  echo "refusing to overwrite an existing Play or shared helper" >&2
  exit 3
fi

mkdir -p "$target_dir"
exec python3 "$script_dir/scaffold-search-experiment.py" \
  "$target_dir" --name "$target_name"
