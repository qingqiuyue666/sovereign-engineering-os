import importlib.util
import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
HOUDINI_ROOT = REPO_ROOT / "assets" / "houdini"
SYSTEM_STATE = "HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS"
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


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class HFXMasterPipelineBootstrapTests(unittest.TestCase):
    def test_all_twelve_layers_are_materialized_with_required_file_classes(self):
        for layer_name in LAYER_NAMES:
            with self.subTest(layer=layer_name):
                layer_dir = HOUDINI_ROOT / layer_name
                self.assertTrue(layer_dir.is_dir())
                self.assertTrue(list(layer_dir.glob("*.schema.json")))
                self.assertTrue(list(layer_dir.glob("*.contract.md")))
                self.assertTrue(list(layer_dir.glob("*validator.py")))
                self.assertTrue((layer_dir / "GLOBAL_SEAL.json").is_file())
                self.assertTrue((layer_dir / "GLOBAL_SEAL.contract.md").is_file())
                self.assertTrue((layer_dir / "global_seal_validator.py").is_file())
                self.assertTrue((layer_dir / "layer_manifest.json").is_file())

    def test_layer_global_seals_are_fail_closed_and_reference_existing_files(self):
        for layer_name in LAYER_NAMES:
            with self.subTest(layer=layer_name):
                layer_dir = HOUDINI_ROOT / layer_name
                seal = read_json(layer_dir / "GLOBAL_SEAL.json")
                self.assertEqual(seal["system_state"], SYSTEM_STATE)
                self.assertEqual(seal["maximum_allowed_state"], SYSTEM_STATE)
                self.assertEqual(seal["validation_policy"], "fail_closed")
                self.assertFalse(seal["final_pixels_authorized"])
                self.assertFalse(seal["client_delivery_authorized"])
                for file_name in seal["required_files"]:
                    self.assertTrue((layer_dir / file_name).exists(), file_name)

    def test_master_pipeline_seal_declares_no_final_pixels(self):
        master_seal = read_json(
            HOUDINI_ROOT / "hfx_master_pipeline_seal" / "HFX_MASTER_PIPELINE_GLOBAL_SEAL.json"
        )
        self.assertEqual(master_seal["system_state"], SYSTEM_STATE)
        self.assertEqual(master_seal["maximum_allowed_state"], SYSTEM_STATE)
        self.assertEqual(master_seal["output"], SYSTEM_STATE)
        self.assertEqual(master_seal["pipeline_root"], ".")
        self.assertEqual(master_seal["houdini_root"], "assets/houdini")
        self.assertEqual(len(master_seal["layers"]), 12)
        self.assertEqual(master_seal["final_pixel_gate"]["claim_policy"], "fail_closed")
        self.assertEqual(master_seal["final_pixel_gate"]["delivery_policy"], "blocked")
        self.assertTrue(master_seal["final_pixel_gate"]["real_exr_required"])
        self.assertFalse(master_seal["delivery_policy"]["client_delivery_allowed"])
        self.assertTrue(all(not layer["final_pixels_authorized"] for layer in master_seal["layers"]))

    def test_generated_schemas_are_json_schema_objects(self):
        for schema_path in sorted(HOUDINI_ROOT.glob("hfx_*/*.schema.json")):
            with self.subTest(schema=str(schema_path.relative_to(REPO_ROOT))):
                schema = read_json(schema_path)
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(schema["type"], "object")
                self.assertEqual(schema["additionalProperties"], False)
                self.assertIn("required", schema)
                self.assertIn("properties", schema)

    def test_generated_validators_compile_and_final_pixel_gate_blocks_claims(self):
        for validator_path in sorted(HOUDINI_ROOT.glob("hfx_*/*validator.py")):
            with self.subTest(validator=str(validator_path.relative_to(REPO_ROOT))):
                compile(validator_path.read_text(encoding="utf-8"), str(validator_path), "exec")

        gate_path = HOUDINI_ROOT / "hfx_final_pixel_gate_layer" / "final_pixel_claim_validator.py"
        spec = importlib.util.spec_from_file_location("hfx_final_pixel_claim_validator", gate_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.validate({"exr_paths": [], "verified_real_exrs": False})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "FINAL_PIXEL_CLAIM_BLOCKED")
        self.assertEqual(result["system_state"], SYSTEM_STATE)

    def test_scaffold_layers_do_not_commit_final_pixel_artifacts(self):
        forbidden_suffixes = {".exr", ".dpx", ".mov", ".mp4"}
        for layer_name in LAYER_NAMES:
            layer_dir = HOUDINI_ROOT / layer_name
            committed_media = [
                path
                for path in layer_dir.rglob("*")
                if path.is_file() and path.suffix.lower() in forbidden_suffixes
            ]
            self.assertEqual(committed_media, [])


if __name__ == "__main__":
    unittest.main()
