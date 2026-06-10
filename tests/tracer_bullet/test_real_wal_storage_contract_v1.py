"""Tests for the Real WAL Storage Contract V1."""

from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

from kernel.stores import real_wal_storage_contract as contract


SOURCE_PATH = Path("kernel/stores/real_wal_storage_contract.py")


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _record(sequence: int = 1, **overrides: object) -> contract.RealWalStorageRecord:
    payload: dict[str, object] = {
        "wal_record_id": f"real-wal-record-{sequence}",
        "wal_storage_contract_version": contract.REAL_WAL_STORAGE_CONTRACT_VERSION,
        "sequence": sequence,
        "previous_hash": None,
        "record_type": "MINIMAL_CONTROLLED_EXECUTION",
        "task_id": "task-001",
        "run_id": "run-001",
        "payload_hash": _hash(f"payload-{sequence}"),
        "digest_bindings": {
            "request_hash": _hash(f"request-{sequence}"),
            "decision_hash": _hash(f"decision-{sequence}"),
        },
        "created_at": "2026-05-27T00:00:00Z",
    }
    payload.update(overrides)
    return contract.RealWalStorageRecord(**payload)  # type: ignore[arg-type]


class RealWalStorageContractV1Tests(unittest.TestCase):
    def test_record_hash_is_deterministic_and_excludes_created_at(self) -> None:
        record = _record()
        later = _record(created_at="2030-01-01T00:00:00Z")

        self.assertEqual(record.record_hash, contract.compute_real_wal_storage_record_hash(record))
        self.assertEqual(record.record_hash, later.record_hash)

    def test_supplied_mismatched_record_hash_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "record_hash_mismatch"):
            _record(record_hash=_hash("wrong"))

    def test_sequence_and_previous_hash_chain_replay_accepts_valid_records(self) -> None:
        first = _record(sequence=1)
        second = _record(sequence=2, previous_hash=first.record_hash)

        result = contract.replay_real_wal_storage_records((first, second))

        self.assertTrue(result.accepted)
        self.assertEqual(result.record_count, 2)
        self.assertEqual(result.first_sequence, 1)
        self.assertEqual(result.last_sequence, 2)
        self.assertEqual(result.last_record_hash, second.record_hash)
        self.assertEqual(
            result.replay_result_hash,
            contract.compute_real_wal_storage_replay_result_hash(result),
        )

    def test_replay_detects_sequence_gap(self) -> None:
        first = _record(sequence=1)
        third = _record(sequence=3, previous_hash=first.record_hash)

        result = contract.replay_real_wal_storage_records((first, third))

        self.assertFalse(result.accepted)
        self.assertIn("sequence_gap_detected", result.rejection_reasons)

    def test_replay_detects_previous_hash_mismatch(self) -> None:
        first = _record(sequence=1)
        second = _record(sequence=2, previous_hash=_hash("not-first"))

        result = contract.replay_real_wal_storage_records((first, second))

        self.assertFalse(result.accepted)
        self.assertIn("previous_hash_mismatch", result.rejection_reasons)

    def test_tampered_record_hash_detected_by_replay(self) -> None:
        first = _record(sequence=1)
        second = _record(sequence=2, previous_hash=first.record_hash)
        object.__setattr__(second, "record_hash", _hash("tampered"))

        result = contract.replay_real_wal_storage_records((first, second))

        self.assertFalse(result.accepted)
        self.assertIn("record_hash_mismatch", result.rejection_reasons)

    def test_parse_rejects_partial_record_line_and_malformed_json(self) -> None:
        record = _record()
        line = contract.serialize_real_wal_storage_record_line(record)

        parsed = contract.parse_real_wal_storage_record_line(line)

        self.assertEqual(parsed.as_dict(), record.as_dict())
        with self.assertRaisesRegex(ValueError, "partial_record_line"):
            contract.parse_real_wal_storage_record_line(line.rstrip("\n"))
        with self.assertRaisesRegex(ValueError, "malformed_json"):
            contract.parse_real_wal_storage_record_line("{not-json}\n")

    def test_secret_raw_output_and_execution_material_fields_rejected(self) -> None:
        base = _record().as_dict()
        for field_name in ("raw_stdout", "stderr", "argv", "cwd", "timeout", "api_key"):
            payload = dict(base)
            payload[field_name] = "blocked"
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, "wal_record_field_forbidden"):
                    contract.real_wal_storage_record_from_mapping(payload)

    def test_digest_binding_names_are_digest_only_and_secret_safe(self) -> None:
        with self.assertRaisesRegex(ValueError, "digest_binding_name_secret_like"):
            _record(digest_bindings={"token_hash": _hash("token")})
        with self.assertRaisesRegex(ValueError, "digest_binding:request_hash_must_be_sha256"):
            _record(digest_bindings={"request_hash": "not-a-digest"})

    def test_unknown_record_type_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "record_type_invalid"):
            _record(record_type="UNCONTROLLED_EXECUTION")

    def test_contract_module_has_no_forbidden_import_surface(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])

        forbidden = {
            "argparse",
            "click",
            "httpx",
            "mcp",
            "openai",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "typer",
            "urllib",
            "webbrowser",
        }
        self.assertFalse(imported_roots.intersection(forbidden))
        self.assertNotIn("kernel.runtime", source)
        self.assertNotIn("kernel.execution", source)
        self.assertNotIn("sqlite3", source)


if __name__ == "__main__":
    unittest.main()
