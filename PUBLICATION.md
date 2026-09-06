# Release v0.1.0

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

This release gives a complete normalized third-center reduction and exact
certificates for six branches.

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
make paper-build
make paper-bundle
```

On the current `main` branch, the source bundle includes the assigned DOI in
`paper/ARXIV_METADATA.md`. To reproduce the immutable published source asset
and its recorded SHA-256 exactly, first check out tag `v0.1.0`, then run
`make paper-bundle`.

## Release And Archive

- Public repository:
  `https://github.com/ruturajr-raval/ternary-covering-code-6-2`
- GitHub release:
  `https://github.com/ruturajr-raval/ternary-covering-code-6-2/releases/tag/v0.1.0`
- Version DOI: `10.5281/zenodo.22510342`
- Stable concept DOI: `10.5281/zenodo.22510341`
- Release commit:
  `3dea87b7e2cd116fcd5fc05c63c21a71259b0923`

Release assets:

```text
ternary-covering-code-6-2-paper.pdf
SHA-256 1096074fd0023ff908b7c7cc1cf4091701945278c40bf5a010865b7d1e3473a0

ternary-covering-code-6-2-source.tar.gz
SHA-256 0ad4c0a0fd44c9714f3123673bad13cbc60cebde4569b1073edf304458f42974
```

The Zenodo repository snapshot is
`ruturajr-raval/ternary-covering-code-6-2-v0.1.0.zip`, with SHA-256
`22044a649126f2836b2ced2135f6c4930e1842cbfc4ef3189ed09f84894eee8e`.
Its 63 files match the immutable release tag tree exactly.

## Significance

Each certificate proves that its residual fractional set-cover relaxation
has value greater than 13. Therefore every integral cover in the branch needs
at least 14 centers in addition to the three fixed centers. Search
implementations can prune these six normalized branches without SAT, MILP,
or floating-point solver trust.

The certificates also provide compact regression instances for symmetry
reduction, residual set cover, exact dual verification, and finite
branch-and-bound software.

## Remaining Work

A final solution still requires either a verified 16-word construction or a
complete checked exclusion of every size-at-most-16 cover. The immediate
route is deeper stabilizer-orbit splitting of the 32 unresolved branches,
combined with additional residual dual certificates and independent
construction search.

## Citation

Citation metadata is in `CITATION.cff`. Cite the archived `v0.1.0` result
using version DOI `10.5281/zenodo.22510342`.
