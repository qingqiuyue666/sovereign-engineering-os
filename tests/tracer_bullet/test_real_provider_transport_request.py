"""Tracer-bullet tests for provider request contract validation."""

import unittest

from tools.provider_transport.provider_request_contract import (
    ProviderRequestContract,
    validate_provider_request,
)


class ProviderRequestValidationTests(unittest.TestCase):
    """Tests for validate_provider_request — the entry gate for all transports."""

    def _valid(self):
        return {
            "provider_id": "mock-finance",
            "request_id": "req-001",
            "capability_token": "fetch_price,validate_asset",
            "evidence_binding": "ev-binding-hash-001",
            "dry_run": True,
            "live_mode": False,
            "network_mode": False,
        }

    # --- valid request ---

    def test_valid_request_accepted(self):
        result = validate_provider_request(self._valid())
        self.assertTrue(result["valid"], result["failures"])
        self.assertIsInstance(result["contract"], ProviderRequestContract)
        self.assertEqual(result["contract"].provider_id, "mock-finance")

    def test_valid_request_has_request_digest(self):
        result = validate_provider_request(self._valid())
        self.assertTrue(len(result["contract"].request_digest) == 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in result["contract"].request_digest))

    def test_valid_request_deterministic(self):
        a = validate_provider_request(self._valid())
        b = validate_provider_request(self._valid())
        self.assertEqual(a["contract"].request_digest, b["contract"].request_digest)

    # --- missing required fields ---

    def test_missing_provider_id_rejected(self):
        p = self._valid()
        del p["provider_id"]
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("missing_required_field: provider_id", result["failures"])

    def test_missing_request_id_rejected(self):
        p = self._valid()
        del p["request_id"]
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("missing_required_field: request_id", result["failures"])

    def test_missing_capability_token_rejected(self):
        p = self._valid()
        del p["capability_token"]
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("missing_required_field: capability_token", result["failures"])

    def test_missing_evidence_binding_rejected(self):
        p = self._valid()
        del p["evidence_binding"]
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("missing_required_field: evidence_binding", result["failures"])

    def test_missing_dry_run_rejected(self):
        p = self._valid()
        del p["dry_run"]
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("missing_required_field: dry_run", result["failures"])

    def test_missing_live_mode_rejected(self):
        p = self._valid()
        del p["live_mode"]
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("missing_required_field: live_mode", result["failures"])

    def test_missing_network_mode_rejected(self):
        p = self._valid()
        del p["network_mode"]
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("missing_required_field: network_mode", result["failures"])

    # --- forbidden provider ---

    def test_live_broker_rejected(self):
        p = self._valid()
        p["provider_id"] = "live-broker"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("forbidden_provider" in f for f in result["failures"]))

    def test_live_exchange_rejected(self):
        p = self._valid()
        p["provider_id"] = "live-exchange"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("forbidden_provider" in f for f in result["failures"]))

    def test_live_payment_rejected(self):
        p = self._valid()
        p["provider_id"] = "live-payment"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("forbidden_provider" in f for f in result["failures"]))

    def test_live_bank_rejected(self):
        p = self._valid()
        p["provider_id"] = "live-bank"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("forbidden_provider" in f for f in result["failures"]))

    # --- unknown provider ---

    def test_unknown_provider_rejected(self):
        p = self._valid()
        p["provider_id"] = "unknown-gpt-cloud"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("unknown_provider" in f for f in result["failures"]))

    # --- dry_run gates ---

    def test_dry_run_false_rejected(self):
        p = self._valid()
        p["dry_run"] = False
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("dry_run_must_be_true", result["failures"])

    def test_dry_run_non_bool_rejected(self):
        p = self._valid()
        p["dry_run"] = "true"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("dry_run_must_be_bool", result["failures"])

    # --- live_mode gates ---

    def test_live_mode_true_rejected(self):
        p = self._valid()
        p["live_mode"] = True
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("live_mode_must_be_false", result["failures"])

    def test_live_mode_non_bool_rejected(self):
        p = self._valid()
        p["live_mode"] = "false"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("live_mode_must_be_bool", result["failures"])

    # --- network_mode gates ---

    def test_network_mode_true_rejected(self):
        p = self._valid()
        p["network_mode"] = True
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("network_mode_must_be_false", result["failures"])

    def test_network_mode_non_bool_rejected(self):
        p = self._valid()
        p["network_mode"] = 1
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertIn("network_mode_must_be_bool", result["failures"])

    # --- forbidden capability in token ---

    def test_live_trade_capability_rejected(self):
        p = self._valid()
        p["capability_token"] = "fetch_price,live_trade"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("forbidden_capability" in f for f in result["failures"]))

    def test_live_withdrawal_capability_rejected(self):
        p = self._valid()
        p["capability_token"] = "live_withdrawal,validate_asset"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("forbidden_capability" in f for f in result["failures"]))

    # --- raw payload field rejection ---

    def test_raw_payload_field_rejected(self):
        p = self._valid()
        p["raw_payload"] = "some raw data"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("raw_payload" in f for f in result["failures"]))

    def test_raw_response_field_rejected(self):
        p = self._valid()
        p["raw_response"] = "some response"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("raw_payload" in f for f in result["failures"]))

    def test_raw_data_field_rejected(self):
        p = self._valid()
        p["raw_data"] = "data"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("raw_payload" in f for f in result["failures"]))

    # --- secret marker detection ---

    def test_secret_marker_in_field_rejected(self):
        p = self._valid()
        p["provider_id"] = "mock-finance"
        p["extra_field"] = "my_secret_key_here"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("secret_marker_detected" in f for f in result["failures"]))

    def test_api_key_marker_rejected(self):
        p = self._valid()
        p["note"] = "use api_key for auth"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("secret_marker_detected" in f for f in result["failures"]))

    def test_password_marker_rejected(self):
        p = self._valid()
        p["config"] = "password=xyz"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("secret_marker_detected" in f for f in result["failures"]))

    def test_credential_marker_rejected(self):
        p = self._valid()
        p["auth"] = "credential_store"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("secret_marker_detected" in f for f in result["failures"]))

    # --- env marker detection ---

    def test_env_marker_rejected(self):
        p = self._valid()
        p["source"] = "from .env file"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("env_marker_detected" in f for f in result["failures"]))

    def test_dotenv_marker_rejected(self):
        p = self._valid()
        p["config_ref"] = "load_dotenv"
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("env_marker_detected" in f for f in result["failures"]))

    # --- non-mapping payload ---

    def test_non_mapping_rejected(self):
        result = validate_provider_request(["list", "payload"])
        self.assertFalse(result["valid"])
        self.assertIn("payload_must_be_mapping", result["failures"])

    def test_none_payload_rejected(self):
        result = validate_provider_request(None)
        self.assertFalse(result["valid"])
        self.assertIn("payload_must_be_mapping", result["failures"])

    # --- provider_id type validation ---

    def test_provider_id_empty_rejected(self):
        p = self._valid()
        p["provider_id"] = ""
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("provider_id" in f for f in result["failures"]))

    def test_provider_id_none_rejected(self):
        p = self._valid()
        p["provider_id"] = None
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("provider_id" in f for f in result["failures"]))

    # --- request_id type validation ---

    def test_request_id_empty_rejected(self):
        p = self._valid()
        p["request_id"] = ""
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("request_id" in f for f in result["failures"]))

    # --- capability_token type validation ---

    def test_capability_token_empty_rejected(self):
        p = self._valid()
        p["capability_token"] = ""
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("capability_token" in f for f in result["failures"]))

    # --- evidence_binding validation ---

    def test_evidence_binding_empty_rejected(self):
        p = self._valid()
        p["evidence_binding"] = ""
        result = validate_provider_request(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("evidence_binding" in f for f in result["failures"]))

    # --- all four known providers accepted ---

    def test_mock_finance_accepted(self):
        p = self._valid()
        p["provider_id"] = "mock-finance"
        result = validate_provider_request(p)
        self.assertTrue(result["valid"])

    def test_mock_market_data_accepted(self):
        p = self._valid()
        p["provider_id"] = "mock-market-data"
        result = validate_provider_request(p)
        self.assertTrue(result["valid"])

    def test_mock_news_accepted(self):
        p = self._valid()
        p["provider_id"] = "mock-news"
        result = validate_provider_request(p)
        self.assertTrue(result["valid"])

    def test_mock_weather_accepted(self):
        p = self._valid()
        p["provider_id"] = "mock-weather"
        result = validate_provider_request(p)
        self.assertTrue(result["valid"])

    # --- contract fields populated correctly ---

    def test_contract_dry_run_is_true(self):
        result = validate_provider_request(self._valid())
        self.assertTrue(result["contract"].dry_run)

    def test_contract_live_mode_is_false(self):
        result = validate_provider_request(self._valid())
        self.assertFalse(result["contract"].live_mode)

    def test_contract_network_mode_is_false(self):
        result = validate_provider_request(self._valid())
        self.assertFalse(result["contract"].network_mode)

    def test_contract_capabilities_parsed(self):
        result = validate_provider_request(self._valid())
        self.assertIn("fetch_price", result["contract"].capabilities)
        self.assertIn("validate_asset", result["contract"].capabilities)


if __name__ == "__main__":
    unittest.main()
