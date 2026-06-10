"""Tests for the human-invoked WAL-gated preflight API."""

from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

from kernel.execution import minimal_controlled_wal_gated_preflight_api as api


SOURCE_PATH = Path("kernel/execution/minimal_controlled_wal_gated_preflight_api.py")
EXISTING_PREFLIGHT_API_PATH = Path("kernel/execution/minimal_controlled_preflight_api.py")
AUDIT_PATH = Path(
    "docs/audit/minimal_controlled_execution_human_invoked_wal_gated_preflight_api_v1.md"
)


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _admission_evidence(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": "task-wal-gated-api",
        "run_id": "run-wal-gated-api",
        "preflight_id": "preflight-wal-gated-api",
        "command_id": "git_status_short",
        "request_hash": _hash("request"),
        "decision_hash": _hash("decision"),
        "admission_record_hash": _hash("admission"),
    }
    payload.update(overrides)
    return payload


def _receipt_evidence(**overrides: object) -> dict[str, object]:
    payload = _admission_evidence(
        outcome_type="EXECUTION_RECEIPT",
        receipt_hash=_hash("receipt"),
        verifier_input_hash=_hash("verifier-input"),
        verifier_binding_hash=_hash("verifier-binding"),
    )
    payload.update(overrides)
    return payload


def _binding_evidence(**overrides: object) -> dict[str, object]:
    payload = _admission_evidence(
        receipt_hash=_hash("receipt"),
        verifier_input_hash=_hash("verifier-input"),
        verifier_binding_hash=_hash("verifier-binding"),
        execution_performed=True,
    )
    payload.update(overrides)
    return payload


def _preflight_evidence(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": "task-wal-gated-api",
        "run_id": "run-wal-gated-api",
        "preflight_id": "preflight-wal-gated-api",
        "preflight_result_hash": _hash("preflight-result"),
        "ordered_command_ids": ("git_status_short", "git_diff_check"),
        "child_request_hashes": (_hash("request-1"), _hash("request-2")),
        "child_decision_hashes": (_hash("decision-1"), _hash("decision-2")),
        "child_admission_hashes": (_hash("admission-1"), _hash("admission-2")),
        "child_receipt_hashes": (_hash("receipt-1"), _hash("receipt-2")),
        "child_failure_bundle_hashes": ("", ""),
        "child_verifier_input_hashes": (
            _hash("verifier-input-1"),
            _hash("verifier-input-2"),
        ),
        "child_verifier_binding_hashes": (
            _hash("verifier-binding-1"),
            _hash("verifier-binding-2"),
        ),
        "pre_snapshot_hashes": (_hash("pre-snapshot-1"), _hash("pre-snapshot-2")),
        "post_snapshot_hashes": (_hash("post-snapshot-1"), _hash("post-snapshot-2")),
        "execution_performed": True,
    }
    payload.update(overrides)
    return payload


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "api_invocation_id": "wal-gated-api-001",
        "wrapper_input_id": "wal-gated-wrapper-input-001",
        "task_id": "task-wal-gated-api",
        "run_id": "run-wal-gated-api",
        "preflight_id": "preflight-wal-gated-api",
        "requested_at": "2026-05-27T00:00:00Z",
        "requester": "operator",
        "human_invoked": True,
        "single_run_scope": True,
        "approved_for_wal_gated_preflight": True,
        "approval_token_id": "approval-token-001",
        "caller_intent": "run human-invoked WAL-gated preflight",
        "admission_evidence": _admission_evidence(),
        "outcome_evidence": _receipt_evidence(),
        "verifier_binding_evidence": _binding_evidence(),
        "preflight_result_evidence": _preflight_evidence(),
    }
    payload.update(overrides)
    return payload


class MinimalControlledExecutionHumanInvokedWalGatedPreflightApiV1Tests(unittest.TestCase):
    def test_all_required_exports_exist(self) -> None:
        expected = (
            "WAL_GATED_PREFLIGHT_API_VERSION",
            "WAL_GATED_PREFLIGHT_API_ALLOWED_FIELDS",
            "WAL_GATED_PREFLIGHT_API_FORBIDDEN_FIELDS",
            "MinimalControlledWalGatedPreflightApiResponse",
            "minimal_controlled_wal_gated_preflight_api_response_hash",
            "run_human_invoked_minimal_controlled_wal_gated_preflight",
        )

        self.assertEqual(tuple(api.__all__), expected)
        for symbol in expected:
            with self.subTest(symbol=symbol):
                self.assertTrue(hasattr(api, symbol))

    def test_accepts_human_invoked_single_run_approved_payload_with_injected_append(self) -> None:
        appended = []

        def append(record: object) -> None:
            appended.append(record)

        response = api.run_human_invoked_minimal_controlled_wal_gated_preflight(
            _payload(),
            append,
        )

        self.assertTrue(response.accepted, response.rejection_reasons)
        self.assertTrue(response.execution_may_proceed)
        self.assertEqual(response.api_invocation_id, "wal-gated-api-001")
        self.assertEqual(response.wrapper_result.ordered_record_hashes[0], appended[0].record_hash)
        self.assertEqual(len(appended), 4)
        self.assertEqual(
            response.api_response_hash,
            api.minimal_controlled_wal_gated_preflight_api_response_hash(response),
        )

    def test_rejects_missing_or_false_required_operator_flags(self) -> None:
        for field_name in (
            "human_invoked",
            "single_run_scope",
            "approved_for_wal_gated_preflight",
        ):
            with self.subTest(field_name=field_name):
                payload = _payload()
                payload[field_name] = False
                with self.assertRaisesRegex(ValueError, field_name + "_required_true"):
                    api.run_human_invoked_minimal_controlled_wal_gated_preflight(
                        payload,
                        lambda record: None,
                    )

    def test_append_callable_must_be_injected_not_payload_supplied(self) -> None:
        with self.assertRaisesRegex(ValueError, "append_callable_required"):
            api.run_human_invoked_minimal_controlled_wal_gated_preflight(
                _payload(),
                append_callable="not-callable",
            )

        with self.assertRaisesRegex(ValueError, "wal_gated_preflight_api_field_forbidden"):
            api.run_human_invoked_minimal_controlled_wal_gated_preflight(
                _payload(append_callable="payload-supplied"),
                lambda record: None,
            )

    def test_rejects_execution_material_and_raw_output_fields(self) -> None:
        for field_name in (
            "argv",
            "cwd",
            "env",
            "path",
            "executable",
            "timeout",
            "shell",
            "stdout",
            "stderr",
            "raw_stdout",
            "raw_stderr",
            "command_line",
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, "field_forbidden"):
                    api.run_human_invoked_minimal_controlled_wal_gated_preflight(
                        _payload(**{field_name: "forbidden"}),
                        lambda record: None,
                    )

    def test_rejects_execution_material_inside_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "admission_evidence_field_forbidden"):
            api.run_human_invoked_minimal_controlled_wal_gated_preflight(
                _payload(admission_evidence=_admission_evidence(stdout="raw")),
                lambda record: None,
            )

    def test_append_failure_blocks_execution(self) -> None:
        def append(_record: object) -> None:
            raise RuntimeError("append unavailable")

        response = api.run_human_invoked_minimal_controlled_wal_gated_preflight(
            _payload(),
            append,
        )

        self.assertFalse(response.accepted)
        self.assertFalse(response.execution_may_proceed)
        self.assertIn("WAL_ADAPTER_APPEND_FAILED", response.rejection_reasons)
        self.assertIn("EXECUTION_NOT_ATTEMPTED", response.rejection_reasons)

    def test_existing_preflight_api_default_surface_is_unchanged(self) -> None:
        source = EXISTING_PREFLIGHT_API_PATH.read_text(encoding="utf-8")

        self.assertNotIn("minimal_controlled_wal_gated_preflight_api", source)
        self.assertNotIn("minimal_controlled_wal_gated_preflight_wrapper", source)
        self.assertIn("run_human_invoked_minimal_controlled_preflight", source)

    def test_source_has_no_broad_runtime_or_execution_imports(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        forbidden_markers = (
            "argparse",
            "click",
            "typer",
            "subprocess",
            "sqlite3",
            "kernel.runtime",
            "kernel.os_engine",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "bpy",
            "hou",
            "unreal",
            "comfyui",
            "mcp",
        )
        for marker in forbidden_markers:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)
                self.assertFalse(any(item == marker or item.startswith(marker + ".") for item in imports))

        self.assertNotIn("minimal_controlled_preflight_sequence", source)
        self.assertNotIn("minimal_controlled_git_status_runner", source)
        self.assertNotIn("minimal_controlled_git_diff_check_runner", source)

    def test_audit_document_records_scope_and_non_goals(self) -> None:
        audit = AUDIT_PATH.read_text(encoding="utf-8")

        for marker in (
            "human_invoked",
            "single_run_scope",
            "approved_for_wal_gated_preflight",
            "append_callable",
            "No default behavior change",
            "No CLI, scheduler, daemon",
            "No arbitrary argv",
            "No raw stdout",
            "Next safe PR",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, audit)


if __name__ == "__main__":
    unittest.main()
