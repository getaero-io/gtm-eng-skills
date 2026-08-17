#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || "$1" != *.play.ts ]]; then
  echo "usage: init-research-experiment-play.sh <target.play.ts>" >&2
  exit 2
fi

target="$1"
if [[ -e "$target" ]]; then
  echo "refusing to overwrite $target" >&2
  exit 3
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill_dir="$(cd "$script_dir/.." && pwd)"
target_dir="$(dirname "$target")"
shared_dir="$target_dir/shared"

for destination in "$shared_dir/research-experiment.ts"; do
  if [[ -e "$destination" ]]; then
    echo "refusing to overwrite $destination" >&2
    exit 3
  fi
done

sources=(
  "$skill_dir/plays/research-experiment.example.play.ts"
  "$skill_dir/plays/shared/research-experiment.ts"
)
for source in "${sources[@]}"; do
  if [[ ! -f "$source" ]]; then
    echo "research-experiment scaffold is incomplete: missing $source" >&2
    exit 4
  fi
done

mkdir -p "$shared_dir"
cp "$skill_dir/plays/research-experiment.example.play.ts" "$target"
cp "$skill_dir/plays/shared/research-experiment.ts" "$shared_dir/research-experiment.ts"

echo "Created $target and local research-experiment helpers."
echo "Edit the visible row contract, claims, candidate topologies, literal provider adapters, and promotion policy."
echo "Do not replace the adapters with inferred mappings or opaque prompt-only research."
