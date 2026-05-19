#!/usr/bin/env python3
"""Deterministic tests for the HFX Factory shot-binding layer."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


LAYER_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = LAYER_ROOT / "tools"
sys.dont_write_bytecode = True
sys.path.insert(0, TOOLS_ROOT.as_posix())

import hfx_shot_binding_lib as lib  # noqa: E402


class HFXShotBindingLayerTests(unittest.TestCase):
    def load_example(self, name: str) -> dict:
        path = LAYER_ROOT / "examples" / name
        return json.loads(path.read_text(encoding="utf-8"))

    def write_temp_request(self, request: dict, temp_dir: str, filename: str = "request.json") -> Path:
        request_path = Path(temp_dir) / filename
        request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return request_path

    def bind_example_to_temp(self, example_name: str) -> tuple[dict, str]:
        temp_context = tempfile.TemporaryDirectory()
        request = self.load_example(example_name)
        request["output_root"] = temp_context.name
        request_path = self.write_temp_request(request, temp_context.name)
        result = lib.bind_shot(request_path)
        self.addCleanup(temp_context.cleanup)
        return result, temp_context.name

    def test_factory_core12_global_seal_is_pass(self) -> None:
        factory = lib.validate_factory_core12()
        self.assertEqual(factory["global_seal"]["status"], "HFX_FACTORY_FINAL_GLOBAL_SEAL_PASS")
        self.assertTrue(factory["global_seal"]["validated"])

    def test_asset_registry_has_12_required_assets(self) -> None:
        factory = lib.validate_factory_core12()
        self.assertEqual(set(factory["assets"]), set(lib.REQUIRED_ASSETS))
        self.assertEqual(len(factory["assets"]), 12)

    def test_bind_energy_impact_package(self) -> None:
        result, _ = self.bind_example_to_temp("shot_request_energy_impact.json")
        manifest = lib.load_json(Path(result["manifest_path"]))
        self.assertEqual(result["status"], "HFX_SHOT_BINDING_PACKAGE_READY")
        self.assertEqual(len(manifest["asset_bindings"]), 6)

    def test_bind_portal_arrival_package(self) -> None:
        result, _ = self.bind_example_to_temp("shot_request_portal_arrival.json")
        manifest = lib.load_json(Path(result["manifest_path"]))
        self.assertEqual(result["status"], "HFX_SHOT_BINDING_PACKAGE_READY")
        self.assertEqual(len(manifest["asset_bindings"]), 7)

    def test_bind_black_hole_package(self) -> None:
        result, _ = self.bind_example_to_temp("shot_request_black_hole.json")
        manifest = lib.load_json(Path(result["manifest_path"]))
        self.assertEqual(result["status"], "HFX_SHOT_BINDING_PACKAGE_READY")
        self.assertEqual(len(manifest["asset_bindings"]), 5)

    def test_reject_unknown_asset_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            request = self.load_example("shot_request_energy_impact.json")
            request["output_root"] = temp_dir
            request["requested_assets"][0]["asset_id"] = "HFX_999"
            request_path = self.write_temp_request(request, temp_dir)
            with self.assertRaises(lib.HFXShotBindingError):
                lib.bind_shot(request_path)

    def test_reject_duplicate_asset_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            request = self.load_example("shot_request_energy_impact.json")
            request["output_root"] = temp_dir
            duplicate = copy.deepcopy(request["requested_assets"][0])
            request["requested_assets"].append(duplicate)
            request_path = self.write_temp_request(request, temp_dir)
            with self.assertRaises(lib.HFXShotBindingError):
                lib.bind_shot(request_path)

    def test_reject_invalid_frame_range(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            request = self.load_example("shot_request_energy_impact.json")
            request["output_root"] = temp_dir
            request["frame_start"] = 1100
            request["frame_end"] = 1001
            request_path = self.write_temp_request(request, temp_dir)
            with self.assertRaises(lib.HFXShotBindingError):
                lib.bind_shot(request_path)

    def test_reject_output_inside_release_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            request = self.load_example("shot_request_energy_impact.json")
            request["output_root"] = (
                lib.CORE12_ROOT / "300_PRODUCTION_UPGRADE" / "HFX_SHOT_BINDING_SHOULD_FAIL"
            ).as_posix()
            request_path = self.write_temp_request(request, temp_dir)
            with self.assertRaises(lib.HFXShotBindingError):
                lib.bind_shot(request_path)

    def test_release_hip_not_mutated(self) -> None:
        factory = lib.validate_factory_core12()
        source_hip = factory["assets"]["HFX_008"]["release_hip"]
        before = lib.sha256_file(source_hip)
        self.bind_example_to_temp("shot_request_energy_impact.json")
        after = lib.sha256_file(source_hip)
        self.assertEqual(before, after)

    def test_validate_generated_shot_package(self) -> None:
        result, _ = self.bind_example_to_temp("shot_request_energy_impact.json")
        report = lib.validate_shot_package(Path(result["package_root"]))
        self.assertEqual(report["status"], "PASS")

    def test_global_shot_binding_seal_pass(self) -> None:
        report = lib.run_global_shot_binding_seal()
        self.assertEqual(report["status"], "HFX_SHOT_BINDING_LAYER_GLOBAL_SEAL_PASS")
        self.assertTrue(report["validated"])


if __name__ == "__main__":
    unittest.main()
