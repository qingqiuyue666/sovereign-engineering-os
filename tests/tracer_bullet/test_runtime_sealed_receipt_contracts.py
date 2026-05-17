import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.runtime_sealed_receipt_contracts import (
    RuntimeSealedReceiptContractViolation,
    validate_postcheck_receipt,
    validate_receipt_chain,
    validate_runtime_sealed_receipt_policy,
    validate_transport_attempt_receipt,
)

POLICY_PATH = Path("governance/runtime/runtime_sealed_receipt_v1.json")
FIXTURE_PATH = Path("governance/runtime/fixtures/runtime_sealed_receipt_fixtures_v1.json")
EXPECTED_HEALTH = "health: test-root-integrity test-leak-prevention-foundation test-security-truth-substrate test-operator-task-ledger test-v12-foundation test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check"


class RuntimeSealedReceiptContractsTests(unittest.TestCase):
    def load_policy(self):
        self.assertTrue(POLICY_PATH.is_file(), str(POLICY_PATH))
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def load_fixtures(self):
        self.assertTrue(FIXTURE_PATH.is_file(), str(FIXTURE_PATH))
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def valid_by_validator(self):
        return {item["validator"]: item["record"] for item in self.load_fixtures()["valid_records"]}

    def test_policy_map_is_accepted_contract_only(self):
        result = validate_runtime_sealed_receipt_policy(self.load_policy())
        self.assertTrue(result.accepted, result.failures)
        self.assertEqual(result.verdict, "accepted_contract_only")

    def test_transport_receipt_requires_seal_postcheck_and_quarantine_link(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_transport_attempt_receipt"])
        payload["sealed"] = False
        payload["postcheck_required"] = False
        payload["failure_quarantine_link_required"] = False
        result = validate_transport_attempt_receipt(payload)
        self.assertIn("sealed_required", result.failures)
        self.assertIn("postcheck_required", result.failures)
        self.assertIn("failure_quarantine_link_required", result.failures)

    def test_receipt_chain_requires_all_links(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_receipt_chain"])
        payload["policy_receipt_ref"] = ""
        payload["chain_complete"] = False
        result = validate_receipt_chain(payload)
        self.assertIn("policy_receipt_ref_required", result.failures)
        self.assertIn("chain_complete_required", result.failures)

    def test_postcheck_requires_passed_result(self):
        payload = copy.deepcopy(self.valid_by_validator()["validate_postcheck_receipt"])
        payload["postcheck_result"] = "failed"
        result = validate_postcheck_receipt(payload)
        self.assertFalse(result.accepted)
        self.assertIn("postcheck_result_not_passed", result.failures)

    def test_non_mapping_payload_raises(self):
        with self.assertRaises(RuntimeSealedReceiptContractViolation):
            validate_runtime_sealed_receipt_policy(["not", "mapping"])

    def test_makefile_declares_runtime_sealed_receipt_gate(self):
        text = Path("Makefile").read_text(encoding="utf-8")
        self.assertIn("test-runtime-sealed-receipt", text)
        self.assertIn(EXPECTED_HEALTH, text)
        self.assertLess(EXPECTED_HEALTH.index("test-gated-provider-transport"), EXPECTED_HEALTH.index("test-real-runtime-provider-transport-execution"))
        self.assertLess(EXPECTED_HEALTH.index("test-real-runtime-provider-transport-execution"), EXPECTED_HEALTH.index("test-runtime-sealed-receipt"))
        self.assertLess(EXPECTED_HEALTH.index("test-protected-evidence-storage"), EXPECTED_HEALTH.index("test-protected-evidence-storage-implementation"))
        self.assertLess(EXPECTED_HEALTH.index("test-real-merkle-proof-realization"), EXPECTED_HEALTH.index("test-generic-payload-full-enforcement"))

    def test_source_does_not_introduce_live_transport_surface(self):
        source = Path("kernel/runtime/runtime_sealed_receipt_contracts.py").read_text(encoding="utf-8")
        for marker in ("requests", "httpx", "socket.", "subprocess", "sqlite3", "write_text("):
            self.assertNotIn(marker, source)

    def test_runbook_exists_and_records_receipt_boundary(self):
        text = Path("docs/runbooks/runtime_sealed_receipt_v1.md").read_text(encoding="utf-8")
        for marker in ("RUNTIME_SEALED_RECEIPT_CONTRACT_READY", "transport attempt receipt", "postcheck receipt", "receipt chain"):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
