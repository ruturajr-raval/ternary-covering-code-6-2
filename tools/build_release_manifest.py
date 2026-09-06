#!/usr/bin/env python3

"""Build a deterministic SHA-256 manifest from the Git index."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "release-manifest.sha256"


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


def index_blob(relative: Path) -> bytes:
    result = subprocess.run(
        ["git", "show", f":{relative.as_posix()}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return result.stdout


def staged_paths(output: Path) -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    output_relative = output.resolve().relative_to(ROOT)
    paths = []
    for raw_entry in result.stdout.split(b"\0"):
        if not raw_entry:
            continue
        metadata, raw_path = raw_entry.split(b"\t", 1)
        mode, _, stage = metadata.decode("ascii").split()
        if stage != "0":
            raise ValueError(
                f"unmerged index entry prevents release: {raw_path!r}"
            )
        if mode not in {"100644", "100755"}:
            raise ValueError(
                "release paths must be regular files: "
                f"{raw_path.decode('utf-8')}"
            )
        relative = Path(raw_path.decode("utf-8"))
        if relative != output_relative:
            paths.append(relative)
    return tuple(sorted(paths, key=lambda path: path.as_posix()))


def ensure_index_ready(output: Path) -> None:
    output_relative = output.resolve().relative_to(ROOT)
    checks = (
        (["git", "diff", "--name-only", "-z"], "unstaged tracked path"),
        (
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            "untracked path",
        ),
        (["git", "ls-files", "--unmerged", "-z"], "unmerged path"),
    )
    errors = []
    for command, label in checks:
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        for raw_path in result.stdout.split(b"\0"):
            if not raw_path:
                continue
            relative = Path(raw_path.decode("utf-8"))
            if relative != output_relative:
                errors.append(f"{label}: {relative}")
    if errors:
        raise ValueError(
            "stage every release file before building the manifest:\n"
            + "\n".join(errors)
        )


def build_manifest(output: Path, paths: Iterable[Path]) -> None:
    selected = tuple(paths)
    if not selected:
        raise ValueError("release manifest would be empty")
    lines = []
    for relative in selected:
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"path must stay inside the repository: {relative}")
        full_path = ROOT / relative
        if not full_path.is_file() or full_path.is_symlink():
            raise ValueError(f"missing regular file: {relative}")
        lines.append(f"{sha256_file(full_path)}  {relative.as_posix()}\n")
    output.write_text("".join(lines), encoding="ascii")


def build_index_manifest(output: Path) -> int:
    ensure_index_ready(output)
    selected = staged_paths(output)
    if not selected:
        raise ValueError("release manifest would be empty")
    lines = [
        f"{sha256_bytes(index_blob(relative))}  {relative.as_posix()}\n"
        for relative in selected
    ]
    output.write_text("".join(lines), encoding="ascii")
    return len(selected)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not git_index_available():
        raise SystemExit("A Git index at the repository root is required.")
    entry_count = build_index_manifest(args.output)
    print(f"output={args.output} entries={entry_count} source=git-index")


if __name__ == "__main__":
    main()
