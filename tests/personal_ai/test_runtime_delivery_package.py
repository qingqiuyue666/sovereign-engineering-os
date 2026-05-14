import json
import tempfile
import unittest
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
        self.assertEqual(
            manifest["generated_output_xlsx_hash"],
            sha256_file(workbook_path),
        )
        self.assertEqual(
            [artifact["artifact_name"] for artifact in manifest["artifacts"]],
            sorted(artifact["artifact_name"] for artifact in manifest["artifacts"]),
        )
        self.assertTrue(validation["complete"])
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


if __name__ == "__main__":
    unittest.main()
