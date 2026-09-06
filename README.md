# Ternary Covering Code `K_3(6,2)`

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22510341.svg)](https://doi.org/10.5281/zenodo.22510341)

## Project Overview

### Project Metadata

| Field | Value |
| --- | --- |
| Author | Ruturaj R Raval |
| Affiliation | Independent Researcher |
| ORCID | [0000-0003-4930-8981](https://orcid.org/0000-0003-4930-8981) |
| Field | Coding theory, set-cover duality, and exact combinatorial search |
| Problem | Determine the ternary covering number `K_3(6,2)` |
| Current result | Exact certificates exclude six of 38 normalized size-at-most-16 branches |
| Result type | Significant certified branch reduction with unchanged global bounds |
| Release | `v0.1.0` |
| Version DOI | `10.5281/zenodo.22510342` |
| Concept DOI | `10.5281/zenodo.22510341` |
| License | MIT for project-original material |

### Problem And Context

The problem asks for the fewest radius-2 Hamming balls covering all 729
ternary words of length 6. The audited interval is
`15 <= K_3(6,2) <= 17`. The upper bound dates to 1991 and the lower bound to
2004, leaving the existence of a 16-word cover unresolved for more than two
decades. A verified 16-word cover would improve the upper bound, while a
complete exclusion would settle the value at 17.

### Work And Verified Outcome

The project verifies a public 17-word cover, retains a seven-hole 16-word
near-cover, and develops exact construction and exclusion tools. Sphere and
antipodal arguments reduce the normalized size-at-most-16 search to 38
third-center branches. Exact integer residual set-cover dual certificates
exclude five weight-5 branches and one weight-6 branch, leaving 32 unresolved.

### Claim Boundary

The six named branch exclusions and the complete 38-branch normalization are
rigorous. The project does not claim a 15-word or 16-word cover, nonexistence
of all size-at-most-16 covers, a new table bound, or a theorem based only on
CP-SAT or SAT solver status. The remaining 32 branches are explicitly open.

### Verification And Reproduction

Independent Python and C++20 exact-integer implementations reconstruct every
certified branch over all 729 ambient words and compare canonical certificate
tables entry for entry. Mutation tests, production-generator comparisons,
deterministic manifests, and current CI provide additional checks. Detailed
commands and evidence paths appear below and under `docs/`. The certificate
replay requires Python 3 and a C++20 compiler, uses no GPU, and is designed
for a commodity workstation; the optional construction and solver campaigns
have explicit time and worker limits and are not part of the theorem.

### Significance, Limitations, And Future Work

The certificates replace exploratory solver statuses with compact exact
proofs and reduce a complete normalized frontier from 38 cases to 32. The
global interval remains unchanged. Next work applies deeper stabilizer-orbit
splits, derives further dual certificates, and continues independent
construction and exact repair searches.

### Release, Citation, And Author

The public repository is
[`ruturajr-raval/ternary-covering-code-6-2`](https://github.com/ruturajr-raval/ternary-covering-code-6-2).
The immutable tagged release is
[`v0.1.0`](https://github.com/ruturajr-raval/ternary-covering-code-6-2/releases/tag/v0.1.0).
It is archived at version DOI `10.5281/zenodo.22510342`; the stable
all-versions DOI is `10.5281/zenodo.22510341`. The Zenodo snapshot contains
63 files that were checked against the release tag tree. GitHub and Zenodo
are the current dissemination baseline; no preprint-server deposit or
external mathematical review is claimed.

The next result gate is either an independently verified 15- or 16-word
construction, or a material exact reduction of the remaining 32 normalized
branches with deterministic case generation and independent certificate
replay. Project-original material is MIT-licensed. The attributed 17-word
regression fixture remains under its upstream BSD 3-Clause terms, and
third-party tools retain their own licenses. Citation metadata is in
`CITATION.cff`. The author is Ruturaj R Raval, Independent Researcher, ORCID
`0000-0003-4930-8981`.

## Origin And History

This project studies the smallest number of radius-2 Hamming balls needed to
cover the 729 ternary words of length 6.

The published interval is

```text
15 <= K_3(6,2) <= 17.
```

The exact `v0.1.0` release is archived at version DOI
`10.5281/zenodo.22510342`. All repository versions are collected under the
stable concept DOI `10.5281/zenodo.22510341`.

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

## Evidence And Repository Map

| Path | Purpose and trust boundary |
| --- | --- |
| [`data/reference_17_code.txt`](data/reference_17_code.txt) | Attributed public 17-word regression witness, checked exhaustively here but not claimed as project-original |
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

## Future Acceptance Gates

1. **Construction gate.** A 16-word candidate must contain 16 distinct words
   and cover all 729 ambient words at radius 2 under the existing verifier
   and a separately implemented exhaustive checker. Such a witness would
   improve the upper bound to 16. A verified 15-word witness would determine
   the exact value at 15.
2. **Further exclusion gate.** Any new branch exclusion must use the complete
   stabilizer-orbit definition, an exact certificate or checked proof object,
   independent replay, mutation tests, and a refreshed prior-art audit.
   Solver status, timeout volume, or search duration alone does not pass this
   gate.
3. **Global exclusion gate.** Every one of the remaining 32 normalized
   branches must be closed by accepted evidence. Together with the verified
   17-word witness, that would prove `K_3(6,2) = 17`.

## Dissemination Status

Release `v0.1.0`, its technical report, deterministic source asset, and exact
certificate data are public through GitHub. Zenodo supplies the immutable
version archive and DOI. No arXiv or HAL deposit is currently part of the
publication record, and no external peer review is claimed. Any public
summary must state that six branches are excluded, 32 remain unresolved, and
the global interval is unchanged.

## License And Provenance

Project-original source, certificate data, and documentation are released
under the MIT License. The reference 17-word code is transcribed from
`florath/covering-codes-lean`, is used only as an attributed regression
fixture, and remains subject to the upstream BSD 3-Clause license recorded in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). No upstream
implementation code is included.

CaDiCaL, Kissat, and OR-Tools are optional external tools installed only in
ignored local environments. They are not release artifacts and remain under
their respective upstream licenses. The six mathematical exclusions depend
on the exact integer certificates and their two independent checkers, not on
CP-SAT or SAT exit status.

## Primary References

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

## Citation And Archive

Citation metadata is in `CITATION.cff`. Cite the exact `v0.1.0` result using
version DOI `10.5281/zenodo.22510342`. The stable all-versions DOI is
`10.5281/zenodo.22510341`.

## Author

Ruturaj R Raval  
Independent Researcher  
ORCID: 0000-0003-4930-8981
