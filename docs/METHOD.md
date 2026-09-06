# Method

## Construction Track

The construction search maintains 16 distinct centers and exact coverage
multiplicities for all 729 points. A move replaces one center with a center
covering a currently uncovered point. The objective:

1. assigns a dominant penalty to uncovered points;
2. increases the weights of persistent holes;
3. uses singly covered points as a secondary robustness term;
4. applies tabu tenure, perturbation, and independent parallel restarts.

Every candidate written by the search is rechecked by `verify_code`.

The repair tool freezes `16-q` centers from a near-cover and solves the
remaining `q`-center residual cover exactly. It uses maximum-gain, optimistic
top-gain, and pairwise-distance packing lower bounds, and it verifies any
completed code before writing it.

## Exclusion Track

The baseline CNF has one selection variable for each of the 729 possible
centers.

- Each ambient point contributes one 73-literal coverage clause.
- A propagation-complete threshold counter enforces exactly 16 selected
  centers. This is equivalent to size at most 16 because adding centers cannot
  destroy coverage.
- Translation symmetry permits fixing `000000` as a center.
- Optional maximum-weight anchors split the search into normalized cases.

For a fixed maximum-weight anchor of weight `d`, the pointwise stabilizer
permutes the first `d` coordinates, permutes the remaining coordinates, and
independently swaps symbols 1 and 2 outside the anchor support. A third
center's orbit is determined by:

- its counts of symbols 0, 1, and 2 inside the anchor support;
- its number of nonzero symbols outside the support.

There are 29, 34, and 26 eligible third-center orbits for anchor weights 4, 5,
and 6. Choosing the earliest occupied orbit and mapping one of its selected
centers to the canonical representative gives an exhaustive 89-case split.
Earlier orbits are forbidden in each case, so the split does not overlap.

The same construction is applied one level deeper. For each third-center
case, the generator enumerates the full subgroup that fixes zero, the
maximum-weight anchor, and the selected third-center representative. The
earliest occupied orbit under this subgroup provides a complete fourth-center
split. This is generated from the automorphism action rather than a
hand-maintained orbit table.

Unresolved fourth-center leaves can be split once more by the stabilizer that
fixes all four selected representatives. The fifth-center orbit generator
uses the same exact group action and earliest-occupied-orbit rule.

For deeper cubes, `--orbit-path A,B,...` applies this construction
recursively to arbitrary depth. `--list-next-orbits` enumerates the complete
next split after any path, so no manually curated case tree is required.

At path length `k`, zero, the maximum-weight anchor, and `k` orbit
representatives are fixed. The earliest-occupied-orbit split is exhaustive
because the formulation selects exactly 16 centers and `k < 14` guarantees
that at least one further center remains. A path of length 14 already fixes
all 16 centers and must be solved directly. Orbit branching is therefore
rejected for at-most formulations, and paths longer than 14 are rejected.

The orbit generator checks that every allowed center outside the fixed set
belongs to exactly one listed stabilizer orbit. The root partitions contain
471, 663, and 727 centers for maximum weights 4, 5, and 6, respectively.

The generator also applies the proven coordinate-symbol bounds from
`STRUCTURAL_LEMMAS.md`: each of the three symbols occurs between 3 and 10
times in every coordinate of a 16-cover.

For difficult leaves, `--projection-cuts` adds all 135 inequalities

```text
2 n_ab + r_a + c_b >= 9.
```

The encoding uses threshold variables for the projection cell and its
row-or-column fringe. It distinguishes cell counts 0, 1, 2, and at least 3,
avoiding a direct weighted-cardinality expansion.

The planned proof package consists of:

- a deterministic CNF generator;
- a complete symmetry case list;
- one proof log per case;
- a pinned independent proof checker;
- hashes and replay commands for every artifact.

No nonexistence claim will be made from solver exit status alone.

## Campaign Coordinator

`tools/recursive_cube_search.py` runs a resumable breadth-first cube
campaign. Each node records the generator, solver, and verifier hashes, the
CNF hash, the time limit, the orbit path, and the solver log. A SAT model is
decoded into 16 words and accepted only after `verify_code` checks all 729
ambient words.

The coordinator uses separate states:

- `SAT_VERIFIED` for a directly checked 16-word construction;
- `SOLVER_UNSAT` for an unchecked solver classification;
- `UNKNOWN` for an unresolved node;
- `ERROR` or `CANCELLED` for an invalid or interrupted run.

A recursive tree reducer distinguishes solver-level closure from certified
closure. Persistent records live under `research-results/`, which is not
removed by `make clean`. Generated CNFs are deleted after UNKNOWN or
solver-only UNSAT outcomes unless `--keep-cnf` is requested.
