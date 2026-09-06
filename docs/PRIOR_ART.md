# Prior Art And Frontier

## Problem

`K_3(6,2)` is the minimum size of a subset of `{0,1,2}^6` whose radius-2
Hamming balls cover all 729 words.

The historical ternary covering-code table records

```text
15 <= K_3(6,2) <= 17.
```

The table attributes the lower bound to Bertolo, Ostergard, and Weakley (2004)
and the upper bound to Hamalainen and Rankinen (1991).

The upper endpoint has therefore stood since 1991, and the interval
`15 <= K_3(6,2) <= 17` has stood since 2004.

Table source:
https://old.sztaki.hu/~keri/codes/3_tables.pdf

Historical sources:

- https://doi.org/10.1016/0097-3165(91)90024-B
- https://doi.org/10.1023/A:1008228721072
- https://doi.org/10.1002/jcd.20008

## Current Explicit Upper Certificate

The `covering-codes-lean` project added a machine-checked explicit 17-word
code on 2026-06-17:

https://github.com/florath/covering-codes-lean/blob/main/CoveringCodes/Database/Sources/SmallExplicitUpper/K_3_6_2.lean

The source does not identify this exact word list as the original 1991
construction. It is therefore treated here as a modern public witness for the
historical upper bound, not as the original code.

The same project records unsuccessful exploratory attempts to exclude 16
centers. Those experiments include pair-distance and local-moment
relaxations, inverse set-cover formulations, and anchored orbit models:

https://github.com/florath/covering-codes-lean/blob/main/docs/failures/K_3_6_2.md

Those notes explicitly identify proof-logged cube-and-conquer and verified
finite search as remaining directions.

The same public failure note reports that its third-orbit residual LP scans
pruned `0/34` maximum-weight-5 cases and `0/26` maximum-weight-6 cases. The
present work uses a different theorem-driven 24-plus-14 orbit partition and
exact residual set-cover dual certificates. Six branches in that reduced
partition are certified impossible.

## Novelty Check

As of 2026-09-06, the reviewed public sources expose neither:

- a verified 16-word code; nor
- a proof that every radius-2 cover needs at least 17 centers; nor
- the six weighted branch certificates recorded in this repository.

This is a public-source search result, not evidence that unpublished or
unindexed work does not exist.

Recent semidefinite-programming calculations give a weaker lower bound for
this cell and do not change the published interval:

- https://arxiv.org/abs/2504.01932

## Reuse Boundary

The implementation in this repository is independent. The only transcribed
artifact is the public 17-word code used as a regression fixture, with
provenance recorded in `THIRD_PARTY_NOTICES.md`.
