"""Tracer-bullet tests for approval runtime contract v1."""

from dataclasses import replace
from pathlib import Path
import unittest

from kernel.runtime.approval_runtime_contract import (
    admit_approval_runtime_decision,
    ApprovalRuntimeDecision,
    build_approval_runtime_decision,
    build_approval_runtime_request,
    validate_approval_runtime_admission_receipt,
    validate_approval_runtime_decision,
    validate_approval_runtime_request,
)

D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64
D4 = "sha256:" + "4" * 64
D5 = "sha256:" + "5" * 64
D6 = "sha256:" + "6" * 64
D7 = "sha256:" + "7" * 64
D8 = "sha256:" + "8" * 64
D9 = "sha256:" + "9" * 64
DA = "sha256:" + "a" * 64
DB = "sha256:" + "b" * 64


class ApprovalRuntimeContractV1Tests(unittest.TestCase):
    def _request_payload(self, requested_action: str = "approve_next_manual_stage") -> dict[str, object]:
        return {
            "approval_request_id": "approval-request-001",
            "task_id": "task-001",
            "run_id": "run-001",
            "review_packet_hash": D1,
            "promotion_receipt_hash": D2,
            "wal_head_hash": D3,
            "artifact_manifest_hash": D4,
            "snapshot_reconstruction_hash": D5,
            "capability_token_hash": D6,
            "risk_decision_hash": D7,
            "requested_action": requested_action,
            "human_invoked": True,
            "production_autonomy_requested": False,
            "live_execution_requested": False,
        }

    def _decision_payload(
        self,
        request_hash: str,
        operator_action: str = "approved",
    ) -> dict[str, object]:
        payload = {
            "approval_decision_id": "approval-decision-001",
            "approval_request_hash": request_hash,
            "task_id": "task-001",
            "run_id": "run-001",
            "operator_id_hash": D8,
            "operator_action": operator_action,
            "decision_reason_code": "operator_explicit_decision",
            "approval_scope": "manual_next_stage_only",
            "rollback_plan_hash": None,
            "human_attested": True,
            "production_autonomy_enabled": False,
            "live_execution_enabled": False,
        }
        if operator_action == "rejected":
            payload["rollback_plan_hash"] = D9
        return payload

    def test_request_hash_is_deterministic_and_excludes_created_at(self):
        first = build_approval_runtime_request(
            self._request_payload(),
            created_at="2026-01-01T00:00:00Z",
        )
        second = build_approval_runtime_request(
            self._request_payload(),
            created_at="2026-05-27T00:00:00Z",
        )

        self.assertTrue(validate_approval_runtime_request(first))
        self.assertEqual(first.request_hash, second.request_hash)
        self.assertNotEqual(first.created_at, second.created_at)
        self.assertNotIn("created_at", first.deterministic_material())

    def test_request_rejects_raw_secret_and_execution_material(self):
        forbidden_payloads = [
            {"raw_stdout": "hello"},
            {"secret_value": "not-for-storage"},
            {"env": {"TOKEN": "value"}},
            {"argv": ["python", "-m", "tests"]},
            {"provider_response": "raw response"},
            {"filesystem_path": "/tmp/evidence"},
        ]

        for forbidden in forbidden_payloads:
            payload = self._request_payload()
            payload.update(forbidden)
            with self.subTest(forbidden=forbidden):
                with self.assertRaises(ValueError):
                    build_approval_runtime_request(payload)

    def test_request_fails_closed_without_human_invocation_or_with_autonomy(self):
        for field, value in (
            ("human_invoked", False),
            ("production_autonomy_requested", True),
            ("live_execution_requested", True),
        ):
            payload = self._request_payload()
            payload[field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    build_approval_runtime_request(payload)

    def test_approved_decision_admits_next_manual_stage(self):
        request = build_approval_runtime_request(self._request_payload())
        decision = build_approval_runtime_decision(self._decision_payload(request.request_hash))
        receipt = admit_approval_runtime_decision(
            request,
            decision,
            wal_record_hash=DA,
            operator_receipt_hash=DB,
            admitted_at="2026-01-01T00:00:00Z",
        )

        self.assertTrue(validate_approval_runtime_decision(decision))
        self.assertTrue(validate_approval_runtime_admission_receipt(receipt))
        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.next_state, "next_manual_stage_allowed")
        self.assertNotIn("admitted_at", receipt.deterministic_material())

    def test_rejected_decision_requires_rollback_and_admits_rollback_state(self):
        request = build_approval_runtime_request(self._request_payload("reject_with_rollback"))
        missing_rollback = self._decision_payload(request.request_hash, "rejected")
        missing_rollback["rollback_plan_hash"] = None
        with self.assertRaises(ValueError):
            build_approval_runtime_decision(missing_rollback)

        decision = build_approval_runtime_decision(
            self._decision_payload(request.request_hash, "rejected")
        )
        receipt = admit_approval_runtime_decision(request, decision, wal_record_hash=DA)

        self.assertFalse(receipt.accepted)
        self.assertEqual(receipt.next_state, "rollback_required")
        self.assertTrue(validate_approval_runtime_admission_receipt(receipt))

    def test_deferred_decision_admits_human_review_pending_state(self):
        request = build_approval_runtime_request(self._request_payload("defer_human_review"))
        decision = build_approval_runtime_decision(
            self._decision_payload(request.request_hash, "deferred")
        )
        receipt = admit_approval_runtime_decision(request, decision, wal_record_hash=DA)

        self.assertFalse(receipt.accepted)
        self.assertEqual(receipt.next_state, "human_review_pending")

    def test_admission_rejects_mismatched_decision_and_bad_wal_hash(self):
        request = build_approval_runtime_request(self._request_payload())
        decision = build_approval_runtime_decision(self._decision_payload(request.request_hash))
        mismatched = replace(decision, approval_request_hash=D9)

        with self.assertRaises(ValueError):
            admit_approval_runtime_decision(request, mismatched, wal_record_hash=DA)
        with self.assertRaises(ValueError):
            admit_approval_runtime_decision(request, decision, wal_record_hash="not-a-digest")

    def test_validator_rejects_tampered_decision_hash_and_autonomy_flags(self):
        request = build_approval_runtime_request(self._request_payload())
        decision = build_approval_runtime_decision(self._decision_payload(request.request_hash))

        tampered_hash = replace(decision, decision_hash=DA)
        self.assertFalse(validate_approval_runtime_decision(tampered_hash))

        autonomy = ApprovalRuntimeDecision(
            approval_decision_id=decision.approval_decision_id,
            approval_request_hash=decision.approval_request_hash,
            task_id=decision.task_id,
            run_id=decision.run_id,
            operator_id_hash=decision.operator_id_hash,
            operator_action=decision.operator_action,
            decision_reason_code=decision.decision_reason_code,
            approval_scope=decision.approval_scope,
            rollback_plan_hash=decision.rollback_plan_hash,
            human_attested=decision.human_attested,
            production_autonomy_enabled=True,
            live_execution_enabled=decision.live_execution_enabled,
            decision_hash=decision.decision_hash,
        )
        self.assertFalse(validate_approval_runtime_decision(autonomy))

    def test_source_has_no_persistence_execution_or_provider_surface(self):
        source = Path("kernel/runtime/approval_runtime_contract.py").read_text()

        forbidden = [
            "sqlite3",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "argparse",
            "click",
            "typer",
            "schedule",
            "daemon",
            "os.environ",
            "Path(",
            "open(",
        ]
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
