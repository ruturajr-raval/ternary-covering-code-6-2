#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid


ALLOWED_SUFFIXES = {
    ".cnf",
    ".drat",
    ".json",
    ".log",
    ".lrat",
    ".proof",
    ".sha256",
    ".txt",
}
SKIPPED_NAMES = {".campaign.lock", ".generation.lock"}
FORBIDDEN_PATTERNS = {
    "home path": re.compile(rb"/(?:Users|home)/[^/\s]+/"),
    "email address": re.compile(
        rb"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
        rb"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    ),
}


def hash_and_scan(path, forbidden_root):
    digest = hashlib.sha256()
    carry = b""
    root_bytes = str(forbidden_root).encode()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            searchable = carry + block
            if root_bytes in searchable:
                raise ValueError(
                    f"{path} contains the local project path"
                )
            for label, pattern in FORBIDDEN_PATTERNS.items():
                if pattern.search(searchable):
                    raise ValueError(f"{path} contains a {label}")
            carry = searchable[-512:]
    return digest.hexdigest()


def collect_files(source, root):
    records = []
    excluded = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symbolic links are not accepted: {path}")
        if path.is_dir():
            continue
        relative = path.relative_to(source)
        if path.name in SKIPPED_NAMES or ".tmp" in path.name:
            excluded.append(str(relative))
            continue
        if path.suffix not in ALLOWED_SUFFIXES:
            raise ValueError(f"unsupported artifact type: {relative}")
        records.append(
            {
                "path": str(relative),
                "size": path.stat().st_size,
                "sha256": hash_and_scan(path, root),
            }
        )
    if not records:
        raise ValueError("campaign directory contains no accepted files")
    if not any(record["path"] == "summary.json" for record in records):
        raise ValueError("campaign directory has no summary.json")
    return records, excluded


def validate_campaign_layout(source, summary):
    has_manifest = "orbit_manifest" in summary
    has_selection = "selected_orbits" in summary
    if not has_manifest and not has_selection:
        return
    if not has_manifest or not has_selection:
        raise ValueError("incomplete CP-SAT campaign layout metadata")

    manifest = summary["orbit_manifest"]
    selected = summary["selected_orbits"]
    if (
        not isinstance(manifest, dict)
        or not isinstance(manifest.get("orbit_count"), int)
        or not isinstance(selected, list)
        or any(
            not isinstance(orbit, int)
            or orbit < 0
            or orbit >= manifest["orbit_count"]
            for orbit in selected
        )
        or len(set(selected)) != len(selected)
    ):
        raise ValueError("invalid CP-SAT campaign layout metadata")

    expected = {f"orbit-{orbit:02d}" for orbit in selected}
    unexpected = sorted(
        path.name
        for path in source.iterdir()
        if path.is_dir() and path.name not in expected
    )
    if unexpected:
        raise ValueError(
            "campaign contains unselected branch directories: "
            + ",".join(unexpected)
        )


def write_json(path, value):
    temporary = path.with_name(
        f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    with temporary.open("w") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def git_state(root):
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return commit, bool(status.strip())


def campaign_metadata(summary, current_commit, allow_noncertified):
    provenance = summary.get("provenance", {})
    source_commit = (
        provenance.get("git_commit")
        if isinstance(provenance, dict)
        else None
    ) or summary.get("git_commit")
    source_dirty = (
        provenance.get("git_dirty")
        if isinstance(provenance, dict)
        and "git_dirty" in provenance
        else summary.get("git_tracked_dirty")
    )
    if (
        not isinstance(source_commit, str)
        or len(source_commit) != 40
        or source_dirty is not False
    ):
        raise ValueError(
            "campaign summary is not bound to a clean source commit"
        )
    if source_commit != current_commit:
        raise ValueError(
            "campaign source commit does not match the checked-out commit"
        )

    witness = summary.get("witness_found") is True
    certified_tree = (
        isinstance(summary.get("run"), dict)
        and summary["run"].get("certified_complete") is True
    )
    certified = witness or certified_tree
    if not certified and not allow_noncertified:
        raise ValueError(
            "campaign is not certified; use --allow-noncertified "
            "only for explicitly labeled exploratory archives"
        )
    return {
        "source_commit": source_commit,
        "certified": certified,
        "witness_found": witness,
        "certified_tree": certified_tree,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--allow-noncertified", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    source = args.campaign
    if not source.is_absolute():
        source = root / source
    source = source.resolve()
    results_root = (root / "research-results").resolve()
    try:
        source.relative_to(results_root)
    except ValueError as error:
        raise SystemExit(
            "campaign must be under research-results"
        ) from error
    if not source.is_dir():
        raise SystemExit(f"campaign directory does not exist: {source}")

    output = args.output or (root / "artifacts" / source.name)
    if not output.is_absolute():
        output = root / output
    output = output.resolve()
    artifact_root = (root / "artifacts").resolve()
    try:
        output.relative_to(artifact_root)
    except ValueError as error:
        raise SystemExit("output must be under artifacts") from error
    if output.exists():
        raise SystemExit(f"output already exists: {output}")

    commit, dirty = git_state(root)
    if dirty and not args.allow_dirty:
        raise SystemExit("refusing to package a dirty worktree")

    try:
        summary = json.loads((source / "summary.json").read_text())
        metadata = campaign_metadata(
            summary,
            commit,
            args.allow_noncertified,
        )
        validate_campaign_layout(source, summary)
        records, excluded = collect_files(source, root.resolve())
    except (ValueError, json.JSONDecodeError, OSError) as error:
        raise SystemExit(str(error)) from error

    output.mkdir(parents=True)
    for record in records:
        destination = output / record["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / record["path"], destination)
        if hash_and_scan(destination, root.resolve()) != record["sha256"]:
            raise RuntimeError(f"copied artifact hash changed: {destination}")
    manifest = {
        "schema": 1,
        "source_campaign": str(source.relative_to(root)),
        "source_commit": metadata["source_commit"],
        "packaging_commit": commit,
        "source_certified": metadata["certified"],
        "source_witness_found": metadata["witness_found"],
        "source_certified_tree": metadata["certified_tree"],
        "packaging_dirty": dirty,
        "excluded_files": excluded,
        "files": records,
    }
    write_json(output / "MANIFEST.json", manifest)
    print(output.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
