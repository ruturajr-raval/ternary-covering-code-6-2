#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
tools_dir="$root/.tools"

cadical_commit="c60730422e758ef1cebe7aeddf2dda31c996bf04"
kissat_commit="8af8e56f174b778aef3aa45af9f739b2a5f492c2"

mkdir -p "$tools_dir"

if [[ ! -d "$tools_dir/cadical/.git" ]]; then
  git clone https://github.com/arminbiere/cadical.git "$tools_dir/cadical"
fi
git -C "$tools_dir/cadical" fetch origin "$cadical_commit"
git -C "$tools_dir/cadical" checkout --detach "$cadical_commit"
(
  cd "$tools_dir/cadical"
  ./configure
  make -j"${JOBS:-4}"
)

if [[ ! -d "$tools_dir/kissat/.git" ]]; then
  git clone https://github.com/arminbiere/kissat.git "$tools_dir/kissat"
fi
git -C "$tools_dir/kissat" fetch origin "$kissat_commit"
git -C "$tools_dir/kissat" checkout --detach "$kissat_commit"
(
  cd "$tools_dir/kissat"
  ./configure
  make -j"${JOBS:-4}"
)

printf 'CaDiCaL %s\n' "$cadical_commit"
printf 'Kissat %s\n' "$kissat_commit"
