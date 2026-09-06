#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
tools_dir="$root/.tools"

cadical_commit="c60730422e758ef1cebe7aeddf2dda31c996bf04"
kissat_commit="8af8e56f174b778aef3aa45af9f739b2a5f492c2"

mkdir -p "$tools_dir"

check_repository() {
  local directory="$1"
  local expected_remote="$2"
  if [[ "$(git -C "$directory" remote get-url origin)" != "$expected_remote" ]]; then
    printf 'unexpected origin for %s\n' "$directory" >&2
    exit 2
  fi
  if ! git -C "$directory" diff --quiet ||
     ! git -C "$directory" diff --cached --quiet; then
    printf 'tracked modifications found in %s\n' "$directory" >&2
    exit 2
  fi
}

if [[ ! -d "$tools_dir/cadical/.git" ]]; then
  git clone https://github.com/arminbiere/cadical.git "$tools_dir/cadical"
fi
check_repository \
  "$tools_dir/cadical" \
  "https://github.com/arminbiere/cadical.git"
git -C "$tools_dir/cadical" fetch origin "$cadical_commit"
git -C "$tools_dir/cadical" checkout --detach "$cadical_commit"
test "$(git -C "$tools_dir/cadical" rev-parse HEAD)" = "$cadical_commit"
(
  cd "$tools_dir/cadical"
  if [[ -f makefile || -f Makefile ]]; then
    make clean
  fi
  ./configure
  make -j"${JOBS:-4}"
)

if [[ ! -d "$tools_dir/kissat/.git" ]]; then
  git clone https://github.com/arminbiere/kissat.git "$tools_dir/kissat"
fi
check_repository \
  "$tools_dir/kissat" \
  "https://github.com/arminbiere/kissat.git"
git -C "$tools_dir/kissat" fetch origin "$kissat_commit"
git -C "$tools_dir/kissat" checkout --detach "$kissat_commit"
test "$(git -C "$tools_dir/kissat" rev-parse HEAD)" = "$kissat_commit"
(
  cd "$tools_dir/kissat"
  if [[ -f makefile || -f Makefile ]]; then
    make clean
  fi
  ./configure
  make -j"${JOBS:-4}"
)

printf 'CaDiCaL %s\n' "$cadical_commit"
printf 'Kissat %s\n' "$kissat_commit"
