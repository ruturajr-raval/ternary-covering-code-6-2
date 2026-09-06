# Method

## Construction Track

The local search maintains 16 distinct centers and exact coverage
multiplicities for all 729 points. A move replaces one center with a center
covering a current hole. The objective gives dominant weight to uncovered
points, increases the weights of persistent holes, and uses singly covered
points as a robustness term. Tabu tenure, perturbation, and independent
parallel restarts provide diversification.

The repair tool freezes `16-q` centers from a near-cover and solves the
remaining `q`-center residual cover exactly. It uses maximum-gain, optimistic
top-gain, and pairwise-distance packing lower bounds.

The compression search maintains an 18-center cover while scoring all
153 ways to delete two centers. Its incremental support masks identify the
best 16-center projection after each move. Distinct near-covers at or below a
configurable hole threshold can be retained for later exact repair.

Before writing a candidate, each construction tool recomputes its coverage
from scratch through the shared exact verifier. A publication witness must
additionally be replayed by an independent implementation.

## Exact Formulation

The baseline formulation has one Boolean selection variable for each of the
729 possible centers.

- Each ambient point requires at least one selected center within distance 2.
- A propagation-complete threshold counter enforces exactly 16 centers.
- Translation symmetry fixes `000000`.
- A maximum-weight anchor splits the normalized problem into weights 5 and 6.
- Coordinate-symbol counts are constrained to the proved interval 3 through
  10.

Exact 16 is equivalent to size at most 16 because adding distinct centers
cannot destroy coverage. The maximum-weight-4 branch is omitted only because
the antipodal-sphere argument in `STRUCTURAL_LEMMAS.md` proves it impossible.

For a branch with fixed and forbidden centers, the generator builds a reduced
core. Coverage clauses already satisfied by fixed centers are omitted, other
coverage clauses contain only allowed centers, and the cardinality counter
contains only undecided centers. Explicit unit clauses for fixed and
forbidden variables remain in the output for auditability.

## Symmetry Branching

For a fixed maximum-weight anchor of weight `d`, the pointwise stabilizer
permutes the first `d` coordinates, permutes the remaining coordinates, and
independently swaps symbols 1 and 2 outside the anchor support. A third
center's orbit is determined by:

- its counts of symbols 0, 1, and 2 inside the anchor support;
- its number of nonzero symbols outside the support.

For a hypothetical 16-cover, the radius-3 capacity lemma proves that every
selected center has another center within distance 4. For maximum-weight
anchors 5 and 6, the canonical third center can therefore be chosen from only
the weight-at-most-4 stabilizer orbits. There are 24 and 14 such orbits. The
29 weight-4-anchor orbits are retained as regression cases even though that
whole anchor branch is excluded mathematically. Choosing the earliest
occupied eligible orbit and mapping one selected center to its canonical
representative gives a complete, nonoverlapping split.

At deeper levels the generator enumerates the full subgroup fixing all
selected representatives. The earliest occupied orbit under that subgroup
provides the next split. `--orbit-path A,B,...` applies this construction
recursively, while `--list-next-orbits` enumerates the complete next branch
set.

Earlier forbidden orbits form an invariant set under the parent stabilizer
and therefore remain invariant under every later subgroup. The generator
carries this full ancestor-forbidden set into each deeper orbit computation
before selecting the next representative.

At path length `k`, zero, the maximum-weight anchor, and `k` orbit
representatives are fixed. Since exactly 16 centers are selected, branching
is exhaustive while fewer than 16 centers are fixed. Orbit branching is
therefore rejected for at-most formulations, and paths longer than 14 are
rejected.

The generator checks that every eligible branching center belongs to exactly
one listed stabilizer orbit. The theorem-driven root partitions contain 471,
472, and 472 candidates for maximum weights 4, 5, and 6. After the third
center is fixed, deeper partitions again include every allowed center up to
the anchor weight.

## Strengthening Inequalities

The CNF generator supports five complementary cut families:

- `--projection-cuts` adds all 135 two-coordinate capacity inequalities;
- `--four-projection-cuts` adds consequences of all 1,215 four-coordinate
  fiber inequalities;
- `--five-projection-cuts` adds all 1,458 five-coordinate fiber
  inequalities;
- `--antipodal-cuts` adds the full radius-6 sphere inequality at every
  symmetry-fixed center;
- `--radial-sphere-cuts` adds two compact radial clauses at every ambient
  reference word.

The CP-SAT formulation uses the same exact cover, cardinality, symmetry,
coordinate, two-coordinate, and optional five-coordinate conditions. It also
adds the complete radius-1 through radius-6 capacity inequalities at every
reference word and their rounded support consequences: at least 4, 9, 6, and
3 selected centers in the positive-capacity shells for radii 3 through 6.

## Campaign Coordinators

`tools/recursive_cube_search.py` runs a resumable breadth-first SAT campaign.
Each node records the generator, solver, and verifier hashes, the CNF hash,
the time limit, the orbit path, and the solver log. A SAT assignment is
decoded into 16 words and accepted only after `verify_code` checks all 729
ambient words.

The SAT coordinator distinguishes:

- `SAT_VERIFIED` for a directly checked 16-word construction;
- `SOLVER_UNSAT` for an unchecked solver classification;
- `UNKNOWN` for an unresolved node;
- `ERROR` or `CANCELLED` for an invalid or interrupted run.

`tools/cp_sat_orbit_campaign.py` runs the 29, 24, or 14 third-center orbit
cases in parallel. It derives the orbit manifest from the model code, then
independently checks every orbit member, representative, disjointness, and
exhaustive coverage of the theorem-eligible low-weight candidate set before
launching any solver. Its campaign fingerprint includes the Git commit and
worktree state, exact scripts and verifier, Python executable, installed
package set, solver version, model configuration, orbit manifest, and branch
seed. A separate run fingerprint records the selected orbit subset, time
limit, and parallel job count. Every completed solver result additionally
records a deterministic serialized-model hash, exact command, solver exit
code, and solver-log hash. Before reusing a cached record, the coordinator
rebuilds that branch without solving and requires the serialized-model hash
to match. A cached witness is reverified and must match its recorded centers
and branch.

Default campaign directory names include the orbit-manifest hash. The
packager also rejects branch directories not named in the campaign summary,
preventing obsolete orbit schemas from entering an archive.

The CP-SAT coordinator reports an `INFEASIBLE` branch only as
`solver-only-no-certificate`. It does not convert that status into a
mathematical nonexistence claim.

Campaign exit codes are 0 for a verified witness, 2 for a complete
solver-only exclusion, 3 for unresolved branches, and 4 for an operational
error. Signals terminate active solver process groups, persist cancellation
records, and return 130 for `SIGINT` or 143 for `SIGTERM`.

Raw campaign directories are not publication artifacts. After a clean,
committed run, `tools/package_campaign.py` requires the campaign's recorded
clean source commit to match the checked-out commit and requires a verified
witness or certified proof tree by default. It copies accepted evidence into
the explicit `artifacts/` allowlist without modifying its bytes, excludes
temporary and lock files, rejects local home paths, email addresses,
symlinks, and unsupported file types, then writes a SHA-256 manifest.

## Certification Standard

A construction result requires:

- a 16-word witness;
- direct exhaustive coverage verification;
- replay by an independent implementation.

A nonexistence result requires:

- deterministic and exhaustive symmetry case generation;
- one proof artifact per terminal case;
- independent proof replay;
- a hash manifest and complete replay commands.

Solver exit status alone is not a certificate.
