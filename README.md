# Ternary Covering Code `K_3(6,2)`

This project studies the smallest number of radius-2 Hamming balls needed to
cover the ternary words of length 6.

The ambient space has `3^6 = 729` words. Each radius-2 ball contains 73 words.
The published interval is

```text
15 <= K_3(6,2) <= 17.
```

The immediate target is the unresolved 16-center case:

- a verified 16-word code would improve the upper bound to 16;
- a checked exclusion of every code of size at most 16, combined with the
  known 17-word code, would prove `K_3(6,2) = 17`.

## Why This Case Matters

This is a small but nontrivial exact covering problem. A result changes a
published entry in the ternary covering-code table, and its evidence can be
made unusually transparent:

- a construction is only 16 words and can be checked by direct enumeration;
- a nonexistence result can be supported by generated CNF, proof logs, and an
  independent proof checker;
- all 729 ambient words can be audited without numerical approximation.

## Current Status

The repository currently provides:

- an independent exact verifier for ternary length-6 codes;
- an attributed regression fixture for the known 17-word code;
- a parallel weighted local-search engine for 16-word constructions;
- a CNF generator for the size-at-most-16 set-cover formulation;
- deterministic regression tests.

No new bound is claimed at this stage.

## Build And Test

```bash
make
make test
```

Verify the known 17-word certificate:

```bash
build/verify_code data/reference_17_code.txt
```

Run a parallel construction search:

```bash
build/search_code \
  --centers 16 \
  --seconds 60 \
  --threads 8 \
  --start data/reference_17_code.txt \
  --output search-results/best_16_code.txt
```

Try exact three-center repair around a near-cover:

```bash
build/repair_code search-results/best_16_code.txt \
  --remove 3 \
  --seconds 300 \
  --output search-results/repaired_16_code.txt
```

Generate the baseline exact-16 CNF:

```bash
mkdir -p build/cnf
build/generate_cnf --centers 16 --fix-zero > build/cnf/k3_6_2_le16.cnf
```

Exact 16 is equivalent to size at most 16 because any smaller covering code can
be augmented with distinct centers without losing coverage. Pass `--at-most`
to generate the unsimplified size-at-most formulation directly.

Bootstrap the pinned SAT solvers used by the sweep tools:

```bash
JOBS=8 tools/bootstrap_solvers.sh
```

Run a resumable recursive cube campaign with projection cuts:

```bash
tools/recursive_cube_search.py \
  --weight 4 \
  --projection-cuts \
  --seconds 30 \
  --jobs 4 \
  --max-depth 8
```

The coordinator stores persistent logs, CNF hashes, and JSON classifications
under `research-results/`, then deletes non-SAT CNFs because they are
deterministically regenerable. `SOLVER_UNSAT` is exploratory evidence only;
it does not become a certified exclusion until a proof is independently
checked. Exit status 3 means the requested campaign remains open or deferred.

## Claim Boundary

This project does not currently claim:

- a 16-word covering code;
- nonexistence of a 16-word covering code;
- the exact value of `K_3(6,2)`;
- novelty for the known 17-word construction.

Any future mathematical claim must be tied to a deterministic certificate,
independent replay, and an explicit statement of what remains open.

## Author

Ruturaj R Raval  
Independent Researcher  
ORCID: 0000-0003-4930-8981
