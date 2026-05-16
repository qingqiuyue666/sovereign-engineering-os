import json
import unittest
from pathlib import Path

from kernel.security.anti_exfiltration_gate import validate_outbound_payload
from kernel.security.secret_scanner import CoreSecretScanner

POLICY_PATH = Path("governance/security/anti_exfiltration_policy_v1.json")


class AntiExfiltrationGateTests(unittest.TestCase):
    def test_policy_uses_core_scanner(self):
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["scanner_engine"], "CoreSecretScanner")
        self.assertTrue(payload["read_only_gate"])
        self.assertTrue(payload["fail_closed"])

    def test_blocks_sensitive_text_to_provider_request(self):
        result = validate_outbound_payload("token = value", sink="provider_request", path="reports/out.txt")
        self.assertFalse(result.accepted)
        self.assertIn("payload_blocked", result.failures)

    def test_blocks_sensitive_mapping_to_report(self):
        result = validate_outbound_payload({"raw_prompt": "value"}, sink="run_report", path="reports/out.json")
        self.assertFalse(result.accepted)
        self.assertTrue(result.findings)

    def test_rejects_unknown_sink(self):
        result = validate_outbound_payload("hello", sink="unknown")
        self.assertFalse(result.accepted)
        self.assertIn("sink_not_declared", result.failures)

    def test_accepts_clean_payload_with_injected_scanner(self):
        result = validate_outbound_payload({"message": "hello"}, sink="run_report", scanner=CoreSecretScanner())
        self.assertTrue(result.accepted, result.findings)


if __name__ == "__main__":
    unittest.main()
