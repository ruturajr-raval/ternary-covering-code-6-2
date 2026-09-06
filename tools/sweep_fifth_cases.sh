#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 5 ]]; then
  echo "usage: $0 WEIGHT THIRD FOURTH [SECONDS] [JOBS]" >&2
  exit 2
fi

weight="$1"
third="$2"
fourth="$3"
seconds="${4:-30}"
jobs="${5:-8}"

root="$(cd "$(dirname "$0")/.." && pwd)"
generator="$root/build/generate_cnf"
solver="$root/.tools/cadical/build/cadical"
case_root="$root/build/fifth-cases/w${weight}_o${third}_f${fourth}"

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
    --fourth-orbit "$fourth" \
    --list-fifth-orbits |
    wc -l |
    tr -d ' '
)"

run_case() {
  local fifth="$1"
  local stem
  stem="$(printf 'g%03d' "$fifth")"
  local cnf="$case_root/$stem.cnf"
  local log="$case_root/$stem.log"
  local result="$case_root/$stem.result"

  "$generator" \
    --centers 16 \
    --anchor-weight "$weight" \
    --third-orbit "$third" \
    --fourth-orbit "$fourth" \
    --fifth-orbit "$fifth" \
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
  printf '%s\t%s\t%s\n' "$fifth" "$outcome" "$rc" >"$result"
}

export root generator solver case_root weight third fourth seconds
export -f run_case

seq 0 $((count - 1)) |
  xargs -P "$jobs" -n 1 bash -c 'run_case "$1"' _

cat "$case_root"/*.result | sort -n >"$case_root/results.tsv"
cat "$case_root/results.tsv"
