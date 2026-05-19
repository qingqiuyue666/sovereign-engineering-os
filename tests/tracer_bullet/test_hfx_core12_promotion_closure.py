"""Tracer-bullet tests for HFX Core12 promotion closure contracts."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.hfx_core12_promotion_closure import (
    HFXCore12PromotionClosure,
    HFX_CORE12_PROMOTION_ASSET_IDS,
    build_hfx_core12_promotion_closure,
    render_hfx_core12_promotion_closure_markdown,
)
from kernel.runtime.hfx_core12_reality_audit import HFX_CORE12_ASSETS


def evidence(present: bool = True, summary: str = "Evidence record exists.") -> dict[str, object]:
    return {"present": present, "summary": summary, "paths": ["assets/houdini/hfx_factory_core12/00_INDEX_资产索引"]}


def route(present: bool = True) -> dict[str, object]:
    return {
        "present": present,
        "route_id": "hfx-test-route",
        "trigger": "Evidence mismatch or promotion gate failure.",
        "action": "Return to candidate state and preserve existing evidence records.",
        "safe_state": "No generated render output and no mutable source asset change.",
    }


def valid_material(*, decision: str = "gold_complete") -> dict[str, object]:
    render_present = decision != "production_complete_pending_shot_proof"
    return {
        "asset_id": "HFX_008",
        "asset_name": "Energy Shockwave",
        "current_reality_status": "gold_complete",
        "target_promotion_status": decision,
        "hip_or_hda_evidence": evidence(),
        "preview_evidence": evidence(),
        "validation_evidence": evidence(),
        "checksum_evidence": evidence(),
        "manifest_evidence": evidence(),
        "shot_binding_evidence": evidence(),
        "render_or_comp_evidence": evidence(render_present, "Final proof is pending." if not render_present else "Proof exists."),
        "rollback_route": route(),
        "quarantine_route": route(),
        "external_asset_dependency_status": {
            "status": "internal_only",
            "declaration": "No external raw asset dependency is required for this closure.",
            "unlicensed_external_dependency": False,
        },
        "missing_gates": [] if render_present else ["render_or_comp_evidence"],
        "next_required_actions": ["Keep final status behind reviewed proof gates."],
        "promotion_decision": decision,
        "policy_version": "hfx-core12-promotion-closure-v1",
        "code_version": "0.1.0",
    }


class HFXCore12PromotionClosureTests(unittest.TestCase):
    def test_valid_per_asset_closure_builds_deterministic_object(self):
        closure = build_hfx_core12_promotion_closure(valid_material())

        self.assertIsInstance(closure, HFXCore12PromotionClosure)
        self.assertEqual(closure.content_hash, digest_payload(closure.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_hfx_core12_promotion_closure(valid_material(), observed_at="one").content_hash,
            build_hfx_core12_promotion_closure(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_rendering_deterministic(self):
        closure = build_hfx_core12_promotion_closure(valid_material())

        self.assertEqual(
            render_hfx_core12_promotion_closure_markdown(closure),
            render_hfx_core12_promotion_closure_markdown(closure),
        )

    def test_missing_asset_id_fails_closed(self):
        material = valid_material()
        del material["asset_id"]

        with self.assertRaises(ValueError):
            build_hfx_core12_promotion_closure(material)

    def test_invalid_promotion_decision_fails_closed(self):
        material = valid_material()
        material["target_promotion_status"] = "complete"
        material["promotion_decision"] = "complete"

        with self.assertRaises(ValueError):
            build_hfx_core12_promotion_closure(material)

    def test_missing_rollback_or_quarantine_blocks_production_complete(self):
        for field in ("rollback_route", "quarantine_route"):
            material = valid_material(decision="production_complete")
            material[field] = route(False)

            with self.assertRaises(ValueError):
                build_hfx_core12_promotion_closure(material)

    def test_missing_shot_render_comp_proof_blocks_gold_complete(self):
        material = valid_material()
        material["render_or_comp_evidence"] = evidence(False, "Final proof remains planned.")

        with self.assertRaises(ValueError):
            build_hfx_core12_promotion_closure(material)

    def test_fake_film_grade_claim_blocks_complete_decisions(self):
        material = valid_material(decision="production_complete")
        material["next_required_actions"] = ["film-grade complete"]

        with self.assertRaises(ValueError):
            build_hfx_core12_promotion_closure(material)

    def test_unlicensed_external_dependency_blocks_complete_decisions(self):
        material = valid_material(decision="production_complete")
        material["external_asset_dependency_status"]["unlicensed_external_dependency"] = True

        with self.assertRaises(ValueError):
            build_hfx_core12_promotion_closure(material)

    def test_forbidden_raw_env_secret_fields_fail_closed(self):
        material = valid_material()
        material["raw_prompt"] = "forbidden"

        with self.assertRaises(ValueError):
            build_hfx_core12_promotion_closure(material)

    def test_source_safety_passes(self):
        source = Path("kernel/runtime/hfx_core12_promotion_closure.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)

    def test_all_12_asset_ids_are_accepted(self):
        names = {asset["asset_id"]: asset["asset_name"] for asset in HFX_CORE12_ASSETS}

        for asset_id in HFX_CORE12_PROMOTION_ASSET_IDS:
            material = valid_material(decision="production_complete_pending_shot_proof")
            material["asset_id"] = asset_id
            material["asset_name"] = names[asset_id]
            material["current_reality_status"] = "production_candidate"
            closure = build_hfx_core12_promotion_closure(material)

            self.assertEqual(closure.asset_id, asset_id)


if __name__ == "__main__":
    unittest.main()
