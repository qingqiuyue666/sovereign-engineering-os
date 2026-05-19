"""Tracer-bullet tests for the HFX Core12 reality audit."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.hfx_core12_reality_audit import (
    HFX_CORE12_ASSETS,
    HFXCore12RealityAudit,
    build_hfx_core12_reality_audit,
    render_hfx_core12_reality_audit_markdown,
)


AUDIT_JSON = Path("assets/houdini/hfx_factory_core12/00_INDEX_资产索引/HFX_CORE12_REALITY_AUDIT.json")
AUDIT_MD = Path("assets/houdini/hfx_factory_core12/00_INDEX_资产索引/HFX_CORE12_REALITY_AUDIT.md")


def valid_asset(asset_id: str, asset_name: str, *, status: str = "production_candidate") -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "asset_name": asset_name,
        "source_files_present": True,
        "hip_files_present": True,
        "hda_files_present": asset_id == "HFX_008",
        "preview_docs_present": status == "gold_candidate",
        "preview_manifests_present": status == "gold_candidate",
        "mid_tier_present": True,
        "final_tier_present": True,
        "validation_reports_present": True,
        "sha256_manifest_present": True,
        "shot_binding_present": True,
        "render_or_comp_report_present": True,
        "empty_file_count": 0,
        "large_file_count_over_50mb": 0,
        "status": status,
    }


def valid_material() -> dict[str, object]:
    assets = []
    for spec in HFX_CORE12_ASSETS:
        status = "gold_candidate" if spec["asset_id"] == "HFX_008" else "production_candidate"
        assets.append(valid_asset(spec["asset_id"], spec["asset_name"], status=status))
    return {
        "audit_id": "hfx-core12-reality-audit-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d13e9aa8f65c8b64d3da08b9a55ff5087b87beb3",
        "source_root": "assets/houdini/hfx_factory_core12",
        "core12_assets": assets,
        "policy_version": "hfx-core12-reality-audit-v1",
        "code_version": "0.1.0",
    }


class HFXCore12RealityAuditTests(unittest.TestCase):
    def test_valid_audit_builds_deterministic_object(self):
        audit = build_hfx_core12_reality_audit(valid_material())

        self.assertIsInstance(audit, HFXCore12RealityAudit)
        self.assertEqual(audit.content_hash, digest_payload(audit.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_hfx_core12_reality_audit(valid_material(), observed_at="one").content_hash,
            build_hfx_core12_reality_audit(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_rendering_deterministic(self):
        audit = build_hfx_core12_reality_audit(valid_material())

        self.assertEqual(
            render_hfx_core12_reality_audit_markdown(audit),
            render_hfx_core12_reality_audit_markdown(audit),
        )

    def test_missing_audit_id_fails_closed(self):
        material = valid_material()
        del material["audit_id"]

        with self.assertRaises(ValueError):
            build_hfx_core12_reality_audit(material)

    def test_missing_asset_list_fails_closed(self):
        material = valid_material()
        del material["core12_assets"]

        with self.assertRaises(ValueError):
            build_hfx_core12_reality_audit(material)

    def test_invalid_asset_status_fails_closed(self):
        material = valid_material()
        material["core12_assets"][0]["status"] = "gold"

        with self.assertRaises(ValueError):
            build_hfx_core12_reality_audit(material)

    def test_gold_candidate_fails_closed_if_required_evidence_absent(self):
        material = valid_material()
        material["core12_assets"][0]["shot_binding_present"] = False

        with self.assertRaises(ValueError):
            build_hfx_core12_reality_audit(material)

    def test_generated_json_exists(self):
        self.assertTrue(AUDIT_JSON.is_file())

    def test_generated_markdown_exists(self):
        self.assertTrue(AUDIT_MD.is_file())

    def test_audit_lists_all_12_hfx_assets(self):
        payload = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
        asset_ids = [asset["asset_id"] for asset in payload["core12_assets"]]

        self.assertEqual(asset_ids, [spec["asset_id"] for spec in HFX_CORE12_ASSETS])

    def test_audit_reports_empty_file_counts(self):
        payload = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))

        self.assertTrue(all("empty_file_count" in asset for asset in payload["core12_assets"]))

    def test_audit_reports_large_file_counts(self):
        payload = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))

        self.assertTrue(all("large_file_count_over_50mb" in asset for asset in payload["core12_assets"]))

    def test_runtime_source_safety_passes(self):
        sources = [
            Path("kernel/runtime/hfx_core12_reality_audit.py"),
            Path("tools/generate_hfx_core12_reality_audit.py"),
        ]
        for source_path in sources:
            source = source_path.read_text(encoding="utf-8")
            for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
