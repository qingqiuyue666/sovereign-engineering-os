"""Tracer-bullet tests for provider transport receipts — dry-run and failure."""

import unittest

from tools.provider_transport.provider_dry_run_receipt import (
    ProviderDryRunReceipt,
    produce_dry_run_receipt,
)
from tools.provider_transport.provider_failure_receipt import (
    ProviderFailureReceipt,
    produce_failure_receipt,
)


class ProviderDryRunReceiptTests(unittest.TestCase):
    """Tests for deterministic dry-run receipt production."""

    def _args(self):
        return dict(
            provider_id="mock-finance",
            request_id="req-001",
            request_digest="a" * 64,
            capability_token="fetch_price,validate_asset",
            evidence_binding="ev-hash-001",
        )

    # --- successful receipt production ---

    def test_receipt_produced(self):
        receipt = produce_dry_run_receipt(**self._args())
        self.assertIsInstance(receipt, ProviderDryRunReceipt)
        self.assertEqual(receipt.status, "gated")

    def test_receipt_has_receipt_id(self):
        receipt = produce_dry_run_receipt(**self._args())
        self.assertTrue(len(receipt.receipt_id) == 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in receipt.receipt_id))

    def test_receipt_has_canonical_hash(self):
        receipt = produce_dry_run_receipt(**self._args())
        self.assertTrue(len(receipt.canonical_hash) == 64)

    # --- deterministic ---

    def test_receipt_deterministic_same_input(self):
        a = produce_dry_run_receipt(**self._args())
        b = produce_dry_run_receipt(**self._args())
        self.assertEqual(a.receipt_id, b.receipt_id)
        self.assertEqual(a.canonical_hash, b.canonical_hash)
        self.assertEqual(a.capability_bits, b.capability_bits)
        self.assertEqual(a.evidence_binding_hash, b.evidence_binding_hash)

    def test_receipt_deterministic_as_dict(self):
        a = produce_dry_run_receipt(**self._args())
        b = produce_dry_run_receipt(**self._args())
        self.assertEqual(a.as_dict(), b.as_dict())

    def test_different_request_produces_different_hash(self):
        a = produce_dry_run_receipt(**self._args())
        args_b = self._args()
        args_b["request_id"] = "req-002"
        b = produce_dry_run_receipt(**args_b)
        self.assertNotEqual(a.canonical_hash, b.canonical_hash)

    def test_different_provider_produces_different_hash(self):
        a = produce_dry_run_receipt(**self._args())
        args_b = self._args()
        args_b["provider_id"] = "mock-weather"
        b = produce_dry_run_receipt(**args_b)
        self.assertNotEqual(a.canonical_hash, b.canonical_hash)

    def test_different_capability_produces_different_hash(self):
        a = produce_dry_run_receipt(**self._args())
        args_b = self._args()
        args_b["capability_token"] = "fetch_news"
        b = produce_dry_run_receipt(**args_b)
        self.assertNotEqual(a.canonical_hash, b.canonical_hash)

    # --- no wall-clock in receipt ---

    def test_no_wall_clock_in_created_at(self):
        """created_at must be the epoch sentinel, not actual wall-clock time."""
        receipt = produce_dry_run_receipt(**self._args())
        self.assertEqual(receipt.created_at, "1970-01-01T00:00:00Z")

    def test_hash_does_not_depend_on_wall_clock(self):
        """Receipt hash must not contain any timestamp that varies between runs."""
        a = produce_dry_run_receipt(**self._args())
        import time
        time.sleep(0.01)  # Ensure time would differ if wall-clock were used
        b = produce_dry_run_receipt(**self._args())
        self.assertEqual(a.canonical_hash, b.canonical_hash)

    # --- no raw payload in receipt ---

    def test_receipt_dict_has_no_raw_payload(self):
        receipt = produce_dry_run_receipt(**self._args())
        d = receipt.as_dict()
        for forbidden in ("raw_payload", "raw_response", "raw_data", "payload", "secret"):
            self.assertNotIn(forbidden, d)

    # --- metadata flags ---

    def test_no_provider_call_is_true(self):
        receipt = produce_dry_run_receipt(**self._args())
        self.assertTrue(receipt.no_provider_call)

    def test_no_network_is_true(self):
        receipt = produce_dry_run_receipt(**self._args())
        self.assertTrue(receipt.no_network)

    def test_dry_run_is_true(self):
        receipt = produce_dry_run_receipt(**self._args())
        self.assertTrue(receipt.dry_run)

    def test_module_version_is_v1(self):
        receipt = produce_dry_run_receipt(**self._args())
        self.assertEqual(receipt.module_version, "v1")

    # --- budget/rate-limit fields ---

    def test_default_budget_consumed_zero(self):
        receipt = produce_dry_run_receipt(**self._args())
        self.assertEqual(receipt.budget_consumed, 0.0)

    def test_default_rate_limit_consumed_zero(self):
        receipt = produce_dry_run_receipt(**self._args())
        self.assertEqual(receipt.rate_limit_consumed, 0)

    def test_budget_consumed_in_hash(self):
        a = produce_dry_run_receipt(**self._args(), budget_consumed=0.0)
        b = produce_dry_run_receipt(**self._args(), budget_consumed=5.0)
        self.assertNotEqual(a.canonical_hash, b.canonical_hash)

    def test_rate_limit_consumed_in_hash(self):
        a = produce_dry_run_receipt(**self._args(), rate_limit_consumed=0)
        b = produce_dry_run_receipt(**self._args(), rate_limit_consumed=3)
        self.assertNotEqual(a.canonical_hash, b.canonical_hash)

    # --- type validation ---

    def test_invalid_provider_id_raises(self):
        with self.assertRaises(ValueError):
            produce_dry_run_receipt(provider_id="", request_id="r", request_digest="d", capability_token="c", evidence_binding="e")

    def test_invalid_request_id_raises(self):
        with self.assertRaises(ValueError):
            produce_dry_run_receipt(provider_id="mock-finance", request_id="", request_digest="d", capability_token="c", evidence_binding="e")

    # --- capability_bits is deterministic ---

    def test_capability_bits_deterministic(self):
        a = produce_dry_run_receipt(**self._args())
        b = produce_dry_run_receipt(**self._args())
        self.assertEqual(a.capability_bits, b.capability_bits)

    # --- evidence_binding_hash is deterministic ---

    def test_evidence_binding_hash_deterministic(self):
        a = produce_dry_run_receipt(**self._args())
        b = produce_dry_run_receipt(**self._args())
        self.assertEqual(a.evidence_binding_hash, b.evidence_binding_hash)


class ProviderFailureReceiptTests(unittest.TestCase):
    """Tests for deterministic failure receipt production."""

    def _args(self):
        return dict(
            provider_id="mock-finance",
            request_id="req-001",
            failure_reason="preflight_failed",
            rejected_at_gate="preflight",
        )

    # --- successful failure receipt ---

    def test_failure_receipt_produced(self):
        receipt = produce_failure_receipt(**self._args())
        self.assertIsInstance(receipt, ProviderFailureReceipt)

    def test_failure_receipt_has_failure_id(self):
        receipt = produce_failure_receipt(**self._args())
        self.assertTrue(len(receipt.failure_id) == 64)

    def test_failure_receipt_has_canonical_hash(self):
        receipt = produce_failure_receipt(**self._args())
        self.assertTrue(len(receipt.canonical_hash) == 64)

    # --- deterministic ---

    def test_failure_receipt_deterministic(self):
        a = produce_failure_receipt(**self._args())
        b = produce_failure_receipt(**self._args())
        self.assertEqual(a.failure_id, b.failure_id)
        self.assertEqual(a.canonical_hash, b.canonical_hash)

    def test_failure_different_reason_different_hash(self):
        a = produce_failure_receipt(**self._args())
        args_b = self._args()
        args_b["failure_reason"] = "capability_rejected"
        b = produce_failure_receipt(**args_b)
        self.assertNotEqual(a.canonical_hash, b.canonical_hash)

    def test_failure_different_gate_different_hash(self):
        a = produce_failure_receipt(**self._args())
        args_b = self._args()
        args_b["rejected_at_gate"] = "request_contract"
        b = produce_failure_receipt(**args_b)
        self.assertNotEqual(a.canonical_hash, b.canonical_hash)

    # --- no wall-clock ---

    def test_failure_no_wall_clock(self):
        receipt = produce_failure_receipt(**self._args())
        self.assertEqual(receipt.created_at, "1970-01-01T00:00:00Z")

    # --- field values ---

    def test_failure_receipt_fields(self):
        receipt = produce_failure_receipt(**self._args())
        self.assertEqual(receipt.provider_id, "mock-finance")
        self.assertEqual(receipt.request_id, "req-001")
        self.assertEqual(receipt.failure_reason, "preflight_failed")
        self.assertEqual(receipt.rejected_at_gate, "preflight")
        self.assertEqual(receipt.module_version, "v1")

    # --- as_dict ---

    def test_failure_as_dict(self):
        receipt = produce_failure_receipt(**self._args())
        d = receipt.as_dict()
        self.assertEqual(d["provider_id"], "mock-finance")
        self.assertEqual(d["failure_reason"], "preflight_failed")

    def test_failure_as_dict_no_raw_payload(self):
        receipt = produce_failure_receipt(**self._args())
        d = receipt.as_dict()
        for forbidden in ("raw_payload", "raw_data", "secret"):
            self.assertNotIn(forbidden, d)

    # --- different providers produce different failures ---

    def test_different_provider_different_failure_hash(self):
        a = produce_failure_receipt(provider_id="mock-finance", request_id="r1", failure_reason="f", rejected_at_gate="g")
        b = produce_failure_receipt(provider_id="mock-weather", request_id="r1", failure_reason="f", rejected_at_gate="g")
        self.assertNotEqual(a.canonical_hash, b.canonical_hash)


if __name__ == "__main__":
    unittest.main()
