#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

reference_output="$(build/verify_code data/reference_17_code.txt)"
grep -q '^centers: 17$' <<<"$reference_output"
grep -q '^distinct: yes$' <<<"$reference_output"
grep -q '^holes: 0$' <<<"$reference_output"

set +e
noncover_output="$(build/verify_code tests/reference_16_noncover.txt 2>&1)"
noncover_status=$?
set -e
test "$noncover_status" -eq 1
grep -Eq '^holes: [1-9][0-9]*$' <<<"$noncover_output"

cnf_output="$(mktemp)"
trap 'rm -f "$cnf_output"' EXIT
build/generate_cnf --centers 16 --fix-zero >"$cnf_output"
grep -q '^p cnf ' "$cnf_output"
grep -q '^1 0$' "$cnf_output"

test "$(
  build/generate_cnf --anchor-weight 4 --list-third-orbits | wc -l |
    tr -d ' '
)" -eq 29
test "$(
  build/generate_cnf --anchor-weight 5 --list-third-orbits | wc -l |
    tr -d ' '
)" -eq 34
test "$(
  build/generate_cnf --anchor-weight 6 --list-third-orbits | wc -l |
    tr -d ' '
)" -eq 26

echo "all tests passed"
