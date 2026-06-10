"""Tracer-bullet tests for worker registry admission contract v1."""

from dataclasses import replace
from pathlib import Path
import unittest

from kernel.runtime.worker_registry_admission_contract import (
    admit_worker_request,
    build_worker_admission_declaration,
    build_worker_admission_request,
    build_worker_registry_admission_manifest,
    validate_worker_admission_declaration,
    validate_worker_admission_receipt,
    validate_worker_admission_request,
    validate_worker_registry_admission_manifest,
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


class WorkerRegistryAdmissionContractV1Tests(unittest.TestCase):
    def _declaration_payload(self, *, human_approval_required: bool = False) -> dict[str, object]:
        return {
            "worker_id": "local-static-checker",
            "worker_kind": "local_deterministic",
            "task_classes": ("static_contract_check", "artifact_summary"),
            "input_contract_hash": D1,
            "output_contract_hash": D2,
            "policy_hash": D3,
            "capability_hashes": (D4, D5),
            "evidence_requirement_hashes": (D6,),
            "human_approval_required": human_approval_required,
            "live_execution_enabled": False,
            "provider_calls_enabled": False,
            "network_enabled": False,
            "browser_enabled": False,
            "dcc_enabled": False,
            "mcp_enabled": False,
        }

    def _request_payload(self, approval_receipt_hash: str | None = None) -> dict[str, object]:
        return {
            "admission_request_id": "worker-admission-001",
            "worker_id": "local-static-checker",
            "task_id": "task-001",
            "run_id": "run-001",
            "requested_task_class": "static_contract_check",
            "queue_job_hash": D7,
            "task_descriptor_hash": D8,
            "idempotency_key_hash": D9,
            "wal_head_hash": DA,
            "artifact_manifest_hash": DB,
            "approval_receipt_hash": approval_receipt_hash,
            "human_invoked": True,
        }

    def test_declaration_hash_is_deterministic_and_excludes_declared_at(self):
        first = build_worker_admission_declaration(
            self._declaration_payload(),
            declared_at="2026-01-01T00:00:00Z",
        )
        second = build_worker_admission_declaration(
            self._declaration_payload(),
            declared_at="2026-05-27T00:00:00Z",
        )

        self.assertTrue(validate_worker_admission_declaration(first))
        self.assertEqual(first.declaration_hash, second.declaration_hash)
        self.assertNotEqual(first.declared_at, second.declared_at)
        self.assertNotIn("declared_at", first.deterministic_material())

    def test_declaration_rejects_enabled_runtime_surfaces(self):
        for field in (
            "live_execution_enabled",
            "provider_calls_enabled",
            "network_enabled",
            "browser_enabled",
            "dcc_enabled",
            "mcp_enabled",
        ):
            payload = self._declaration_payload()
            payload[field] = True
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    build_worker_admission_declaration(payload)

    def test_declaration_rejects_raw_execution_and_secret_material(self):
        forbidden_payloads = [
            {"argv": ["python", "-m", "tests"]},
            {"command": "python -m tests"},
            {"cwd": "/tmp"},
            {"env": {"TOKEN": "value"}},
            {"stdout": "raw"},
            {"raw_stderr": "raw"},
            {"provider_response": "raw provider"},
            {"secret_value": "secret"},
            {"filesystem_path": "/tmp/artifact"},
        ]
        for forbidden in forbidden_payloads:
            payload = self._declaration_payload()
            payload.update(forbidden)
            with self.subTest(forbidden=forbidden):
                with self.assertRaises(ValueError):
                    build_worker_admission_declaration(payload)

    def test_request_hash_is_deterministic_and_requires_human_invoked(self):
        first = build_worker_admission_request(
            self._request_payload(),
            requested_at="2026-01-01T00:00:00Z",
        )
        second = build_worker_admission_request(
            self._request_payload(),
            requested_at="2026-05-27T00:00:00Z",
        )

        self.assertTrue(validate_worker_admission_request(first))
        self.assertEqual(first.request_hash, second.request_hash)
        self.assertNotIn("requested_at", first.deterministic_material())

        payload = self._request_payload()
        payload["human_invoked"] = False
        with self.assertRaises(ValueError):
            build_worker_admission_request(payload)

    def test_admits_matching_worker_without_dispatch_or_execution(self):
        declaration = build_worker_admission_declaration(self._declaration_payload())
        request = build_worker_admission_request(self._request_payload())
        receipt = admit_worker_request(
            declaration,
            request,
            wal_record_hash=D1,
            admitted_at="2026-01-01T00:00:00Z",
        )

        self.assertTrue(validate_worker_admission_receipt(receipt))
        self.assertTrue(receipt.admitted)
        self.assertEqual(receipt.admission_state, "queue_admission_allowed")
        self.assertEqual(receipt.failure_reasons, ())
        self.assertNotIn("admitted_at", receipt.deterministic_material())

    def test_human_approval_required_blocks_until_approval_hash_present(self):
        declaration = build_worker_admission_declaration(
            self._declaration_payload(human_approval_required=True)
        )
        missing = build_worker_admission_request(self._request_payload())
        blocked = admit_worker_request(declaration, missing, wal_record_hash=D1)

        self.assertFalse(blocked.admitted)
        self.assertEqual(blocked.admission_state, "human_approval_required")
        self.assertIn("approval_receipt_hash_required", blocked.failure_reasons)
        self.assertTrue(validate_worker_admission_receipt(blocked))

        approved = build_worker_admission_request(self._request_payload(approval_receipt_hash=D2))
        receipt = admit_worker_request(declaration, approved, wal_record_hash=D1)
        self.assertTrue(receipt.admitted)

    def test_rejects_worker_id_task_class_and_unexpected_approval_mismatch(self):
        declaration = build_worker_admission_declaration(self._declaration_payload())

        wrong_worker = build_worker_admission_request(
            {**self._request_payload(), "worker_id": "other-worker"}
        )
        wrong_worker_receipt = admit_worker_request(declaration, wrong_worker, wal_record_hash=D1)
        self.assertFalse(wrong_worker_receipt.admitted)
        self.assertIn("worker_id_mismatch", wrong_worker_receipt.failure_reasons)

        wrong_task = build_worker_admission_request(
            {**self._request_payload(), "requested_task_class": "code_review"}
        )
        wrong_task_receipt = admit_worker_request(declaration, wrong_task, wal_record_hash=D1)
        self.assertFalse(wrong_task_receipt.admitted)
        self.assertIn("requested_task_class_not_declared", wrong_task_receipt.failure_reasons)

        unexpected = build_worker_admission_request(self._request_payload(approval_receipt_hash=D2))
        unexpected_receipt = admit_worker_request(declaration, unexpected, wal_record_hash=D1)
        self.assertFalse(unexpected_receipt.admitted)
        self.assertIn("approval_receipt_hash_unexpected", unexpected_receipt.failure_reasons)

    def test_manifest_rejects_duplicates_and_tampering(self):
        declaration = build_worker_admission_declaration(self._declaration_payload())
        manifest = build_worker_registry_admission_manifest(
            manifest_id="worker-registry-admission-001",
            registry_policy_hash=D3,
            wal_head_hash=DA,
            declarations=(declaration,),
            created_at="2026-01-01T00:00:00Z",
        )

        self.assertTrue(validate_worker_registry_admission_manifest(manifest))
        self.assertEqual(manifest.admitted_worker_ids, (declaration.worker_id,))
        self.assertNotIn("created_at", manifest.deterministic_material())

        with self.assertRaises(ValueError):
            build_worker_registry_admission_manifest(
                manifest_id="worker-registry-admission-001",
                registry_policy_hash=D3,
                wal_head_hash=DA,
                declarations=(declaration, declaration),
            )
        self.assertFalse(
            validate_worker_registry_admission_manifest(
                replace(manifest, manifest_hash=DB)
            )
        )

    def test_source_has_no_execution_provider_browser_or_scheduler_surface(self):
        source = Path("kernel/runtime/worker_registry_admission_contract.py").read_text()

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
