#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || "$1" != *.play.ts ]]; then
  echo "usage: init-company-question-research-play.sh <target.play.ts>" >&2
  exit 2
fi

target="$1"
if [[ -e "$target" ]]; then
  echo "refusing to overwrite $target" >&2
  exit 3
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$script_dir/../plays/company-question-research.kernel.play.ts" "$target"

echo "Created $target with the official-web company-question kernel"
