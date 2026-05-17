"""Cross-module contract tests — verify structural compatibility across modules.

Uses actual module imports and receipt production to verify inter-module contracts.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

# Import all generated modules
from generated_evidence_vault_foundation import (  # type: ignore[import-not-found]
    produce_evidence_vault_receipt,
    EvidenceVaultReceipt,
)
from generated_replay_engine_foundation import (  # type: ignore[import-not-found]
    produce_replay_engine_receipt,
    ReplayEngineReceipt,
)
from generated_decision_report_foundation import (  # type: ignore[import-not-found]
    produce_decision_report_receipt,
    DecisionReportReceipt,
)
from generated_provider_transport_boundary import (  # type: ignore[import-not-found]
    produce_provider_transport_receipt,
    validate_provider_transport_request,
)
from generated_decision_engine_foundation import (  # type: ignore[import-not-found]
    produce_decision_engine_receipt,
    validate_decision_request,
)
from generated_alert_delivery_foundation import (  # type: ignore[import-not-found]
    produce_alert_delivery_receipt,
    validate_alert_delivery_request,
)
from generated_operator_daily_run_foundation import (  # type: ignore[import-not-found]
    produce_operator_daily_run_receipt,
    validate_operator_daily_run_request,
)
from generated_asset_mapping_foundation import (  # type: ignore[import-not-found]
    produce_asset_mapping_receipt,
    validate_asset_mapping_request,
)

VALID_SHA256 = "a" * 64


def _evid_payload() -> dict:
    return {
        "artifact_id": "ART-001",
        "artifact_type": "run_log",
        "content_hash": VALID_SHA256,
        "hash_algorithm": "sha256",
        "created_at": "2025-01-01T00:00:00Z",
        "producer": "test-runner",
        "lineage": ["run-001", "stage-002"],
        "immutable": True,
        "append_only": True,
    }


class CrossModuleContractTests(unittest.TestCase):
    """Verify structural compatibility by producing real receipts."""

    # ── Evidence → Replay chain ───────────────────────────────────

    def test_evidence_produces_valid_receipt_with_content_hash(self):
        receipt = produce_evidence_vault_receipt(_evid_payload())
        self.assertEqual(receipt["status"], "sealed")
        self.assertEqual(receipt["content_hash"], VALID_SHA256)
        self.assertEqual(receipt["hash_algorithm"], "sha256")

    def test_replay_accepts_input_snapshot_hash_matching_evidence_format(self):
        """Replay's input_snapshot_hash uses same sha256-64 format as evidence content_hash."""
        replay_payload = {
            "replay_anchor_id": "ANCHOR-001",
            "input_snapshot_hash": VALID_SHA256,
            "policy_version": "v1.0.0",
            "code_version": "abc123def456",
            "environment_fingerprint": "env-hash-001",
            "deterministic_mode": True,
            "no_cloud_requery": True,
            "created_at": "2025-01-01T00:00:00Z",
        }
        receipt = produce_replay_engine_receipt(replay_payload)
        self.assertEqual(receipt["status"], "ready")
        self.assertEqual(receipt["input_snapshot_hash"], VALID_SHA256)

    # ── Evidence → Decision Report chain ──────────────────────────

    def test_decision_report_accepts_evidence_links(self):
        """Decision report references evidence artifacts via evidence_links."""
        payload = {
            "decision_id": "DEC-001",
            "action": "HOLD",
            "evidence_links": ["ART-001", "ART-002"],
            "confidence_rationale": {"confidence": 0.85, "claims": ["market_data_consistent"]},
            "friction_summary": {"summary": "Low spread on NYSE"},
            "human_review": {"reviewed": True, "reviewer_id": "OP-001", "reviewed_at": "2025-01-01T00:00:00Z"},
            "created_at": "2025-01-01T00:00:00Z",
        }
        receipt = produce_decision_report_receipt(payload)
        self.assertEqual(receipt["status"], "published")
        self.assertTrue(receipt["evidence_links_present"])

    def test_evidence_and_decision_report_hash_compatible(self):
        """Both use the same sha256 hex format for hashes."""
        ev_receipt = produce_evidence_vault_receipt(_evid_payload())
        self.assertEqual(len(ev_receipt["content_hash"]), 64)
        # Decision report evidence links reference artifact IDs (same hash namespace)
        dr_payload = {
            "decision_id": "DEC-002",
            "action": "HOLD",
            "evidence_links": [ev_receipt["artifact_id"]],
            "confidence_rationale": {"confidence": 0.80, "claims": ["c1"]},
            "friction_summary": {"summary": "ok"},
            "human_review": {"reviewed": True, "reviewer_id": "OP-001", "reviewed_at": "t"},
            "created_at": "2025-01-01T00:00:00Z",
        }
        dr_receipt = produce_decision_report_receipt(dr_payload)
        self.assertTrue(dr_receipt["evidence_links_present"])
        self.assertEqual(ev_receipt["content_hash"], VALID_SHA256)

    # ── Provider transport requires evidence binding ──────────────

    def test_provider_transport_rejects_missing_evidence_binding(self):
        """Provider transport must fail when evidence_binding is missing."""
        payload = {
            "provider_id": "mock-market-data",
            "capability_token": "cap-token-xyz-123",
            "evidence_binding": "",
            "request_payload": {"symbol": "TEST", "field": "price"},
            "created_at": "2025-01-01T00:00:00Z",
        }
        # The preflight should fail
        from generated_provider_transport_boundary import validate_provider_transport_preflight
        result = validate_provider_transport_preflight(payload)
        self.assertFalse(result["preflight_passed"])

    def test_provider_transport_receipt_records_evidence_binding(self):
        payload = {
            "provider_id": "mock-market-data",
            "capability_token": "cap-token-xyz-123",
            "evidence_binding": "evid-binding-001",
            "request_payload": {"symbol": "TEST", "field": "price"},
            "created_at": "2025-01-01T00:00:00Z",
        }
        receipt = produce_provider_transport_receipt(payload)
        self.assertTrue(receipt["evidence_binding_present"])
        self.assertEqual(receipt["status"], "gated")

    # ── Decision engine requires evidence and friction ────────────

    def test_decision_engine_requires_evidence_refs(self):
        """Decision engine rejects requests without evidence_refs."""
        with self.assertRaises(ValueError):
            validate_decision_request({
                "decision_id": "D-1",
                "actions": ["HOLD"],
                "confidence": 0.85,
                "friction_data": {"spread": 0.01, "venue": "NYSE"},
                "human_review": {"reviewed": True, "reviewer_id": "OP-001"},
                # missing evidence_refs
                "created_at": "2025-01-01T00:00:00Z",
            })

    def test_decision_engine_produces_receipt_with_friction_gate(self):
        payload = {
            "decision_id": "DEC-010",
            "actions": ["HOLD"],
            "confidence": 0.85,
            "friction_data": {"spread": 0.01, "venue": "NYSE"},
            "human_review": {"reviewed": True, "reviewer_id": "OP-001", "reviewed_at": "2025-01-01T00:00:00Z"},
            "evidence_refs": ["evid-001"],
            "created_at": "2025-01-01T00:00:00Z",
        }
        receipt = produce_decision_engine_receipt(payload)
        self.assertTrue(receipt["friction_gate_passed"])
        self.assertTrue(receipt["confidence_gate_passed"])
        self.assertEqual(receipt["status"], "approved")

    # ── Alert delivery requires evidence ref and operator ack ─────

    def test_alert_delivery_rejects_missing_evidence_reference(self):
        with self.assertRaises(ValueError):
            validate_alert_delivery_request({
                "alert_id": "A-1",
                "channel": "log",
                "alert_payload": {"severity": "high", "message": "test", "timestamp": "t"},
                "operator_acknowledgement": {"acknowledged": True, "operator_id": "OP-001"},
                # missing evidence_reference
                "created_at": "2025-01-01T00:00:00Z",
            })

    def test_alert_delivery_receipt_requires_operator_ack(self):
        payload = {
            "alert_id": "ALERT-010",
            "channel": "log",
            "alert_payload": {"severity": "high", "message": "Test alert", "timestamp": "2025-01-01T00:00:00Z"},
            "operator_acknowledgement": {"acknowledged": True, "operator_id": "OP-001"},
            "evidence_reference": "evid-ref-001",
            "created_at": "2025-01-01T00:00:00Z",
        }
        receipt = produce_alert_delivery_receipt(payload)
        self.assertTrue(receipt["operator_acknowledged"])
        self.assertTrue(receipt["evidence_reference_present"])
        self.assertEqual(receipt["status"], "queued")

    # ── Operator daily run requires human review ──────────────────

    def test_operator_daily_run_rejects_incomplete_human_review(self):
        with self.assertRaises(ValueError):
            validate_operator_daily_run_request({
                "run_id": "R-1",
                "operator_id": "OP-1",
                "runbook_reference": "x",
                "evidence_summary": "summary",
                "human_review": {"completed": False, "reviewer_id": ""},
                "approval": {"operator_approved": True, "approver_id": "OP-1", "approval_timestamp": "t"},
                "run_window": {"start": "2025-01-01T08:00:00Z", "end": "2025-01-01T18:00:00Z"},
                "created_at": "2025-01-01T00:00:00Z",
            })

    def test_operator_daily_run_receipt_records_human_review(self):
        payload = {
            "run_id": "RUN-010",
            "operator_id": "OP-001",
            "runbook_reference": "docs/runbooks/daily_v1.md",
            "evidence_summary": "All checks green",
            "human_review": {"completed": True, "reviewer_id": "OP-001", "reviewed_at": "2025-01-01T09:00:00Z"},
            "approval": {"operator_approved": True, "approver_id": "OP-001", "approval_timestamp": "2025-01-01T09:05:00Z"},
            "run_window": {"start": "2025-01-01T08:00:00Z", "end": "2025-01-01T18:00:00Z"},
            "created_at": "2025-01-01T00:00:00Z",
        }
        receipt = produce_operator_daily_run_receipt(payload)
        self.assertTrue(receipt["human_review_completed"])
        self.assertTrue(receipt["approval_gate_passed"])
        self.assertEqual(receipt["status"], "approved")

    # ── Asset mapping requires evidence and venue ─────────────────

    def test_asset_mapping_rejects_missing_evidence(self):
        with self.assertRaises(ValueError):
            validate_asset_mapping_request({
                "candidate_id": "C-1",
                "asset_class": "equity",
                "venue": "NYSE",
                "product_id": "AAPL",
                "evidence_refs": [],
                "confidence": 0.85,
                "friction_data": {"spread": 0.01},
                "created_at": "2025-01-01T00:00:00Z",
            })

    def test_asset_mapping_receipt_records_evidence_and_venue(self):
        payload = {
            "candidate_id": "CAND-010",
            "asset_class": "equity",
            "venue": "NYSE",
            "product_id": "AAPL",
            "evidence_refs": ["evid-001", "evid-002"],
            "confidence": 0.85,
            "friction_data": {"spread": 0.01, "liquidity": "high"},
            "created_at": "2025-01-01T00:00:00Z",
        }
        receipt = produce_asset_mapping_receipt(payload)
        self.assertTrue(receipt["evidence_present"])
        self.assertEqual(receipt["venue"], "NYSE")
        self.assertEqual(receipt["product_id"], "AAPL")
        self.assertEqual(receipt["status"], "mapped")


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
