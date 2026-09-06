#!/usr/bin/env python3

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TITLE = (
    "Six Certified Branch Exclusions for the Ternary Covering Problem "
    "K_3(6,2)"
)
VERSION = "0.1.0"
AUTHOR = "Ruturaj R Raval"
ORCID = "0000-0003-4930-8981"
VERSION_DOI = "10.5281/zenodo.22510342"
CONCEPT_DOI = "10.5281/zenodo.22510341"
REPRESENTATIVES = (
    "011110",
    "011120",
    "011220",
    "012220",
    "022220",
    "002222",
)


class PublicationMetadataTests(unittest.TestCase):
    def test_title_version_and_author_are_consistent(self):
        zenodo = json.loads(
            (ROOT / ".zenodo.json").read_text(encoding="ascii")
        )
        release = json.loads(
            (ROOT / "release.json").read_text(encoding="ascii")
        )
        cff = (ROOT / "CITATION.cff").read_text(encoding="ascii")
        metadata = (ROOT / "paper" / "ARXIV_METADATA.md").read_text(
            encoding="ascii"
        )
        manuscript = (ROOT / "paper" / "main.tex").read_text(
            encoding="utf-8"
        )

        self.assertEqual(zenodo["title"], TITLE)
        self.assertEqual(release["technical_report"]["title"], TITLE)
        self.assertIn(f'title: "{TITLE}"', cff)
        self.assertIn(TITLE, metadata)
        self.assertEqual(zenodo["version"], VERSION)
        self.assertEqual(release["version"], VERSION)
        self.assertIn(f"version: {VERSION}", cff)
        self.assertEqual(zenodo["creators"][0]["name"], "Raval, Ruturaj R")
        self.assertEqual(zenodo["creators"][0]["orcid"], ORCID)
        self.assertIn("family-names: Raval", cff)
        self.assertIn("given-names: Ruturaj R", cff)
        self.assertIn(AUTHOR, metadata)
        self.assertIn(AUTHOR, manuscript)
        self.assertIn(ORCID, cff)
        self.assertIn(ORCID, metadata)
        self.assertIn(ORCID, manuscript)

    def test_certificate_scope_and_counts_are_consistent(self):
        certificate_data = json.loads(
            (
                ROOT / "data" / "weighted_branch_certificates.json"
            ).read_text(encoding="ascii")
        )
        certificates = certificate_data["certificates"]
        self.assertEqual(len(certificates), 6)
        self.assertEqual(
            tuple(item["representative"] for item in certificates),
            REPRESENTATIVES,
        )
        self.assertEqual(
            tuple(item["anchor_weight"] for item in certificates),
            (5, 5, 5, 5, 5, 6),
        )
        for item in certificates:
            self.assertGreater(
                item["expected_total_weight"],
                13 * item["expected_max_capacity"],
            )

        publication_text = "\n".join(
            (ROOT / relative).read_text(encoding="utf-8")
            for relative in (
                "README.md",
                "PUBLICATION.md",
                "docs/COMPUTATIONAL_STATUS.md",
                "docs/WEIGHTED_BRANCH_CERTIFICATES.md",
                "paper/main.tex",
                "paper/ARXIV_METADATA.md",
                ".zenodo.json",
                "CITATION.cff",
            )
        )
        for representative in REPRESENTATIVES:
            self.assertGreaterEqual(publication_text.count(representative), 4)
        self.assertIn("38 branches to 32", publication_text)
        self.assertIn("global interval", publication_text)
        self.assertIn("remains unchanged", publication_text)

    def test_release_gate_matches_claim_boundary(self):
        release = json.loads(
            (ROOT / "release.json").read_text(encoding="ascii")
        )
        gate = json.loads(
            (ROOT / "research" / "release-gate.json").read_text(
                encoding="ascii"
            )
        )
        self.assertTrue(gate["gates"]["significant_original_result"])
        self.assertFalse(gate["gates"]["complete_exact_value_result"])
        self.assertTrue(gate["gates"]["six_exact_certificates_pass"])
        self.assertTrue(gate["gates"]["canonical_tables_match"])
        self.assertTrue(
            gate["gates"]["production_generator_manifests_match"]
        )
        self.assertTrue(gate["gates"]["public_release_created"])
        self.assertTrue(gate["gates"]["zenodo_version_doi_assigned"])
        self.assertEqual(gate["artifact_decision"], "released")
        self.assertEqual(release["release_status"], "released")
        self.assertEqual(
            release["verification"]["certified_branches"],
            6,
        )
        self.assertEqual(
            release["verification"]["unresolved_branches"],
            32,
        )
        limitations = "\n".join(release["limitations"])
        self.assertIn("exact value", limitations)
        self.assertIn("global interval", limitations)

    def test_release_and_archive_identifiers_are_consistent(self):
        release = json.loads(
            (ROOT / "release.json").read_text(encoding="ascii")
        )
        report = release["technical_report"]
        self.assertEqual(report["release_tag"], "v0.1.0")
        self.assertEqual(
            report["release_tag_object"],
            "820713e18e09aa74611f0dc23b19bb18e7c54c95",
        )
        self.assertEqual(
            report["release_commit"],
            "3dea87b7e2cd116fcd5fc05c63c21a71259b0923",
        )
        self.assertEqual(
            report["github_release"],
            "https://github.com/ruturajr-raval/"
            "ternary-covering-code-6-2/releases/tag/v0.1.0",
        )
        self.assertEqual(report["release_version_doi"], VERSION_DOI)
        self.assertEqual(report["release_concept_doi"], CONCEPT_DOI)
        self.assertEqual(report["github_release_id"], 383520038)
        self.assertEqual(report["current_source_bundle"]["size"], 9142)
        self.assertEqual(
            report["current_source_bundle"]["sha256"],
            "66e084ee2032f1f565f26838867691f34d1228543f4e6d4c42bb2b6abd977f7d",
        )
        self.assertEqual(report["release_assets"]["pdf"]["size"], 321190)
        self.assertEqual(
            report["release_assets"]["pdf"]["sha256"],
            "1096074fd0023ff908b7c7cc1cf4091701945278c40bf5a010865b7d1e3473a0",
        )
        self.assertEqual(report["release_assets"]["source"]["size"], 9131)
        self.assertEqual(
            report["release_assets"]["source"]["sha256"],
            "0ad4c0a0fd44c9714f3123673bad13cbc60cebde4569b1073edf304458f42974",
        )
        self.assertEqual(
            report["release_zenodo_archive"]["file"],
            "ruturajr-raval/ternary-covering-code-6-2-v0.1.0.zip",
        )
        self.assertEqual(report["release_zenodo_archive"]["size"], 135788)
        self.assertEqual(
            report["release_zenodo_archive"]["md5"],
            "a4678b6226e4c074f6d5840d71e8d953",
        )
        self.assertEqual(
            report["release_zenodo_archive"]["sha256"],
            "22044a649126f2836b2ced2135f6c4930e1842cbfc4ef3189ed09f84894eee8e",
        )
        self.assertEqual(
            report["ci"],
            {
                "workbench_main": 34022553335,
                "public_main": 34022706058,
                "workbench_tag": 34022845395,
                "public_tag": 34022847941,
            },
        )
        self.assertTrue(release["verification"]["release_assets_download_match"])
        self.assertTrue(
            release["verification"]["zenodo_archive_matches_release_tag"]
        )
        self.assertEqual(
            release["verification"]["zenodo_archive_file_count"],
            63,
        )

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        publication = (ROOT / "PUBLICATION.md").read_text(encoding="utf-8")
        arxiv = (ROOT / "paper" / "ARXIV_METADATA.md").read_text(
            encoding="utf-8"
        )
        cff = (ROOT / "CITATION.cff").read_text(encoding="ascii")
        for text in (readme, publication, arxiv, cff):
            self.assertIn(VERSION_DOI, text)
        for text in (readme, publication):
            self.assertIn(CONCEPT_DOI, text)
        self.assertGreaterEqual(cff.count(VERSION_DOI), 2)

    def test_upstream_attribution_is_correct(self):
        manuscript = (ROOT / "paper" / "main.tex").read_text(
            encoding="utf-8"
        )
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("A.~Florath", manuscript)
        self.assertNotIn("F.~Rath", manuscript)
        self.assertIn("Andreas Florath", notices)

    def test_publication_files_have_no_local_or_visibility_traces(self):
        excluded_parts = {
            ".git",
            ".tools",
            "__pycache__",
            "build",
            "dist",
            "research-results",
            "search-results",
        }
        forbidden = (
            "\u2014",
            "/" + "Users" + "/",
            "ruturajr" + "-innovation",
            "research" + "-workbench",
            "private " + "repository",
            "private " + "repo",
            "private" + "_",
        )
        for path in ROOT.rglob("*"):
            relative = path.relative_to(ROOT)
            if any(part in excluded_parts for part in relative.parts):
                continue
            if not path.is_file() or path.is_symlink():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for token in forbidden:
                self.assertNotIn(token, text, f"{relative}: forbidden trace")


if __name__ == "__main__":
    unittest.main()
