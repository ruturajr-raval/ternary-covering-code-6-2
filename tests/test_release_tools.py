#!/usr/bin/env python3

import hashlib
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.build_paper_bundle import MEMBERS, build_bundle
import tools.build_release_manifest as build_release_manifest
from tools.build_release_manifest import (
    build_manifest,
    git_index_available,
    index_blob,
    sha256_bytes,
)
from tools.verify_checksum_manifest import (
    parse_manifest,
    verify_entries,
    verify_index_entries,
    verify_tracked_coverage,
)
import tools.verify_checksum_manifest as verify_checksum_manifest
from tools.verify_release_assets import verify_asset


ROOT = Path(__file__).resolve().parents[1]


class PaperBundleTests(unittest.TestCase):
    def test_bundle_is_deterministic_and_allowlisted(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".paper-bundle-test-",
        ) as temporary_directory:
            first = Path(temporary_directory) / "first.tar.gz"
            second = Path(temporary_directory) / "second.tar.gz"
            build_bundle(first)
            build_bundle(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

            with tarfile.open(first, mode="r:gz") as archive:
                members = archive.getmembers()
                self.assertEqual(
                    tuple(member.name for member in members),
                    tuple(path.as_posix() for path in MEMBERS),
                )
                for member in members:
                    self.assertTrue(member.isfile())
                    self.assertEqual(member.mode, 0o644)
                    self.assertEqual(member.mtime, 0)
                    self.assertEqual(member.uid, 0)
                    self.assertEqual(member.gid, 0)
                    extracted = archive.extractfile(member)
                    self.assertIsNotNone(extracted)
                    self.assertEqual(
                        extracted.read(),
                        (ROOT / member.name).read_bytes(),
                    )


class ChecksumManifestTests(unittest.TestCase):
    def test_missing_git_is_reported_as_unavailable(self):
        with patch.object(
            build_release_manifest.subprocess,
            "run",
            side_effect=FileNotFoundError,
        ):
            self.assertFalse(build_release_manifest.git_index_available())
        with patch.object(
            verify_checksum_manifest.subprocess,
            "run",
            side_effect=FileNotFoundError,
        ):
            self.assertFalse(verify_checksum_manifest.git_index_available())

    def test_index_blob_matches_tracked_file(self):
        if not git_index_available():
            self.skipTest("Git index is unavailable in a source archive.")
        payload = index_blob(Path("LICENSE"))
        self.assertEqual(
            sha256_bytes(payload),
            hashlib.sha256((ROOT / "LICENSE").read_bytes()).hexdigest(),
        )

    def test_manifest_builder_is_deterministic(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".checksum-manifest-test-",
        ) as temporary_directory:
            directory = Path(temporary_directory)
            first_payload = directory / "first.txt"
            second_payload = directory / "second.txt"
            first_payload.write_text("first\n", encoding="ascii")
            second_payload.write_text("second\n", encoding="ascii")
            relative_paths = (
                first_payload.relative_to(ROOT),
                second_payload.relative_to(ROOT),
            )
            first_manifest = directory / "first.sha256"
            second_manifest = directory / "second.sha256"
            build_manifest(first_manifest, relative_paths)
            build_manifest(second_manifest, relative_paths)
            self.assertEqual(
                first_manifest.read_bytes(),
                second_manifest.read_bytes(),
            )
            self.assertEqual(
                verify_entries(parse_manifest(first_manifest)),
                (),
            )

    def test_manifest_parser_and_verifier(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".checksum-manifest-test-",
        ) as temporary_directory:
            directory = Path(temporary_directory)
            payload = directory / "payload.txt"
            payload.write_text("verified\n", encoding="ascii")
            relative = payload.relative_to(ROOT)
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            manifest = directory / "manifest.sha256"
            manifest.write_text(
                f"{digest}  {relative.as_posix()}\n",
                encoding="ascii",
            )
            self.assertEqual(
                verify_entries(parse_manifest(manifest)),
                (),
            )
            payload.write_text("changed\n", encoding="ascii")
            self.assertEqual(len(verify_entries(parse_manifest(manifest))), 1)

    def test_manifest_rejects_parent_paths(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".checksum-manifest-test-",
        ) as temporary_directory:
            manifest = Path(temporary_directory) / "manifest.sha256"
            manifest.write_text(
                f"{'0' * 64}  ../outside\n",
                encoding="ascii",
            )
            with self.assertRaises(ValueError):
                parse_manifest(manifest)

    def test_repository_manifest_matches_files_and_index(self):
        manifest = ROOT / "release-manifest.sha256"
        if not manifest.exists():
            self.skipTest("Release manifest has not been generated yet.")
        entries = parse_manifest(manifest)
        self.assertEqual(verify_entries(entries), ())
        if git_index_available():
            self.assertEqual(verify_index_entries(entries), ())
            self.assertEqual(
                verify_tracked_coverage(entries, manifest),
                (),
            )


class ReleaseAssetTests(unittest.TestCase):
    def test_asset_verifier_detects_size_and_hash_changes(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT,
            prefix=".release-asset-test-",
        ) as temporary_directory:
            asset = Path(temporary_directory) / "asset.bin"
            asset.write_bytes(b"verified\n")
            metadata = {
                "name": asset.name,
                "size": asset.stat().st_size,
                "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
            }
            self.assertEqual(verify_asset(asset, metadata), ())
            asset.write_bytes(b"changed\n")
            self.assertEqual(len(verify_asset(asset, metadata)), 2)


if __name__ == "__main__":
    unittest.main()
