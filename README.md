# Ternary Covering Code `K_3(6,2)`

This project studies the smallest number of radius-2 Hamming balls needed to
cover the 729 ternary words of length 6.

The published interval is

```text
15 <= K_3(6,2) <= 17.
```

The upper bound dates to work of Hamalainen and Rankinen in 1991. The lower
bound of 15 was recorded by Bertolo, Ostergard, and Weakley in 2004. The
16-center case has therefore remained the exact gap for more than two
decades. Sources and the current-frontier review are recorded in
[`docs/PRIOR_ART.md`](docs/PRIOR_ART.md).

## Why This Case Matters

A resolution would change a published covering-code table entry:

- a verified 16-word cover would improve the upper bound to 16;
- a certified exclusion of every 16-word cover, together with the known
  17-word cover, would prove `K_3(6,2) = 17`.

The instance is small enough for unusually transparent evidence. A
construction contains only 16 words and can be checked against every ambient
word. A nonexistence result can be decomposed into finite symmetry cases
closed by exact certificates or by proof-producing SAT instances with
independently replayed proof logs.

## Verified Progress

The repository currently provides:

- a standalone exact verifier and an attributed 17-word regression
  certificate;
- a verified 18-word search seed and a 16-word near-cover leaving 7 holes;
- local search, exact residual repair, and 18-to-16 compression tools;
- deterministic CNF and CP-SAT formulations of the exact 16-center problem;
- recursive stabilizer-orbit branching to arbitrary depth;
- proved coordinate, projection, radial-sphere, and antipodal capacity cuts;
- exact integer weighted-hole certificates for six normalized branches;
- resumable campaigns with source and executable fingerprints, hashed
  instances and logs, plus CP-SAT model and environment fingerprints.

One broad normalized branch is closed by a direct counting argument. After
translating a hypothetical 16-cover so that one center is `000000`, its
maximum center weight cannot be at most 4. The 64 words antipodal to
`000000` would receive capacity at most `15 * 4 = 60`. Thus only
maximum-weight cases 5 and 6 remain.

The radius-3 sphere gives a complementary reduction. If all other centers had
weight at least 5, they would cover at most `15 * 10 = 150` of its 160 words.
Every normalized 16-cover therefore contains another center of weight at most
4. The theorem-driven third-center split has 24 weight-5-anchor orbits and 14
weight-6-anchor orbits, for 38 live cases rather than 60.

A clean 60-second CP-SAT pass identified six candidate exclusions. Each now
has an exact integer-scaled residual set-cover dual certificate that is
checked over all 729 ambient words and every center allowed by its branch.
The five weight-5 branches
represented by `011110`, `011120`, `011220`, `012220`, and `022220`, and the
weight-6 branch represented by `002222`, are rigorously excluded. The
normalized frontier is therefore reduced from 38 branches to 32.

The proof and exact values are recorded in
[`docs/WEIGHTED_BRANCH_CERTIFICATES.md`](docs/WEIGHTED_BRANCH_CERTIFICATES.md).
Campaign settings and fingerprints remain in
[`docs/COMPUTATIONAL_STATUS.md`](docs/COMPUTATIONAL_STATUS.md).

This is a rigorous certified branch reduction, not a new bound on
`K_3(6,2)`.

## Build And Test

```bash
make
make test
```

Verify the known 17-word certificate and the current near-cover:

```bash
build/verify_code data/reference_17_code.txt
build/verify_code data/seed_16_near_cover.txt
```

Verify all six weighted branch certificates:

```bash
python3 tools/verify_branch_certificates.py
build/verify_branch_certificates
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

Search projections of a maintained 18-word cover:

```bash
build/compress_code \
  --seconds 60 \
  --threads 8 \
  --start data/seed_18_supercode.txt \
  --output search-results/compressed_best_16.txt
```

Try exact three-center repair around a near-cover:

```bash
build/repair_code data/seed_16_near_cover.txt \
  --remove 3 \
  --seconds 300 \
  --output search-results/repaired_16_code.txt
```

Generate a normalized exact-16 CNF with the strongest implemented cuts:

```bash
mkdir -p build/cnf
build/generate_cnf \
  --centers 16 \
  --anchor-weight 5 \
  --projection-cuts \
  --four-projection-cuts \
  --five-projection-cuts \
  --antipodal-cuts \
  --radial-sphere-cuts \
  > build/cnf/k3_6_2_w5.cnf
```

Exact 16 is equivalent to size at most 16 because any smaller cover can be
augmented with distinct centers without losing coverage. Pass `--at-most` to
generate the unsimplified size-at-most formulation directly.

Bootstrap the pinned SAT solvers used by the recursive campaign:

```bash
JOBS=8 tools/bootstrap_solvers.sh
```

Run a resumable recursive cube campaign:

```bash
tools/recursive_cube_search.py \
  --weight 5 \
  --projection-cuts \
  --five-projection-cuts \
  --antipodal-cuts \
  --radial-sphere-cuts \
  --seconds 30 \
  --jobs 4 \
  --max-depth 8
```

The optional CP-SAT path uses a platform-specific hash-locked environment:

```bash
tools/bootstrap_ortools.sh
make test-cp-sat
.tools/ortools-venv/bin/python tools/cp_sat_orbit_campaign.py \
  --weight 5 \
  --five-projection-cuts \
  --seconds 60 \
  --jobs 4 \
  --workers-per-job 2
```

Campaign records are written under `research-results/`, which is intentionally
excluded from source control. Solver `INFEASIBLE` remains exploratory evidence
only. The six current exclusions are claimed from the separate exact integer
certificates, not from solver exit status. Cached CP-SAT branches are accepted
only after the current code reconstructs the same serialized model, and
interrupted campaigns terminate their active solver process groups before
returning.

## Claim Boundary

This project currently claims the implemented and tested search machinery,
the stated necessary conditions, the verified 17-word certificate, the
7-hole near-cover, the proof that the normalized maximum-weight-4 branch is
impossible, the complete 38-case low-weight third-center reduction, the exact
weighted-hole exclusion of six named branches, the resulting 32-branch
frontier, and the reproducible campaign record.

It does not claim:

- a 16-word covering code;
- nonexistence of a 16-word covering code;
- the exact value of `K_3(6,2)`;
- novelty for the known 17-word construction;
- exclusion of any of the remaining 32 normalized branches;
- a certified exclusion based only on a solver status.

## Author

Ruturaj R Raval  
Independent Researcher  
ORCID: 0000-0003-4930-8981
