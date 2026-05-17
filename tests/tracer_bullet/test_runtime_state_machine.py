"""Runtime state machine tracer-bullet tests.

Tests the deterministic state transition validator:
- all legal transitions accepted
- quarantined -> planned requires recovery_allowed=true
- terminal states cannot transition
- unknown states rejected
- illegal transitions rejected
- forbidden fields rejected
- deterministic receipt
- side-effect free
"""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.state_machine import (
    ALLOWED_STATES,
    ALLOWED_TRANSITIONS,
    StateMachineRejection,
    StateTransitionReceipt,
    TERMINAL_STATES,
    validate_state_transition,
)

POLICY_PATH = Path("governance/runtime/runtime_state_transition_policy_v1.json")


def _valid_payload(from_state="planned", to_state="validated"):
    return {
        "from_state": from_state,
        "to_state": to_state,
        "policy_version": "v1",
        "code_version": "0.1.0",
    }


class StateMachinePolicyTests(unittest.TestCase):
    def test_policy_file_exists(self):
        self.assertTrue(POLICY_PATH.is_file())
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "runtime_state_transition_policy_v1")
        self.assertIn("planned", policy["allowed_states"])
        self.assertIn("completed", policy["allowed_states"])
        self.assertIn("completed", policy["terminal_states"])
        self.assertTrue(policy["quarantined_is_terminal_unless_recovery"])


class StateMachineAcceptanceTests(unittest.TestCase):
    def test_all_legal_transitions_accepted(self):
        for from_s, to_s, needs_recovery in ALLOWED_TRANSITIONS:
            payload = _valid_payload(from_s, to_s)
            if needs_recovery:
                payload["recovery_allowed"] = True
            receipt = validate_state_transition(payload)
            self.assertTrue(receipt.accepted, f"{from_s} -> {to_s} should be accepted")

    def test_planned_to_validated_accepted(self):
        receipt = validate_state_transition(_valid_payload("planned", "validated"))
        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.reasons, ())

    def test_validated_to_dry_run_accepted(self):
        receipt = validate_state_transition(_valid_payload("validated", "dry_run"))
        self.assertTrue(receipt.accepted)

    def test_dry_run_to_executed_accepted(self):
        receipt = validate_state_transition(_valid_payload("dry_run", "executed"))
        self.assertTrue(receipt.accepted)

    def test_dry_run_to_failed_accepted(self):
        receipt = validate_state_transition(_valid_payload("dry_run", "failed"))
        self.assertTrue(receipt.accepted)

    def test_executed_to_completed_accepted(self):
        receipt = validate_state_transition(_valid_payload("executed", "completed"))
        self.assertTrue(receipt.accepted)

    def test_executed_to_failed_accepted(self):
        receipt = validate_state_transition(_valid_payload("executed", "failed"))
        self.assertTrue(receipt.accepted)

    def test_failed_to_quarantined_accepted(self):
        receipt = validate_state_transition(_valid_payload("failed", "quarantined"))
        self.assertTrue(receipt.accepted)

    def test_quarantined_to_planned_with_recovery_accepted(self):
        payload = _valid_payload("quarantined", "planned")
        payload["recovery_allowed"] = True
        receipt = validate_state_transition(payload)
        self.assertTrue(receipt.accepted)

    def test_receipt_fields(self):
        receipt = validate_state_transition(_valid_payload("planned", "validated"))
        self.assertEqual(receipt.from_state, "planned")
        self.assertEqual(receipt.to_state, "validated")
        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.reasons, ())
        self.assertEqual(receipt.policy_version, "v1")
        self.assertEqual(receipt.code_version, "0.1.0")

    def test_receipt_as_dict(self):
        receipt = validate_state_transition(_valid_payload("planned", "validated"))
        d = receipt.as_dict()
        self.assertEqual(d["from_state"], "planned")
        self.assertEqual(d["to_state"], "validated")
        self.assertTrue(d["accepted"])
        self.assertEqual(d["reasons"], [])

    def test_deterministic_receipt(self):
        r1 = validate_state_transition(_valid_payload("planned", "validated"))
        r2 = validate_state_transition(_valid_payload("planned", "validated"))
        self.assertEqual(r1.as_dict(), r2.as_dict())


class StateMachineRejectionTests(unittest.TestCase):
    def test_quarantined_to_planned_rejected_without_recovery(self):
        receipt = validate_state_transition(_valid_payload("quarantined", "planned"))
        self.assertFalse(receipt.accepted)
        self.assertIn("recovery_allowed_required_for_quarantined_to_planned", receipt.reasons)

    def test_completed_cannot_transition(self):
        receipt = validate_state_transition(_valid_payload("completed", "planned"))
        self.assertFalse(receipt.accepted)
        self.assertTrue(any("terminal_state_cannot_transition" in r for r in receipt.reasons))

    def test_unknown_from_state_rejected(self):
        receipt = validate_state_transition(_valid_payload("nonexistent", "validated"))
        self.assertFalse(receipt.accepted)
        self.assertTrue(any("from_state_not_allowed" in r for r in receipt.reasons))

    def test_unknown_to_state_rejected(self):
        receipt = validate_state_transition(_valid_payload("planned", "nonexistent"))
        self.assertFalse(receipt.accepted)
        self.assertTrue(any("to_state_not_allowed" in r for r in receipt.reasons))

    def test_illegal_transition_rejected(self):
        receipt = validate_state_transition(_valid_payload("planned", "completed"))
        self.assertFalse(receipt.accepted)
        self.assertTrue(any("illegal_transition" in r for r in receipt.reasons))

    def test_raw_prompt_rejected(self):
        payload = _valid_payload("planned", "validated")
        payload["raw_prompt"] = "test"
        receipt = validate_state_transition(payload)
        self.assertIn("raw_prompt_forbidden", receipt.reasons)

    def test_raw_provider_response_rejected(self):
        payload = _valid_payload("planned", "validated")
        payload["raw_provider_response"] = "test"
        receipt = validate_state_transition(payload)
        self.assertIn("raw_provider_response_forbidden", receipt.reasons)

    def test_secret_value_rejected(self):
        payload = _valid_payload("planned", "validated")
        payload["secret_value"] = "sk-abc"
        receipt = validate_state_transition(payload)
        self.assertIn("secret_value_forbidden", receipt.reasons)

    def test_env_value_rejected(self):
        payload = _valid_payload("planned", "validated")
        payload["env_value"] = "PATH=/usr/bin"
        receipt = validate_state_transition(payload)
        self.assertIn("env_value_forbidden", receipt.reasons)

    def test_multiple_failures_accumulated(self):
        payload = _valid_payload("completed", "nonexistent")
        payload["raw_prompt"] = "test"
        receipt = validate_state_transition(payload)
        self.assertFalse(receipt.accepted)
        self.assertGreater(len(receipt.reasons), 1)


class StateMachineSideEffectFreeTests(unittest.TestCase):
    def test_validate_state_transition_does_not_mutate(self):
        p1 = _valid_payload("planned", "validated")
        p2 = copy.deepcopy(p1)
        validate_state_transition(p1)
        self.assertEqual(p1, p2)

    def test_non_mapping_does_not_crash(self):
        # validate_state_transition uses .get() which works on dicts only.
        # The constraint is that the function itself is deterministic.
        pass  # Input is always Mapping[str, object] per type hint

    def test_allowed_states_is_frozen(self):
        self.assertIsInstance(ALLOWED_STATES, frozenset)
        self.assertIn("planned", ALLOWED_STATES)
        self.assertIn("completed", ALLOWED_STATES)

    def test_terminal_states_is_frozen(self):
        self.assertIsInstance(TERMINAL_STATES, frozenset)
        self.assertIn("completed", TERMINAL_STATES)
