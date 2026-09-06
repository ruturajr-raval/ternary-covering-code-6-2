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

Citation metadata is in `CITATION.cff`. Cite the versioned GitHub release and
its archival DOI after the archive is assigned.
