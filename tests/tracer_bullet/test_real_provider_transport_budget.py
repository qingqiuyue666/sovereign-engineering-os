"""Tracer-bullet tests for provider transport budget/rate-limit and preflight."""

import unittest

from tools.provider_transport.provider_rate_limit_budget import (
    RateLimitBudgetResult,
    validate_rate_limit_budget,
    DEFAULT_BUDGET_LIMITS,
    DEFAULT_RATE_LIMITS,
)
from tools.provider_transport.provider_transport_preflight import (
    PreflightResult,
    run_provider_transport_preflight,
)
from tools.provider_transport.provider_adapter_registry import (
    ProviderAdapterDescriptor,
    register_provider_adapter,
)


class RateLimitBudgetTests(unittest.TestCase):
    """Tests for budget and rate-limit validation."""

    # --- valid budget ---

    def test_valid_within_budget(self):
        result = validate_rate_limit_budget("mock-finance", budget_consumed=100.0, budget_limit=1000.0)
        self.assertTrue(result.valid, result.failures)

    def test_default_budget_limit_applied(self):
        result = validate_rate_limit_budget("mock-finance")
        self.assertEqual(result.budget_limit, DEFAULT_BUDGET_LIMITS["mock-finance"])

    def test_default_rate_limit_applied(self):
        result = validate_rate_limit_budget("mock-news")
        self.assertEqual(result.rate_limit, DEFAULT_RATE_LIMITS["mock-news"])

    def test_all_known_providers_have_budget_limits(self):
        for pid in ["mock-finance", "mock-market-data", "mock-news", "mock-weather"]:
            result = validate_rate_limit_budget(pid)
            self.assertGreater(result.budget_limit, 0, f"{pid} should have non-zero budget limit")

    def test_all_known_providers_have_rate_limits(self):
        for pid in ["mock-finance", "mock-market-data", "mock-news", "mock-weather"]:
            result = validate_rate_limit_budget(pid)
            self.assertGreater(result.rate_limit, 0, f"{pid} should have non-zero rate limit")

    # --- budget exceeded ---

    def test_budget_exceeded_rejected(self):
        result = validate_rate_limit_budget("mock-finance", budget_consumed=2000.0, budget_limit=1000.0)
        self.assertFalse(result.valid)
        self.assertTrue(any("budget_exceeded" in f for f in result.failures))

    def test_budget_exactly_at_limit_accepted(self):
        result = validate_rate_limit_budget("mock-finance", budget_consumed=1000.0, budget_limit=1000.0)
        self.assertTrue(result.valid, result.failures)

    def test_budget_remaining_calculated(self):
        result = validate_rate_limit_budget("mock-finance", budget_consumed=300.0, budget_limit=1000.0)
        self.assertEqual(result.budget_remaining, 700.0)

    def test_budget_remaining_clamped_to_zero(self):
        result = validate_rate_limit_budget("mock-finance", budget_consumed=2000.0, budget_limit=1000.0)
        self.assertEqual(result.budget_remaining, 0.0)

    # --- rate limit exhausted ---

    def test_rate_limit_exhausted_rejected(self):
        result = validate_rate_limit_budget("mock-finance", rate_limit_consumed=100, rate_limit=100)
        self.assertFalse(result.valid)
        self.assertTrue(any("rate_limit_exhausted" in f for f in result.failures))

    def test_rate_limit_available_accepted(self):
        result = validate_rate_limit_budget("mock-finance", rate_limit_consumed=50, rate_limit=100)
        self.assertTrue(result.valid, result.failures)

    def test_rate_limit_remaining_calculated(self):
        result = validate_rate_limit_budget("mock-finance", rate_limit_consumed=30, rate_limit=100)
        self.assertEqual(result.rate_limit_remaining, 70)

    # --- type validation ---

    def test_negative_budget_consumed_rejected(self):
        result = validate_rate_limit_budget("mock-finance", budget_consumed=-10.0)
        self.assertFalse(result.valid)

    def test_negative_rate_limit_consumed_rejected(self):
        result = validate_rate_limit_budget("mock-finance", rate_limit_consumed=-5)
        self.assertFalse(result.valid)

    def test_non_numeric_budget_rejected(self):
        result = validate_rate_limit_budget("mock-finance", budget_limit=-1.0)
        self.assertFalse(result.valid)

    def test_empty_provider_id_rejected(self):
        result = validate_rate_limit_budget("")
        self.assertFalse(result.valid)
        self.assertTrue(any("provider_id" in f for f in result.failures))

    # --- result structure ---

    def test_result_as_dict(self):
        result = validate_rate_limit_budget("mock-finance", budget_consumed=100.0, budget_limit=1000.0, rate_limit_consumed=5, rate_limit=100)
        d = result.as_dict()
        self.assertTrue(d["valid"])
        self.assertEqual(d["budget_limit"], 1000.0)
        self.assertEqual(d["rate_limit"], 100)

    def test_result_immutable(self):
        result = validate_rate_limit_budget("mock-finance")
        with self.assertRaises(Exception):
            result.valid = False  # frozen dataclass

    # --- budget consumed contributes to uniqueness ---

    def test_different_budget_different_in_result(self):
        a = validate_rate_limit_budget("mock-finance", budget_consumed=0.0, budget_limit=1000.0)
        b = validate_rate_limit_budget("mock-finance", budget_consumed=100.0, budget_limit=1000.0)
        self.assertNotEqual(a.budget_remaining, b.budget_remaining)


class PreflightTests(unittest.TestCase):
    """Tests for preflight gate checks."""

    def setUp(self):
        """Register adapters for preflight tests."""
        for pid in ["mock-finance", "mock-market-data", "mock-news", "mock-weather"]:
            try:
                register_provider_adapter(ProviderAdapterDescriptor(
                    provider_id=pid,
                    capabilities=frozenset({"mock_execute"}),
                    boundary_ref="boundary-v1",
                    enabled=False,
                    dry_run_only=True,
                    no_network=True,
                ))
            except Exception:
                pass  # Already registered

    def _valid_args(self):
        return dict(
            provider_id="mock-finance",
            capability_token="fetch_price",
            evidence_binding_present=True,
            dry_run=True,
            live_mode=False,
            network_mode=False,
        )

    # --- valid preflight ---

    def test_valid_preflight_passes(self):
        result = run_provider_transport_preflight(**self._valid_args())
        self.assertTrue(result.passed, result.failures)

    def test_all_gates_pass_for_valid_request(self):
        result = run_provider_transport_preflight(**self._valid_args())
        self.assertTrue(all(result.gates.values()),
                        f"Some gates failed: {[(k, v) for k, v in result.gates.items() if not v]}")

    # --- provider checks ---

    def test_unknown_provider_fails_preflight(self):
        args = self._valid_args()
        args["provider_id"] = "unknown-provider"
        result = run_provider_transport_preflight(**args)
        self.assertFalse(result.passed)
        self.assertIn("provider_not_known", result.failures)

    def test_forbidden_provider_fails_preflight(self):
        args = self._valid_args()
        args["provider_id"] = "live-broker"
        result = run_provider_transport_preflight(**args)
        self.assertFalse(result.passed)
        self.assertIn("provider_is_forbidden", result.failures)

    # --- capability token ---

    def test_missing_capability_token_fails(self):
        args = self._valid_args()
        args["capability_token"] = ""
        result = run_provider_transport_preflight(**args)
        self.assertFalse(result.passed)
        self.assertIn("capability_token_missing", result.failures)

    def test_forbidden_capability_in_token_fails(self):
        args = self._valid_args()
        args["capability_token"] = "live_trade"
        result = run_provider_transport_preflight(**args)
        self.assertFalse(result.passed)
        self.assertTrue(any("forbidden_capability_detected" in f for f in result.failures))

    # --- evidence binding ---

    def test_missing_evidence_binding_fails(self):
        args = self._valid_args()
        args["evidence_binding_present"] = False
        result = run_provider_transport_preflight(**args)
        self.assertFalse(result.passed)
        self.assertIn("evidence_binding_missing", result.failures)

    # --- mode gates ---

    def test_dry_run_false_fails(self):
        args = self._valid_args()
        args["dry_run"] = False
        result = run_provider_transport_preflight(**args)
        self.assertFalse(result.passed)
        self.assertIn("dry_run_required", result.failures)

    def test_live_mode_true_fails(self):
        args = self._valid_args()
        args["live_mode"] = True
        result = run_provider_transport_preflight(**args)
        self.assertFalse(result.passed)
        self.assertIn("live_mode_rejected", result.failures)

    def test_network_mode_true_fails(self):
        args = self._valid_args()
        args["network_mode"] = True
        result = run_provider_transport_preflight(**args)
        self.assertFalse(result.passed)
        self.assertIn("network_mode_rejected", result.failures)

    # --- budget/rate-limit gates ---

    def test_budget_exceeded_fails(self):
        args = self._valid_args()
        args["budget_remaining"] = -1.0
        args["budget_limit"] = 100.0
        result = run_provider_transport_preflight(**args)
        self.assertFalse(result.gates["budget_within_limit"])

    def test_rate_limit_exhausted_fails(self):
        args = self._valid_args()
        args["rate_limit_remaining"] = 0
        args["budget_limit"] = 100.0  # Signal rate-limit is configured
        result = run_provider_transport_preflight(**args)
        self.assertFalse(result.gates["rate_limit_available"])

    # --- PreflightResult structure ---

    def test_preflight_result_as_dict(self):
        result = run_provider_transport_preflight(**self._valid_args())
        d = result.as_dict()
        self.assertTrue(d["passed"])
        self.assertEqual(len(d["failures"]), 0)
        self.assertTrue(len(d["gates"]) >= 10)

    def test_preflight_result_failures_are_tuple(self):
        result = run_provider_transport_preflight(**self._valid_args())
        self.assertIsInstance(result.failures, tuple)

    def test_preflight_all_known_providers_pass(self):
        for pid in ["mock-finance", "mock-market-data", "mock-news", "mock-weather"]:
            args = self._valid_args()
            args["provider_id"] = pid
            result = run_provider_transport_preflight(**args)
            self.assertTrue(result.passed, f"{pid} preflight failed: {result.failures}")

    def test_preflight_deterministic_same_input(self):
        a = run_provider_transport_preflight(**self._valid_args())
        b = run_provider_transport_preflight(**self._valid_args())
        self.assertEqual(a.passed, b.passed)
        self.assertEqual(a.failures, b.failures)

    # --- adapter not registered ---

    def test_all_known_providers_registered_in_setup(self):
        for pid in ["mock-finance", "mock-market-data", "mock-news", "mock-weather"]:
            args = self._valid_args()
            args["provider_id"] = pid
            result = run_provider_transport_preflight(**args)
            self.assertTrue(result.gates.get("adapter_registered", False),
                            f"{pid} adapter not registered")


if __name__ == "__main__":
    unittest.main()
