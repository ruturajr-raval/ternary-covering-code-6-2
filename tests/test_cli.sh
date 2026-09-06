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

compression_projection="$(mktemp "$root/build/test-compression.XXXXXX")"
fourth_specialized="$(mktemp "$root/build/test-fourth-specialized.XXXXXX")"
fourth_generic="$(mktemp "$root/build/test-fourth-generic.XXXXXX")"
fifth_specialized="$(mktemp "$root/build/test-fifth-specialized.XXXXXX")"
fifth_generic="$(mktemp "$root/build/test-fifth-generic.XXXXXX")"
cnf_output="$(mktemp "$root/build/test-cnf.XXXXXX")"
trap 'rm -f "$cnf_output" "$compression_projection" "$fourth_specialized" "$fourth_generic" "$fifth_specialized" "$fifth_generic"' EXIT
compression_output="$(
  build/compress_code \
    --evaluate-only \
    --start data/seed_18_supercode.txt \
    --output "$compression_projection"
)"
grep -q '^supercode centers: 18$' <<<"$compression_output"
grep -q '^supercode holes: 0$' <<<"$compression_output"
grep -q '^best projected holes: 7$' <<<"$compression_output"
grep -q '^four-coordinate violations: 12$' <<<"$compression_output"

build/generate_cnf --centers 16 --fix-zero >"$cnf_output"
grep -q '^p cnf ' "$cnf_output"
grep -q '^1 0$' "$cnf_output"

build/generate_cnf \
  --centers 16 \
  --anchor-weight 5 \
  >"$cnf_output"
grep -q \
  '^c reduced branch core: 2 fixed centers, 64 forbidden centers, 583 unresolved point clauses$' \
  "$cnf_output"
python3 tests/test_cnf_semantics.py "$cnf_output"

build/generate_cnf \
  --centers 16 \
  --anchor-weight 5 \
  --antipodal-cuts \
  --radial-sphere-cuts \
  >"$cnf_output"
grep -q '^c antipodal capacity cuts at 2 symmetry-fixed centers enabled$' \
  "$cnf_output"
grep -q '^c all 1458 radial distance-1 and distance-2 cuts enabled$' \
  "$cnf_output"

test "$(
  build/generate_cnf --anchor-weight 4 --list-third-orbits | wc -l |
    tr -d ' '
)" -eq 29
test "$(
  build/generate_cnf --anchor-weight 5 --list-third-orbits | wc -l |
    tr -d ' '
)" -eq 24
test "$(
  build/generate_cnf --anchor-weight 6 --list-third-orbits | wc -l |
    tr -d ' '
)" -eq 14

test "$(
  build/generate_cnf --anchor-weight 4 --list-next-orbits |
    awk -F'orbit_size=' '{total += $2} END {print total}'
)" -eq 471
test "$(
  build/generate_cnf --anchor-weight 5 --list-next-orbits |
    awk -F'orbit_size=' '{total += $2} END {print total}'
)" -eq 472
test "$(
  build/generate_cnf --anchor-weight 6 --list-next-orbits |
    awk -F'orbit_size=' '{total += $2} END {print total}'
)" -eq 472

build/generate_cnf \
  --centers 16 \
  --anchor-weight 5 \
  --third-orbit 0 \
  >"$cnf_output"
grep -q \
  '^c reduced branch core: 3 fixed centers, 64 forbidden centers,' \
  "$cnf_output"
grep -q '^-729 0$' "$cnf_output"
! grep -q '^-727 0$' "$cnf_output"

build/generate_cnf \
  --centers 16 \
  --anchor-weight 6 \
  --third-orbit 0 \
  >"$cnf_output"
grep -q \
  '^c reduced branch core: 3 fixed centers, 0 forbidden centers,' \
  "$cnf_output"
! grep -q '^-729 0$' "$cnf_output"

build/generate_cnf \
  --anchor-weight 5 \
  --third-orbit 3 \
  --list-fourth-orbits \
  >"$fourth_specialized"
build/generate_cnf \
  --anchor-weight 5 \
  --orbit-path 3 \
  --list-next-orbits \
  >"$fourth_generic"
cmp "$fourth_specialized" "$fourth_generic"

build/generate_cnf \
  --anchor-weight 6 \
  --third-orbit 2 \
  --fourth-orbit 1 \
  --list-fifth-orbits \
  >"$fifth_specialized"
build/generate_cnf \
  --anchor-weight 6 \
  --orbit-path 2,1 \
  --list-next-orbits \
  >"$fifth_generic"
cmp "$fifth_specialized" "$fifth_generic"

set +e
build/generate_cnf \
  --centers 16 \
  --at-most \
  --anchor-weight 4 \
  --orbit-path 0 \
  >/dev/null 2>&1
at_most_orbit_status=$?
build/generate_cnf \
  --centers 17 \
  --no-structural \
  --anchor-weight 5 \
  --list-third-orbits \
  >/dev/null 2>&1
wrong_cardinality_orbit_status=$?
build/generate_cnf \
  --centers 16 \
  --anchor-weight 4 \
  --orbit-path 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 \
  >/dev/null 2>&1
overlong_path_status=$?
set -e
test "$at_most_orbit_status" -eq 2
test "$wrong_cardinality_orbit_status" -eq 2
test "$overlong_path_status" -eq 2

python3 tests/test_recursive_cube_search.py
python3 tests/test_cp_sat_campaign.py
python3 tests/test_package_campaign.py

echo "all tests passed"
