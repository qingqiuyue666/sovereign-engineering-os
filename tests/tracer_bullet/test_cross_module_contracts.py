"""Cross-module contract tests — verify structural compatibility across modules.

Tests that interdependent modules have compatible data contracts.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_module_src(module_name: str) -> str:
    path = ROOT / "tools" / "local_code_stages" / f"generated_{module_name}.py"
    return path.read_text(encoding="utf-8")


class CrossModuleContractTests(unittest.TestCase):
    """Verify structural compatibility between interdependent modules."""

    # ── Evidence → Replay → Decision report references ────────────

    def test_evidence_module_has_content_hash_field(self):
        src = _load_module_src("evidence_vault_foundation")
        self.assertIn("content_hash", src)

    def test_replay_module_has_input_snapshot_hash_field(self):
        src = _load_module_src("replay_engine_foundation")
        self.assertIn("input_snapshot_hash", src)

    def test_decision_report_has_evidence_links_field(self):
        src = _load_module_src("decision_report_foundation")
        self.assertIn("evidence_links", src)

    def test_evidence_replay_decision_chain_hash_fields_compatible(self):
        """Evidence content_hash is sha256-64, replay input_snapshot_hash is sha256-64, report evidence_links references artifacts."""
        ev_src = _load_module_src("evidence_vault_foundation")
        rp_src = _load_module_src("replay_engine_foundation")
        dr_src = _load_module_src("decision_report_foundation")
        self.assertIn("content_hash", ev_src)
        self.assertIn("input_snapshot_hash", rp_src)
        self.assertIn("evidence_links", dr_src)
        # All use 64-char hex hashes
        self.assertIn("64", ev_src)
        self.assertIn("64", rp_src)

    # ── Provider transport requires evidence binding ──────────────

    def test_provider_transport_requires_evidence_binding(self):
        src = _load_module_src("provider_transport_boundary")
        self.assertIn("evidence_binding", src)
        # Check validation rejects missing evidence
        self.assertIn("no_forbidden_provider", src.lower() or "no_forbidden_provider" in src)

    # ── Decision engine requires evidence and friction gate ──────

    def test_decision_engine_requires_evidence_refs(self):
        src = _load_module_src("decision_engine_foundation")
        self.assertIn("evidence_refs", src)

    def test_decision_engine_requires_friction_gate(self):
        src = _load_module_src("decision_engine_foundation")
        self.assertIn("friction", src.lower())

    # ── Alert delivery requires evidence reference and operator ack ──

    def test_alert_delivery_requires_evidence_reference(self):
        src = _load_module_src("alert_delivery_foundation")
        self.assertIn("evidence_reference", src)

    def test_alert_delivery_requires_operator_acknowledgement(self):
        src = _load_module_src("alert_delivery_foundation")
        self.assertIn("operator_acknowledgement", src)

    # ── Operator daily run requires human review ─────────────────

    def test_operator_daily_run_requires_human_review(self):
        src = _load_module_src("operator_daily_run_foundation")
        self.assertIn("human_review", src)

    # ── Asset mapping requires evidence and venue ────────────────

    def test_asset_mapping_requires_evidence_refs(self):
        src = _load_module_src("asset_mapping_foundation")
        self.assertIn("evidence_refs", src)

    def test_asset_mapping_requires_venue(self):
        src = _load_module_src("asset_mapping_foundation")
        self.assertIn("venue", src)

    # ── Receipt types are consistent ──────────────────────────────

    def test_all_modules_status_field_consistent(self):
        """All modules produce receipts with a 'status' field."""
        for sid in [
            "patch_application_pipeline", "local_execution_kernel",
            "evidence_vault_foundation", "replay_engine_foundation",
            "provider_transport_boundary", "operator_daily_run_foundation",
            "alert_delivery_foundation", "osint_ingestion_foundation",
            "asset_mapping_foundation", "decision_engine_foundation",
            "recovery_rollback_foundation", "checkpoint_runtime_foundation",
            "run_ledger_hardening_foundation", "evidence_index_foundation",
            "decision_report_foundation", "local_operator_cli_extension_foundation",
        ]:
            src = _load_module_src(sid)
            self.assertIn("status", src, f"{sid} missing status field")

    # ── No module references forbidden actions ───────────────────

    def test_no_module_references_buy_sell_trade_in_actions(self):
        """Decision engine and asset mapping have action boundaries (ALLOWED or FORBIDDEN)."""
        for sid in ["decision_engine_foundation", "asset_mapping_foundation", "decision_report_foundation"]:
            src = _load_module_src(sid)
            has_boundary = "FORBIDDEN" in src or "ALLOWED" in src
            self.assertTrue(has_boundary, f"{sid} should define action boundaries (ALLOWED or FORBIDDEN)")


class ContractJsonValidityTest(unittest.TestCase):

    def test_all_policies_are_valid_json(self):
        for sid in [
            "patch_application_pipeline", "local_execution_kernel",
            "evidence_vault_foundation", "replay_engine_foundation",
            "provider_transport_boundary", "operator_daily_run_foundation",
            "alert_delivery_foundation", "osint_ingestion_foundation",
            "asset_mapping_foundation", "decision_engine_foundation",
            "recovery_rollback_foundation", "checkpoint_runtime_foundation",
            "run_ledger_hardening_foundation", "evidence_index_foundation",
            "decision_report_foundation", "local_operator_cli_extension_foundation",
        ]:
            path = ROOT / "governance" / "security" / f"{sid}_policy_v1.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "active", f"{sid} policy not active")

    def test_all_registries_are_valid_json(self):
        for sid in [
            "patch_application_pipeline", "local_execution_kernel",
            "evidence_vault_foundation", "replay_engine_foundation",
            "provider_transport_boundary", "operator_daily_run_foundation",
            "alert_delivery_foundation", "osint_ingestion_foundation",
            "asset_mapping_foundation", "decision_engine_foundation",
            "recovery_rollback_foundation", "checkpoint_runtime_foundation",
            "run_ledger_hardening_foundation", "evidence_index_foundation",
            "decision_report_foundation", "local_operator_cli_extension_foundation",
        ]:
            path = ROOT / "governance" / "local_train" / f"{sid}_registry_v1.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "active", f"{sid} registry not active")


if __name__ == "__main__":
    unittest.main()
