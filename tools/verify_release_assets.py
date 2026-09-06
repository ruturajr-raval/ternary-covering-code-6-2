#!/usr/bin/env python3

"""Verify deterministic release assets recorded in release.json."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
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


def verify_zenodo_archive(
    path: Path,
    metadata: dict[str, object],
) -> tuple[str, ...]:
    expected_name = Path(str(metadata.get("file", ""))).name
    normalized = {
        "name": expected_name,
        "size": metadata.get("size"),
        "sha256": metadata.get("sha256"),
    }
    errors = list(verify_asset(path, normalized))
    if path.is_file() and not path.is_symlink():
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        if metadata.get("md5") != digest:
            errors.append(
                f"asset MD5 mismatch: expected {metadata.get('md5')}, "
                f"found {digest}"
            )
    return tuple(errors)


def git_blob(commit: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return result.stdout


def git_tree_paths(commit: str) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "-z", commit],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return tuple(
        raw.decode("utf-8")
        for raw in result.stdout.split(b"\0")
        if raw
    )


def verify_zenodo_tag_tree(
    archive: Path,
    commit: str,
) -> tuple[str, ...]:
    errors = []
    with zipfile.ZipFile(archive) as handle:
        file_names = tuple(
            name for name in handle.namelist() if not name.endswith("/")
        )
        roots = {name.split("/", 1)[0] for name in file_names}
        if len(roots) != 1:
            return ("Zenodo archive must contain one repository root.",)
        root = next(iter(roots))
        archived = {
            name.split("/", 1)[1]: handle.read(name)
            for name in file_names
            if "/" in name
        }

    expected_paths = git_tree_paths(commit)
    archived_paths = tuple(sorted(archived))
    if archived_paths != tuple(sorted(expected_paths)):
        missing = sorted(set(expected_paths) - set(archived_paths))
        extra = sorted(set(archived_paths) - set(expected_paths))
        errors.append(f"Zenodo tree path mismatch: missing={missing} extra={extra}")
        return tuple(errors)

    for relative in expected_paths:
        if archived[relative] != git_blob(commit, relative):
            errors.append(f"Zenodo tree content mismatch: {root}/{relative}")
    return tuple(errors)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-pdf", type=Path)
    parser.add_argument("--release-source", type=Path)
    parser.add_argument("--zenodo-archive", type=Path)
    args = parser.parse_args()

    release = json.loads(RELEASE_METADATA.read_text(encoding="ascii"))
    report = release["technical_report"]
    source_path = ROOT / report["source_archive"]
    source_metadata = report.get("current_source_bundle")
    if source_metadata is None:
        source_metadata = report["candidate_release_assets"]["source"]
    errors = verify_asset(source_path, source_metadata)
    if errors:
        raise SystemExit(
            "Release asset verification failed:\n" + "\n".join(errors)
        )
    messages = [
        f"asset={source_path.relative_to(ROOT)} "
        f"sha256={source_metadata['sha256']} status=verified"
    ]

    published = report["release_assets"]
    optional_assets = (
        (args.release_pdf, published["pdf"]),
        (args.release_source, published["source"]),
    )
    for path, metadata in optional_assets:
        if path is None:
            continue
        asset_errors = verify_asset(path, metadata)
        if asset_errors:
            raise SystemExit(
                "Published asset verification failed:\n"
                + "\n".join(asset_errors)
            )
        messages.append(
            f"asset={path} sha256={metadata['sha256']} status=verified"
        )

    if args.zenodo_archive is not None:
        archive_metadata = report["release_zenodo_archive"]
        archive_errors = verify_zenodo_archive(
            args.zenodo_archive,
            archive_metadata,
        )
        archive_errors += verify_zenodo_tag_tree(
            args.zenodo_archive,
            report["release_commit"],
        )
        if archive_errors:
            raise SystemExit(
                "Zenodo archive verification failed:\n"
                + "\n".join(archive_errors)
            )
        messages.append(
            f"asset={args.zenodo_archive} "
            f"sha256={archive_metadata['sha256']} "
            "tag_tree=verified status=verified"
        )

    print("\n".join(messages))


if __name__ == "__main__":
    main()
