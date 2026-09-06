# Publication Artifacts

This directory is the explicit source-control allowlist for reviewed campaign
packages. Raw working files remain under ignored `research-results/`.

Create a package only after the source revision and campaign are final:

```bash
tools/package_campaign.py research-results/<campaign>
```

The packager requires the campaign's clean source commit to match the current
checkout. It copies accepted files without modification, excludes lock and
temporary files, rejects home paths, email addresses, and symlinks, and writes
a SHA-256 manifest. Review the resulting directory for mathematical
completeness and content safety before committing or archiving it.
