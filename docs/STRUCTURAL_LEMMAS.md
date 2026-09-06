# Structural Lemmas For A Hypothetical 16-Cover

This note records elementary necessary conditions used by the exact search.
All statements concern a set `C` of 16 distinct ternary words of length 6
whose radius-2 balls cover the whole space.

## Pair-Overlap Lower Bound

Let `A_d` be the number of unordered pairs of centers at Hamming distance
`d`. Radius-2 balls centered at words at distances 1 through 6 have
intersection sizes

```text
33, 25, 12, 6, 0, 0.
```

Thus the total pairwise ball overlap is

```text
P = 33 A_1 + 25 A_2 + 12 A_3 + 6 A_4.
```

Let

```text
G = sum_d (6-d) A_d.
```

`G` counts center-pair agreements coordinate by coordinate. If the three
symbol multiplicities in one coordinate are `n_0,n_1,n_2`, that coordinate
contributes

```text
C(n_0,2) + C(n_1,2) + C(n_2,2) >= 35,
```

because `n_0+n_1+n_2=16`, with equality only for a permutation of
`(5,5,6)`. Summing over six coordinates gives `G >= 210`.

Using `sum_d A_d = C(16,2) = 120`, direct coefficient comparison gives

```text
P = 540 + 6(G-210) + 9 A_1 + 7 A_2 + 6 A_6.
```

Therefore every 16-word set satisfies `P >= 540`. Values 541 through 545 are
impossible because every positive term on the right contributes at least 6.

If the 16 balls cover all 729 points and `m(x)` is the coverage multiplicity,
then

```text
sum_x (m(x)-1) = 16*73 - 729 = 439
```

and

```text
sum_x C(m(x)-1,2) = P - 439 >= 101.
```

Thus any 16-cover must contain substantial triple-or-higher coverage.

## Antipodal-Sphere Capacity

Fix a center `z` in `C` and let `N_d(z)` count centers at distance `d` from
`z`. The sphere of radius 6 around `z` contains 64 words. A radius-2 ball
centered at distance `d` from `z` covers the following number of those words:

```text
d:          0  1  2  3  4   5   6
capacity:   0  0  0  0  4  12  22
```

Consequently every 16-cover satisfies

```text
4 N_4(z) + 12 N_5(z) + 22 N_6(z) >= 64.
```

If all other 15 centers were within distance 4 of `z`, their total capacity
would be at most `15*4 = 60`, a contradiction. Every center of a 16-cover
therefore has another center at distance at least 5.

After translating one selected center to `000000`, a maximum-weight anchor
can consequently have only weight 5 or 6. This proves that the normalized
maximum-weight-4 exact-search branch is impossible.

The CNF generator emits the full antipodal inequality at each center fixed by
the current symmetry branch.

## Two-Coordinate Capacity Inequality

Fix two coordinates and symbols `a,b`. Let:

- `n_ab` be the number of centers with projection `(a,b)`;
- `r_a` be the number with first symbol `a`;
- `c_b` be the number with second symbol `b`.

Consider the 81 ambient words whose selected coordinates equal `(a,b)`.

- A center matching both selected coordinates can cover at most 33 of them.
- A center matching exactly one can cover at most 9.
- A center matching neither can cover at most 1.

The total available coverage capacity is therefore

```text
33 n_ab
+ 9 (r_a + c_b - 2 n_ab)
+ (16 - r_a - c_b + n_ab)
= 16 + 8(r_a + c_b + 2 n_ab).
```

Coverage of all 81 words requires

```text
2 n_ab + r_a + c_b >= 9.
```

Summing this inequality over `b` for a fixed `a` gives

```text
5 r_a + 16 >= 27,
```

so `r_a >= 3`. Since all three row totals sum to 16, each is also at most 10.
The same applies to every symbol in every coordinate.

The 18 symbol-count bounds are emitted by default. The 135 two-coordinate
inequalities are enabled by `--projection-cuts`.

## Four-Coordinate Projection Capacity

Fix four coordinates and a projected word `y`. Let `N_i` count centers at
projected distance `i` from `y`. The nine words in the corresponding
two-coordinate fiber receive capacity 9, 5, and 1 from centers at projected
distances 0, 1, and 2. Hence

```text
9 N_0 + 5 N_1 + N_2 >= 9.
```

The CNF option `--four-projection-cuts` emits two useful consequences for
each of the 1,215 coordinate-pattern choices:

```text
N_0 + N_1 >= 1  or  N_2 >= 9,
N_0 >= 1  or  N_1 >= 2  or  N_2 >= 4.
```

## Five-Coordinate Projection Capacity

Delete one coordinate and fix a projected word `y` of length 5. Let `N_i`
count centers at projected distance `i` from `y`.

A center at projected distance 0 or 1 covers all three words in the omitted
coordinate fiber. A center at projected distance 2 covers exactly the fiber
word matching its omitted-coordinate symbol. More distant centers cover none.
Therefore

```text
3 N_0 + 3 N_1 + N_2 >= 3.
```

Equivalently,

```text
N_0 >= 1  or  N_1 >= 1  or  N_2 >= 3.
```

The option `--five-projection-cuts` emits all 1,458 such inequalities.

## Complete Radial Capacity Table

For a reference word `z`, let `S_r(z)` be its radius-`r` sphere. A center at
distance `d` from `z` covers a number `a_r(d)` of points in `S_r(z)`. Direct
Hamming counting gives:

```text
r\d    0    1    2    3    4    5    6    |S_r|
 1    12   12    4    3    0    0    0      12
 2    60   20   20    9    6    0    0      60
 3     0   40   24   25   16   10    0     160
 4     0    0   24   24   27   25   15     240
 5     0    0    0   12   20   26   36     192
 6     0    0    0    0    4   12   22      64
```

Every cover must satisfy, for each `z` and each radius `r`,

```text
sum_d a_r(d) N_d(z) >= |S_r(z)|.
```

If `z` is selected in a 16-center cover and every other center were at
distance at least 5, the radius-3 row would provide capacity at most

```text
15 * 10 = 150 < 160.
```

Thus every selected center has another center at distance at most 4. After
translating a center to zero and fixing a maximum-weight anchor of weight 5 or
6, a third center can always be chosen with weight at most 4. Its stabilizer
orbits give 24 cases for anchor weight 5 and 14 cases for anchor weight 6.
Together with the antipodal exclusion of anchor weight 4, this is a complete
38-case normalized third-center split.

Bounding every positive coefficient by the largest coefficient in its row
and rounding the resulting quotient up gives support lower bounds. Every
reference word has at least 4, 9, 6, and 3 selected centers in the
positive-capacity shells for radii 3, 4, 5, and 6.

The CP-SAT model adds all six inequalities and these rounded support bounds at
every reference word. The CNF option `--radial-sphere-cuts` adds the following
compact consequences of the radius-1 and radius-2 rows:

```text
N_0+N_1 >= 1  or  N_1+N_2 >= 3  or  N_3 >= 2,
N_0 >= 1  or  N_1+N_2 >= 3  or  N_3 >= 3  or  N_4 >= 1.
```

Aggregate radial, projection, and ordinary distance-distribution conditions
remain necessary rather than sufficient. The current 7-hole near-cover
satisfies the complete radial inequalities, so higher-order branch structure
is still required.

## Weighted-Hole Branch Exclusions

Fix one normalized third-center branch. Let `F` contain its three fixed
centers, let `E` contain all earlier third-center orbits, and let `U` contain
every center of weight at most the anchor weight outside `F` and `E`. Let `H`
be the points farther than 2 from every member of `F`.

For nonnegative integer weights `w(p)` on `H`, define

```text
W = sum_{p in H} w(p)
K(c) = sum_{p in H, distance(p,c) <= 2} w(p).
```

If `K(c) <= Q` for every `c` in `U`, any branch cover with at most 16 centers
would use at most 13 members of `U` and satisfy

```text
W <= 13Q.
```

Exact certificates violate this inequality in six branches:

| Anchor | Orbit | Representative | `W` | `Q` | `13Q` |
| --- | ---: | --- | ---: | ---: | ---: |
| 5 | 19 | `011110` | 80 | 6 | 78 |
| 5 | 20 | `011120` | 40 | 3 | 39 |
| 5 | 21 | `011220` | 40 | 3 | 39 |
| 5 | 22 | `012220` | 40 | 3 | 39 |
| 5 | 23 | `022220` | 80 | 6 | 78 |
| 6 | 13 | `002222` | 132 | 10 | 130 |

The machine-readable weights are in
`../data/weighted_branch_certificates.json`, and the full proof is in
`WEIGHTED_BRANCH_CERTIFICATES.md`. The checker evaluates every admissible
center, so the result does not depend on a solver classification or on
testing only orbit representatives.

## Claim Boundary

These lemmas exclude the maximum-weight-4 normalized branch, reduce the
remaining normalized third-center split to 38 cases, and rigorously exclude
six of those cases. The current normalized frontier has 32 unresolved
branches. These results do not prove that a 16-cover exists or does not exist.
