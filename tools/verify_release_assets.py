#!/usr/bin/env python3

"""Verify deterministic release assets recorded in release.json."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_METADATA = ROOT / "release.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_asset(path: Path, metadata: dict[str, object]) -> tuple[str, ...]:
    errors = []
    if not path.is_file() or path.is_symlink():
        return (f"missing regular file: {path}",)
    if metadata.get("name") != path.name:
        errors.append(
            f"asset name mismatch: expected {metadata.get('name')}, "
            f"found {path.name}"
        )
    size = path.stat().st_size
    if metadata.get("size") != size:
        errors.append(
            f"asset size mismatch: expected {metadata.get('size')}, "
            f"found {size}"
        )
    digest = sha256_file(path)
    if metadata.get("sha256") != digest:
        errors.append(
            f"asset hash mismatch: expected {metadata.get('sha256')}, "
            f"found {digest}"
        )
    return tuple(errors)


def main() -> None:
    release = json.loads(RELEASE_METADATA.read_text(encoding="ascii"))
    report = release["technical_report"]
    source_path = ROOT / report["source_archive"]
    source_metadata = report["candidate_release_assets"]["source"]
    errors = verify_asset(source_path, source_metadata)
    if errors:
        raise SystemExit(
            "Release asset verification failed:\n" + "\n".join(errors)
        )
    print(
        f"asset={source_path.relative_to(ROOT)} "
        f"sha256={source_metadata['sha256']} status=verified"
    )


if __name__ == "__main__":
    main()
