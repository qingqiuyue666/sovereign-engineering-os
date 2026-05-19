"""Tracer-bullet tests for the HFX gold asset standard."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.hfx_gold_asset_standard import (
    GOLD_ASSET_GATES,
    HFXGoldAssetStandard,
    build_hfx_gold_asset_standard,
    render_hfx_gold_asset_standard_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "standard_id": "hfx-gold-standard-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d13e9aa8f65c8b64d3da08b9a55ff5087b87beb3",
        "gold_gates": {gate: True for gate in GOLD_ASSET_GATES},
        "standard_notes": ["Gold status is allowed only when every hard gate is true."],
        "blocked_claims": ["No fake film-grade claim is allowed."],
        "gold_status_decision": "gold_allowed",
        "policy_version": "hfx-gold-asset-standard-v1",
        "code_version": "0.1.0",
    }


class HFXGoldAssetStandardTests(unittest.TestCase):
    def test_valid_standard_builds_deterministic_object(self):
        standard = build_hfx_gold_asset_standard(valid_material())

        self.assertIsInstance(standard, HFXGoldAssetStandard)
        self.assertEqual(standard.content_hash, digest_payload(standard.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_hfx_gold_asset_standard(valid_material(), observed_at="one").content_hash,
            build_hfx_gold_asset_standard(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        standard = build_hfx_gold_asset_standard(valid_material())

        self.assertEqual(
            render_hfx_gold_asset_standard_markdown(standard),
            render_hfx_gold_asset_standard_markdown(standard),
        )

    def test_missing_standard_id_fails_closed(self):
        material = valid_material()
        del material["standard_id"]

        with self.assertRaises(ValueError):
            build_hfx_gold_asset_standard(material)

    def test_incomplete_gate_blocks_gold(self):
        material = valid_material()
        material["gold_gates"]["preview_proof_exists"] = False

        with self.assertRaises(ValueError):
            build_hfx_gold_asset_standard(material)

    def test_external_unlicensed_dependency_blocks_gold(self):
        material = valid_material()
        material["gold_gates"]["no_unlicensed_third_party_raw_asset_dependency"] = False

        with self.assertRaises(ValueError):
            build_hfx_gold_asset_standard(material)

    def test_fake_film_grade_claim_blocks_gold(self):
        material = valid_material()
        material["gold_gates"]["no_fake_film_grade_claim"] = False

        with self.assertRaises(ValueError):
            build_hfx_gold_asset_standard(material)

    def test_generated_standard_doc_exists(self):
        self.assertTrue(Path("assets/houdini/hfx_factory_core12/00_INDEX_资产索引/HFX_GOLD_ASSET_STANDARD.md").is_file())

    def test_source_safety_passes(self):
        source = Path("kernel/runtime/hfx_gold_asset_standard.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
