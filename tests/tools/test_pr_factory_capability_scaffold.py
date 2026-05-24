from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.pr_factory.generate_capability_scaffold import (
    CapabilityScaffoldConfig,
    DEFAULT_FORBIDDEN_BOUNDARIES,
    ScaffoldCollisionError,
    generate_scaffold,
)


class CapabilityScaffoldGeneratorTests(unittest.TestCase):
    def build_scaffold(self, *, allow_overwrite: bool = False) -> tuple[Path, tuple[Path, ...]]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        written = generate_scaffold(
            CapabilityScaffoldConfig(
                capability_id="sample-capability",
                capability_file_name="sample_capability.py",
                output_dir=root,
                output_file_names=(
                    "result_contract.json",
                    "output_artifact_manifest.json",
                    "artifact_index.json",
                    "artifact_index_manifest.json",
                    "summary.md",
                    "checklist.md",
                ),
                allow_overwrite=allow_overwrite,
            )
        )
        return root, written

    def combined_text(self, root: Path) -> str:
        return "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(root.rglob("*"))
            if path.is_file()
        )

    def test_generator_creates_expected_skeleton_files_into_temp_directory(self):
        root, written = self.build_scaffold()
        relatives = {path.relative_to(root).as_posix() for path in written}

        self.assertEqual(
            relatives,
            {
                "capability/sample_capability.py",
                "tests/tracer_bullet/test_sample_capability.py",
                "docs/decisions/sample-capability_decision.md",
                "contracts/result_contract.md",
                "contracts/output_artifact_manifest_contract.md",
                "contracts/artifact_index_contract.md",
                "contracts/artifact_index_manifest_contract.md",
                "reports/summary.md",
                "checklists/forbidden_boundary_checklist.md",
                "reports/pr_report_template.md",
                "validation/validation_checklist.md",
            },
        )

    def test_generator_refuses_output_collision_unless_explicit_safe_flag_exists(self):
        root, _ = self.build_scaffold()

        with self.assertRaisesRegex(ScaffoldCollisionError, "output_collision"):
            generate_scaffold(
                CapabilityScaffoldConfig(
                    capability_id="sample-capability",
                    capability_file_name="sample_capability.py",
                    output_dir=root,
                )
            )

        written = generate_scaffold(
            CapabilityScaffoldConfig(
                capability_id="sample-capability",
                capability_file_name="sample_capability.py",
                output_dir=root,
                allow_overwrite=True,
            )
        )
        self.assertTrue(written)

    def test_generated_skeleton_contains_metadata_only_boundary_warnings(self):
        root, _ = self.build_scaffold()
        text = self.combined_text(root)

        self.assertIn("METADATA-ONLY SCAFFOLD", text)
        self.assertIn("fail-closed", text.lower())
        self.assertIn("forbidden_boundary_requested", text)
        for forbidden in DEFAULT_FORBIDDEN_BOUNDARIES:
            self.assertIn(forbidden, text)

    def test_generated_skeleton_contains_no_live_website_support(self):
        root, _ = self.build_scaffold()
        text = self.combined_text(root).lower()

        self.assertIn("live website automation", text)
        self.assertNotIn("live website support", text)
        self.assertNotIn("live site support", text)

    def test_generated_skeleton_contains_no_token_issuance_implementation(self):
        root, _ = self.build_scaffold()
        text = self.combined_text(root)

        self.assertNotIn("def issue_token", text)
        self.assertNotIn("def mint_token", text)
        self.assertNotIn("class TokenIssuer", text)

    def test_generated_skeleton_contains_no_runner_implementation(self):
        root, _ = self.build_scaffold()
        text = self.combined_text(root)

        self.assertNotIn("class Runner", text)
        self.assertNotIn("def run_runner", text)
        self.assertNotIn("create_runner(", text)

    def test_generated_skeleton_contains_no_browser_launch_implementation(self):
        root, _ = self.build_scaffold()
        text = self.combined_text(root)

        self.assertNotIn("webbrowser", text)
        self.assertNotIn("browser.launch", text)
        self.assertNotIn("open_browser(", text)
        self.assertNotIn("launch_browser(", text)

    def test_generated_skeleton_contains_no_network_access_implementation(self):
        root, _ = self.build_scaffold()
        text = self.combined_text(root)

        self.assertNotIn("import socket", text)
        self.assertNotIn("import urllib", text)
        self.assertNotIn("import http.client", text)
        self.assertNotIn("urlopen(", text)
        self.assertNotIn("fetch(", text)
        self.assertNotIn("curl ", text)
        self.assertNotIn("wget ", text)

    def test_generated_pr_report_template_contains_required_fields(self):
        root, _ = self.build_scaffold()
        report = (root / "reports/pr_report_template.md").read_text(encoding="utf-8")

        for field in (
            "PR",
            "Branch",
            "Head commit",
            "Base commit",
            "Changed files",
            "Additions/deletions",
            "Validation",
            "Remaining blockers",
        ):
            self.assertIn(f"{field}:", report)

    def test_generated_validation_checklist_contains_required_commands(self):
        root, _ = self.build_scaffold()
        checklist = (root / "validation/validation_checklist.md").read_text(encoding="utf-8")

        self.assertIn("targeted unittest", checklist)
        self.assertIn("python3 -m unittest tests.tools.test_pr_factory_capability_scaffold", checklist)
        self.assertIn("unittest discover", checklist)
        self.assertIn("python3 -m unittest discover tests", checklist)
        self.assertIn("make ci", checklist)
        self.assertIn("git diff --check", checklist)
        self.assertIn("git status --short --branch", checklist)


if __name__ == "__main__":
    unittest.main()
