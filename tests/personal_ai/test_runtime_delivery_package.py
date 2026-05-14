import json
import tempfile
import unittest
import uuid
from pathlib import Path

from openpyxl import Workbook

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically
from kernel.personal_ai.runtime_delivery_package import (
    build_runtime_delivery_package,
    validate_runtime_delivery_package,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class RuntimeDeliveryPackageTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        runtime_dir = root / "runtime"
        package_root = root / "packages"
        input_dir.mkdir()
        runtime_dir.mkdir()
        package_root.mkdir()
        workbook_path = runtime_dir / "derived_xlsx_summary.xlsx"
        workbook = Workbook()
        workbook.active["A1"] = "metadata only"
        workbook.save(workbook_path)

        write_json_atomically(
            runtime_dir / "xlsx_inspection.json",
            {
                "inspection_type": "personal_ai_execution_os_v2_xlsx_readonly_inspection",
                "raw_cell_values_copied": False,
            },
        )
        write_markdown_atomically(
            runtime_dir / "xlsx_inspection_summary.md",
            "raw cell values copied: false\n",
        )
        write_json_atomically(
            runtime_dir / "xlsx_output_manifest.json",
            {
                "manifest_type": "personal_ai_execution_os_v2_xlsx_output_manifest",
                "input_sha256": "0" * 64,
                "plan_sha256": "1" * 64,
                "approval_sha256": "2" * 64,
                "xlsx_inspection_sha256": sha256_file(
                    runtime_dir / "xlsx_inspection.json"
                ),
                "output_workbook_path": workbook_path.as_posix(),
                "output_workbook_sha256": sha256_file(workbook_path),
            },
        )
        write_json_atomically(
            runtime_dir / "xlsx_output_validation.json",
            {"complete": True, "raw_value_leakage_detected": False},
        )
        write_json_atomically(
            runtime_dir / "model_inference_artifact.json",
            {"artifact_type": "personal_ai_execution_os_v2_model_inference_artifact"},
        )
        write_json_atomically(
            runtime_dir / "browser_action_log.json",
            {"log_type": "personal_ai_execution_os_v2_browser_action_log"},
        )
        write_json_atomically(
            runtime_dir / "browser_evidence_manifest.json",
            {"manifest_type": "personal_ai_execution_os_v2_browser_evidence_manifest"},
        )
        return input_dir, runtime_dir, package_root, workbook_path

    def test_builds_runtime_delivery_package_with_hash_bound_manifest(self):
        input_dir, runtime_dir, package_root, workbook_path = self.build_workspace()

        result = build_runtime_delivery_package(
            runtime_dir,
            package_root,
            package_id="runtime-delivery-001",
            input_dir=input_dir,
        )
        manifest = read_json(result.runtime_delivery_manifest_path)
        validation = read_json(result.runtime_delivery_validation_path)

        self.assertTrue(result.complete)
        self.assertFalse(result.raw_value_leakage_detected)
        self.assertIn("generated_output_xlsx", result.packaged_artifacts)
        self.assertTrue(manifest["delivery_policy"]["requires_replay_verification"])
        self.assertFalse(manifest["delivery_policy"]["raw_derived_allowed"])
        self.assertEqual(
            manifest["artifact_order"],
            sorted(manifest["artifact_order"]),
        )
        self.assertEqual(manifest["artifact_count"], len(manifest["artifacts"]))
        self.assertEqual(
            manifest["package_replay"]["artifact_set_sha256"],
            read_json(result.runtime_delivery_validation_path)
            and manifest["package_replay"]["artifact_set_sha256"],
        )
        artifact_categories = {
            artifact["artifact_name"]: artifact["output_category"]
            for artifact in manifest["artifacts"]
        }
        self.assertEqual(artifact_categories["generated_output_xlsx"], "derived_data")
        self.assertEqual(artifact_categories["xlsx_inspection_json"], "metadata_only")
        self.assertEqual(
            manifest["generated_output_xlsx_hash"],
            sha256_file(workbook_path),
        )
        self.assertEqual(
            [artifact["artifact_name"] for artifact in manifest["artifacts"]],
            sorted(artifact["artifact_name"] for artifact in manifest["artifacts"]),
        )
        self.assertTrue(validation["complete"])
        self.assertTrue(validation["artifact_hashes_verified"])
        self.assertTrue(validation["package_replay_verified"])
        self.assertTrue(validation["policy_verified"])
        self.assertIn("approval_sha256", manifest["provenance_chain_references"])

    def test_refuses_overwrite_and_output_inside_input_dir(self):
        input_dir, runtime_dir, package_root, _ = self.build_workspace()
        (package_root / "runtime-delivery-001").mkdir()

        with self.assertRaises(ValueError):
            build_runtime_delivery_package(
                runtime_dir,
                package_root,
                package_id="runtime-delivery-001",
                input_dir=input_dir,
            )

        unsafe_root = input_dir / "packages"
        unsafe_root.mkdir()
        with self.assertRaises(ValueError):
            build_runtime_delivery_package(
                runtime_dir,
                unsafe_root,
                package_id="runtime-delivery-002",
                input_dir=input_dir,
            )

    def test_validation_detects_raw_value_leakage(self):
        _, runtime_dir, package_root, _ = self.build_workspace()
        result = build_runtime_delivery_package(
            runtime_dir,
            package_root,
            package_id="runtime-delivery-001",
        )
        leaked = result.package_dir / "leak.json"
        write_json_atomically(leaked, {"value": "RAW_CELL_SECRET"})
        rerun_path = package_root / "rerun_validation.json"

        validation = validate_runtime_delivery_package(result.package_dir, rerun_path)

        self.assertFalse(validation.complete)
        self.assertTrue(validation.raw_value_leakage_detected)

    def test_validation_detects_dynamic_raw_sentinel_leakage(self):
        _, runtime_dir, package_root, _ = self.build_workspace()
        result = build_runtime_delivery_package(
            runtime_dir,
            package_root,
            package_id="runtime-delivery-001",
        )
        dynamic_sentinel = "secret_" + uuid.uuid4().hex
        write_markdown_atomically(result.package_dir / "notes.md", dynamic_sentinel)
        rerun_path = package_root / "dynamic_validation.json"

        validation = validate_runtime_delivery_package(
            result.package_dir,
            rerun_path,
            raw_sentinel_values=[dynamic_sentinel],
        )
        validation_payload = read_json(rerun_path)

        self.assertFalse(validation.complete)
        self.assertTrue(validation.raw_value_leakage_detected)
        self.assertTrue(validation_payload["raw_value_leakage_detected"])

    def test_validation_detects_tampered_artifact_and_replay_mismatch(self):
        _, runtime_dir, package_root, _ = self.build_workspace()
        result = build_runtime_delivery_package(
            runtime_dir,
            package_root,
            package_id="runtime-delivery-001",
        )
        copied_artifact = result.package_dir / "model_inference_artifact.json"
        write_json_atomically(
            copied_artifact,
            {"artifact_type": "personal_ai_execution_os_v2_model_inference_artifact", "tampered": True},
        )
        rerun_path = package_root / "tamper_validation.json"

        validation = validate_runtime_delivery_package(result.package_dir, rerun_path)
        validation_payload = read_json(rerun_path)

        self.assertFalse(validation.complete)
        self.assertIn("model_inference_artifact", validation_payload["hash_mismatches"])
        self.assertFalse(validation_payload["package_replay_verified"])

    def test_validation_rejects_malformed_manifest_schema(self):
        _, runtime_dir, package_root, _ = self.build_workspace()
        result = build_runtime_delivery_package(
            runtime_dir,
            package_root,
            package_id="runtime-delivery-001",
        )
        manifest = read_json(result.runtime_delivery_manifest_path)
        manifest.pop("artifact_hashes")
        result.runtime_delivery_manifest_path.write_text(
            json.dumps(manifest, sort_keys=True), encoding="utf-8"
        )

        with self.assertRaisesRegex(ValueError, "artifact_hashes malformed"):
            validate_runtime_delivery_package(
                result.package_dir,
                package_root / "malformed_validation.json",
            )

    def test_validation_enforces_raw_derived_policy_gate(self):
        _, runtime_dir, package_root, _ = self.build_workspace()
        result = build_runtime_delivery_package(
            runtime_dir,
            package_root,
            package_id="runtime-delivery-001",
        )
        manifest = read_json(result.runtime_delivery_manifest_path)
        for artifact in manifest["artifacts"]:
            if artifact["artifact_name"] == "browser_evidence_manifest":
                artifact["output_category"] = "raw_derived"
        result.runtime_delivery_manifest_path.write_text(
            json.dumps(manifest, sort_keys=True), encoding="utf-8"
        )
        rerun_path = package_root / "policy_validation.json"

        validation = validate_runtime_delivery_package(result.package_dir, rerun_path)
        validation_payload = read_json(rerun_path)

        self.assertFalse(validation.complete)
        self.assertFalse(validation_payload["policy_verified"])
        self.assertIn(
            "browser_evidence_manifest:raw_derived",
            validation_payload["policy_failures"],
        )


if __name__ == "__main__":
    unittest.main()
