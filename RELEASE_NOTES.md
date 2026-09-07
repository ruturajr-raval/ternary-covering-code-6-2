# Release Notes

## [v0.1.1](https://github.com/ruturajr-raval/ternary-covering-code-6-2/releases/tag/v0.1.1) - 2026-09-07

### Archival And Documentation Patch

This patch adds a paper-inclusive archival release set:

- `ternary-covering-code-6-2-paper.pdf`;
- `ternary-covering-code-6-2-source.tar.gz`;
- `SHA256SUMS`.

The compiled PDF and deterministic source archive are intended for both the
GitHub release and Zenodo record. The version DOI is
`10.5281/zenodo.22647771`, and the stable concept DOI remains
`10.5281/zenodo.22510341`.

The theorem, proof, certificates, data, computations, six excluded branches,
32 unresolved branches, and global interval are unchanged from `v0.1.0`.
This patch makes no new mathematical claim.

Asset hashes:

```text
ternary-covering-code-6-2-paper.pdf  c0a8bc60bb0d83fb0ed3ff19764c78badf9fe69cac119447c9b25acacddbf321
ternary-covering-code-6-2-source.tar.gz  0e1d5433493905c7ab0bdd83667b74c5cf6e93e46e09607e64408aa3a220fdbb
SHA256SUMS  7a89a7fde2b523e3a5bf65c12228d75cf710283feba6b99e86362021b56455c8
```

## [v0.1.0](https://github.com/ruturajr-raval/ternary-covering-code-6-2/releases/tag/v0.1.0) - 2026-09-06

### Result

Exact integer dual certificates exclude six named branches in the complete
38-branch normalized third-center partition for size-at-most-16 ternary
radius-2 covers of length 6. The certified normalized frontier is reduced
from 38 branches to 32.

The global interval remains

```text
15 <= K_3(6,2) <= 17.
```

### Verification

The release includes machine-readable certificate weights, deterministic
branch reconstruction, and independently encoded Python and C++20 verifiers.
Both implementations check every one of the 729 ambient words, every
admissible residual center, all exact integer capacities, and the same six
canonical branches. Mutation and production-generator regression tests pass.

The maintained `main` publication surface is bound by
`release-manifest.sha256`. The immutable `v0.1.0` release is bound separately
by its protected tag and commit, recorded asset hashes, and the 63-file Zenodo
archive-to-tag comparison in `release.json`.

### Scope

This release does not construct a 15-word or 16-word covering code, exclude
the remaining 32 normalized branches, determine the exact value, or improve
the global interval. Solver status and search time are not used as proof. No
external mathematical review is claimed.

### Release And Archive

- Tagged release:
  `https://github.com/ruturajr-raval/ternary-covering-code-6-2/releases/tag/v0.1.0`
- Release commit:
  `3dea87b7e2cd116fcd5fc05c63c21a71259b0923`
- Version DOI: `10.5281/zenodo.22510342`
- Stable concept DOI: `10.5281/zenodo.22510341`
- Zenodo snapshot:
  `ruturajr-raval/ternary-covering-code-6-2-v0.1.0.zip`
- Zenodo snapshot SHA-256:
  `22044a649126f2836b2ced2135f6c4930e1842cbfc4ef3189ed09f84894eee8e`
