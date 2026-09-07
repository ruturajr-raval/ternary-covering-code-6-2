# Technical Report

The manuscript is `main.tex`.

Build the PDF from the repository root:

```bash
make paper-build
```

Build the deterministic source archive:

```bash
make paper-bundle
```

The paper outputs are:

```text
build/paper/main.pdf
dist/paper/ternary-covering-code-6-2-paper.pdf
dist/paper/ternary-covering-code-6-2-source.tar.gz
```

Build the paper-inclusive archival release set with:

```bash
make release-assets
make release-checksums
make verify-release-assets
```

Release `v0.1.1` adds the explicitly named PDF, deterministic source archive,
and `SHA256SUMS`. The mathematical result and all proof artifacts are
unchanged from `v0.1.0`.

Replay the central theorem independently with:

```bash
python3 tools/verify_branch_certificates.py
build/verify_branch_certificates
```

The complete repository test suite is:

```bash
make test
make test-cp-sat
```

`ARXIV_METADATA.md` records optional preprint-submission metadata.
`RIGHTS.md` records authorship and licensing boundaries.
