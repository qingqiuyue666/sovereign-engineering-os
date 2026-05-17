"""Dry-run runtime orchestrator tracer-bullet tests.

Tests the deterministic dry-run orchestrator that wires:
- execution_descriptor
- runner
- state_machine
- idempotency
- event_journal
- provider_execution_plane
- evidence_vault_boundary
- protected_storage_interface
- failure_bundle
- replay_plan
"""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.dry_run_orchestrator import (
    DryRunOrchestrationReceipt,
    DryRunOrchestratorRejection,
    orchestrate_dry_run,
)
from kernel.runtime.idempotency import IdempotencyGuard
from kernel.runtime.event_journal import EventJournal

POLICY_PATH = Path("governance/runtime/dry_run_orchestrator_policy_v1.json")


def _valid_descriptor():
    return {
        "task_id": "task_orch1234567890123456",
        "run_id": "run_orch1234567890123456",
        "execution_id": "exec_orch1234567890123456",
        "stage": "validated",
        "policy_version": "v1",
        "code_version": "0.1.0",
        "input_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "task_manifest_digest": "sha256:00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff",
        "operator_intent_digest": "sha256:ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100",
        "dry_run": True,
        "provider_enabled": False,
        "network_access": False,
        "production_autonomy": False,
    }


class DryRunOrchestratorPolicyTests(unittest.TestCase):
    """Policy file integrity tests."""

    def test_policy_file_exists_and_is_valid_json(self):
        self.assertTrue(POLICY_PATH.is_file(), f"Policy file missing: {POLICY_PATH}")
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "dry_run_orchestrator_policy_v1")
        self.assertEqual(policy["version"], "v1")
        self.assertTrue(policy["dry_run_only"])
        self.assertTrue(policy["deterministic_required"])
        self.assertIn("validate_execution_descriptor", policy["orchestration_flow"])
        self.assertIn("validate_state_transition_planned_to_validated", policy["orchestration_flow"])
        self.assertIn("validate_idempotency", policy["orchestration_flow"])
        self.assertIn("produce_dry_run_runner_receipt", policy["orchestration_flow"])
        self.assertIn("append_event_journal_descriptor_validated", policy["orchestration_flow"])
        self.assertIn("refuse_provider_execution", policy["orchestration_flow"])
        self.assertIn("refuse_evidence_vault_live_write", policy["orchestration_flow"])
        self.assertIn("append_event_journal_dry_run_completed", policy["orchestration_flow"])


class DryRunOrchestratorAcceptanceTests(unittest.TestCase):
    """Happy-path acceptance tests."""

    def test_valid_dry_run_orchestration_accepted(self):
        receipt = orchestrate_dry_run(_valid_descriptor())
        self.assertIsInstance(receipt, DryRunOrchestrationReceipt)
        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.final_status, "dry_run_completed")
        self.assertEqual(receipt.dry_run, True)
        self.assertEqual(receipt.failures, ())

    def test_receipt_contains_all_expected_digests(self):
        receipt = orchestrate_dry_run(_valid_descriptor())
        self.assertTrue(receipt.state_transition_receipt_digest.startswith("sha256:"))
        self.assertTrue(receipt.idempotency_receipt_digest.startswith("sha256:"))
        self.assertTrue(receipt.runner_receipt_digest.startswith("sha256:"))
        self.assertTrue(receipt.provider_boundary_receipt_digest.startswith("sha256:"))
        self.assertTrue(receipt.evidence_boundary_receipt_digest.startswith("sha256:"))
        self.assertTrue(receipt.event_journal_digest.startswith("sha256:"))

    def test_deterministic_receipt(self):
        r1 = orchestrate_dry_run(_valid_descriptor())
        r2 = orchestrate_dry_run(_valid_descriptor())
        self.assertEqual(r1.as_dict(), r2.as_dict())

    def test_input_not_mutated(self):
        payload = _valid_descriptor()
        before = copy.deepcopy(payload)
        orchestrate_dry_run(payload)
        self.assertEqual(payload, before)

    def test_event_journal_receives_events(self):
        journal = EventJournal()
        orchestrate_dry_run(_valid_descriptor(), journal=journal)
        self.assertGreaterEqual(journal.event_count(), 2)
        event_types = [e.event_type for e in journal.events]
        self.assertIn("descriptor_validated", event_types)
        self.assertIn("dry_run_completed", event_types)

    def test_provider_boundary_refusal_is_recorded(self):
        receipt = orchestrate_dry_run(_valid_descriptor())
        self.assertTrue(len(receipt.provider_boundary_receipt_digest) > 0)
        self.assertTrue(receipt.provider_boundary_receipt_digest.startswith("sha256:"))

    def test_evidence_boundary_refusal_is_recorded(self):
        receipt = orchestrate_dry_run(_valid_descriptor())
        self.assertTrue(len(receipt.evidence_boundary_receipt_digest) > 0)
        self.assertTrue(receipt.evidence_boundary_receipt_digest.startswith("sha256:"))

    def test_failure_bundle_digest_empty_on_success(self):
        receipt = orchestrate_dry_run(_valid_descriptor())
        self.assertEqual(receipt.failure_bundle_digest, "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_replay_plan_digest_empty_on_success(self):
        receipt = orchestrate_dry_run(_valid_descriptor())
        self.assertEqual(receipt.replay_plan_digest, "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")


class DryRunOrchestratorRejectionTests(unittest.TestCase):
    """Rejection-path tests."""

    def test_non_mapping_rejected(self):
        with self.assertRaises(DryRunOrchestratorRejection):
            orchestrate_dry_run(None)

        with self.assertRaises(DryRunOrchestratorRejection):
            orchestrate_dry_run("not_a_mapping")

        with self.assertRaises(DryRunOrchestratorRejection):
            orchestrate_dry_run(42)

    def test_dry_run_false_in_descriptor_rejected(self):
        d = _valid_descriptor()
        d["dry_run"] = False
        receipt = orchestrate_dry_run(d)
        self.assertFalse(receipt.accepted)
        self.assertIn("dry_run_must_be_true", receipt.failures)

    def test_provider_enabled_true_rejected(self):
        d = _valid_descriptor()
        d["provider_enabled"] = True
        receipt = orchestrate_dry_run(d)
        self.assertFalse(receipt.accepted)
        self.assertIn("provider_enabled_must_be_false", receipt.failures)

    def test_network_access_true_rejected(self):
        d = _valid_descriptor()
        d["network_access"] = True
        receipt = orchestrate_dry_run(d)
        self.assertFalse(receipt.accepted)
        self.assertIn("network_access_must_be_false", receipt.failures)

    def test_production_autonomy_true_rejected(self):
        d = _valid_descriptor()
        d["production_autonomy"] = True
        receipt = orchestrate_dry_run(d)
        self.assertFalse(receipt.accepted)
        self.assertIn("production_autonomy_must_be_false", receipt.failures)

    def test_raw_prompt_rejected(self):
        d = _valid_descriptor()
        d["raw_prompt"] = "do something"
        receipt = orchestrate_dry_run(d)
        self.assertFalse(receipt.accepted)
        self.assertIn("raw_prompt_forbidden", receipt.failures)

    def test_secret_value_rejected(self):
        d = _valid_descriptor()
        d["secret_value"] = "my-secret"
        receipt = orchestrate_dry_run(d)
        self.assertFalse(receipt.accepted)
        self.assertIn("secret_value_forbidden", receipt.failures)

    def test_failure_produces_failure_bundle(self):
        d = _valid_descriptor()
        d["dry_run"] = False
        receipt = orchestrate_dry_run(d)
        self.assertFalse(receipt.accepted)
        self.assertTrue(receipt.failure_bundle_digest.startswith("sha256:"))
        self.assertNotEqual(receipt.failure_bundle_digest, "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_failure_produces_replay_plan(self):
        d = _valid_descriptor()
        d["dry_run"] = False
        receipt = orchestrate_dry_run(d)
        self.assertFalse(receipt.accepted)
        self.assertTrue(receipt.replay_plan_digest.startswith("sha256:"))
        self.assertNotEqual(receipt.replay_plan_digest, "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")


class DryRunOrchestratorIdempotencyTests(unittest.TestCase):
    """Idempotency-specific tests."""

    def test_duplicate_same_digest_is_duplicate_safe(self):
        guard = IdempotencyGuard()
        d1 = _valid_descriptor()
        r1 = orchestrate_dry_run(d1, guard=guard)
        self.assertTrue(r1.accepted)

        d2 = _valid_descriptor()
        r2 = orchestrate_dry_run(d2, guard=guard)
        self.assertTrue(r2.accepted, f"Expected accepted but got failures: {r2.failures}")

    def test_different_descriptors_produce_different_idempotency_keys(self):
        guard = IdempotencyGuard()
        d1 = _valid_descriptor()
        r1 = orchestrate_dry_run(d1, guard=guard)
        self.assertTrue(r1.accepted)

        d2 = _valid_descriptor()
        d2["execution_id"] = "exec_different_id_here_123456"
        r2 = orchestrate_dry_run(d2, guard=guard)
        self.assertTrue(r2.accepted, f"Expected accepted but got failures: {r2.failures}")


class DryRunOrchestratorSideEffectFreeTests(unittest.TestCase):
    """Side-effect freedom tests."""

    def test_orchestrate_dry_run_does_not_mutate(self):
        payload = _valid_descriptor()
        before = copy.deepcopy(payload)
        orchestrate_dry_run(payload)
        self.assertEqual(payload, before)

    def test_no_network_imports(self):
        import kernel.runtime.dry_run_orchestrator as mod
        source = mod.__file__
        if source:
            with open(source, "r") as f:
                content = f.read()
            self.assertNotIn("requests", content)
            self.assertNotIn("urllib", content)
            self.assertNotIn("http.client", content)

    def test_no_sqlite_import(self):
        import kernel.runtime.dry_run_orchestrator as mod
        source = mod.__file__
        if source:
            with open(source, "r") as f:
                content = f.read()
            self.assertNotIn("sqlite3", content)
