"""Tracer-bullet tests for local runtime promotion gate."""

import unittest
from pathlib import Path

from kernel.runtime.local_runtime_promotion_gate import (
    LocalRuntimePromotionResult,
    evaluate_promotion_gate,
    validate_promotion_result,
)

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64
VALID_DIGEST_3 = "sha256:" + "c" * 64


def _all_boundary_flags_passed():
    return {
        "dry_run_only": True,
        "no_network": True,
        "no_live_provider_calls": True,
        "no_subprocess": True,
        "no_secret_or_env_reads": True,
        "no_sqlite_mutation": True,
        "no_production_autonomy": True,
    }


def _valid_base_args(**overrides):
    args = {
        "runtime_accepted": True,
        "guard_accepted": True,
        "boundary_flags": _all_boundary_flags_passed(),
        "provider_dry_run_receipt_exists": True,
        "provider_transport_attempted": True,
        "audit_chain_head_exists": True,
        "runtime_receipt_hash": VALID_DIGEST,
        "review_packet_hash": VALID_DIGEST_2,
        "observed_at": "2026-01-01T00:00:00Z",
    }
    args.update(overrides)
    return args


class PromotionGateAcceptTests(unittest.TestCase):
    """Test that accepted local runtime results are eligible for human review."""

    def test_all_conditions_met_eligible_for_human_review(self):
        result = evaluate_promotion_gate(**_valid_base_args())
        self.assertTrue(result.accepted, result.reasons)
        self.assertEqual(result.decision, "eligible_for_human_review")
        self.assertTrue(validate_promotion_result(result))

    def test_promotion_receipt_hash_is_deterministic(self):
        first = evaluate_promotion_gate(**_valid_base_args(observed_at="2026-01-01T00:00:00Z"))
        second = evaluate_promotion_gate(**_valid_base_args(observed_at="2027-06-15T12:00:00Z"))
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.promotion_receipt_hash, second.promotion_receipt_hash)

    def test_no_provider_transport_attempted_without_receipt_still_accepted(self):
        """When provider transport was NOT attempted, missing receipt is not an error."""
        result = evaluate_promotion_gate(**_valid_base_args(
            provider_transport_attempted=False,
            provider_dry_run_receipt_exists=False,
        ))
        self.assertTrue(result.accepted, result.reasons)

    def test_boundary_flags_dry_run_only_is_required(self):
        flags = _all_boundary_flags_passed()
        flags.pop("dry_run_only")
        result = evaluate_promotion_gate(**_valid_base_args(boundary_flags=flags))
        self.assertFalse(result.accepted)
        self.assertIn("boundary_flag_not_proven:dry_run_only", result.reasons)


class PromotionGateRejectTests(unittest.TestCase):
    """Test fail-closed rejection paths."""

    def test_rejected_runtime_result_fail_closed(self):
        result = evaluate_promotion_gate(**_valid_base_args(runtime_accepted=False))
        self.assertFalse(result.accepted)
        self.assertEqual(result.decision, "rejected")
        self.assertIn("runtime_result_not_accepted", result.reasons)

    def test_rejected_guard_result_fail_closed(self):
        result = evaluate_promotion_gate(**_valid_base_args(guard_accepted=False))
        self.assertFalse(result.accepted)
        self.assertIn("guard_result_not_accepted", result.reasons)

    def test_missing_provider_receipt_when_transport_attempted_fail_closed(self):
        result = evaluate_promotion_gate(**_valid_base_args(
            provider_transport_attempted=True,
            provider_dry_run_receipt_exists=False,
        ))
        self.assertFalse(result.accepted)
        self.assertIn("provider_transport_attempted_but_receipt_missing", result.reasons)

    def test_missing_audit_chain_head_fail_closed(self):
        result = evaluate_promotion_gate(**_valid_base_args(audit_chain_head_exists=False))
        self.assertFalse(result.accepted)
        self.assertIn("audit_chain_head_missing", result.reasons)

    def test_unsafe_boundary_flag_fail_closed(self):
        unsafe_flags = {
            "dry_run_only": False,
            "no_network": False,
            "no_live_provider_calls": True,
            "no_subprocess": True,
            "no_secret_or_env_reads": True,
        }
        result = evaluate_promotion_gate(**_valid_base_args(boundary_flags=unsafe_flags))
        self.assertFalse(result.accepted)
        self.assertTrue(any(r.startswith("boundary_flag_not_proven:") for r in result.reasons))

    def test_invalid_runtime_receipt_hash_raises_value_error(self):
        with self.assertRaises(ValueError):
            evaluate_promotion_gate(**_valid_base_args(runtime_receipt_hash="bad-hash"))

    def test_observed_at_excluded_from_promotion_hash(self):
        first = evaluate_promotion_gate(
            **_valid_base_args(
                runtime_accepted=False,
                observed_at="2026-06-01T00:00:00Z",
            )
        )
        second = evaluate_promotion_gate(
            **_valid_base_args(
                runtime_accepted=False,
                observed_at="2027-06-01T00:00:00Z",
            )
        )
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.promotion_receipt_hash, second.promotion_receipt_hash)


class PromotionGateResultValidationTests(unittest.TestCase):
    def test_validate_accepts_valid_result(self):
        result = evaluate_promotion_gate(**_valid_base_args())
        self.assertTrue(validate_promotion_result(result))

    def test_validate_rejects_non_result(self):
        self.assertFalse(validate_promotion_result(None))
        self.assertFalse(validate_promotion_result("not-a-result"))


class PromotionGateSourceSafetyTests(unittest.TestCase):
    def test_source_does_not_import_forbidden_surfaces(self):
        source = Path("kernel/runtime/local_runtime_promotion_gate.py").read_text(encoding="utf-8")
        for marker in ("import subprocess", "import socket", "import requests",
                       "import httpx", "import sqlite3"):
            self.assertNotIn(marker, source)
        for marker in ("os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
