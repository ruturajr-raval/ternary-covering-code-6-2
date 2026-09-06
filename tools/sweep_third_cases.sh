#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo "usage: $0 ANCHOR_WEIGHT [SECONDS] [JOBS]" >&2
  exit 2
fi

weight="$1"
seconds="${2:-30}"
jobs="${3:-8}"

root="$(cd "$(dirname "$0")/.." && pwd)"
generator="$root/build/generate_cnf"
solver="$root/.tools/cadical/build/cadical"
case_root="$root/build/third-cases/w${weight}"

if [[ ! -x "$generator" ]]; then
  echo "missing generator: run make first" >&2
  exit 2
fi
if [[ ! -x "$solver" ]]; then
  echo "missing CaDiCaL under .tools/cadical" >&2
  exit 2
fi

mkdir -p "$case_root"
count="$(
  "$generator" \
    --anchor-weight "$weight" \
    --list-third-orbits |
    wc -l |
    tr -d ' '
)"

run_case() {
  local third="$1"
  local stem
  stem="$(printf 'o%03d' "$third")"
  local cnf="$case_root/$stem.cnf"
  local log="$case_root/$stem.log"
  local result="$case_root/$stem.result"

  "$generator" \
    --centers 16 \
    --anchor-weight "$weight" \
    --third-orbit "$third" \
    >"$cnf"

  set +e
  "$solver" -t "$seconds" "$cnf" >"$log" 2>&1
  local rc=$?
  set -e

  local outcome="ERROR"
  if grep -q '^s SATISFIABLE' "$log"; then
    outcome="SAT"
  elif grep -q '^s UNSATISFIABLE' "$log"; then
    outcome="UNSAT"
  elif grep -q '^c UNKNOWN' "$log"; then
    outcome="UNKNOWN"
  fi
  printf '%s\t%s\t%s\n' "$third" "$outcome" "$rc" >"$result"
}

export root generator solver case_root weight seconds
export -f run_case

seq 0 $((count - 1)) |
  xargs -P "$jobs" -n 1 bash -c 'run_case "$1"' _

cat "$case_root"/*.result | sort -n >"$case_root/results.tsv"
cat "$case_root/results.tsv"
