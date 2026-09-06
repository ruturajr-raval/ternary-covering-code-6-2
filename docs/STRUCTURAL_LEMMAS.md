# Structural Lemmas For A Hypothetical 16-Cover

This note records elementary necessary conditions used by the exact search.
All statements concern a set `C` of 16 distinct ternary words of length 6.

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

Therefore every 16-word set satisfies

```text
P >= 540.
```

Moreover, values 541 through 545 are impossible because every positive term
on the right contributes at least 6.

If the 16 balls cover all 729 points and `m(x)` is the coverage multiplicity
of point `x`, then

```text
sum_x (m(x)-1) = 16*73 - 729 = 439
```

and

```text
sum_x C(m(x)-1,2) = P - 439 >= 101.
```

Thus any 16-cover must contain substantial triple-or-higher coverage.

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

These 18 bounds are emitted by default in `generate_cnf`.

## Five-Coordinate Projection Rule

Delete one coordinate and fix a projected word `y` of length 5. Suppose no
center lies within projected distance 1 of `y`.

A center at projected distance 2 can cover the full word `(y,s)` only when
its omitted-coordinate symbol equals `s`. Centers farther away cannot cover
`(y,s)`.

Therefore, the omitted-coordinate symbols among all projected-distance-2
centers must contain all three symbols. This rule is reserved for later
branch-specific propagation.

## Claim Boundary

These lemmas do not prove that a 16-cover exists or does not exist. They are
necessary conditions and solver cuts only.

