import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.output_package_manifest import (
    ApprovedOutputManifestResult,
    build_approved_output_manifest,
)


EXPECTED_MANIFEST_KEYS = {
    "manifest_type",
    "authority",
    "execution_capability",
    "output_package_dir",
    "artifacts",
    "artifact_presence",
    "complete",
    "missing_artifacts",
    "approval_verified",
    "boundaries",
    "forbidden_actions",
    "next_allowed_action",
}

REQUIRED_OUTPUT_FILES = {
    "approved_output_manifest.json",
    "delivery_summary.json",
    "approval_receipt.json",
    "spreadsheet_structural_report.json",
    "spreadsheet_structural_report.md",
    "final_job_manifest.json",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class OutputPackageManifestTests(unittest.TestCase):
    def build_output_package_dir(self, final_manifest_payload=None):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        output_package_dir = root / "approved-001"
        output_package_dir.mkdir()
        write_json(
            output_package_dir / "delivery_summary.json",
            {"summary_type": "personal_ai_local_v1_delivery_summary"},
        )
        write_json(
            output_package_dir / "approval_receipt.json",
            {"approval_verified": True},
        )
        write_json(
            output_package_dir / "spreadsheet_structural_report.json",
            {"report_status": "report_planning_ready"},
        )
        (output_package_dir / "spreadsheet_structural_report.md").write_text(
            "# Structural Report\n",
            encoding="utf-8",
        )
        write_json(
            output_package_dir / "final_job_manifest.json",
            final_manifest_payload
            or {"manifest_type": "personal_ai_local_v1_final_job_manifest"},
        )
        return output_package_dir

    def test_builds_manifest(self):
        output_package_dir = self.build_output_package_dir()
        output_manifest_path = output_package_dir / "approved_output_manifest.json"

        result = build_approved_output_manifest(
            output_package_dir,
            output_manifest_path,
        )
        manifest = read_json(output_manifest_path)

        self.assertIsInstance(result, ApprovedOutputManifestResult)
        self.assertEqual(result.output_package_dir, output_package_dir)
        self.assertEqual(result.output_manifest_path, output_manifest_path)
        self.assertEqual(set(manifest), EXPECTED_MANIFEST_KEYS)
        self.assertEqual(
            manifest["manifest_type"],
            "personal_ai_local_v1_approved_output_manifest",
        )

    def test_complete_true_when_all_files_present(self):
        output_package_dir = self.build_output_package_dir()

        result = build_approved_output_manifest(
            output_package_dir,
            output_package_dir / "approved_output_manifest.json",
        )
        manifest = read_json(output_package_dir / "approved_output_manifest.json")

        self.assertIs(result.complete, True)
        self.assertIs(manifest["complete"], True)
        self.assertEqual(manifest["missing_artifacts"], [])
        self.assertTrue(all(manifest["artifact_presence"].values()))

    def test_missing_artifact_recorded_when_file_missing(self):
        output_package_dir = self.build_output_package_dir()
        (output_package_dir / "final_job_manifest.json").unlink()

        result = build_approved_output_manifest(
            output_package_dir,
            output_package_dir / "approved_output_manifest.json",
        )
        manifest = read_json(output_package_dir / "approved_output_manifest.json")

        self.assertIs(result.complete, False)
        self.assertEqual(result.missing_artifacts, ["final_job_manifest.json"])
        self.assertIs(manifest["artifact_presence"]["final_job_manifest"], False)

    def test_artifact_presence_is_deterministic(self):
        output_package_dir = self.build_output_package_dir()
        output_manifest_path = output_package_dir / "approved_output_manifest.json"

        build_approved_output_manifest(output_package_dir, output_manifest_path)
        first_manifest = read_json(output_manifest_path)
        build_approved_output_manifest(output_package_dir, output_manifest_path)
        second_manifest = read_json(output_manifest_path)

        self.assertEqual(
            first_manifest["artifact_presence"],
            second_manifest["artifact_presence"],
        )
        self.assertEqual(
            set(first_manifest["artifact_presence"]),
            {
                "approved_output_manifest",
                "delivery_summary",
                "approval_receipt",
                "spreadsheet_structural_report_json",
                "spreadsheet_structural_report_markdown",
                "final_job_manifest",
            },
        )

    def test_manifest_does_not_copy_raw_sentinel_value(self):
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        output_package_dir = self.build_output_package_dir(
            final_manifest_payload={"source_note": sentinel},
        )
        output_manifest_path = output_package_dir / "approved_output_manifest.json"

        build_approved_output_manifest(output_package_dir, output_manifest_path)

        self.assertNotIn(
            sentinel,
            output_manifest_path.read_text(encoding="utf-8"),
        )

    def test_manifest_is_non_authority(self):
        output_package_dir = self.build_output_package_dir()
        output_manifest_path = output_package_dir / "approved_output_manifest.json"

        build_approved_output_manifest(output_package_dir, output_manifest_path)
        manifest = read_json(output_manifest_path)

        self.assertEqual(manifest["authority"], "non_authority")
        self.assertTrue(manifest["boundaries"]["no_runtime_authority"])

    def test_execution_capability_not_introduced(self):
        output_package_dir = self.build_output_package_dir()
        output_manifest_path = output_package_dir / "approved_output_manifest.json"

        build_approved_output_manifest(output_package_dir, output_manifest_path)
        manifest = read_json(output_manifest_path)

        self.assertEqual(manifest["execution_capability"], "not_introduced")
        self.assertEqual(manifest["next_allowed_action"], "human_review_only")


if __name__ == "__main__":
    unittest.main()
