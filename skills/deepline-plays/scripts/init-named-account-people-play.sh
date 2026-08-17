#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || "$1" != *.play.ts ]]; then
  echo "usage: init-named-account-people-play.sh <target.play.ts>" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill_dir="$(cd "$script_dir/.." && pwd)"
target="$1"
target_dir="$(dirname "$target")"

if [[ -e "$target" || -e "$target_dir/shared/route-experiment.ts" ]]; then
  echo "refusing to overwrite an existing Play or shared helper" >&2
  exit 3
fi

mkdir -p "$target_dir/shared"
cp "$skill_dir/plays/named-account-people.kernel.play.ts" "$target"
cp "$skill_dir/plays/shared/route-experiment.ts" "$target_dir/shared/route-experiment.ts"
cp "$skill_dir/plays/shared/rerank.ts" "$target_dir/shared/rerank.ts"
echo "Created $target and local helpers. Confirm the two live adapters, then edit ROLE_TERMS, SENIORITY_TERMS, and the final export fields."
