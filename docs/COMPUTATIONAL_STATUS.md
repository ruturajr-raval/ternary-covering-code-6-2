# Computational Status

This report records the clean exact-16 campaign run on 2026-09-06 from Git
revision `710949c54ac0caa04e3758c5843ae7b98d82eec1`.

## Finite Frontier

The analytic reductions leave exactly 38 normalized third-center cases:

| Maximum-weight anchor | Third-center cases |
| --- | ---: |
| 5 | 24 |
| 6 | 14 |
| Total | 38 |

Each case fixes the earliest occupied theorem-eligible orbit of a center with
weight at most 4. Centers of weight 5 or 6 remain allowed when permitted by
the maximum-weight anchor.

## Clean CP-SAT Campaign

Both campaigns used:

- OR-Tools 9.14.6206;
- exact cardinality 16;
- two-coordinate and five-coordinate projection cuts;
- all radial capacity inequalities and rounded support bounds;
- 60 seconds per branch;
- four concurrent jobs with two solver workers per job;
- seed base 1000;
- a clean worktree at revision `710949c`.

| Anchor | Cases | Solver-only `INFEASIBLE` | `UNKNOWN` | Witnesses |
| --- | ---: | ---: | ---: | ---: |
| 5 | 24 | 5 | 19 | 0 |
| 6 | 14 | 1 | 13 | 0 |
| Total | 38 | 6 | 32 | 0 |

The solver-only infeasible cases are:

| Anchor | Orbit | Representative | Orbit size |
| --- | ---: | --- | ---: |
| 5 | 19 | `011110` | 5 |
| 5 | 20 | `011120` | 20 |
| 5 | 21 | `011220` | 30 |
| 5 | 22 | `012220` | 20 |
| 5 | 23 | `022220` | 5 |
| 6 | 13 | `002222` | 15 |

All other cases reached the time limit with status `UNKNOWN`.

## Reproducibility

The campaign records are stored locally at:

```text
research-results/cp-sat/w5_third_orbits_p2_p5_710949c
research-results/cp-sat/w6_third_orbits_p2_p5_710949c
```

The recorded fingerprints are:

| Anchor | Orbit manifest | Campaign | Run |
| --- | --- | --- | --- |
| 5 | `623c00f6083230738f58809c387d854e38e71b4eef4324fa52c7851e4b666000` | `649af4ffa35d2bde84be094188bf78ef14c60ac71205c54bd4ed14b4d95fae0e` | `cf3259d1dd20177b4e9c8de3d480d2644cd9f150c2f8ddd18e6adfa38cd8464a` |
| 6 | `db0f8bf6ed6466037db2fcd7866abec74e0328daf679508d5cd6d690108dd89e` | `3761dd12a02dba96b0ae945a67ab12ed96667c7f65b82ba252b8ca5286faabfe` | `26fa1a160cd5af5e0353a580bc3fb05243a91ef132e45181d8d3f13abde915a7` |

A second complete invocation reconstructed every serialized model hash and
accepted all 24 and 14 records from cache. GitHub Actions run
`34020306773` passed the native and CP-SAT jobs for the source revision.

Reproduction commands:

```bash
.tools/ortools-venv/bin/python tools/cp_sat_orbit_campaign.py \
  --weight 5 \
  --seconds 60 \
  --jobs 4 \
  --workers-per-job 2 \
  --five-projection-cuts \
  --output research-results/cp-sat/w5_third_orbits_p2_p5_710949c

.tools/ortools-venv/bin/python tools/cp_sat_orbit_campaign.py \
  --weight 6 \
  --seconds 60 \
  --jobs 4 \
  --workers-per-job 2 \
  --five-projection-cuts \
  --output research-results/cp-sat/w6_third_orbits_p2_p5_710949c
```

## Claim Limit

CP-SAT does not emit a checkable unsatisfiability proof. The six
`INFEASIBLE` classifications are reproducible solver evidence, not certified
branch exclusions. This campaign does not prove that a 16-word cover exists
or does not exist and does not determine `K_3(6,2)`.

## Next Work

1. Re-encode the six solver-infeasible cases with a proof-producing SAT
   solver and independently replay each proof.
2. Apply deeper stabilizer-orbit splitting to the 32 unresolved cases.
3. Continue construction search in parallel, because one verified 16-word
   witness would settle the upper-bound direction immediately.
