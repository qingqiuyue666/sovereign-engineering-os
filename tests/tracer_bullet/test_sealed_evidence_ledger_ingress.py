import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from kernel.evidence.append_only_ledger import AppendOnlyLedger, LedgerViolation
from kernel.stores.sqlite.repositories import AuditRepository


class SealedEvidenceLedgerIngressTests(unittest.TestCase):
    def make_ledger(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "audit.sqlite3"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        self.addCleanup(conn.close)
        self._create_schema(conn)
        repo = AuditRepository(conn)
        ledger = AppendOnlyLedger(repository=repo, actor_identity="test-actor")
        return conn, ledger

    def digest(self, text="payload"):
        return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _create_schema(self, conn):
        conn.executescript(
            """
            CREATE TABLE audit_records (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_record_id TEXT NOT NULL UNIQUE,
                task_id TEXT,
                root_revision_id TEXT,
                record_type TEXT NOT NULL,
                causality_ref TEXT,
                actor_identity TEXT NOT NULL,
                artifact_refs_json TEXT NOT NULL,
                version_tuple_hash TEXT NOT NULL,
                taint_set_json TEXT NOT NULL,
                payload_json TEXT,
                failure_bundle_id TEXT,
                replay_anchor_id TEXT,
                approval_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TRIGGER audit_records_no_update
            BEFORE UPDATE ON audit_records
            BEGIN
                SELECT RAISE(ABORT, 'audit records are append-only');
            END;
            CREATE TRIGGER audit_records_no_delete
            BEFORE DELETE ON audit_records
            BEGIN
                SELECT RAISE(ABORT, 'audit records are append-only');
            END;
            """
        )

    def test_plain_payload_without_evidence_markers_still_appends(self):
        conn, ledger = self.make_ledger()

        audit_id = ledger.append(
            record_type="ordinary_audit_note",
            task_id="task-plain",
            payload={"status": "ok", "detail": "ordinary"},
        )

        row = conn.execute(
            "SELECT audit_record_id, payload_json FROM audit_records WHERE audit_record_id = ?",
            (audit_id,),
        ).fetchone()
        self.assertEqual(row["audit_record_id"], audit_id)
        self.assertIn("ordinary", row["payload_json"])

    def test_sealed_contract_payload_appends_when_valid(self):
        conn, ledger = self.make_ledger()

        audit_id = ledger.append(
            record_type="sealed_evidence_audit_note",
            task_id="task-sealed",
            payload={
                "evidence_contract": "sealed_redaction_v1",
                "evidence": {
                    "evidence_id": "ev-secret-hash-only",
                    "classification": "secret",
                    "digest": self.digest("secret"),
                    "representation": "sha256",
                    "payload": {
                        "contains_sensitive_material": True,
                        "stored_as": "hash_only",
                    },
                },
            },
        )

        row = conn.execute(
            "SELECT audit_record_id, payload_json FROM audit_records WHERE audit_record_id = ?",
            (audit_id,),
        ).fetchone()
        self.assertEqual(row["audit_record_id"], audit_id)
        self.assertIn("sealed_redaction_v1", row["payload_json"])

    def test_raw_prompt_payload_is_rejected_before_persist(self):
        conn, ledger = self.make_ledger()

        with self.assertRaisesRegex(LedgerViolation, "sealed evidence payload rejected"):
            ledger.append(
                record_type="unsafe_raw_prompt",
                task_id="task-unsafe",
                payload={
                    "classification": "restricted",
                    "digest": self.digest("unsafe"),
                    "payload": {"raw_prompt": "do not persist this"},
                },
            )

        count = conn.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0]
        self.assertEqual(count, 0)

    def test_plaintext_secret_marker_is_rejected_before_persist(self):
        conn, ledger = self.make_ledger()

        with self.assertRaisesRegex(LedgerViolation, "sealed evidence payload rejected"):
            ledger.append(
                record_type="unsafe_secret_marker",
                task_id="task-secret",
                payload={
                    "evidence_contract": "sealed_redaction_v1",
                    "evidence_id": "ev-secret-leak",
                    "classification": "secret",
                    "digest": self.digest("leak"),
                    "representation": "sha256",
                    "payload": {"note": "OPENAI_API_KEY=sk-test-secret-value"},
                },
            )

        count = conn.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0]
        self.assertEqual(count, 0)

    def test_sealed_blob_reference_is_required_for_sealed_blob_representation(self):
        conn, ledger = self.make_ledger()

        with self.assertRaisesRegex(LedgerViolation, "sealed_ref_required"):
            ledger.append(
                record_type="unsafe_missing_sealed_ref",
                task_id="task-sealed-ref",
                payload={
                    "evidence_contract": "sealed_redaction_v1",
                    "evidence_id": "ev-missing-ref",
                    "classification": "secret",
                    "digest": self.digest("missing-ref"),
                    "representation": "sealed_blob_ref",
                    "payload": {"contains_sensitive_material": True},
                },
            )

        count = conn.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0]
        self.assertEqual(count, 0)

    def test_source_does_not_introduce_runtime_network_or_secret_read_surface(self):
        source = Path("kernel/evidence/append_only_ledger.py").read_text(encoding="utf-8")
        forbidden_markers = (
            "requests",
            "httpx",
            "urllib",
            "socket.",
            "subprocess",
            "os.system",
            "openai.",
            "getenv",
            "environ",
        )
        for marker in forbidden_markers:
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
