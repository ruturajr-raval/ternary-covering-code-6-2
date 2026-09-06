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

The archive is written to:

```text
dist/paper/ternary-covering-code-6-2-source.tar.gz
```

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
