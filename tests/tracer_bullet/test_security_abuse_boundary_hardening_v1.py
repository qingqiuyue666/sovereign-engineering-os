"""Tests for Security / Abuse Boundary Hardening V1."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.security_abuse_boundary_hardening import (
    ZERO_HASH,
    FileBackedSecurityAbuseBoundaryHardening,
    compute_security_abuse_boundary_receipt_hash,
    compute_security_abuse_control_result_hash,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage

SOURCE_PATH = Path("kernel/runtime/security_abuse_boundary_hardening.py")
OBSERVED_AT = "2026-05-29T00:40:00+00:00"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _valid_payload() -> dict[str, object]:
    return {
        "request_id": "security-528",
        "task_id": "task-528",
        "run_id": "run-528",
        "approval_required": True,
        "replay_required": True,
        "approval_receipt_hash": _hash("approval"),
        "replay_receipt_hash": _hash("replay"),
        "audit_append_only": True,
        "audit_mode": "append_only",
        "audit_chain_hash": _hash("audit"),
        "operator_console_snapshot_hash": _hash("console"),
        "console_mutation_route": "approval_controlled_execution_runtime",
        "allowed_write_relpaths": ("reports/security.json",),
        "requested_write_relpaths": ("reports/security.json",),
        "network_accessed": False,
        "subprocess_requested": False,
        "daemon_enabled": False,
        "background_daemon_enabled": False,
        "model_direct_mutation": False,
        "tool_direct_mutation": False,
        "audit_mutable": False,
        "silent_repair": False,
        "provider_enabled": False,
        "provider_id": "disabled",
        "raw_payload_persisted": False,
        "env_credential_capture": False,
        "direct_console_edits_enabled": False,
        "console_mutation_enabled": False,
    }


def _evaluate(root: Path, payload: dict[str, object]):
    return FileBackedSecurityAbuseBoundaryHardening(runtime_root=root).evaluate(
        payload,
        observed_at=OBSERVED_AT,
    )


class SecurityAbuseBoundaryHardeningV1Tests(unittest.TestCase):
    def test_accepts_hardened_request_and_persists_digest_only_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            receipt = _evaluate(root, _valid_payload())
            receipt_path = next((root / "security-abuse-boundary" / "receipts").glob("*.json"))
            persisted = json.loads(receipt_path.read_text(encoding="utf-8"))
            wal_records = FileBackedRealWalStorage(
                root / "security-abuse-boundary" / "security.real-wal.jsonl"
            ).read_records()

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertEqual(
            receipt.receipt_hash,
            compute_security_abuse_boundary_receipt_hash(receipt),
        )
        self.assertEqual(persisted["receipt_hash"], receipt.receipt_hash)
        self.assertEqual(wal_records[-1].record_type, "SYSTEM_ACCEPTANCE_EVENT")
        self.assertEqual(wal_records[-1].record_hash, receipt.wal_record_hash)
        self.assertTrue(all(control.accepted for control in receipt.control_results))
        for control in receipt.control_results:
            self.assertEqual(
                control.result_hash,
                compute_security_abuse_control_result_hash(control),
            )
            self.assertNotEqual(control.evidence_hash, ZERO_HASH)
        self.assertFalse(receipt.network_accessed)
        self.assertFalse(receipt.subprocess_spawned)
        self.assertFalse(receipt.credential_material_read)
        self.assertFalse(receipt.provider_called)
        self.assertFalse(receipt.direct_mutation_performed)
        self.assertFalse(receipt.silent_repair_performed)

    def test_each_abuse_class_rejects_fail_closed(self) -> None:
        cases = {
            "unsafe_subprocess": {"command": "rm -rf /"},
            "hidden_network": {"request_url": "https://example.invalid/callback"},
            "credential_access": {"api_key": "sk-abcdefghijklmnopqrstuvwx"},
            "path_traversal": {"requested_write_relpaths": ("../escape.json",)},
            "arbitrary_write": {"requested_write_relpaths": ("reports/other.json",)},
            "daemon_default": {"daemon_enabled": True},
            "model_tool_direct_mutation": {"tool_direct_mutation": True},
            "approval_replay_bypass": {"approval_required": False},
            "mutable_audit": {"audit_append_only": False},
            "silent_repair": {"silent_repair": True},
            "uncontrolled_provider": {"provider_enabled": True},
            "leakage": {"raw_provider_response": "model output"},
            "env_credential_capture": {"env": {"API_KEY": "blocked"}},
            "console_mutation_bypass": {"direct_console_edits_enabled": True},
        }
        for control_id, patch in cases.items():
            with self.subTest(control_id=control_id):
                payload = _valid_payload()
                payload.update(patch)
                with tempfile.TemporaryDirectory() as tempdir:
                    receipt = _evaluate(Path(tempdir), payload)
                by_id = {control.control_id: control for control in receipt.control_results}
                self.assertFalse(receipt.accepted)
                self.assertFalse(by_id[control_id].accepted)
                self.assertTrue(by_id[control_id].failures)
                self.assertNotEqual(receipt.wal_record_hash, ZERO_HASH)

    def test_symlink_escape_rejects_existing_symlink_path(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            outside = root / "outside"
            outside.mkdir()
            link = root / "link"
            link.symlink_to(outside, target_is_directory=True)
            payload = _valid_payload()
            payload["allowed_write_relpaths"] = ("link/report.json",)
            payload["requested_write_relpaths"] = ("link/report.json",)

            receipt = _evaluate(root, payload)

        by_id = {control.control_id: control for control in receipt.control_results}
        self.assertFalse(receipt.accepted)
        self.assertFalse(by_id["symlink_escape"].accepted)
        self.assertIn("symlink_escape_forbidden:requested_write_relpaths", by_id["symlink_escape"].failures)

    def test_rejected_receipt_does_not_persist_sensitive_payload_values(self) -> None:
        payload = _valid_payload()
        payload.update(
            {
                "api_key": "sk-abcdefghijklmnopqrstuvwx",
                "raw_provider_response": "plain model output",
                "request_url": "https://example.invalid/leak",
            }
        )
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            receipt = _evaluate(root, payload)
            receipt_text = next(
                (root / "security-abuse-boundary" / "receipts").glob("*.json")
            ).read_text(encoding="utf-8")

        self.assertFalse(receipt.accepted)
        self.assertIn("request_fingerprint_hash", receipt_text)
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwx", receipt_text)
        self.assertNotIn("plain model output", receipt_text)
        self.assertNotIn("https://example.invalid/leak", receipt_text)

    def test_source_has_no_external_execution_imports(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])

        forbidden_imports = {
            "argparse",
            "asyncio",
            "httpx",
            "mcp",
            "openai",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "threading",
            "urllib",
            "webbrowser",
        }
        self.assertFalse(imports.intersection(forbidden_imports))
        for marker in ("requests.", "urllib.", "socket.", "Popen", "os.system", "while True"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
