"""Tracer bullet tests for the SQLite WAL OS engine brain."""

from __future__ import annotations

import gc
import sqlite3
import tempfile
import unittest
import warnings
from pathlib import Path

from kernel.os_engine.database import DatabasePathError, OSDatabase, UnsafePayloadError, canonical_json, stable_content_hash
from kernel.os_engine.schema_version import SCHEMA_CONTENT_HASH, schema_content_hash


class OSEngineDatabaseWalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = self.root / "brain.sqlite3"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _db(self) -> OSDatabase:
        return OSDatabase(root=self.root, db_path=self.db_path)

    def test_wal_foreign_keys_schema_version_and_required_tables_exist(self) -> None:
        summary = self._db().initialize()
        self.assertEqual(summary.journal_mode, "wal")
        self.assertTrue(summary.foreign_keys)
        for table in {"schema_version", "jobs", "job_events", "artifacts", "materializations", "human_reviews"}:
            self.assertIn(table, summary.tables)
        with sqlite3.connect(self.db_path) as connection:
            self.assertEqual(connection.execute("SELECT content_hash FROM schema_version").fetchone()[0], SCHEMA_CONTENT_HASH)

    def test_repeated_initialization_is_idempotent_and_preserves_data(self) -> None:
        db = self._db()
        db.initialize()
        with db.connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "job_preserved",
                    "test",
                    "2026-01-01T00:00:00+00:00",
                    "created",
                    "{}",
                    "",
                    0,
                    0,
                    "",
                    1,
                    stable_content_hash({"job_id": "job_preserved"}),
                ),
            )
        first = db.initialize().schema_hash
        second = db.initialize().schema_hash
        self.assertEqual(first, second)
        with db.connect() as connection:
            count = connection.execute("SELECT COUNT(*) FROM jobs WHERE job_id = 'job_preserved'").fetchone()[0]
        self.assertEqual(count, 1)

    def test_path_escape_and_symlink_escape_are_rejected(self) -> None:
        with self.assertRaises(DatabasePathError):
            OSDatabase(root=self.root, db_path=self.root.parent / "escape.sqlite3")
        outside = self.root.parent / "outside-db"
        outside.mkdir(exist_ok=True)
        link = self.root / "linked"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlinks are unavailable on this filesystem")
        with self.assertRaises(DatabasePathError):
            OSDatabase(root=self.root, db_path=link / "brain.sqlite3")

    def test_connection_cleanup_does_not_emit_resourcewarning(self) -> None:
        db = self._db()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            gc.collect()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            for _ in range(5):
                db.initialize()
                with db.connect() as connection:
                    connection.execute("SELECT 1").fetchone()
                with self.assertRaises(sqlite3.ProgrammingError):
                    connection.execute("SELECT 1").fetchone()
        self.assertEqual([item for item in caught if issubclass(item.category, ResourceWarning)], [])

    def test_secret_like_payload_and_raw_env_keys_are_rejected(self) -> None:
        for payload in ({"api_key": "raw"}, {"env": {"TOKEN": "raw"}}, {"value": "Bearer abcdefghijklmnopqrstuvwxyz"}):
            with self.subTest(payload=payload):
                with self.assertRaises(UnsafePayloadError):
                    canonical_json(payload)

    def test_schema_hash_is_deterministic(self) -> None:
        self.assertEqual(schema_content_hash(), schema_content_hash())
        self.assertEqual(schema_content_hash(), SCHEMA_CONTENT_HASH)


if __name__ == "__main__":
    unittest.main()
