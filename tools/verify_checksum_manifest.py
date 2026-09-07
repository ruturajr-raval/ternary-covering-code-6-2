#!/usr/bin/env python3

"""Verify a repository-relative SHA-256 manifest."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "release-manifest.sha256"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_index_available() -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False
    if result.returncode != 0:
        return False
    return Path(result.stdout.strip()).resolve() == ROOT.resolve()


def parse_manifest(path: Path) -> tuple[tuple[str, Path], ...]:
    entries = []
    for line_number, line in enumerate(
        path.read_text(encoding="ascii").splitlines(),
        start=1,
    ):
        if not line:
            continue
        try:
            expected, relative_text = line.split("  ", 1)
        except ValueError as error:
            raise ValueError(
                f"{path}:{line_number}: expected '<sha256>  <path>'"
            ) from error
        if len(expected) != 64 or any(
            character not in "0123456789abcdef"
            for character in expected
        ):
            raise ValueError(
                f"{path}:{line_number}: invalid SHA-256 digest"
            )
        relative = Path(relative_text)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(
                f"{path}:{line_number}: path must stay inside the repository"
            )
        entries.append((expected, relative))
    if not entries:
        raise ValueError(f"{path}: manifest is empty")
    return tuple(entries)


def verify_entries(
    entries: Iterable[tuple[str, Path]],
) -> tuple[str, ...]:
    errors = []
    seen = set()
    for expected, relative in entries:
        if relative in seen:
            errors.append(f"duplicate path: {relative}")
            continue
        seen.add(relative)
        full_path = ROOT / relative
        if not full_path.is_file() or full_path.is_symlink():
            errors.append(f"missing regular file: {relative}")
            continue
        actual = sha256_file(full_path)
        if actual != expected:
            errors.append(
                f"hash mismatch: {relative}: expected {expected}, found {actual}"
            )
    return tuple(errors)


def verify_index_entries(
    entries: Iterable[tuple[str, Path]],
) -> tuple[str, ...]:
    errors = []
    for expected, relative in entries:
        result = subprocess.run(
            ["git", "show", f":{relative.as_posix()}"],
            cwd=ROOT,
            capture_output=True,
        )
        if result.returncode != 0:
            errors.append(f"path is absent from Git index: {relative}")
            continue
        actual = sha256_bytes(result.stdout)
        if actual != expected:
            errors.append(
                "Git index hash mismatch: "
                f"{relative}: expected {expected}, found {actual}"
            )
    return tuple(errors)


def verify_tracked_coverage(
    entries: Iterable[tuple[str, Path]],
    manifest: Path,
) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    manifest_relative = manifest.resolve().relative_to(ROOT)
    tracked = {
        Path(raw_path.decode("utf-8"))
        for raw_path in result.stdout.split(b"\0")
        if raw_path
    }
    tracked.discard(manifest_relative)
    listed = {relative for _, relative in entries}
    errors = []
    for relative in sorted(tracked - listed, key=lambda path: path.as_posix()):
        errors.append(f"tracked file missing from manifest: {relative}")
    for relative in sorted(listed - tracked, key=lambda path: path.as_posix()):
        errors.append(f"manifest path is not tracked: {relative}")
    return tuple(errors)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST,
    )
    parser.add_argument(
        "--listed-only",
        action="store_true",
        help="verify listed hashes without comparing against tracked files",
    )
    parser.add_argument(
        "--worktree",
        action="store_true",
        help="verify current tracked files without comparing Git index blobs",
    )
    args = parser.parse_args()
    if args.listed_only and args.worktree:
        parser.error("--listed-only and --worktree are mutually exclusive")
    entries = parse_manifest(args.manifest)
    errors = list(verify_entries(entries))
    index_checked = False
    worktree_coverage_checked = False
    if not args.listed_only and git_index_available():
        if not args.worktree:
            errors.extend(verify_index_entries(entries))
            index_checked = True
        errors.extend(verify_tracked_coverage(entries, args.manifest))
        worktree_coverage_checked = args.worktree
    if errors:
        raise SystemExit("Manifest verification failed:\n" + "\n".join(errors))
    if index_checked:
        mode = "files-and-git-index"
    elif worktree_coverage_checked:
        mode = "files-and-tracked-coverage"
    else:
        mode = "listed-files"
    print(f"manifest={args.manifest} status=verified mode={mode}")


if __name__ == "__main__":
    main()
