# Release v0.1.1

## Release Identity

| Field | Value |
| --- | --- |
| Title | Six Certified Branch Exclusions for the Ternary Covering Problem K_3(6,2) |
| Author | Ruturaj R Raval |
| Affiliation | Independent Researcher |
| ORCID | [0000-0003-4930-8981](https://orcid.org/0000-0003-4930-8981) |
| Tagged release | [`v0.1.1`](https://github.com/ruturajr-raval/ternary-covering-code-6-2/releases/tag/v0.1.1) |
| Release date | 2026-09-07 |
| Audited release commit | `6824254e627fe4f4125423e8d1b0976f1f712d3b` |
| Version DOI | [`10.5281/zenodo.22647771`](https://doi.org/10.5281/zenodo.22647771) |
| Concept DOI | [`10.5281/zenodo.22510341`](https://doi.org/10.5281/zenodo.22510341) |
| Archive status | GitHub release and paper-inclusive Zenodo version published; all three public assets downloaded and verified |
| License | MIT for project-original material |

## Background

The ternary covering number `K_3(6,2)` asks for the minimum number of
length-6 ternary words whose radius-2 Hamming balls cover all 729 ambient
words. The established interval remains

```text
15 <= K_3(6,2) <= 17.
```

A verified 16-word cover would improve the upper bound. A complete checked
exclusion of every size-at-most-16 cover, together with the known 17-word
construction, would determine the exact value at 17.

## What This Release Adds

Version `v0.1.1` is an archival and documentation patch. It adds an
explicitly named compiled report PDF, a deterministic report-source archive,
and `SHA256SUMS` for the release assets. The theorem, proof, certificates,
data, computations, branch counts, and global claim boundary are unchanged
from `v0.1.0`.

The mathematical result retained by this patch gives a complete normalized
third-center reduction and exact certificates for six branches.

After translating one selected center to `000000`, an antipodal-sphere
argument excludes maximum weight at most 4. A radius-3 sphere argument then
forces another selected center of weight at most 4. Stabilizer orbits give
24 weight-5-anchor branches and 14 weight-6-anchor branches.

For six branches, nonnegative integer weights on the points left uncovered
by the three fixed centers give total weight `W`, while every remaining
admissible center covers weighted capacity at most `Q`, with `W > 13Q`.
These are exact residual fractional set-cover dual certificates.

The certified branches are represented by:

```text
011110
011120
011220
012220
022220
002222
```

The first five use a maximum-weight-5 anchor. The last uses a
maximum-weight-6 anchor.

Independent Python and C++20 implementations reconstruct the branch
definitions, evaluate all 729 ambient words and every admissible center, and
produce byte-identical exact summaries and canonical certificate-data dumps.
The reconstructed fixed, forbidden, and admissible center sets are compared
with manifests from the production CNF generator for all six branches.
Mutation tests reject malformed certificates and invalid numeric types.

The normalized frontier is reduced from 38 branches to 32.

## What Is Not Claimed

- No 15-word or 16-word covering code has been found.
- Nonexistence of all size-at-most-16 covering codes has not been proved.
- The exact value of `K_3(6,2)` remains open.
- The global interval `15 <= K_3(6,2) <= 17` is unchanged.
- The remaining 32 normalized branches are not excluded.
- Solver exit status is not used as a proof.
- No external mathematical review is claimed.

## Reproduction

Build and replay the exact certificates:

```bash
make
python3 tools/verify_branch_certificates.py
build/verify_branch_certificates
make test
make test-cp-sat
```

Build the technical report and deterministic source archive:

```bash
make release-assets
make release-checksums
make verify-release-assets
```

The source bundle includes the `v0.1.1` DOI in
`paper/ARXIV_METADATA.md`. Its tar and gzip headers are normalized, so
repeated builds from the same source tree are byte-identical.

`release-manifest.sha256` authenticates the maintained `main` publication
surface. The prepared release set is independently bound by `SHA256SUMS` and
the asset records in `release.json`.

## Release And Archive

- Public repository:
  `https://github.com/ruturajr-raval/ternary-covering-code-6-2`
- Release identity:
  `https://github.com/ruturajr-raval/ternary-covering-code-6-2/releases/tag/v0.1.1`
- Version DOI: `10.5281/zenodo.22647771`
- Stable concept DOI: `10.5281/zenodo.22510341`
- Release commit: `6824254e627fe4f4125423e8d1b0976f1f712d3b`
- Publication status: protected tag, GitHub release, and Zenodo version are
  public; all three release assets were downloaded and verified

Release assets:

```text
ternary-covering-code-6-2-paper.pdf
SHA-256 c0a8bc60bb0d83fb0ed3ff19764c78badf9fe69cac119447c9b25acacddbf321

ternary-covering-code-6-2-source.tar.gz
SHA-256 0e1d5433493905c7ab0bdd83667b74c5cf6e93e46e09607e64408aa3a220fdbb

SHA256SUMS
SHA-256 7a89a7fde2b523e3a5bf65c12228d75cf710283feba6b99e86362021b56455c8
```

The prior `v0.1.0` archive remains available at version DOI
`10.5281/zenodo.22510342`. Its 63-file snapshot matched release commit
`3dea87b7e2cd116fcd5fc05c63c21a71259b0923`. The paper-inclusive successor
`10.5281/zenodo.22647771` contains the compiled paper, deterministic source
archive, and checksum manifest listed above. All three public files were
downloaded and verified against the local release set.

## Provenance Boundary

Project-original source, certificate data, and documentation are MIT
licensed. The attributed 17-word regression fixture remains under its
upstream BSD 3-Clause terms, as recorded in `THIRD_PARTY_NOTICES.md`.
CaDiCaL, Kissat, and OR-Tools are optional external tools and are not bundled
as project-original artifacts.

## Review Status

The mathematical release passed claim-scope, normalization, implementation,
reproducibility, mutation, and manuscript review. Python and C++20
independently verify the six exact certificate claims. The `v0.1.1` local
paper and release assets were verified separately before publication and
were downloaded again from both public services after publication.
No external mathematical or peer review is claimed.

## Significance

Each certificate proves that its residual fractional set-cover relaxation
has value greater than 13. Therefore every integral cover in the branch needs
at least 14 centers in addition to the three fixed centers. Search
implementations can prune these six normalized branches without SAT, MILP,
or floating-point solver trust.

The certificates also provide compact regression instances for symmetry
reduction, residual set cover, exact dual verification, and finite
branch-and-bound software.

## Remaining Work And Next Acceptance Gate

A final solution still requires either a verified 16-word construction or a
complete checked exclusion of every size-at-most-16 cover. The immediate
route is deeper stabilizer-orbit splitting of the 32 unresolved branches,
combined with additional residual dual certificates and independent
construction search.

The next acceptance gate is either an independently verified 15- or 16-word
construction, or a material exact reduction of the remaining 32 normalized
branches with deterministic case generation and independent certificate
replay.

## Public Summary

Release `v0.1.1` is a paper-inclusive archival and documentation patch for
the six certified branch exclusions. It adds an explicit compiled PDF,
deterministic source archive, and checksums. Independent Python and C++20
exact verifiers still check every certificate. The certified normalized
frontier remains 32 unresolved branches, and
`15 <= K_3(6,2) <= 17` remains unchanged.

## Citation

Citation metadata is in `CITATION.cff`. Cite the paper-inclusive `v0.1.1`
archival patch using version DOI `10.5281/zenodo.22647771`.
Historical release scope is summarized in `RELEASE_NOTES.md`.
