# arXiv Submission Metadata

## Title

Six Certified Branch Exclusions for the Ternary Covering Problem K_3(6,2)

## Author

Ruturaj R Raval

Affiliation: Independent Researcher

ORCID: 0000-0003-4930-8981

## Abstract

Let K_3(6,2) be the minimum number of radius-two Hamming balls needed to
cover the ternary space {0,1,2}^6. The published interval remains
15 <= K_3(6,2) <= 17. A hypothetical cover with at most sixteen centers can
be normalized to contain 000000 and a maximum-weight anchor of weight five
or six. A radius-three sphere argument forces an additional center of weight
at most four, producing 24 normalized third-center branches for maximum
weight five and 14 for maximum weight six. This report certifies six of those
38 branches as impossible. For each branch, nonnegative integer weights on
the points left uncovered by its three fixed centers give total weight W,
while every remaining admissible center covers weighted capacity at most Q,
with W > 13Q. After scaling by Q, these are exact feasible dual solutions for
the residual fractional set-cover relaxations with objective greater than
thirteen. Independent Python and C++20 verifiers reconstruct every branch,
evaluate all 729 ambient words and every admissible center, and agree on all
exact counts. The normalized frontier is reduced from 38 branches to 32. The
global interval is unchanged.

## Categories

Primary: math.CO

Cross-list: cs.IT

## Comments

Contains elementary normalization lemmas, six exact residual set-cover dual
certificates, independent Python and C++20 verification, canonical
cross-language data comparison, production-generator regression checks,
mutation tests, and complete replay commands. The global interval
15 <= K_3(6,2) <= 17 remains unchanged.

## Keywords

covering codes; ternary codes; Hamming space; set cover duality; exact
computation; symmetry reduction; computational combinatorics

## License

arXiv.org perpetual, non-exclusive license

## Source Package

Upload the LaTeX source and only the files required to compile it. The paper
uses no external bibliography, figures, or generated tables.

## Claim Boundary

- Claimed: the normalized maximum-weight-at-most-4 branch is impossible.
- Claimed: the remaining normalized size-at-most-16 search has a complete
  24-plus-14 third-center branch partition.
- Claimed: exact residual dual certificates exclude the weight-5 branches
  represented by 011110, 011120, 011220, 012220, and 022220.
- Claimed: an exact residual dual certificate excludes the weight-6 branch
  represented by 002222.
- Claimed: 32 normalized third-center branches remain unresolved.
- Not claimed: a 15-word or 16-word covering code.
- Not claimed: nonexistence of all size-at-most-16 covering codes.
- Not claimed: a new global lower or upper bound.
- Not claimed: the exact value of K_3(6,2).

## Data And Code

The accompanying source repository contains the machine-readable
certificates, independent Python and C++20 verifiers, mutation tests,
production-generator branch-manifest checks, structural search code, and
complete replay commands. Cite GitHub release `v0.1.1` together with the
Zenodo version DOI `10.5281/zenodo.22647771`. This archival and documentation
patch adds the compiled PDF and deterministic source bundle without changing
the theorem, proof, certificates, data, or computations.
