"""Tracer-bullet tests for Minimal Controlled Execution admission/WAL/verifier V1."""

from __future__ import annotations

import ast
from dataclasses import fields
import copy
import json
import unittest
from pathlib import Path

from kernel.execution.minimal_controlled_execution_contract import (
    DEFERRED_COMMAND_IDS,
    EXECUTION_FAILURE_TYPES,
    EXECUTION_REQUEST_FORBIDDEN_FIELDS,
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
    decision_hash,
    failure_bundle_hash,
    receipt_hash,
    request_hash,
    snapshot_hash,
    verifier_input_hash,
)
from kernel.execution.minimal_controlled_execution_admission_wal_verifier import (
    EXECUTION_ADMISSION_RECORD_FIELDS,
    EXECUTION_REPLAY_EVIDENCE_MANIFEST_FIELDS,
    EXECUTION_REPLAY_MANIFEST_STATUSES,
    EXECUTION_VERIFIER_BINDING_FIELDS,
    EXECUTION_WAL_RECORD_FIELDS,
    EXECUTION_WAL_RECORD_TYPES,
    ExecutionAdmissionRecord,
    ExecutionReplayEvidenceManifest,
    ExecutionVerifierBinding,
    ExecutionWalRecord,
    admission_record_hash,
    build_execution_admission_record,
    build_execution_replay_evidence_manifest,
    build_execution_verifier_binding,
    build_execution_wal_record,
    replay_manifest_hash,
    verifier_binding_hash,
    wal_record_hash,
)


CONTRACT_PATH = Path(
    "governance/execution/minimal_controlled_execution_admission_wal_verifier_v1.json"
)
DOC_PATH = Path("docs/execution/minimal_controlled_execution_admission_wal_verifier_v1.md")
SOURCE_PATH = Path("kernel/execution/minimal_controlled_execution_admission_wal_verifier.py")


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _request_payload(command_id: str = "git_status_short", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "approval_token_id": "",
        "caller_intent": "bind command-id admission evidence only",
        "command_id": command_id,
        "policy_version": POLICY_VERSION,
        "request_id": "request-001",
        "requested_at": "2026-05-25T00:00:00Z",
        "requester": "contract_test",
        "run_id": "run-001",
        "snapshot_ref": "snapshot:preflight-root",
        "task_id": "task-001",
        "use_case_ids": ["uc_001_codex_pr_preflight"],
    }
    payload.update(overrides)
    return payload


def _request_decision_admission(command_id: str = "git_status_short"):
    request = build_execution_request(_request_payload(command_id))
    decision = decide_execution_request(
        request,
        decision_id="decision-" + command_id,
        decided_at="2026-05-25T00:00:01Z",
    )
    admission = build_execution_admission_record(
        request,
        admission_record_id="admission-" + command_id,
        decision_id="decision-" + command_id,
        decided_at="2026-05-25T00:00:01Z",
        created_at="2026-05-25T00:00:02Z",
    )
    return request, decision, admission


def _snapshot(snapshot_type: str) -> ExecutionSnapshotRef:
    return ExecutionSnapshotRef(
        snapshot_id="snapshot-" + snapshot_type.lower(),
        task_id="task-001",
        run_id="run-001",
        command_id="git_status_short",
        snapshot_type=snapshot_type,
        root_hash="sha256:" + snapshot_type.lower()[0] * 64,
        captured_at="2026-05-25T00:00:00Z",
        execution_performed=False,
    )


def _failure_bundle(
    *,
    command_id: str,
    failure_type: str,
    policy_decision_hash: str,
    registry_entry_hash: str,
) -> ExecutionFailureBundle:
    return ExecutionFailureBundle(
        failure_bundle_id="failure-" + failure_type.lower(),
        request_id="request-001",
        command_id=command_id,
        failure_type=failure_type,
        failure_reasons=(failure_type,),
        policy_decision_hash=policy_decision_hash,
        registry_entry_hash=registry_entry_hash,
        pre_snapshot_hash="sha256:" + "1" * 64,
        post_snapshot_hash="sha256:" + "2" * 64,
        execution_performed=False,
    )


class MinimalControlledExecutionAdmissionWalVerifierV1Tests(unittest.TestCase):
    def test_contract_objects_define_required_fields(self):
        objects = _contract()["contract_objects"]
        expected_fields = {
            "ExecutionAdmissionRecord": EXECUTION_ADMISSION_RECORD_FIELDS,
            "ExecutionWalRecord": EXECUTION_WAL_RECORD_FIELDS,
            "ExecutionVerifierBinding": EXECUTION_VERIFIER_BINDING_FIELDS,
            "ExecutionReplayEvidenceManifest": EXECUTION_REPLAY_EVIDENCE_MANIFEST_FIELDS,
        }
        for object_name, field_names in expected_fields.items():
            self.assertEqual(objects[object_name]["required_fields"], list(field_names))
        self.assertEqual(
            set(objects["ExecutionWalRecord"]["allowed_wal_record_type"]),
            EXECUTION_WAL_RECORD_TYPES,
        )
        self.assertEqual(
            set(objects["ExecutionReplayEvidenceManifest"]["allowed_manifest_status"]),
            EXECUTION_REPLAY_MANIFEST_STATUSES,
        )

    def test_admission_accepts_known_command_ids(self):
        for command_id in ("git_status_short", "git_diff_check"):
            with self.subTest(command_id=command_id):
                request, decision, admission = _request_decision_admission(command_id)
                self.assertTrue(decision.accepted)
                self.assertTrue(admission.accepted)
                self.assertEqual(admission.rejection_reasons, ())
                self.assertEqual(admission.request_hash, request.request_hash)
                self.assertEqual(admission.registry_entry_hash, decision.registry_entry_hash)
                self.assertEqual(
                    admission.registry_entry_hash,
                    INITIAL_COMMAND_REGISTRY[command_id].registry_entry_hash,
                )
                self.assertEqual(admission.registry_hash, command_registry_hash())
                self.assertFalse(admission.execution_performed)

    def test_admission_rejects_unknown_deferred_and_forbidden_request_fields(self):
        for command_id, expected_reason in (
            ("unknown_command", "UNKNOWN_COMMAND_ID"),
            ("unittest_discover_tests", "DEFERRED_COMMAND_ID"),
            ("make_ci", "DEFERRED_COMMAND_ID"),
        ):
            with self.subTest(command_id=command_id):
                request, _decision, admission = _request_decision_admission(command_id)
                self.assertFalse(admission.accepted)
                self.assertEqual(admission.request_hash, request.request_hash)
                self.assertIn("POLICY_REJECTED", admission.rejection_reasons)
                self.assertIn(expected_reason, admission.rejection_reasons)
                self.assertFalse(admission.execution_performed)

        for forbidden_field in sorted(EXECUTION_REQUEST_FORBIDDEN_FIELDS):
            payload = _request_payload(**{forbidden_field: "payload-supplied"})
            with self.subTest(forbidden_field=forbidden_field):
                with self.assertRaisesRegex(ValueError, "forbidden_request_field"):
                    build_execution_admission_record(
                        payload,
                        admission_record_id="admission-forbidden",
                        decision_id="decision-forbidden",
                        created_at="2026-05-25T00:00:02Z",
                    )

    def test_admission_record_invariants_and_hash_determinism(self):
        request, _decision, admission = _request_decision_admission("git_status_short")
        self.assertEqual(admission.request_hash, request_hash(request))
        self.assertEqual(admission.admission_record_hash, admission_record_hash(admission))

        changed = copy.deepcopy(admission.as_dict())
        changed["created_at"] = "2026-05-25T00:00:03Z"
        self.assertNotEqual(admission.admission_record_hash, admission_record_hash(changed))

        mismatched = copy.deepcopy(admission.as_dict())
        mismatched["admission_record_hash"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "admission_record_hash_mismatch"):
            ExecutionAdmissionRecord(**mismatched)

        rejected = copy.deepcopy(admission.as_dict())
        rejected["accepted"] = False
        rejected["rejection_reasons"] = []
        rejected["admission_record_hash"] = ""
        with self.assertRaisesRegex(ValueError, "rejected_admission_requires_rejection_reasons"):
            ExecutionAdmissionRecord(**rejected)

        accepted_with_reason = copy.deepcopy(admission.as_dict())
        accepted_with_reason["rejection_reasons"] = ["POLICY_REJECTED"]
        accepted_with_reason["admission_record_hash"] = ""
        with self.assertRaisesRegex(ValueError, "accepted_admission_cannot_have_rejection"):
            ExecutionAdmissionRecord(**accepted_with_reason)

        performed = copy.deepcopy(admission.as_dict())
        performed["execution_performed"] = True
        performed["admission_record_hash"] = ""
        with self.assertRaisesRegex(ValueError, "execution_performed_must_be_false"):
            ExecutionAdmissionRecord(**performed)

    def test_wal_record_is_wal_safe_and_deterministic(self):
        request, decision, admission = _request_decision_admission("git_status_short")
        payload = {
            "admission_record_hash": admission.admission_record_hash,
            "command_id": request.command_id,
            "created_at": "2026-05-25T00:00:03Z",
            "decision_hash": decision.decision_hash,
            "execution_performed": False,
            "failure_bundle_hash": "",
            "registry_entry_hash": admission.registry_entry_hash,
            "registry_hash": admission.registry_hash,
            "request_hash": request.request_hash,
            "run_id": request.run_id,
            "sequence": 1,
            "task_id": request.task_id,
            "verifier_input_hash": "",
            "wal_record_id": "wal-001",
            "wal_record_type": "EXECUTION_ADMISSION_ACCEPTED",
        }
        wal = build_execution_wal_record(payload)
        self.assertGreater(wal.sequence, 0)
        self.assertIn(wal.wal_record_type, EXECUTION_WAL_RECORD_TYPES)
        self.assertFalse(wal.execution_performed)
        self.assertEqual(wal.wal_record_hash, wal_record_hash(wal))

        wal_fields = {field.name for field in fields(type(wal))}
        for forbidden in ("argv", "command_line", "stdout", "stderr", "raw_stdout", "raw_stderr"):
            self.assertNotIn(forbidden, wal_fields)

        for raw_field in ("stdout", "stderr", "command_line", "argv"):
            raw_payload = dict(payload)
            raw_payload[raw_field] = "raw evidence"
            with self.subTest(raw_field=raw_field):
                with self.assertRaisesRegex(ValueError, "raw_evidence_field_forbidden"):
                    build_execution_wal_record(raw_payload)

        bad_sequence = dict(payload)
        bad_sequence["sequence"] = 0
        with self.assertRaisesRegex(ValueError, "sequence_must_be_positive"):
            build_execution_wal_record(bad_sequence)

        mismatched = dict(wal.as_dict())
        mismatched["wal_record_hash"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "wal_record_hash_mismatch"):
            build_execution_wal_record(mismatched)

    def test_failure_bundle_can_represent_rejection_and_not_attempted_states(self):
        self.assertTrue(
            {"UNKNOWN_COMMAND_ID", "DEFERRED_COMMAND_ID", "EXECUTION_NOT_ATTEMPTED"}.issubset(
                EXECUTION_FAILURE_TYPES
            )
        )
        registry_entry_hash = INITIAL_COMMAND_REGISTRY["git_status_short"].registry_entry_hash
        for command_id, failure_type in (
            ("unknown_command", "UNKNOWN_COMMAND_ID"),
            ("unittest_discover_tests", "DEFERRED_COMMAND_ID"),
            ("git_status_short", "EXECUTION_NOT_ATTEMPTED"),
        ):
            request = build_execution_request(_request_payload(command_id))
            decision = decide_execution_request(
                request,
                decision_id="decision-failure-" + failure_type.lower(),
                decided_at="2026-05-25T00:00:01Z",
            )
            bundle = _failure_bundle(
                command_id=command_id,
                failure_type=failure_type,
                policy_decision_hash=decision.decision_hash,
                registry_entry_hash=registry_entry_hash,
            )
            self.assertEqual(bundle.failure_type, failure_type)
            self.assertEqual(bundle.failure_bundle_hash, failure_bundle_hash(bundle))
            self.assertFalse(bundle.execution_performed)

    def test_verifier_binding_binds_hashes_and_rejects_success_claims(self):
        request, decision, admission = _request_decision_admission("git_status_short")
        pre_snapshot = _snapshot("PRE")
        post_snapshot = _snapshot("POST")
        receipt = build_execution_receipt(
            {
                "command_id": request.command_id,
                "execution_performed": False,
                "exit_code": 0,
                "finished_at": "CONTRACT_ONLY_NOT_EXECUTED",
                "output_limit_bytes": INITIAL_COMMAND_REGISTRY[request.command_id].output_limit_bytes,
                "policy_decision_hash": decision.decision_hash,
                "post_snapshot_hash": post_snapshot.snapshot_hash,
                "pre_snapshot_hash": pre_snapshot.snapshot_hash,
                "receipt_id": "receipt-001",
                "receipt_status": "CONTRACT_ONLY_NOT_EXECUTED",
                "registry_entry_hash": admission.registry_entry_hash,
                "request_id": request.request_id,
                "started_at": "CONTRACT_ONLY_NOT_EXECUTED",
                "stderr_digest": "sha256:" + "0" * 64,
                "stderr_truncated": False,
                "stdout_digest": "sha256:" + "0" * 64,
                "stdout_truncated": False,
            }
        )
        failure = _failure_bundle(
            command_id=request.command_id,
            failure_type="EXECUTION_NOT_ATTEMPTED",
            policy_decision_hash=decision.decision_hash,
            registry_entry_hash=admission.registry_entry_hash,
        )
        verifier_input = ExecutionVerifierInput(
            verifier_input_id="verifier-input-001",
            request_hash=request.request_hash,
            decision_hash=decision.decision_hash,
            registry_entry_hash=admission.registry_entry_hash,
            receipt_hash=receipt.receipt_hash,
            pre_snapshot_hash=pre_snapshot.snapshot_hash,
            post_snapshot_hash=post_snapshot.snapshot_hash,
            verifier_policy_version=POLICY_VERSION,
            execution_performed=False,
        )
        binding = build_execution_verifier_binding(
            {
                "admission_record_hash": admission.admission_record_hash,
                "decision_hash": decision.decision_hash,
                "execution_performed": False,
                "failure_bundle_hash": failure.failure_bundle_hash,
                "post_snapshot_hash": post_snapshot.snapshot_hash,
                "pre_snapshot_hash": pre_snapshot.snapshot_hash,
                "receipt_hash": receipt.receipt_hash,
                "registry_entry_hash": admission.registry_entry_hash,
                "registry_hash": admission.registry_hash,
                "request_hash": request.request_hash,
                "verifier_binding_id": "verifier-binding-001",
                "verifier_policy_version": POLICY_VERSION,
            }
        )
        self.assertEqual(verifier_input.verifier_input_hash, verifier_input_hash(verifier_input))
        self.assertEqual(binding.request_hash, request.request_hash)
        self.assertEqual(binding.decision_hash, decision_hash(decision))
        self.assertEqual(binding.admission_record_hash, admission.admission_record_hash)
        self.assertEqual(binding.receipt_hash, receipt_hash(receipt))
        self.assertEqual(binding.failure_bundle_hash, failure.failure_bundle_hash)
        self.assertEqual(binding.pre_snapshot_hash, snapshot_hash(pre_snapshot))
        self.assertEqual(binding.post_snapshot_hash, snapshot_hash(post_snapshot))
        self.assertEqual(binding.registry_hash, command_registry_hash())
        self.assertEqual(binding.verifier_binding_hash, verifier_binding_hash(binding))
        self.assertFalse(binding.execution_performed)

        performed = dict(binding.as_dict())
        performed["execution_performed"] = True
        performed["verifier_binding_hash"] = ""
        with self.assertRaisesRegex(ValueError, "execution_performed_must_be_false"):
            build_execution_verifier_binding(performed)

        no_receipt_or_failure = dict(binding.as_dict())
        no_receipt_or_failure["receipt_hash"] = ""
        no_receipt_or_failure["failure_bundle_hash"] = ""
        no_receipt_or_failure["verifier_binding_hash"] = ""
        with self.assertRaisesRegex(ValueError, "receipt_or_failure_bundle_hash_required"):
            build_execution_verifier_binding(no_receipt_or_failure)

    def test_replay_manifest_orders_wal_hashes_and_rejects_raw_evidence(self):
        request, decision, admission = _request_decision_admission("git_status_short")
        wal_records = [
            build_execution_wal_record(
                {
                    "admission_record_hash": admission.admission_record_hash,
                    "command_id": request.command_id,
                    "created_at": "2026-05-25T00:00:0" + str(sequence + 2) + "Z",
                    "decision_hash": decision.decision_hash,
                    "execution_performed": False,
                    "failure_bundle_hash": "",
                    "registry_entry_hash": admission.registry_entry_hash,
                    "registry_hash": admission.registry_hash,
                    "request_hash": request.request_hash,
                    "run_id": request.run_id,
                    "sequence": sequence,
                    "task_id": request.task_id,
                    "verifier_input_hash": "",
                    "wal_record_id": "wal-" + str(sequence),
                    "wal_record_type": wal_record_type,
                }
            )
            for sequence, wal_record_type in (
                (1, "EXECUTION_ADMISSION_ACCEPTED"),
                (2, "EXECUTION_NOT_ATTEMPTED"),
            )
        ]
        manifest = build_execution_replay_evidence_manifest(
            {
                "admission_record_hash": admission.admission_record_hash,
                "command_id": request.command_id,
                "created_at": "2026-05-25T00:00:05Z",
                "decision_hash": decision.decision_hash,
                "execution_performed": False,
                "failure_bundle_hash": "",
                "manifest_status": "CONTRACT_ONLY_ACCEPTED_NOT_EXECUTED",
                "registry_hash": admission.registry_hash,
                "replay_manifest_id": "manifest-001",
                "request_hash": request.request_hash,
                "run_id": request.run_id,
                "task_id": request.task_id,
                "verifier_binding_hash": "",
                "verifier_input_hash": "",
                "wal_record_hashes": [record.wal_record_hash for record in wal_records],
            }
        )
        self.assertEqual(
            manifest.wal_record_hashes,
            tuple(record.wal_record_hash for record in wal_records),
        )
        self.assertGreater(len(manifest.wal_record_hashes), 0)
        self.assertIn(manifest.manifest_status, EXECUTION_REPLAY_MANIFEST_STATUSES)
        self.assertEqual(manifest.replay_manifest_hash, replay_manifest_hash(manifest))
        self.assertFalse(manifest.execution_performed)

        for raw_field in ("stdout", "stderr", "command_line", "argv"):
            raw_manifest = dict(manifest.as_dict())
            raw_manifest[raw_field] = "raw evidence"
            raw_manifest["replay_manifest_hash"] = ""
            with self.subTest(raw_field=raw_field):
                with self.assertRaisesRegex(ValueError, "raw_evidence_field_forbidden"):
                    build_execution_replay_evidence_manifest(raw_manifest)

        empty_manifest = dict(manifest.as_dict())
        empty_manifest["wal_record_hashes"] = []
        empty_manifest["replay_manifest_hash"] = ""
        with self.assertRaisesRegex(ValueError, "wal_record_hashes_required"):
            build_execution_replay_evidence_manifest(empty_manifest)

        mismatched = dict(manifest.as_dict())
        mismatched["replay_manifest_hash"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "replay_manifest_hash_mismatch"):
            build_execution_replay_evidence_manifest(mismatched)

    def test_registry_boundary_remains_exactly_two_command_ids(self):
        self.assertEqual(tuple(INITIAL_COMMAND_REGISTRY), ("git_status_short", "git_diff_check"))
        self.assertEqual(DEFERRED_COMMAND_IDS, {"unittest_discover_tests", "make_ci"})
        self.assertEqual(
            _contract()["initial_registry_command_ids"],
            ["git_status_short", "git_diff_check"],
        )
        self.assertNotIn("unittest_discover_tests", INITIAL_COMMAND_REGISTRY)
        self.assertNotIn("make_ci", INITIAL_COMMAND_REGISTRY)

    def test_execution_performed_false_across_all_new_integration_objects(self):
        request, decision, admission = _request_decision_admission("git_status_short")
        wal = build_execution_wal_record(
            {
                "admission_record_hash": admission.admission_record_hash,
                "command_id": request.command_id,
                "created_at": "2026-05-25T00:00:03Z",
                "decision_hash": decision.decision_hash,
                "execution_performed": False,
                "failure_bundle_hash": "",
                "registry_entry_hash": admission.registry_entry_hash,
                "registry_hash": admission.registry_hash,
                "request_hash": request.request_hash,
                "run_id": request.run_id,
                "sequence": 1,
                "task_id": request.task_id,
                "verifier_input_hash": "",
                "wal_record_id": "wal-invariant",
                "wal_record_type": "EXECUTION_ADMISSION_ACCEPTED",
            }
        )
        binding = build_execution_verifier_binding(
            {
                "admission_record_hash": admission.admission_record_hash,
                "decision_hash": decision.decision_hash,
                "execution_performed": False,
                "failure_bundle_hash": "sha256:" + "4" * 64,
                "post_snapshot_hash": "sha256:" + "3" * 64,
                "pre_snapshot_hash": "sha256:" + "2" * 64,
                "receipt_hash": "",
                "registry_entry_hash": admission.registry_entry_hash,
                "registry_hash": admission.registry_hash,
                "request_hash": request.request_hash,
                "verifier_binding_id": "binding-invariant",
                "verifier_policy_version": POLICY_VERSION,
            }
        )
        manifest = build_execution_replay_evidence_manifest(
            {
                "admission_record_hash": admission.admission_record_hash,
                "command_id": request.command_id,
                "created_at": "2026-05-25T00:00:05Z",
                "decision_hash": decision.decision_hash,
                "execution_performed": False,
                "failure_bundle_hash": "sha256:" + "4" * 64,
                "manifest_status": "CONTRACT_ONLY_FAILURE_NOT_EXECUTED",
                "registry_hash": admission.registry_hash,
                "replay_manifest_id": "manifest-invariant",
                "request_hash": request.request_hash,
                "run_id": request.run_id,
                "task_id": request.task_id,
                "verifier_binding_hash": binding.verifier_binding_hash,
                "verifier_input_hash": "",
                "wal_record_hashes": [wal.wal_record_hash],
            }
        )
        for contract_object in (admission, wal, binding, manifest):
            self.assertFalse(contract_object.execution_performed)

    def test_source_has_no_forbidden_execution_or_external_surface(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for marker in (
            "subprocess",
            "os.system",
            "Popen",
            "shell=True",
            "exec(",
            "eval(",
            "argparse",
            "click",
            "typer",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "openai",
            "anthropic",
            "bpy",
            "hou",
            "unreal",
            "comfyui",
            "mcp",
        ):
            self.assertNotIn(marker, source)

    def test_new_module_does_not_import_runner_or_local_execution_kernel(self):
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)

        for forbidden_import in (
            "runner",
            "local_execution_kernel",
            "real_local_execution_kernel",
            "local_job_runner",
            "local_stage_executor",
            "local_train_runner",
        ):
            self.assertFalse(
                any(forbidden_import in imported for imported in imported_modules),
                imported_modules,
            )

    def test_docs_record_contract_only_boundary(self):
        doc = DOC_PATH.read_text(encoding="utf-8")
        self.assertIn("contract-only", doc.lower())
        self.assertIn("does not implement subprocess behavior", doc)
        self.assertIn("does not add a runner", doc)
        self.assertIn("does not widen the registry", doc)


if __name__ == "__main__":
    unittest.main()
