# Ternary Covering Code `K_3(6,2)`

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22510341.svg)](https://doi.org/10.5281/zenodo.22510341)

## Project Overview

| Field | Value |
| --- | --- |
| Author | Ruturaj R Raval |
| Affiliation | Independent Researcher |
| ORCID | [0000-0003-4930-8981](https://orcid.org/0000-0003-4930-8981) |
| Field | Coding theory, set-cover duality, and exact combinatorial search |
| Problem | Determine the ternary covering number `K_3(6,2)` |
| Current result | Exact certificates exclude six of 38 normalized size-at-most-16 branches |
| Result type | Significant certified branch reduction with unchanged global bounds |
| Release | `v0.1.1` |
| Version DOI | [10.5281/zenodo.22647771](https://doi.org/10.5281/zenodo.22647771) |
| Concept DOI | [10.5281/zenodo.22510341](https://doi.org/10.5281/zenodo.22510341) |
| License | MIT for project-original material |

This repository studies whether the 729 ternary words of length 6 can be
covered by fewer than 17 Hamming balls of radius 2. It supplies a verified
17-word cover, a seven-hole 16-word near-cover, exact construction and
exclusion tools, and independently replayable certificates that reduce the
complete normalized size-at-most-16 frontier from 38 branches to 32.

## Problem And Background

For ternary words of length 6, `K_3(6,2)` is the minimum number of radius-2
Hamming balls needed to cover the full space of `3^6 = 729` words. The
recorded bounds for this instance appeared in published covering-code tables,
with the 17-word upper bound supplied by Hamalainen and Rankinen in 1991 and
the lower bound 15 recorded by Bertolo, Ostergard, and Weakley in 2004. The
audited interval is

```text
15 <= K_3(6,2) <= 17.
```

A construction with 16 distinct centers would improve the upper bound to 16.
A 15-word construction would determine the value at 15. Conversely, an
exact exclusion of every size-at-most-16 cover, together with the known
17-word cover, would prove `K_3(6,2) = 17`.

The instance is small enough for unusually transparent evidence. A candidate
construction can be checked exhaustively against all 729 ambient words, and
a nonexistence result can be divided into finite symmetry cases closed by
exact certificates or proof-producing SAT instances with independently
replayed proof logs.

## Starting Frontier And Longstanding Gap

Hamalainen and Rankinen supplied the recorded 17-word upper bound in 1991.
Bertolo, Ostergard, and Weakley recorded the lower bound 15 in 2004. The
existence of a 16-word cover has therefore remained unresolved for more than
two decades.

Before this project, the public frontier was the interval
`15 <= K_3(6,2) <= 17`, with no accepted construction of size 15 or 16 and no
complete exclusion of size-at-most-16 covers. The dated table history,
novelty search, and reuse boundary are documented in
[`docs/PRIOR_ART.md`](docs/PRIOR_ART.md).

## Main Result

After translating a hypothetical 16-cover so that one center is `000000`, a
direct antipodal argument excludes the case in which every other center has
weight at most 4. The 64 words antipodal to `000000` would receive total
capacity at most `15 * 4 = 60`.

The radius-3 sphere gives a complementary reduction. If all other centers had
weight at least 5, they would cover at most `15 * 10 = 150` of its 160 words.
Every normalized 16-cover therefore contains another center of weight at
most 4.

These facts reduce the theorem-driven third-center split to 24
weight-5-anchor orbits and 14 weight-6-anchor orbits. The resulting complete
normalized frontier has 38 live cases rather than 60.

A clean 60-second CP-SAT pass identified six candidate exclusions. Each
candidate was then replaced by an exact integer-scaled residual set-cover
dual certificate checked against every allowed center and all 729 ambient
words. The excluded weight-5 branches are represented by
`011110`, `011120`, `011220`, `012220`, and `022220`. The excluded weight-6
branch is represented by `002222`.

The rigorous outcome is a reduction from 38 normalized branches to 32. The
project-original contribution is this exact six-branch certificate theorem
and its independently checked normalized reduction. The known 17-word cover
is prior work and is only reverified here. The global interval remains
unchanged. Exact values and proofs are recorded in
[`docs/WEIGHTED_BRANCH_CERTIFICATES.md`](docs/WEIGHTED_BRANCH_CERTIFICATES.md).

## Method And Proof Architecture

The project combines finite geometry, symmetry normalization, constructive
search, exact residual set cover, and independently implemented certificate
replay:

- A standalone verifier checks the attributed public 17-word witness.
- Maintained search data include a verified 18-word seed and a 16-word
  near-cover with seven uncovered words.
- Local search, exact residual repair, and 18-to-16 compression tools explore
  constructions.
- Deterministic CNF and CP-SAT formulations encode the exact 16-center
  problem.
- Recursive stabilizer-orbit branching supports arbitrary depth.
- Coordinate, projection, radial-sphere, and antipodal capacity cuts reduce
  the search.
- Integer weighted-hole dual certificates prove the six named branch
  exclusions without relying on solver exit status.
- Resumable campaigns record source and executable fingerprints, hashed
  instances and logs, and CP-SAT formulation and environment fingerprints.

The proof architecture separates exploratory discovery from the theorem.
CP-SAT suggested candidate branches, but the mathematical exclusions depend
only on exact integer certificates and their independent checkers.

## Verification And Evidence

Independent Python and C++20 implementations reconstruct every certified
branch, evaluate all 729 ambient words, and compare canonical certificate
tables entry for entry. Mutation tests, production-generator comparisons,
deterministic manifests, and current CI provide additional checks.

The certificate replay requires Python 3 and a C++20 compiler, uses no GPU,
and is designed for a commodity workstation. Optional construction and
solver campaigns have explicit time and worker limits and are not part of
the theorem.

The selected evidence includes:

- the attributed 17-word regression witness;
- the 18-word search seed and seven-hole 16-word near-cover;
- machine-readable weights for all six certified exclusions;
- two independently encoded exact-integer certificate checkers;
- structural lemmas and the complete 38-branch normalization;
- deterministic campaign records and fail-closed claim boundaries.

Campaign settings and fingerprints are documented in
[`docs/COMPUTATIONAL_STATUS.md`](docs/COMPUTATIONAL_STATUS.md).

## Reproduction

Build the project and run the test suite:

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

Campaign records are written under `research-results/`, which is excluded
from source control. Solver `INFEASIBLE` remains exploratory evidence only.
Cached CP-SAT branches are accepted only after the current code reconstructs
the same serialized formulation, and interrupted campaigns terminate their
active solver process groups before returning.

The exact certificate replay is CPU-bound, uses no GPU, and fits an ordinary
workstation. The optional construction, SAT, and CP-SAT campaigns have
user-selected runtime, memory, worker, and storage requirements and are not
needed to verify the six certified exclusions.

## Claims

This project claims:

- the implemented and tested search and verification machinery;
- the verified attributed 17-word regression certificate;
- the verified 18-word seed and seven-hole 16-word near-cover;
- the stated coordinate, projection, radial-sphere, and antipodal necessary
  conditions;
- the proof that the normalized maximum-weight-4 branch is impossible;
- the complete 38-case low-weight third-center reduction;
- exact weighted-hole exclusion of the six named branches;
- the resulting 32-branch normalized frontier;
- reproducible source-bound campaign records.

The complete human-readable claim boundary is maintained in
[`docs/CLAIMS.md`](docs/CLAIMS.md), with machine-readable claims in
[`research/claim.yaml`](research/claim.yaml).

## Limitations And Nonclaims

This project does not claim:

- a 15-word or 16-word covering code;
- nonexistence of a 16-word covering code;
- the exact value of `K_3(6,2)`;
- a new published table bound;
- novelty for the known 17-word construction;
- exclusion of any of the remaining 32 normalized branches;
- a theorem based only on CP-SAT or SAT solver status;
- completed external mathematical review;
- priority over unpublished or unindexed work.

The result is a certified branch reduction, not a resolution of the full
covering-number problem. No arXiv or HAL deposit is currently part of the
publication record. Any public summary must state that six branches are
excluded, 32 remain unresolved, and the global interval is unchanged.

Release `v0.1.1` is an archival and documentation patch. It adds an
explicitly named compiled PDF, a deterministic report-source archive, and a
checksum manifest. The theorem, proof, certificates, data, computations, and
global claim boundary are unchanged from `v0.1.0`.

## Significance And Use

The result replaces exploratory solver statuses with compact exact proofs and
reduces a complete finite normalized frontier from 38 branches to 32. The
certificates provide independently checkable progress toward resolving a
covering-code table entry that has remained open for more than two decades.

The repository can be used to:

- verify the known upper-bound witness independently;
- reproduce the structural normalization and six exact exclusions;
- test new 15-word or 16-word construction methods;
- develop deeper stabilizer-orbit splits and residual dual certificates;
- compare proof-producing SAT approaches with exact set-cover duality;
- reuse the certificate and campaign architecture for related covering-code
  instances.

## Remaining Work And Future Directions

The immediate search frontier consists of 32 unresolved normalized branches.
The strongest next routes are deeper stabilizer-orbit splits, further exact
dual certificates, proof-producing SAT closures, and independent
construction or exact repair searches.

Future results must pass these acceptance gates:

1. **Construction gate.** A 16-word candidate must contain 16 distinct words
   and cover all 729 ambient words at radius 2 under the existing verifier
   and a separately implemented exhaustive checker. Such a witness would
   improve the upper bound to 16. A verified 15-word witness would determine
   the exact value at 15.
2. **Further exclusion gate.** A new branch exclusion must use the complete
   stabilizer-orbit definition, an exact certificate or checked proof object,
   independent replay, mutation tests, and a refreshed prior-art audit.
   Solver status, timeout volume, or search duration alone does not pass this
   gate.
3. **Global exclusion gate.** All 32 remaining normalized branches must be
   closed by accepted evidence. Together with the verified 17-word witness,
   that would prove `K_3(6,2) = 17`.

The ranked research routes and kill criteria are maintained in
[`docs/RESEARCH_PLAN.md`](docs/RESEARCH_PLAN.md).

## Repository Layout

| Path | Purpose and trust boundary |
| --- | --- |
| [`data/reference_17_code.txt`](data/reference_17_code.txt) | Attributed public 17-word regression witness, checked exhaustively here but not claimed as project-original |
| [`data/seed_16_near_cover.txt`](data/seed_16_near_cover.txt) | Verified 16-word near-cover with seven uncovered words |
| [`data/weighted_branch_certificates.json`](data/weighted_branch_certificates.json) | Machine-readable integer weights for the six certified exclusions |
| [`tools/verify_branch_certificates.py`](tools/verify_branch_certificates.py) | Python reconstruction and exact-capacity checker |
| [`src/verify_branch_certificates.cpp`](src/verify_branch_certificates.cpp) | Independently encoded C++20 checker and canonical certificate table |
| [`docs/WEIGHTED_BRANCH_CERTIFICATES.md`](docs/WEIGHTED_BRANCH_CERTIFICATES.md) | Certificate theorem, exact values, branch definitions, and replay procedure |
| [`docs/STRUCTURAL_LEMMAS.md`](docs/STRUCTURAL_LEMMAS.md) | Sphere, antipodal, projection, and normalization lemmas |
| [`docs/COMPUTATIONAL_STATUS.md`](docs/COMPUTATIONAL_STATUS.md) | Exact finite frontier, exploratory solver statuses, fingerprints, and claim limits |
| [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md) | Dated table history, novelty search, and reuse boundary |
| [`docs/CLAIMS.md`](docs/CLAIMS.md) | Human-readable claims, nonclaims, significance, and review boundary |
| [`docs/RESEARCH_PLAN.md`](docs/RESEARCH_PLAN.md) | Ranked next routes, acceptance gates, and kill criteria |
| [`research/claim.yaml`](research/claim.yaml) | Machine-readable supported claims and nonclaims |
| [`research/release-gate.json`](research/release-gate.json) | Publication-gate decisions for the scoped theorem |
| [`paper/main.tex`](paper/main.tex) | Technical report source |
| [`PUBLICATION.md`](PUBLICATION.md) | Release result, asset, archive, and limitation record |
| [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | Upstream witness provenance and third-party licensing |

## Publication Citation And Archive

The public repository is
[`ruturajr-raval/ternary-covering-code-6-2`](https://github.com/ruturajr-raval/ternary-covering-code-6-2).
The paper-inclusive archival patch is identified as
[`v0.1.1`](https://github.com/ruturajr-raval/ternary-covering-code-6-2/releases/tag/v0.1.1).
Its release set contains
`ternary-covering-code-6-2-paper.pdf`,
`ternary-covering-code-6-2-source.tar.gz`, and `SHA256SUMS`.

Release `v0.1.1` uses version DOI
[10.5281/zenodo.22647771](https://doi.org/10.5281/zenodo.22647771), while
[10.5281/zenodo.22510341](https://doi.org/10.5281/zenodo.22510341) is the
stable concept DOI for all versions. The prior `v0.1.0` archive remains the
historical first release of the same scoped theorem.

GitHub and Zenodo are the current dissemination baseline. No preprint-server
deposit or external mathematical review is claimed. Citation metadata is in
[`CITATION.cff`](CITATION.cff), release history is in
[`RELEASE_NOTES.md`](RELEASE_NOTES.md), and the complete release record is in
[`PUBLICATION.md`](PUBLICATION.md). Cite the paper-inclusive `v0.1.1`
archival patch using its version DOI.

## Authorship

Ruturaj R Raval, Independent Researcher

ORCID: [0000-0003-4930-8981](https://orcid.org/0000-0003-4930-8981)

## Licensing And Provenance

Project-original source, certificate data, documentation, and report material
are released under the MIT License.

The reference 17-word code is transcribed from
[`florath/covering-codes-lean`](https://github.com/florath/covering-codes-lean).
It is used only as an attributed regression fixture and remains under the
upstream BSD 3-Clause terms recorded in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). No upstream
implementation code is included.

CaDiCaL, Kissat, and OR-Tools are optional external tools installed only in
ignored local environments. They are not release artifacts and remain under
their respective upstream licenses. The six mathematical exclusions depend
on exact integer certificates and two independent checkers, not on CP-SAT or
SAT exit status.

## References

- G. Keri, [Tables for covering codes](https://old.sztaki.hu/~keri/codes/3_tables.pdf),
  accessed 2026-09-06.
- H. Hamalainen and S. Rankinen, [Upper bounds for football pool problems and
  mixed covering codes](https://doi.org/10.1016/0097-3165(91)90024-B),
  *Journal of Combinatorial Theory, Series A* 56 (1991), 84-95.
- P. R. J. Ostergard and H. O. Hamalainen, [A new table of binary/ternary
  mixed covering codes](https://doi.org/10.1023/A:1008228721072),
  *Designs, Codes and Cryptography* 11 (1997), 151-178.
- R. Bertolo, P. R. J. Ostergard, and W. D. Weakley, [An updated table of
  binary/ternary mixed covering codes](https://doi.org/10.1002/jcd.20008),
  *Journal of Combinatorial Designs* 12 (2004), 157-176.
- D. Gijswijt and S. Polak, [Semidefinite lower bounds for covering
  codes](https://arxiv.org/abs/2504.01932), arXiv:2504.01932v2, 2026.
- A. Florath,
  [`covering-codes-lean`](https://github.com/florath/covering-codes-lean),
  including the explicit `K_3(6,2) <= 17` witness and its documented failed
  search directions.
