#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 4 ]]; then
  echo "usage: $0 ANCHOR_WEIGHT THIRD_ORBIT [SECONDS] [JOBS]" >&2
  exit 2
fi

weight="$1"
third="$2"
seconds="${3:-30}"
jobs="${4:-8}"

root="$(cd "$(dirname "$0")/.." && pwd)"
generator="$root/build/generate_cnf"
solver="$root/.tools/cadical/build/cadical"
case_root="$root/research-results/fourth-cases/w${weight}_o${third}"

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
    --third-orbit "$third" \
    --list-fourth-orbits |
    wc -l |
    tr -d ' '
)"

run_case() {
  local fourth="$1"
  local stem
  stem="$(printf 'f%03d' "$fourth")"
  local cnf="$case_root/$stem.cnf"
  local log="$case_root/$stem.log"
  local result="$case_root/$stem.result"

  "$generator" \
    --centers 16 \
    --anchor-weight "$weight" \
    --third-orbit "$third" \
    --fourth-orbit "$fourth" \
    >"$cnf"

  set +e
  "$solver" -t "$seconds" "$cnf" >"$log" 2>&1
  local rc=$?
  set -e

  local outcome="ERROR"
  if grep -q '^s SATISFIABLE' "$log"; then
    outcome="SOLVER_SAT"
  elif grep -q '^s UNSATISFIABLE' "$log"; then
    outcome="SOLVER_UNSAT"
  elif grep -q '^c UNKNOWN' "$log"; then
    outcome="UNKNOWN"
  fi
  printf '%s\t%s\t%s\n' "$fourth" "$outcome" "$rc" >"$result"
}

export root generator solver case_root weight third seconds
export -f run_case

seq 0 $((count - 1)) |
  xargs -P "$jobs" -n 1 bash -c 'run_case "$1"' _

cat "$case_root"/*.result | sort -n >"$case_root/results.tsv"
cat "$case_root/results.tsv"
