"""Spine integration tests — ProviderTransport receipt linked into Runtime Receipt Spine.

Verifies that ProviderDryRunReceipt can be linked into the existing Runtime
Receipt Spine chain without modification to the spine. Tests that the
canonical_hash field is compatible with the spine's hash format.
"""

import hashlib
import unittest

from tools.provider_transport.provider_dry_run_receipt import (
    ProviderDryRunReceipt,
    produce_dry_run_receipt,
)
from tools.provider_transport.provider_transport_runtime import (
    TransportExecutionResult,
    execute_provider_transport,
)
from tools.runtime_spine.runtime_receipt_validator import RuntimeReceiptValidator
from tools.runtime_spine.runtime_spine_security import RuntimeSpineSecurity


class ProviderTransportSpineCompatibilityTests(unittest.TestCase):
    """Tests that ProviderTransport receipt is compatible with Runtime Spine."""

    def _valid_payload(self):
        return {
            "provider_id": "mock-finance",
            "request_id": "req-spine-001",
            "capability_token": "fetch_price,validate_asset",
            "evidence_binding": "ev-spine-001",
            "dry_run": True,
            "live_mode": False,
            "network_mode": False,
        }

    def _mock_evidence_receipt(self):
        return {
            "artifact_id": "artifact-001",
            "content_hash": hashlib.sha256(b"content").hexdigest(),
            "hash_algorithm": "sha256",
        }

    def _mock_replay_receipt(self, evidence_ids=None):
        if evidence_ids is None:
            evidence_ids = ["artifact-001"]
        return {
            "receipt_id": hashlib.sha256(b"replay").hexdigest(),
            "anchor_id": "anchor-001",
            "canonical_hash": hashlib.sha256(b"replay-canonical").hexdigest(),
            "evidence_artifact_ids": evidence_ids,
            "evidence_binding_hash": hashlib.sha256(b"ev-binding").hexdigest(),
            "evidence_binding_valid": True,
        }

    def _mock_patch_receipt(self, replay_hash=None):
        if replay_hash is None:
            replay_hash = hashlib.sha256(b"replay-canonical").hexdigest()
        return {
            "receipt_id": hashlib.sha256(b"patch").hexdigest(),
            "request_id": "patch-001",
            "canonical_hash": hashlib.sha256(b"patch-canonical").hexdigest(),
            "replay_receipt_hash": replay_hash,
        }

    def _mock_execution_receipt(self, patch_hash=None):
        if patch_hash is None:
            patch_hash = hashlib.sha256(b"patch-canonical").hexdigest()
        return {
            "receipt_id": hashlib.sha256(b"exec").hexdigest(),
            "execution_id": "exec-001",
            "canonical_hash": hashlib.sha256(b"exec-canonical").hexdigest(),
            "patch_receipt_hash": patch_hash,
        }

    def _mock_operator_receipt(self, exec_hash=None):
        if exec_hash is None:
            exec_hash = hashlib.sha256(b"exec-canonical").hexdigest()
        return {
            "receipt_id": hashlib.sha256(b"op").hexdigest(),
            "run_id": "run-001",
            "canonical_hash": hashlib.sha256(b"op-canonical").hexdigest(),
            "execution_receipt_hashes": [exec_hash],
        }

    # --- receipt hash format ---

    def test_provider_receipt_canonical_hash_is_64_char_hex(self):
        receipt = produce_dry_run_receipt(
            provider_id="mock-finance",
            request_id="req-001",
            request_digest="a" * 64,
            capability_token="fetch_price",
            evidence_binding="ev-001",
        )
        self.assertEqual(len(receipt.canonical_hash), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in receipt.canonical_hash))

    def test_canonical_hash_matches_spine_hash_format(self):
        """Provider receipt canonical_hash uses same sha256 hex format as spine."""
        spine_hash = hashlib.sha256(b"test").hexdigest()
        receipt = produce_dry_run_receipt(
            provider_id="mock-finance",
            request_id="req-001",
            request_digest="a" * 64,
            capability_token="fetch_price",
            evidence_binding="ev-001",
        )
        # Both are 64-char lowercase hex
        self.assertEqual(len(receipt.canonical_hash), len(spine_hash))

    # --- spine validation unchanged ---

    def test_spine_validator_still_works(self):
        """Existing RuntimeReceiptValidator must work without modification."""
        evidence = self._mock_evidence_receipt()
        replay = self._mock_replay_receipt()
        result = RuntimeReceiptValidator.validate_evidence_to_replay(evidence, replay)
        self.assertTrue(result["compatible"], result["issues"])

    def test_full_spine_still_validates(self):
        """Full spine must still validate without provider transport changes."""
        evidence = self._mock_evidence_receipt()
        replay = self._mock_replay_receipt()
        patch = self._mock_patch_receipt()
        execution = self._mock_execution_receipt()
        operator = self._mock_operator_receipt()

        result = RuntimeReceiptValidator.validate_full_spine(
            evidence, replay, patch, execution, operator,
        )
        self.assertTrue(result["spine_valid"], result["pairs"])

    # --- security gates unchanged ---

    def test_spine_security_gates_unchanged(self):
        gates = RuntimeSpineSecurity.security_gates()
        self.assertTrue(gates["no_network"])
        self.assertTrue(gates["no_live_provider"])
        self.assertTrue(gates["no_raw_payload"])
        self.assertTrue(gates["deterministic_chain_hash"])

    # --- provider receipt has no raw payload ---

    def test_provider_receipt_as_dict_no_raw_payload(self):
        receipt = produce_dry_run_receipt(
            provider_id="mock-finance",
            request_id="req-001",
            request_digest="a" * 64,
            capability_token="fetch_price",
            evidence_binding="ev-001",
        )
        d = receipt.as_dict()
        self.assertNotIn("raw_payload", d)
        self.assertNotIn("payload", d)
        self.assertNotIn("raw_data", d)

    def test_provider_receipt_passes_spine_no_raw_payload_check(self):
        receipt = produce_dry_run_receipt(
            provider_id="mock-finance",
            request_id="req-001",
            request_digest="a" * 64,
            capability_token="fetch_price",
            evidence_binding="ev-001",
        )
        result = RuntimeSpineSecurity.validate_no_raw_payload(receipt.as_dict())
        self.assertTrue(result)

    # --- future linkability ---

    def test_provider_receipt_can_be_hashed_for_spine_link(self):
        """The canonical_hash can be referenced by a future spine link."""
        receipt = produce_dry_run_receipt(
            provider_id="mock-finance",
            request_id="req-001",
            request_digest="a" * 64,
            capability_token="fetch_price",
            evidence_binding="ev-001",
        )
        spine_link_hash = hashlib.sha256(
            f"provider_transport={receipt.canonical_hash}".encode()
        ).hexdigest()
        self.assertEqual(len(spine_link_hash), 64)

    def test_provider_receipt_deterministic_for_spine(self):
        """For spine integration, receipts must be fully deterministic."""
        a = produce_dry_run_receipt(
            provider_id="mock-finance",
            request_id="req-spine-001",
            request_digest="a" * 64,
            capability_token="fetch_price",
            evidence_binding="ev-spine-001",
        )
        b = produce_dry_run_receipt(
            provider_id="mock-finance",
            request_id="req-spine-001",
            request_digest="a" * 64,
            capability_token="fetch_price",
            evidence_binding="ev-spine-001",
        )
        self.assertEqual(a.canonical_hash, b.canonical_hash)

    # --- integration: execute_provider_transport returns valid receipt ---

    def test_execute_produces_valid_spine_compatible_receipt(self):
        from tools.provider_transport.provider_adapter_registry import (
            ProviderAdapterDescriptor,
            register_provider_adapter,
        )
        # Register adapter
        try:
            register_provider_adapter(ProviderAdapterDescriptor(
                provider_id="mock-finance",
                capabilities=frozenset({"fetch_price", "validate_asset", "mock_execute"}),
                boundary_ref="boundary-v1",
                enabled=False,
                dry_run_only=True,
                no_network=True,
            ))
        except Exception:
            pass

        result = execute_provider_transport(self._valid_payload())
        self.assertTrue(result.accepted, result.as_dict())
        self.assertIsNotNone(result.dry_run_receipt)
        self.assertIsNone(result.failure_receipt)

        # Receipt passes no-raw-payload check
        spine_check = RuntimeSpineSecurity.validate_no_raw_payload(
            result.dry_run_receipt.as_dict()
        )
        self.assertTrue(spine_check)


class RuntimeFullPipelineTests(unittest.TestCase):
    """End-to-end tests for the ProviderTransportRuntime pipeline."""

    def _valid_payload(self):
        return {
            "provider_id": "mock-finance",
            "request_id": "req-full-001",
            "capability_token": "fetch_price,validate_asset,mock_execute",
            "evidence_binding": "ev-full-001",
            "dry_run": True,
            "live_mode": False,
            "network_mode": False,
        }

    @classmethod
    def setUpClass(cls):
        from tools.provider_transport.provider_adapter_registry import (
            ProviderAdapterDescriptor,
            register_provider_adapter,
        )
        for pid in ["mock-finance", "mock-market-data", "mock-news", "mock-weather"]:
            try:
                register_provider_adapter(ProviderAdapterDescriptor(
                    provider_id=pid,
                    capabilities=frozenset({"fetch_price", "fetch_news", "fetch_weather",
                                             "calculate_risk", "validate_asset", "mock_execute"}),
                    boundary_ref="boundary-v1",
                    enabled=False,
                    dry_run_only=True,
                    no_network=True,
                ))
            except Exception:
                pass

    # --- golden path ---

    def test_execute_valid_payload_accepted(self):
        result = execute_provider_transport(self._valid_payload())
        self.assertTrue(result.accepted, f"Result: {result.as_dict()}")

    def test_execute_produces_dry_run_receipt(self):
        result = execute_provider_transport(self._valid_payload())
        self.assertIsNotNone(result.dry_run_receipt)
        self.assertEqual(result.dry_run_receipt.status, "gated")

    def test_execute_returns_all_validation_results(self):
        result = execute_provider_transport(self._valid_payload())
        self.assertIsNotNone(result.preflight_result)
        self.assertIsNotNone(result.capability_result)
        self.assertIsNotNone(result.evidence_result)
        self.assertIsNotNone(result.budget_result)
        self.assertIsNotNone(result.network_result)

    def test_execute_preflight_passed(self):
        result = execute_provider_transport(self._valid_payload())
        self.assertTrue(result.preflight_result.passed, result.preflight_result.failures)

    def test_execute_capability_valid(self):
        result = execute_provider_transport(self._valid_payload())
        self.assertTrue(result.capability_result.valid, result.capability_result.failures)

    def test_execute_budget_valid(self):
        result = execute_provider_transport(self._valid_payload())
        self.assertTrue(result.budget_result.valid, result.budget_result.failures)

    # --- deterministic ---

    def test_execute_deterministic(self):
        a = execute_provider_transport(self._valid_payload())
        b = execute_provider_transport(self._valid_payload())
        self.assertEqual(a.accepted, b.accepted)
        self.assertEqual(
            a.dry_run_receipt.canonical_hash,
            b.dry_run_receipt.canonical_hash,
        )

    # --- rejection paths ---

    def test_live_mode_rejected_in_pipeline(self):
        p = self._valid_payload()
        p["live_mode"] = True
        result = execute_provider_transport(p)
        self.assertFalse(result.accepted)
        self.assertIsNotNone(result.failure_receipt)
        self.assertIn("live_mode_must_be_false", result.failure_receipt.failure_reason)

    def test_network_mode_rejected_in_pipeline(self):
        p = self._valid_payload()
        p["network_mode"] = True
        result = execute_provider_transport(p)
        self.assertFalse(result.accepted)
        self.assertIsNotNone(result.failure_receipt)

    def test_dry_run_false_rejected_in_pipeline(self):
        p = self._valid_payload()
        p["dry_run"] = False
        result = execute_provider_transport(p)
        self.assertFalse(result.accepted)
        self.assertIsNotNone(result.failure_receipt)

    def test_forbidden_provider_rejected_in_pipeline(self):
        p = self._valid_payload()
        p["provider_id"] = "live-broker"
        result = execute_provider_transport(p)
        self.assertFalse(result.accepted)
        self.assertIsNotNone(result.failure_receipt)

    def test_unknown_provider_rejected_in_pipeline(self):
        p = self._valid_payload()
        p["provider_id"] = "openai-gpt-cloud"
        result = execute_provider_transport(p)
        self.assertFalse(result.accepted)
        self.assertIsNotNone(result.failure_receipt)

    def test_missing_evidence_binding_rejected(self):
        p = self._valid_payload()
        p["evidence_binding"] = ""
        result = execute_provider_transport(p)
        self.assertFalse(result.accepted)
        self.assertIsNotNone(result.failure_receipt)

    def test_forbidden_capability_rejected_in_pipeline(self):
        p = self._valid_payload()
        p["capability_token"] = "live_trade,fetch_price"
        result = execute_provider_transport(p)
        self.assertFalse(result.accepted)
        self.assertIsNotNone(result.failure_receipt)

    def test_secret_marker_rejected_in_pipeline(self):
        p = self._valid_payload()
        p["note"] = "contains secret key"
        result = execute_provider_transport(p)
        self.assertFalse(result.accepted)

    def test_raw_payload_rejected_in_pipeline(self):
        p = self._valid_payload()
        p["raw_payload"] = "leaked data"
        result = execute_provider_transport(p)
        self.assertFalse(result.accepted)

    # --- all known providers work ---

    def test_all_mock_providers_accepted(self):
        provider_caps = {
            "mock-finance": "fetch_price,validate_asset,mock_execute",
            "mock-market-data": "fetch_price,validate_asset,mock_execute",
            "mock-news": "fetch_news,mock_execute",
            "mock-weather": "fetch_weather,mock_execute",
        }
        for pid, caps in provider_caps.items():
            p = self._valid_payload()
            p["provider_id"] = pid
            p["capability_token"] = caps
            result = execute_provider_transport(p)
            self.assertTrue(result.accepted, f"{pid} rejected: {result.as_dict()}")

    # --- TransportExecutionResult structure ---

    def test_result_as_dict(self):
        result = execute_provider_transport(self._valid_payload())
        d = result.as_dict()
        self.assertTrue(d["accepted"])
        self.assertIsNotNone(d["dry_run_receipt"])
        self.assertIsNone(d["failure_receipt"])

    def test_rejection_result_as_dict(self):
        p = self._valid_payload()
        p["provider_id"] = "live-broker"
        result = execute_provider_transport(p)
        d = result.as_dict()
        self.assertFalse(d["accepted"])
        self.assertIsNone(d["dry_run_receipt"])
        self.assertIsNotNone(d["failure_receipt"])

    # --- no provider call ---

    def test_receipt_declares_no_provider_call(self):
        result = execute_provider_transport(self._valid_payload())
        self.assertTrue(result.dry_run_receipt.no_provider_call)

    def test_receipt_declares_no_network(self):
        result = execute_provider_transport(self._valid_payload())
        self.assertTrue(result.dry_run_receipt.no_network)

    def test_receipt_declares_dry_run(self):
        result = execute_provider_transport(self._valid_payload())
        self.assertTrue(result.dry_run_receipt.dry_run)

    # --- failure receipt determinism ---

    def test_failure_receipt_deterministic(self):
        p = self._valid_payload()
        p["provider_id"] = "live-broker"
        a = execute_provider_transport(p)
        b = execute_provider_transport(p)
        self.assertEqual(
            a.failure_receipt.canonical_hash,
            b.failure_receipt.canonical_hash,
        )


if __name__ == "__main__":
    unittest.main()
