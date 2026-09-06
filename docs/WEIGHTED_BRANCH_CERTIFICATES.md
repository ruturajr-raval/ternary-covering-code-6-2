# Weighted Branch Certificates

This note gives exact finite certificates excluding six normalized branches
of the size-at-most-16 search for `K_3(6,2)`.

The certificates use only:

- the three centers fixed by a normalized third-center branch;
- the earlier third-center orbits forbidden by that branch;
- the ordinary radius-2 coverage condition; and
- the fact that at most 13 additional centers can be selected.

They do not rely on CP-SAT, SAT solver output, projection inequalities,
radial inequalities, or floating-point arithmetic.

## Weighted-Hole Lemma

Fix a normalized branch with three selected centers

```text
F = {000000, a, t},
```

where `a` is the maximum-weight anchor and `t` is the canonical third-center
representative. Let `E` be the union of all earlier third-center orbits in
the weight-at-most-4 partition. If the anchor has weight `d`, define

```text
U = {c in {0,1,2}^6 : weight(c) <= d} \ (F union E).
```

Thus `U` contains every center still permitted by the branch, including
unused members of the selected orbit, all later third-center orbits, and all
heavier centers allowed by the anchor.

Let `H` be the set of words not covered by the three fixed centers:

```text
H = {p : distance(p,f) > 2 for every f in F}.
```

Assign a nonnegative integer weight `w(p)` to every `p` in `H`. Define

```text
W = sum_{p in H} w(p)
```

and, for each admissible remaining center `c`,

```text
K(c) = sum_{p in H, distance(p,c) <= 2} w(p).
```

If `K(c) <= Q` for every `c` in `U`, then any branch cover using at most 16
centers would satisfy

```text
W <= sum_{selected c in U} K(c) <= 13 Q.
```

The first inequality holds because every positive-weight hole must be covered
by at least one selected remaining center. Therefore any weight function with

```text
W > 13 Q
```

is a certificate that the branch contains no radius-2 cover of size at most
16.

After dividing every weight by `Q`, the same argument is a feasible dual
solution for the residual fractional set-cover relaxation with objective
`W/Q > 13`. Thus each certified branch needs more than 13 additional centers
even fractionally, and therefore at least 17 centers in total.

## Certified Branches

The machine-readable weights are in
[`data/weighted_branch_certificates.json`](../data/weighted_branch_certificates.json).
The exact checker independently reconstructs the branch, expands every
positive-weight orbit, evaluates every ambient word, and checks every
individual admissible center.

| Anchor | Orbit | Representative | `|U|` | `|H|` | `W` | `Q` | `13Q` | Margin |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 19 | `011110` | 270 | 549 | 80 | 6 | 78 | 2 |
| 5 | 20 | `011120` | 265 | 541 | 40 | 3 | 39 | 1 |
| 5 | 21 | `011220` | 245 | 528 | 40 | 3 | 39 | 1 |
| 5 | 22 | `012220` | 215 | 522 | 40 | 3 | 39 | 1 |
| 5 | 23 | `022220` | 195 | 516 | 80 | 6 | 78 | 2 |
| 6 | 13 | `002222` | 269 | 516 | 132 | 10 | 130 | 2 |

All six strict inequalities are exact integer comparisons.

## Orbit-Key Format

For a weight-5 anchor, the first five coordinates are partitioned according
to whether the third-center representative has symbol 0, 1, or 2. Each
three-digit block records the counts of symbols 0, 1, and 2 in one coordinate
group. The final bit records whether coordinate 6 is zero or nonzero.

For example,

```text
001|202|000|0
```

describes one stabilizer orbit for the branch represented by `011110`.

For the weight-6 branch represented by `002222`, the first block records
symbol counts in the two coordinates where the representative is zero, and
the second block records symbol counts in the four coordinates where it is
two.

The data file records only positive-weight orbits. Every omitted hole has
weight zero.

## Verification

Run:

```bash
python3 tools/verify_branch_certificates.py
build/verify_branch_certificates
```

The Python and C++20 implementations are independent and must report
identical results in `make test`. Mutation tests require malformed
representatives, weights, orbit sizes, totals, and capacity bounds to fail
closed. A canonical-data dump also requires the C++ certificate table to
match the JSON source entry for entry. Each checker validates:

1. the complete canonical third-center orbit partition;
2. the branch representative and all earlier forbidden orbits;
3. every admissible center of weight at most the anchor weight;
4. every hole left by the three fixed centers;
5. every compact orbit key and claimed orbit size;
6. every nonnegative integer point weight;
7. `W` and all individual values `K(c)`; and
8. the strict inequality `W > 13Q`.

The certificate branch sets are compared against the production CNF
generator's `--branch-manifest-json` output for all six cases.

The certificate checker is also part of `make test`.

## Consequence And Limit

The original structural argument reduces the normalized search to 38
third-center branches. These certificates rigorously exclude six of them,
leaving 32 unresolved branches.

This result does not construct a 16-word cover, exclude all size-at-most-16
covers, determine `K_3(6,2)`, or change the published interval
`15 <= K_3(6,2) <= 17`.
