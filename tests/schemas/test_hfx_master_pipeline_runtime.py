import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
HOUDINI_ROOT = REPO_ROOT / "assets" / "houdini"
SYSTEM_STATE = "HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS"
PASS_STATE = "HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS_PASS"
LAYER_NAMES = [
    "hfx_assetization_layer",
    "hfx_aov_pass_contract_layer",
    "hfx_resource_library_layer",
    "hfx_lookdev_shader_contract_layer",
    "hfx_plate_camera_integration_layer",
    "hfx_render_automation_layer",
    "hfx_comp_automation_layer",
    "hfx_color_management_layer",
    "hfx_review_dailies_layer",
    "hfx_final_pixel_gate_layer",
    "hfx_delivery_package_layer",
    "hfx_master_pipeline_seal",
]
MASTER_OUTPUTS = [
    "HFX_MASTER_PIPELINE_VALIDATION_REPORT.json",
    "HFX_MASTER_PIPELINE_VALIDATION_REPORT.md",
    "HFX_MASTER_PIPELINE_MANIFEST.json",
    "HFX_MASTER_PIPELINE_SHA256SUMS.txt",
    "HFX_MASTER_PIPELINE_FILE_TREE.txt",
]


def mutable_runtime_outputs():
    outputs = [
        HOUDINI_ROOT / layer_name / "GLOBAL_SEAL_VALIDATION.json"
        for layer_name in LAYER_NAMES
    ]
    outputs.extend(
        HOUDINI_ROOT / "hfx_master_pipeline_seal" / file_name
        for file_name in MASTER_OUTPUTS
    )
    return outputs


def snapshot_outputs(paths):
    snapshot = {}
    for path in paths:
        snapshot[path] = path.read_bytes() if path.exists() else None
    return snapshot


def restore_outputs(snapshot):
    for path, payload in snapshot.items():
        if payload is None:
            if path.exists():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_python(path):
    return subprocess.run(
        [sys.executable, str(path)],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=True,
    )


def run_master_validator():
    validator = HOUDINI_ROOT / "hfx_master_pipeline_seal" / "hfx_master_pipeline_validate.py"
    result = run_python(validator)
    assert PASS_STATE in result.stdout
    return read_json(HOUDINI_ROOT / "hfx_master_pipeline_seal" / "HFX_MASTER_PIPELINE_VALIDATION_REPORT.json")


class HFXMasterPipelineRuntimeTests(unittest.TestCase):
    def setUp(self):
        self._output_snapshot = snapshot_outputs(mutable_runtime_outputs())

    def tearDown(self):
        restore_outputs(self._output_snapshot)

    def test_all_twelve_layer_directories_exist(self):
        for layer_name in LAYER_NAMES:
            with self.subTest(layer=layer_name):
                self.assertTrue((HOUDINI_ROOT / layer_name).is_dir())

    def test_each_layer_has_manifest_seal_and_validator(self):
        for layer_name in LAYER_NAMES:
            with self.subTest(layer=layer_name):
                layer_dir = HOUDINI_ROOT / layer_name
                self.assertTrue((layer_dir / "layer_manifest.json").is_file())
                self.assertTrue((layer_dir / "GLOBAL_SEAL.json").is_file())
                self.assertTrue((layer_dir / "GLOBAL_SEAL.contract.md").is_file())
                self.assertTrue((layer_dir / "global_seal_validator.py").is_file())
                self.assertTrue((layer_dir / "GLOBAL_SEAL_VALIDATION.json").is_file())
                self.assertTrue((layer_dir / "fixtures" / "pass_minimal_no_final_pixels.json").is_file())
                self.assertTrue((layer_dir / "fixtures" / "fail_forbidden_final_pixel_claim.json").is_file())

    def test_each_layer_global_validator_passes_without_final_pixels(self):
        for layer_name in LAYER_NAMES:
            with self.subTest(layer=layer_name):
                layer_dir = HOUDINI_ROOT / layer_name
                result = run_python(layer_dir / "global_seal_validator.py")
                self.assertEqual(result.stdout.strip(), "PASS")
                report = read_json(layer_dir / "GLOBAL_SEAL_VALIDATION.json")
                self.assertEqual(report["status"], "PASS")
                self.assertEqual(report["system_state"], SYSTEM_STATE)
                self.assertFalse(report["final_pixels_authorized"])
                self.assertFalse(report["client_delivery_allowed"])

    def test_master_pipeline_validator_passes_no_final_pixels(self):
        report = run_master_validator()
        self.assertEqual(report["status"], PASS_STATE)
        self.assertEqual(report["system_state"], SYSTEM_STATE)
        self.assertEqual(report["output"], SYSTEM_STATE)
        self.assertFalse(report["final_pixels_authorized"])
        self.assertFalse(report["client_delivery_allowed"])
        self.assertEqual(report["final_pixel_gate"]["claim_policy"], "fail_closed")
        self.assertTrue(report["final_pixel_gate"]["real_exr_required"])

    def test_final_pixel_claim_remains_blocked(self):
        module = load_module(
            HOUDINI_ROOT / "hfx_final_pixel_gate_layer" / "final_pixel_claim_validator.py",
            "final_pixel_claim_validator",
        )
        result = module.validate({"exr_paths": ["metadata_only.exr"], "verified_real_exrs": True})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "FINAL_PIXEL_CLAIM_BLOCKED")
        self.assertFalse(result["final_pixels_authorized"])
        self.assertFalse(result["metadata_only_authorized"])

    def test_client_delivery_remains_blocked(self):
        module = load_module(
            HOUDINI_ROOT / "hfx_delivery_package_layer" / "client_delivery_blocker.py",
            "client_delivery_blocker",
        )
        result = module.validate({"delivery_id": "attempted_delivery"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "CLIENT_DELIVERY_BLOCKED")
        self.assertFalse(result["client_delivery_allowed"])
        self.assertFalse(result["public_delivery_allowed"])

    def test_core12_and_shot_binding_references_do_not_enable_final_pixels(self):
        report = run_master_validator()
        references = {reference["label"]: reference for reference in report["references"]}
        self.assertIn("Core 12 factory global seal", references)
        self.assertIn("Shot Binding Layer global seal", references)
        for reference in references.values():
            self.assertFalse(reference["final_pixels_authorized"])
        self.assertFalse(report["final_pixels_authorized"])
        self.assertFalse(report["client_delivery_allowed"])

    def test_master_pipeline_manifest_and_checksums_exist(self):
        run_master_validator()
        output_dir = HOUDINI_ROOT / "hfx_master_pipeline_seal"
        for file_name in MASTER_OUTPUTS:
            with self.subTest(file=file_name):
                path = output_dir / file_name
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 0)
        manifest = read_json(output_dir / "HFX_MASTER_PIPELINE_MANIFEST.json")
        self.assertEqual(manifest["status"], PASS_STATE)
        self.assertEqual(manifest["layer_count"], 12)

    def test_no_final_pixel_ready_state_is_claimed_anywhere_in_master_outputs(self):
        run_master_validator()
        output_dir = HOUDINI_ROOT / "hfx_master_pipeline_seal"
        forbidden_tokens = [
            "HFX_MASTER_PIPELINE_FINAL_PIXEL_READY",
            "FINAL_PIXEL_READY",
            "CLIENT_DELIVERY_READY",
        ]
        for file_name in MASTER_OUTPUTS:
            text = (output_dir / file_name).read_text(encoding="utf-8")
            for token in forbidden_tokens:
                with self.subTest(file=file_name, token=token):
                    self.assertNotIn(token, text)

    def test_no_release_hip_files_modified_by_this_branch(self):
        base_ref = "origin/main"
        if subprocess.run(
            ["git", "rev-parse", "--verify", base_ref],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        ).returncode != 0:
            base_ref = "main"
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref + "...HEAD"],
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
            check=True,
        )
        modified_core12_hips = [
            path
            for path in result.stdout.splitlines()
            if path.startswith("assets/houdini/hfx_factory_core12/") and path.endswith(".hip")
        ]
        self.assertEqual(modified_core12_hips, [])


if __name__ == "__main__":
    unittest.main()
