"""Tracer-bullet tests for HFX asset closure contracts."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.hfx_asset_closure import (
    HFXAssetClosure,
    build_hfx_asset_closure,
    render_hfx_asset_closure_markdown,
)
from kernel.runtime.hfx_gold_asset_standard import GOLD_ASSET_GATES


def valid_material() -> dict[str, object]:
    return {
        "closure_id": "hfx-008-closure-test",
        "asset_id": "HFX_008",
        "asset_name": "Energy Shockwave",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d13e9aa8f65c8b64d3da08b9a55ff5087b87beb3",
        "closure_status": "gold_complete",
        "evidence_gates": {gate: True for gate in GOLD_ASSET_GATES},
        "evidence_notes": ["Internal reusable asset gold gates are present."],
        "boundary_conditions": ["no_houdini_launch", "no_hython_execution", "no_render_execution"],
        "policy_version": "hfx-asset-closure-v1",
        "code_version": "0.1.0",
    }


class HFXAssetClosureTests(unittest.TestCase):
    def test_valid_closure_builds_deterministic_object(self):
        closure = build_hfx_asset_closure(valid_material())

        self.assertIsInstance(closure, HFXAssetClosure)
        self.assertEqual(closure.content_hash, digest_payload(closure.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_hfx_asset_closure(valid_material(), observed_at="one").content_hash,
            build_hfx_asset_closure(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        closure = build_hfx_asset_closure(valid_material())

        self.assertEqual(render_hfx_asset_closure_markdown(closure), render_hfx_asset_closure_markdown(closure))

    def test_missing_asset_id_fails_closed(self):
        material = valid_material()
        del material["asset_id"]

        with self.assertRaises(ValueError):
            build_hfx_asset_closure(material)

    def test_missing_evidence_gates_fail_closed(self):
        material = valid_material()
        del material["evidence_gates"]

        with self.assertRaises(ValueError):
            build_hfx_asset_closure(material)

    def test_gold_complete_blocked_if_preview_validation_or_shot_evidence_missing(self):
        for gate in ("preview_proof_exists", "validation_report_exists", "shot_binding_exists"):
            material = valid_material()
            material["evidence_gates"][gate] = False

            with self.assertRaises(ValueError):
                build_hfx_asset_closure(material)

    def test_generated_docs_exist(self):
        root = Path("assets/houdini/hfx_factory_core12/300_PRODUCTION_UPGRADE/HFX_008_ENERGY_SHOCKWAVE")

        self.assertTrue((root / "HFX_008_GOLD_CANDIDATE_CLOSURE.md").is_file())
        self.assertTrue((root / "HFX_008_GOLD_CANDIDATE_CLOSURE.json").is_file())

    def test_source_safety_passes(self):
        sources = [
            Path("kernel/runtime/hfx_asset_closure.py"),
            Path("tools/generate_hfx_008_gold_candidate_closure.py"),
        ]
        for source_path in sources:
            source = source_path.read_text(encoding="utf-8")
            for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
