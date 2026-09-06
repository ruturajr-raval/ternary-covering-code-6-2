# Claims And Nonclaims

Status date: 2026-09-06

## Supported Result

The normalized size-at-most-16 search for `K_3(6,2)` contains 38
third-center branches. Exact residual set-cover dual certificates exclude
the five weight-5 representatives

```text
011110
011120
011220
012220
022220
```

and the weight-6 representative `002222`. Independent Python and C++20
implementations reconstruct each branch, evaluate all 729 ambient words and
every admissible residual center, and verify the exact integer inequalities.
The certified normalized frontier is therefore reduced from 38 branches to
32.

## Reproduced Prior Art

The repository exhaustively verifies an attributed 17-word covering code as
a regression fixture. That construction is not claimed as project-original.
The historical interval remains

```text
15 <= K_3(6,2) <= 17.
```

## Not Claimed

- No 15-word or 16-word covering code is constructed.
- The remaining 32 normalized branches are not excluded.
- Nonexistence of all size-at-most-16 covering codes is not proved.
- The exact value and global table interval are unchanged.
- Solver exit status, repeated timeouts, and near-cover quality are not used
  as proofs.
- No external mathematical review is claimed.

## Significance And Reuse

The result converts six exploratory solver candidates into compact exact
certificates with two independently encoded checkers. The branch generator,
canonical tables, mutation tests, and dual-certificate format can be reused
for the remaining branches and for related finite covering problems.

## Evidence

- Machine-readable certificates:
  `data/weighted_branch_certificates.json`
- Python verifier: `tools/verify_branch_certificates.py`
- C++20 verifier: `src/verify_branch_certificates.cpp`
- Detailed theorem and replay procedure:
  `docs/WEIGHTED_BRANCH_CERTIFICATES.md`
- Machine-readable claim record: `research/claim.yaml`
- Release decision record: `research/release-gate.json`
