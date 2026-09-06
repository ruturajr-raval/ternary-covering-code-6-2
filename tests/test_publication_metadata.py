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

    def test_publication_files_have_no_local_or_generated_traces(self):
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
            "generated " + "by a language model",
            "language-model " + "generated",
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
