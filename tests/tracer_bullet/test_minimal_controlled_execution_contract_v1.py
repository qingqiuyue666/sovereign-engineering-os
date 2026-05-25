"""Tracer-bullet tests for Minimal Controlled Execution Contract V1."""

from __future__ import annotations

from dataclasses import fields
import copy
import json
import unittest
from pathlib import Path

from kernel.execution.minimal_controlled_execution_contract import (
    COMMAND_REGISTRY_ENTRY_FIELDS,
    EXECUTION_FAILURE_BUNDLE_FIELDS,
    EXECUTION_FAILURE_TYPES,
    EXECUTION_POLICY_DECISION_FIELDS,
    EXECUTION_RECEIPT_FIELDS,
    EXECUTION_REQUEST_FIELDS,
    EXECUTION_REQUEST_FORBIDDEN_FIELDS,
    EXECUTION_SNAPSHOT_REF_FIELDS,
    EXECUTION_SNAPSHOT_TYPES,
    EXECUTION_VERIFIER_INPUT_FIELDS,
    INITIAL_COMMAND_REGISTRY,
    POLICY_VERSION,
    ExecutionCommandRegistryEntry,
    ExecutionFailureBundle,
    ExecutionSnapshotRef,
    ExecutionVerifierInput,
    build_execution_receipt,
    build_execution_request,
    decide_execution_request,
    registry_entry_hash,
)


CONTRACT_PATH = Path("governance/execution/minimal_controlled_execution_contract_v1.json")
DOC_PATH = Path("docs/execution/minimal_controlled_execution_contract_v1.md")
SOURCE_PATH = Path("kernel/execution/minimal_controlled_execution_contract.py")


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _request_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "request_id": "request_001",
        "task_id": "task_001",
        "run_id": "run_001",
        "command_id": "git_status_short",
        "approval_token_id": "",
        "requested_at": "2026-05-25T00:00:00Z",
        "requester": "contract_test",
        "policy_version": POLICY_VERSION,
        "use_case_ids": ["uc_001_codex_pr_preflight"],
        "snapshot_ref": "snapshot:preflight-root",
        "caller_intent": "invoke allowlisted command contract by command_id",
    }
    payload.update(overrides)
    return payload


def _receipt_payload(**overrides: object) -> dict[str, object]:
    entry = INITIAL_COMMAND_REGISTRY["git_status_short"]
    payload: dict[str, object] = {
        "receipt_id": "receipt_001",
        "request_id": "request_001",
        "command_id": "git_status_short",
        "receipt_status": "CONTRACT_ONLY_NOT_EXECUTED",
        "started_at": "2026-05-25T00:00:01Z",
        "finished_at": "2026-05-25T00:00:02Z",
        "exit_code": 0,
        "stdout_digest": "sha256:" + "1" * 64,
        "stderr_digest": "sha256:" + "2" * 64,
        "stdout_truncated": False,
        "stderr_truncated": False,
        "output_limit_bytes": entry.output_limit_bytes,
        "pre_snapshot_hash": "sha256:" + "3" * 64,
        "post_snapshot_hash": "sha256:" + "4" * 64,
        "registry_entry_hash": entry.registry_entry_hash,
        "policy_decision_hash": "sha256:" + "5" * 64,
        "execution_performed": False,
    }
    payload.update(overrides)
    return payload


class MinimalControlledExecutionContractTests(unittest.TestCase):
    def test_contract_objects_define_required_fields(self):
        objects = _contract()["contract_objects"]
        expected_fields = {
            "ExecutionCommandRegistryEntry": COMMAND_REGISTRY_ENTRY_FIELDS,
            "ExecutionRequest": EXECUTION_REQUEST_FIELDS,
            "ExecutionPolicyDecision": EXECUTION_POLICY_DECISION_FIELDS,
            "ExecutionReceipt": EXECUTION_RECEIPT_FIELDS,
            "ExecutionFailureBundle": EXECUTION_FAILURE_BUNDLE_FIELDS,
            "ExecutionSnapshotRef": EXECUTION_SNAPSHOT_REF_FIELDS,
            "ExecutionVerifierInput": EXECUTION_VERIFIER_INPUT_FIELDS,
        }
        for object_name, field_names in expected_fields.items():
            self.assertEqual(objects[object_name]["required_fields"], list(field_names))

    def test_initial_registry_contains_exactly_two_command_ids(self):
        self.assertEqual(
            tuple(INITIAL_COMMAND_REGISTRY.keys()),
            ("git_status_short", "git_diff_check"),
        )
        contract_ids = tuple(entry["command_id"] for entry in _contract()["initial_registry"])
        self.assertEqual(contract_ids, ("git_status_short", "git_diff_check"))

    def test_unit_tests_and_make_ci_are_not_initial_registry_entries(self):
        self.assertNotIn("unittest_discover_tests", INITIAL_COMMAND_REGISTRY)
        self.assertNotIn("make_ci", INITIAL_COMMAND_REGISTRY)
        deferred_ids = {entry["command_id"] for entry in _contract()["deferred_command_ids"]}
        self.assertEqual(deferred_ids, {"unittest_discover_tests", "make_ci"})

    def test_registry_entries_have_immutable_argv_and_deterministic_hash(self):
        entry = INITIAL_COMMAND_REGISTRY["git_status_short"]
        self.assertIsInstance(entry.argv, tuple)
        self.assertEqual(entry.argv, ("git", "status", "--short"))
        self.assertEqual(entry.registry_entry_hash, registry_entry_hash(entry))

        changed = copy.deepcopy(entry.as_dict())
        changed["argv"] = ["git", "status"]
        self.assertNotEqual(entry.registry_entry_hash, registry_entry_hash(changed))

        mismatched = copy.deepcopy(entry.as_dict())
        mismatched["registry_entry_hash"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "registry_entry_hash_mismatch"):
            ExecutionCommandRegistryEntry(**mismatched)

    def test_execution_request_accepts_command_id_reference_only(self):
        request = build_execution_request(_request_payload(command_id="git_diff_check"))
        self.assertEqual(request.command_id, "git_diff_check")
        self.assertEqual(set(request.as_dict()), set(EXECUTION_REQUEST_FIELDS))
        for forbidden_field in EXECUTION_REQUEST_FORBIDDEN_FIELDS:
            self.assertNotIn(forbidden_field, request.as_dict())
            self.assertFalse(hasattr(request, forbidden_field))

    def test_execution_request_rejects_forbidden_fields(self):
        for forbidden_field in sorted(EXECUTION_REQUEST_FORBIDDEN_FIELDS):
            payload = _request_payload(**{forbidden_field: "forbidden"})
            with self.subTest(forbidden_field=forbidden_field):
                with self.assertRaisesRegex(ValueError, "forbidden_request_field"):
                    build_execution_request(payload)

    def test_unknown_command_id_produces_policy_rejected_decision(self):
        request = build_execution_request(_request_payload(command_id="unknown_command"))
        decision = decide_execution_request(
            request,
            decision_id="decision_unknown_001",
            decided_at="2026-05-25T00:00:03Z",
        )
        self.assertFalse(decision.accepted)
        self.assertIn("POLICY_REJECTED", decision.rejection_reasons)
        self.assertIn("UNKNOWN_COMMAND_ID", decision.rejection_reasons)
        self.assertEqual(decision.registry_entry_hash, "")
        self.assertEqual(decision.policy_version, POLICY_VERSION)

    def test_human_approval_requirement_is_contract_data_only(self):
        entry_payload = copy.deepcopy(INITIAL_COMMAND_REGISTRY["git_status_short"].as_dict())
        entry_payload["command_id"] = "approval_required_git_status"
        entry_payload["requires_human_approval"] = True
        entry_payload["registry_entry_hash"] = ""
        approval_entry = ExecutionCommandRegistryEntry(**entry_payload)

        request = build_execution_request(_request_payload(command_id=approval_entry.command_id))
        decision = decide_execution_request(
            request,
            {approval_entry.command_id: approval_entry},
            decision_id="decision_approval_missing_001",
            decided_at="2026-05-25T00:00:03Z",
        )
        self.assertFalse(decision.accepted)
        self.assertIn("APPROVAL_MISSING", decision.rejection_reasons)
        self.assertTrue(decision.required_approval_token_id.startswith("approval:"))

        approved_request = build_execution_request(
            _request_payload(
                command_id=approval_entry.command_id,
                approval_token_id="approval_token_contract_data_only",
            )
        )
        approved_decision = decide_execution_request(
            approved_request,
            {approval_entry.command_id: approval_entry},
            decision_id="decision_approval_present_001",
            decided_at="2026-05-25T00:00:04Z",
        )
        self.assertTrue(approved_decision.accepted)

    def test_execution_receipt_stores_digests_not_raw_output(self):
        receipt = build_execution_receipt(_receipt_payload())
        receipt_field_names = {field.name for field in fields(type(receipt))}
        self.assertIn("stdout_digest", receipt_field_names)
        self.assertIn("stderr_digest", receipt_field_names)
        self.assertIn("stdout_truncated", receipt_field_names)
        self.assertIn("stderr_truncated", receipt_field_names)
        self.assertNotIn("stdout", receipt_field_names)
        self.assertNotIn("stderr", receipt_field_names)

        with self.assertRaisesRegex(ValueError, "raw_output_field_forbidden"):
            build_execution_receipt(_receipt_payload(stdout="raw output"))
        with self.assertRaisesRegex(ValueError, "raw_output_field_forbidden"):
            build_execution_receipt(_receipt_payload(stderr="raw error"))

    def test_failure_bundle_includes_required_failure_types(self):
        self.assertIn("WAL_APPEND_FAILED", EXECUTION_FAILURE_TYPES)
        self.assertIn("EXECUTION_NOT_ATTEMPTED", EXECUTION_FAILURE_TYPES)
        bundle = ExecutionFailureBundle(
            failure_bundle_id="failure_bundle_001",
            request_id="request_001",
            command_id="git_status_short",
            failure_type="WAL_APPEND_FAILED",
            failure_reasons=("wal append contract failure",),
            policy_decision_hash="sha256:" + "6" * 64,
            registry_entry_hash=INITIAL_COMMAND_REGISTRY["git_status_short"].registry_entry_hash,
            pre_snapshot_hash="sha256:" + "7" * 64,
            post_snapshot_hash="sha256:" + "8" * 64,
            execution_performed=False,
        )
        self.assertEqual(bundle.failure_type, "WAL_APPEND_FAILED")
        self.assertTrue(bundle.failure_bundle_hash.startswith("sha256:"))

    def test_snapshot_ref_supports_pre_and_post_snapshot_types(self):
        for snapshot_type in ("PRE", "POST"):
            snapshot = ExecutionSnapshotRef(
                snapshot_id="snapshot_" + snapshot_type.lower(),
                task_id="task_001",
                run_id="run_001",
                command_id="git_status_short",
                snapshot_type=snapshot_type,
                root_hash="sha256:" + snapshot_type[0].lower() * 64,
                captured_at="2026-05-25T00:00:00Z",
                execution_performed=False,
            )
            self.assertIn(snapshot.snapshot_type, EXECUTION_SNAPSHOT_TYPES)
            self.assertTrue(snapshot.snapshot_hash.startswith("sha256:"))

        with self.assertRaisesRegex(ValueError, "snapshot_type_invalid"):
            ExecutionSnapshotRef(
                snapshot_id="snapshot_bad",
                task_id="task_001",
                run_id="run_001",
                command_id="git_status_short",
                snapshot_type="MID",
                root_hash="sha256:" + "9" * 64,
                captured_at="2026-05-25T00:00:00Z",
                execution_performed=False,
            )

    def test_verifier_input_binds_request_decision_registry_receipt_and_snapshot_hashes(self):
        request = build_execution_request(_request_payload())
        decision = decide_execution_request(
            request,
            decision_id="decision_accept_001",
            decided_at="2026-05-25T00:00:05Z",
        )
        receipt = build_execution_receipt(
            _receipt_payload(
                policy_decision_hash=decision.decision_hash,
                registry_entry_hash=decision.registry_entry_hash,
            )
        )
        verifier_input = ExecutionVerifierInput(
            verifier_input_id="verifier_input_001",
            request_hash=request.request_hash,
            decision_hash=decision.decision_hash,
            registry_entry_hash=decision.registry_entry_hash,
            receipt_hash=receipt.receipt_hash,
            pre_snapshot_hash=receipt.pre_snapshot_hash,
            post_snapshot_hash=receipt.post_snapshot_hash,
            verifier_policy_version=POLICY_VERSION,
            execution_performed=False,
        )
        self.assertEqual(verifier_input.request_hash, request.request_hash)
        self.assertEqual(verifier_input.decision_hash, decision.decision_hash)
        self.assertEqual(verifier_input.registry_entry_hash, decision.registry_entry_hash)
        self.assertEqual(verifier_input.receipt_hash, receipt.receipt_hash)
        self.assertEqual(verifier_input.pre_snapshot_hash, receipt.pre_snapshot_hash)
        self.assertEqual(verifier_input.post_snapshot_hash, receipt.post_snapshot_hash)
        self.assertTrue(verifier_input.verifier_input_hash.startswith("sha256:"))

    def test_no_subprocess_runner_or_shell_execution_surface_exists(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("from subprocess", source)
        self.assertNotIn("subprocess.", source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("Popen", source)
        self.assertNotIn("if __name__", source)
        self.assertFalse(Path("kernel/execution/runner.py").exists())
        self.assertFalse(Path("kernel/execution/minimal_controlled_execution_runner.py").exists())

    def test_no_cli_scheduler_daemon_or_existing_runtime_widening(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for path in (
            Path("kernel/execution/cli.py"),
            Path("kernel/execution/main.py"),
            Path("kernel/execution/scheduler.py"),
            Path("kernel/execution/daemon.py"),
        ):
            self.assertFalse(path.exists(), str(path))
        for marker in (
            "kernel.runtime.runner",
            "kernel.runtime.task_runner",
            "kernel.runtime.dry_run_executor",
            "kernel.runtime.local_runtime_orchestrator",
        ):
            self.assertNotIn(marker, source)

    def test_no_network_provider_browser_dcc_comfyui_plugin_execution_exists(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden_import in (
            "import requests",
            "from requests",
            "import httpx",
            "from httpx",
            "import urllib",
            "from urllib",
            "import socket",
            "from socket",
            "import webbrowser",
            "from webbrowser",
            "import playwright",
            "from playwright",
            "import openai",
            "from openai",
            "import anthropic",
            "from anthropic",
            "import bpy",
            "from bpy",
        ):
            self.assertNotIn(forbidden_import, source)
        for forbidden_call in (
            "browser.launch",
            "plugin.execute",
            "dcc.launch",
            "comfyui.run",
            "mcp.call",
        ):
            self.assertNotIn(forbidden_call, source.lower())

    def test_docs_record_contract_only_boundary(self):
        doc = DOC_PATH.read_text(encoding="utf-8")
        self.assertIn("contract-only", doc.lower())
        self.assertIn("does not implement subprocess behavior", doc)
        self.assertIn("does not widen existing execution runtime modules", doc)


if __name__ == "__main__":
    unittest.main()
