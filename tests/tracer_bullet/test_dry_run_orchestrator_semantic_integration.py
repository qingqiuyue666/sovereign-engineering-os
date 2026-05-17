"""Semantic integration tests for the dry-run orchestrator."""

import unittest

from kernel.runtime.dry_run_orchestrator import orchestrate_dry_run

EMPTY_DIGEST = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _valid_descriptor():
    return {
        "task_id": "task_semantic_orch_123456",
        "run_id": "run_semantic_orch_123456",
        "execution_id": "exec_semantic_orch_123456",
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


class DryRunOrchestratorSemanticIntegrationTests(unittest.TestCase):
    def test_success_path_records_provider_refusal(self):
        receipt = orchestrate_dry_run(_valid_descriptor())
        self.assertTrue(receipt.accepted)
        self.assertTrue(receipt.provider_boundary_refused)
        self.assertIn("provider_enabled_rejected_default_disabled", receipt.provider_boundary_failures)
        self.assertIn("network_access_rejected", receipt.provider_boundary_failures)
        self.assertIn("tool_calls_enabled_rejected", receipt.provider_boundary_failures)
        self.assertIn("file_edits_enabled_rejected", receipt.provider_boundary_failures)
        self.assertIn("production_autonomy_rejected", receipt.provider_boundary_failures)

    def test_success_path_records_evidence_live_write_refusal(self):
        receipt = orchestrate_dry_run(_valid_descriptor())
        self.assertTrue(receipt.accepted)
        self.assertTrue(receipt.evidence_boundary_refused)
        self.assertIn("vault_enabled_rejected_default_disabled", receipt.evidence_boundary_failures)
        self.assertIn("live_write_rejected", receipt.evidence_boundary_failures)

    def test_rejected_path_uses_nonempty_failure_bundle_and_replay_plan(self):
        descriptor = _valid_descriptor()
        descriptor["dry_run"] = False
        receipt = orchestrate_dry_run(descriptor)
        self.assertFalse(receipt.accepted)
        self.assertNotEqual(receipt.failure_bundle_digest, EMPTY_DIGEST)
        self.assertNotEqual(receipt.replay_plan_digest, EMPTY_DIGEST)
        self.assertTrue(receipt.failure_bundle_digest.startswith("sha256:"))
        self.assertTrue(receipt.replay_plan_digest.startswith("sha256:"))

    def test_rejected_path_is_deterministic(self):
        descriptor = _valid_descriptor()
        descriptor["network_access"] = True
        first = orchestrate_dry_run(descriptor).as_dict()
        second = orchestrate_dry_run(descriptor).as_dict()
        self.assertEqual(first, second)

    def test_no_live_surface_is_claimed_on_success(self):
        receipt = orchestrate_dry_run(_valid_descriptor())
        self.assertTrue(receipt.accepted)
        self.assertTrue(receipt.dry_run)
        self.assertEqual(receipt.final_status, "dry_run_completed")
        self.assertEqual(receipt.failure_bundle_digest, EMPTY_DIGEST)
        self.assertEqual(receipt.replay_plan_digest, EMPTY_DIGEST)


if __name__ == "__main__":
    unittest.main()
