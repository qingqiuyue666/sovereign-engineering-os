"""Tests for production code stage pack manifest integrity."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MANIFEST_PATH = ROOT / "governance" / "local_train" / "production_code_stage_pack_manifest_v1.json"
READINESS_PATH = ROOT / "docs" / "runbooks" / "production_code_stage_pack_integration_readiness_v1.md"

EXPECTED_STAGES = [
    "patch_application_pipeline",
    "local_execution_kernel",
    "evidence_vault_foundation",
    "replay_engine_foundation",
    "provider_transport_boundary",
    "operator_daily_run_foundation",
    "alert_delivery_foundation",
    "osint_ingestion_foundation",
    "asset_mapping_foundation",
    "decision_engine_foundation",
    "recovery_rollback_foundation",
    "checkpoint_runtime_foundation",
    "run_ledger_hardening_foundation",
    "evidence_index_foundation",
    "decision_report_foundation",
    "local_operator_cli_extension_foundation",
]


class ProductionCodeStagePackManifestTests(unittest.TestCase):

    def test_manifest_exists(self):
        self.assertTrue(MANIFEST_PATH.is_file())

    def test_readiness_report_exists(self):
        self.assertTrue(READINESS_PATH.is_file())

    def test_manifest_is_valid_json(self):
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["manifest_name"], "production_code_stage_pack_manifest_v1")
        self.assertEqual(data["status"], "active")
        self.assertEqual(data["total_stages"], 16)

    def test_manifest_lists_all_16_stages(self):
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        stage_ids = [s["stage_id"] for s in data["stages"]]
        self.assertEqual(len(stage_ids), 16)
        for expected in EXPECTED_STAGES:
            self.assertIn(expected, stage_ids, f"Missing stage: {expected}")

    def test_all_stages_are_contract_only(self):
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        for stage in data["stages"]:
            self.assertEqual(stage["status"], "contract-only",
                             f"{stage['stage_id']} should be contract-only")
            self.assertTrue(stage["no_real_side_effects"],
                            f"{stage['stage_id']} should have no_real_side_effects")

    def test_each_stage_has_all_artifact_paths(self):
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        for stage in data["stages"]:
            for key in ["generator", "module", "registry", "policy", "runbook", "test"]:
                path = ROOT / stage[key]
                self.assertTrue(path.is_file(),
                                f"{stage['stage_id']} missing {key}: {stage[key]}")

    def test_manifest_declares_no_real_side_effects(self):
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertTrue(data["all_stages_contract_only"])
        self.assertTrue(data["no_real_side_effects_in_v1"])

    def test_manifest_has_cross_cutting_artifacts(self):
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cca = data["cross_cutting_artifacts"]
        self.assertIn("meta_tests", cca)
        self.assertIn("contract_tests", cca)
        self.assertIn("integration_readiness_report", cca)

    def test_manifest_has_blocked_items(self):
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertGreater(len(data["blocked_before_production"]), 0)

    def test_manifest_has_next_stages(self):
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertGreater(len(data["next_production_stages"]), 0)

    def test_readiness_report_contains_contract_only_statement(self):
        text = READINESS_PATH.read_text(encoding="utf-8")
        self.assertIn("contract-only", text)
        self.assertIn("No Real Side Effects", text)

    def test_readiness_report_lists_blocked_items(self):
        text = READINESS_PATH.read_text(encoding="utf-8")
        self.assertIn("Blocked Before Production Runtime", text)

    def test_each_module_file_actually_exists(self):
        for sid in EXPECTED_STAGES:
            path = ROOT / "tools" / "local_code_stages" / f"generated_{sid}.py"
            self.assertTrue(path.is_file(), f"Module not found: {path}")


if __name__ == "__main__":
    unittest.main()
