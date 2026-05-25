"""Tracer-bullet tests for Minimal Controlled Execution Contract-Only V1."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest
from pathlib import Path

from kernel.execution import minimal_controlled_execution_contract as contract
from kernel.execution.minimal_controlled_execution_contract import (
    COMMAND_REGISTRY_HASH,
    DEFERRED_COMMAND_IDS,
    EXECUTION_REQUEST_FORBIDDEN_FIELDS,
    FORBIDDEN_SURFACE_FLAGS_FALSE,
    INITIAL_COMMAND_REGISTRY,
    POLICY_VERSION,
    REGISTRY_VERSION,
    ExecutionFailureBundle,
    ExecutionSnapshotRef,
    ExecutionVerifierInput,
    build_execution_receipt,
    build_execution_request,
    command_registry_hash,
    decide_execution_request,
)


CONTRACT_SOURCE = Path("kernel/execution/minimal_controlled_execution_contract.py")


def _request_payload(command_id: str = "git_status_short") -> dict[str, object]:
    return {
        "approval_token_id": "",
        "caller_intent": "inspect repository status without execution",
        "command_id": command_id,
        "policy_version": POLICY_VERSION,
        "request_id": "req-001",
        "requested_at": "2026-05-25T00:00:00Z",
        "requester": "codex",
        "run_id": "run-001",
        "snapshot_ref": "snapshot:preflight-root",
        "task_id": "task-001",
        "use_case_ids": ["uc_001_codex_pr_preflight"],
    }


def _accepted_decision():
    request = build_execution_request(_request_payload())
    return request, decide_execution_request(
        request,
        decision_id="decision-001",
        decided_at="2026-05-25T00:00:01Z",
    )


def _snapshot(snapshot_type: str) -> ExecutionSnapshotRef:
    return ExecutionSnapshotRef(
        snapshot_id="snapshot-" + snapshot_type.lower(),
        task_id="task-001",
        run_id="run-001",
        command_id="git_status_short",
        snapshot_type=snapshot_type,
        root_hash="sha256:" + ("a" * 64),
        captured_at="2026-05-25T00:00:00Z",
        execution_performed=False,
    )


class MinimalControlledExecutionContractOnlyV1Tests(unittest.TestCase):
    def test_initial_registry_exactly_contains_two_git_command_ids(self):
        self.assertEqual(
            tuple(INITIAL_COMMAND_REGISTRY),
            ("git_status_short", "git_diff_check"),
        )
        self.assertEqual(DEFERRED_COMMAND_IDS, {"unittest_discover_tests", "make_ci"})
        self.assertEqual(COMMAND_REGISTRY_HASH, command_registry_hash())

        for command_id, entry in INITIAL_COMMAND_REGISTRY.items():
            self.assertEqual(entry.command_id, command_id)
            self.assertIsInstance(entry.argv, tuple)
            self.assertEqual(entry.command_class, "REPOSITORY_READ_ONLY_CHECK")
            self.assertTrue(entry.read_only_expectation)
            self.assertTrue(entry.allowed_verifier.endswith("_contract_verifier"))
            self.assertEqual(entry.registry_version, REGISTRY_VERSION)
            self.assertEqual(entry.registry_entry_hash, contract.registry_entry_hash(entry))

        with self.assertRaises(TypeError):
            INITIAL_COMMAND_REGISTRY["make_ci"] = INITIAL_COMMAND_REGISTRY["git_status_short"]  # type: ignore[index]

    def test_deferred_and_unknown_command_ids_are_rejected_by_policy_decision(self):
        for command_id in ("unittest_discover_tests", "make_ci"):
            request = build_execution_request(_request_payload(command_id))
            decision = decide_execution_request(
                request,
                decision_id="decision-" + command_id,
                decided_at="2026-05-25T00:00:01Z",
            )
            self.assertFalse(decision.accepted)
            self.assertIn("DEFERRED_COMMAND_ID", decision.rejection_reasons)
            self.assertFalse(decision.execution_performed)

        request = build_execution_request(_request_payload("unknown_command"))
        decision = decide_execution_request(
            request,
            decision_id="decision-unknown",
            decided_at="2026-05-25T00:00:01Z",
        )
        self.assertFalse(decision.accepted)
        self.assertIn("UNKNOWN_COMMAND_ID", decision.rejection_reasons)

    def test_execution_request_rejects_forbidden_payload_fields(self):
        required_fields = {
            "argv",
            "cwd",
            "env",
            "path",
            "executable",
            "timeout",
            "command",
            "command_line",
            "shell",
        }
        self.assertTrue(required_fields.issubset(EXECUTION_REQUEST_FORBIDDEN_FIELDS))
        for forbidden_field in sorted(EXECUTION_REQUEST_FORBIDDEN_FIELDS):
            payload = _request_payload()
            payload[forbidden_field] = True
            with self.assertRaises(ValueError, msg=forbidden_field):
                build_execution_request(payload)

    def test_policy_decision_includes_registry_hash_and_forbidden_flags_false(self):
        request, decision = _accepted_decision()

        self.assertTrue(decision.accepted)
        self.assertEqual(decision.request_id, request.request_id)
        self.assertEqual(decision.policy_version, POLICY_VERSION)
        self.assertEqual(decision.registry_version, REGISTRY_VERSION)
        self.assertEqual(decision.registry_hash, COMMAND_REGISTRY_HASH)
        self.assertEqual(
            dict(decision.forbidden_surface_flags),
            dict(FORBIDDEN_SURFACE_FLAGS_FALSE),
        )
        self.assertTrue(all(value is False for _, value in decision.forbidden_surface_flags))
        self.assertFalse(decision.execution_performed)

    def test_contract_hashes_are_stable_and_dataclasses_are_immutable(self):
        request, decision = _accepted_decision()
        pre_snapshot = _snapshot("PRE")
        post_snapshot = _snapshot("POST")
        receipt = build_execution_receipt(
            {
                "command_id": "git_status_short",
                "execution_performed": False,
                "exit_code": 0,
                "finished_at": "CONTRACT_ONLY_NOT_EXECUTED",
                "output_limit_bytes": 65536,
                "policy_decision_hash": decision.decision_hash,
                "post_snapshot_hash": post_snapshot.snapshot_hash,
                "pre_snapshot_hash": pre_snapshot.snapshot_hash,
                "receipt_id": "receipt-001",
                "receipt_status": "CONTRACT_ONLY_NOT_EXECUTED",
                "registry_entry_hash": INITIAL_COMMAND_REGISTRY["git_status_short"].registry_entry_hash,
                "request_id": request.request_id,
                "started_at": "CONTRACT_ONLY_NOT_EXECUTED",
                "stderr_digest": "sha256:" + ("0" * 64),
                "stderr_truncated": False,
                "stdout_digest": "sha256:" + ("0" * 64),
                "stdout_truncated": False,
            }
        )
        failure = ExecutionFailureBundle(
            failure_bundle_id="failure-001",
            request_id=request.request_id,
            command_id="git_status_short",
            failure_type="EXECUTION_NOT_ATTEMPTED",
            failure_reasons=("contract-only",),
            policy_decision_hash=decision.decision_hash,
            registry_entry_hash=INITIAL_COMMAND_REGISTRY["git_status_short"].registry_entry_hash,
            pre_snapshot_hash=pre_snapshot.snapshot_hash,
            post_snapshot_hash=post_snapshot.snapshot_hash,
            execution_performed=False,
        )
        verifier_input = ExecutionVerifierInput(
            verifier_input_id="verifier-001",
            request_hash=request.request_hash,
            decision_hash=decision.decision_hash,
            registry_entry_hash=INITIAL_COMMAND_REGISTRY["git_status_short"].registry_entry_hash,
            receipt_hash=receipt.receipt_hash,
            pre_snapshot_hash=pre_snapshot.snapshot_hash,
            post_snapshot_hash=post_snapshot.snapshot_hash,
            verifier_policy_version=POLICY_VERSION,
            execution_performed=False,
        )

        self.assertEqual(request.request_hash, contract.request_hash(request.as_dict()))
        self.assertEqual(decision.decision_hash, contract.decision_hash(decision.as_dict()))
        self.assertEqual(receipt.receipt_hash, contract.receipt_hash(receipt.as_dict()))
        self.assertEqual(
            failure.failure_bundle_hash,
            contract.failure_bundle_hash(failure.as_dict()),
        )
        self.assertEqual(pre_snapshot.snapshot_hash, contract.snapshot_hash(pre_snapshot.as_dict()))
        self.assertEqual(
            verifier_input.verifier_input_hash,
            contract.verifier_input_hash(verifier_input.as_dict()),
        )
        with self.assertRaises(FrozenInstanceError):
            request.command_id = "git_diff_check"  # type: ignore[misc]

    def test_receipt_failure_snapshot_and_verifier_cannot_imply_success(self):
        request, decision = _accepted_decision()
        pre_snapshot = _snapshot("PRE")
        post_snapshot = _snapshot("POST")
        base_receipt = {
            "command_id": "git_status_short",
            "execution_performed": False,
            "exit_code": 0,
            "finished_at": "CONTRACT_ONLY_NOT_EXECUTED",
            "output_limit_bytes": 65536,
            "policy_decision_hash": decision.decision_hash,
            "post_snapshot_hash": post_snapshot.snapshot_hash,
            "pre_snapshot_hash": pre_snapshot.snapshot_hash,
            "receipt_id": "receipt-002",
            "receipt_status": "CONTRACT_ONLY_NOT_EXECUTED",
            "registry_entry_hash": INITIAL_COMMAND_REGISTRY["git_status_short"].registry_entry_hash,
            "request_id": request.request_id,
            "started_at": "CONTRACT_ONLY_NOT_EXECUTED",
            "stderr_digest": "sha256:" + ("0" * 64),
            "stderr_truncated": False,
            "stdout_digest": "sha256:" + ("0" * 64),
            "stdout_truncated": False,
        }

        success_status = dict(base_receipt)
        success_status["receipt_status"] = "passed"
        with self.assertRaises(ValueError):
            build_execution_receipt(success_status)

        performed_receipt = dict(base_receipt)
        performed_receipt["execution_performed"] = True
        with self.assertRaises(ValueError):
            build_execution_receipt(performed_receipt)

        with self.assertRaises(ValueError):
            ExecutionFailureBundle(
                failure_bundle_id="failure-002",
                request_id=request.request_id,
                command_id="git_status_short",
                failure_type="EXECUTION_NOT_ATTEMPTED",
                failure_reasons=("contract-only",),
                policy_decision_hash=decision.decision_hash,
                registry_entry_hash=INITIAL_COMMAND_REGISTRY["git_status_short"].registry_entry_hash,
                pre_snapshot_hash=pre_snapshot.snapshot_hash,
                post_snapshot_hash=post_snapshot.snapshot_hash,
                execution_performed=True,
            )

        with self.assertRaises(ValueError):
            ExecutionSnapshotRef(
                snapshot_id="snapshot-bad",
                task_id="task-001",
                run_id="run-001",
                command_id="git_status_short",
                snapshot_type="PRE",
                root_hash="sha256:" + ("a" * 64),
                captured_at="2026-05-25T00:00:00Z",
                execution_performed=True,
            )

        with self.assertRaises(ValueError):
            ExecutionVerifierInput(
                verifier_input_id="verifier-002",
                request_hash=request.request_hash,
                decision_hash=decision.decision_hash,
                registry_entry_hash=INITIAL_COMMAND_REGISTRY["git_status_short"].registry_entry_hash,
                receipt_hash="sha256:" + ("b" * 64),
                pre_snapshot_hash=pre_snapshot.snapshot_hash,
                post_snapshot_hash=post_snapshot.snapshot_hash,
                verifier_policy_version=POLICY_VERSION,
                execution_performed=True,
            )

    def test_contract_source_contains_no_execution_imports_or_calls(self):
        source = CONTRACT_SOURCE.read_text(encoding="utf-8")
        for marker in (
            "import subprocess",
            "subprocess.",
            "os.system",
            "Popen",
            "exec(",
            "eval(",
        ):
            self.assertNotIn(marker, source)

    def test_contract_source_contains_no_external_surface_activation_markers(self):
        source = CONTRACT_SOURCE.read_text(encoding="utf-8").lower()
        for marker in (
            "import requests",
            "import httpx",
            "import urllib",
            "webbrowser.",
            "from playwright",
            "from selenium",
            "provider_api",
            "mcp_client",
            "dcc_launch",
            "comfyui_client",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
