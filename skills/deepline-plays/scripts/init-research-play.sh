#!/usr/bin/env bash
set -euo pipefail

force=false
if [[ "${1:-}" == "--force" ]]; then
  force=true
  shift
fi

if [[ $# -ne 1 || "$1" != *.play.ts ]]; then
  echo "usage: init-research-play.sh [--force] <target.play.ts>" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill_dir="$(cd "$script_dir/.." && pwd)"
target="$1"
target_dir="$(dirname "$target")"

outputs=(
  "$target"
  "$target_dir/shared/rerank.ts"
  "$target_dir/shared/route-experiment.ts"
  "$target_dir/shared/research-kernel.ts"
)
if [[ "$force" != true ]]; then
  for output in "${outputs[@]}"; do
    if [[ -e "$output" ]]; then
      echo "refusing to overwrite $output; pass --force to replace the scaffold" >&2
      exit 3
    fi
  done
fi

mkdir -p "$target_dir/shared"
cp "$skill_dir/plays/shared/rerank.ts" "$target_dir/shared/rerank.ts"
cp "$skill_dir/plays/shared/route-experiment.ts" "$target_dir/shared/route-experiment.ts"
cp "$skill_dir/plays/shared/research-kernel.ts" "$target_dir/shared/research-kernel.ts"
cp "$skill_dir/plays/research-kernel.example.play.ts" "$target"

echo "Created $target with the Deepline research kernel in $target_dir/shared"
