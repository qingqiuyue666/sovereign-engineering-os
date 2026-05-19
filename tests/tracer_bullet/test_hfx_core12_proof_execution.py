"""Tracer-bullet tests for the HFX Core12 proof execution contract."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.hfx_core12_proof_execution import (
    HFXCore12ProofExecution,
    HFX_CORE12_PROOF_ASSET_IDS,
    build_hfx_core12_proof_execution,
    render_hfx_core12_proof_execution_markdown,
)
from kernel.runtime.hfx_core12_reality_audit import HFX_CORE12_ASSETS


REPOSITORY_URL = "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os"


def valid_material() -> dict[str, object]:
    assets = []
    packages = []
    for spec in HFX_CORE12_ASSETS:
        asset_id = spec["asset_id"]
        asset_name = spec["asset_name"]
        package_path = (
            "assets/houdini/hfx_factory_core12/600_PROOF_EXECUTION/"
            f"HFX_CORE12_FULL_PROOF_RUN_001/{asset_id}_PACKAGE/proof_package.json"
        )
        assets.append(
            {
                "asset_id": asset_id,
                "asset_name": asset_name,
                "proof_package_path": package_path,
            }
        )
        packages.append(
            {
                "asset_id": asset_id,
                "asset_name": asset_name,
                "proof_package_status": "package_created",
                "promotion_closure_path": f"assets/houdini/hfx_factory_core12/300_PRODUCTION_UPGRADE/{asset_id}/PROMOTION_CLOSURE.json",
                "rollback_quarantine_route_path": "assets/houdini/hfx_factory_core12/00_INDEX_资产索引/HFX_CORE12_ROLLBACK_QUARANTINE_ROUTES.json",
                "shot_render_proof_plan_path": "assets/houdini/hfx_factory_core12/00_INDEX_资产索引/HFX_CORE12_SHOT_RENDER_PROOF_PLAN.json",
                "shot_proof_status": "package_created",
                "render_proof_status": "package_created",
                "comp_proof_status": "package_created",
                "review_status": "package_created",
                "acceptance_decision": "pending_execution",
                "expected_artifacts": ["shot binding receipt", "render manifest", "comp review notes"],
                "missing_proof_artifacts": ["actual shot proof", "actual render proof", "actual comp review"],
                "minimum_shot_proof_checklist": ["Bind asset to named shot and frame range."],
                "minimum_render_proof_checklist": ["Render proof artifact with deterministic manifest."],
                "minimum_comp_review_checklist": ["Review composite integration against acceptance criteria."],
                "acceptance_criteria": ["All shot, render, and comp proof artifacts are executed and reviewed."],
                "rejection_criteria": ["Missing actual proof artifact blocks acceptance."],
                "quarantine_trigger": "Unsafe proof claim, missing artifact, or unlicensed dependency.",
                "rollback_trigger": "Proof artifact mismatch or failed review.",
                "final_claim_allowed": False,
                "actual_proof_artifacts": [],
                "external_asset_dependency_status": {
                    "status": "internal_only_external_friend_assets_deferred",
                    "declaration": "No external asset dependency is enabled for this proof package.",
                    "unlicensed_external_dependency": False,
                },
            }
        )
    return {
        "proof_run_id": "HFX_CORE12_FULL_PROOF_RUN_001",
        "repository_url": REPOSITORY_URL,
        "main_commit": "36bf95e637bab87542086f1ee44edf862c22dd6c",
        "core12_assets": assets,
        "per_asset_proof_package": packages,
        "shot_proof_status": "package_created",
        "render_proof_status": "package_created",
        "comp_proof_status": "package_created",
        "review_status": "package_created",
        "acceptance_decision": "pending_execution",
        "rejection_reasons": [],
        "quarantine_decision": "not_triggered_pending_execution",
        "rollback_decision": "not_triggered_pending_execution",
        "final_claim_allowed": False,
        "remaining_gates": [
            "actual_shot_execution_for_all_12_assets",
            "actual_render_execution_for_all_12_assets",
            "actual_comp_execution_for_all_12_assets",
            "reviewed_acceptance_for_all_12_assets",
        ],
        "policy_version": "hfx-core12-proof-execution-v1",
        "code_version": "0.1.0",
    }


class HFXCore12ProofExecutionTests(unittest.TestCase):
    def test_valid_proof_package_builds_deterministic_object(self):
        proof = build_hfx_core12_proof_execution(valid_material())

        self.assertIsInstance(proof, HFXCore12ProofExecution)
        self.assertEqual(proof.content_hash, digest_payload(proof.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_hfx_core12_proof_execution(valid_material(), observed_at="one").content_hash,
            build_hfx_core12_proof_execution(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_rendering_deterministic(self):
        proof = build_hfx_core12_proof_execution(valid_material())

        self.assertEqual(
            render_hfx_core12_proof_execution_markdown(proof),
            render_hfx_core12_proof_execution_markdown(proof),
        )

    def test_missing_proof_run_id_fails_closed(self):
        material = valid_material()
        del material["proof_run_id"]

        with self.assertRaises(ValueError):
            build_hfx_core12_proof_execution(material)

    def test_missing_asset_id_fails_closed(self):
        material = valid_material()
        del material["per_asset_proof_package"][0]["asset_id"]

        with self.assertRaises(ValueError):
            build_hfx_core12_proof_execution(material)

    def test_invalid_proof_status_fails_closed(self):
        material = valid_material()
        material["render_proof_status"] = "planned_not_executed"

        with self.assertRaises(ValueError):
            build_hfx_core12_proof_execution(material)

    def test_planned_only_proof_blocks_final_claim_allowed(self):
        material = valid_material()
        material["final_claim_allowed"] = True

        with self.assertRaises(ValueError):
            build_hfx_core12_proof_execution(material)

    def test_fake_hollywood_final_pixel_claim_fails_closed(self):
        material = valid_material()
        material["per_asset_proof_package"][0]["rejection_criteria"].append("Hollywood final-pixel complete.")

        with self.assertRaises(ValueError):
            build_hfx_core12_proof_execution(material)

    def test_unlicensed_external_dependency_blocks_acceptance(self):
        material = valid_material()
        material["shot_proof_status"] = "proof_reviewed"
        material["render_proof_status"] = "proof_reviewed"
        material["comp_proof_status"] = "proof_reviewed"
        material["review_status"] = "proof_reviewed"
        material["acceptance_decision"] = "accepted_for_internal_library"
        for package in material["per_asset_proof_package"]:
            package["shot_proof_status"] = "proof_reviewed"
            package["render_proof_status"] = "proof_reviewed"
            package["comp_proof_status"] = "proof_reviewed"
            package["review_status"] = "proof_reviewed"
            package["acceptance_decision"] = "accepted_for_internal_library"
        material["per_asset_proof_package"][0]["external_asset_dependency_status"][
            "unlicensed_external_dependency"
        ] = True

        with self.assertRaises(ValueError):
            build_hfx_core12_proof_execution(material)

    def test_forbidden_raw_env_secret_fields_fail_closed(self):
        material = valid_material()
        material["raw_artifact_dump"] = "forbidden"

        with self.assertRaises(ValueError):
            build_hfx_core12_proof_execution(material)

    def test_all_12_asset_ids_are_accepted(self):
        proof = build_hfx_core12_proof_execution(valid_material())

        self.assertEqual(
            [asset["asset_id"] for asset in proof.core12_assets],
            list(HFX_CORE12_PROOF_ASSET_IDS),
        )

    def test_source_safety_passes(self):
        source = Path("kernel/runtime/hfx_core12_proof_execution.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
