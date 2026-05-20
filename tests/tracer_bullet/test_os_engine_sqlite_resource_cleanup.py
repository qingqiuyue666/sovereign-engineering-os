"""Resource cleanup tests for SQLite-backed OS engine components."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.database import DatabaseError, OSDatabase
from kernel.os_engine.event_log import EventLog
from kernel.os_engine.human_review_gate import HumanReviewGate
from kernel.os_engine.os_engine_bootstrap import bootstrap_os_engine
from kernel.os_engine.sqlite_artifact_store import SQLiteArtifactStore
from kernel.os_engine.sqlite_job_queue import SQLiteJobQueue


class OSEngineSQLiteResourceCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_database_connection_can_be_closed_explicitly(self) -> None:
        database = OSDatabase(root=self.root, db_path=self.root / "brain.sqlite3")
        database.initialize()
        connection = database.connect()
        handle = connection.__enter__()
        handle.execute("SELECT 1").fetchone()
        connection.__exit__(None, None, None)
        database.close()
        self.assertTrue(database.closed)
        with self.assertRaises(DatabaseError):
            database.initialize()

    def test_context_manager_closes_database_wrapper(self) -> None:
        with OSDatabase(root=self.root, db_path=self.root / "brain.sqlite3") as database:
            self.assertFalse(database.closed)
            self.assertTrue(database.table_names())
        self.assertTrue(database.closed)

    def test_components_close_or_delegate_ownership_cleanly(self) -> None:
        database = OSDatabase(root=self.root, db_path=self.root / "brain.sqlite3")
        event_log = EventLog(database)
        queue = SQLiteJobQueue(database)
        store = SQLiteArtifactStore(database=database, artifact_root=self.root / "artifacts")
        gate = HumanReviewGate(database)
        event_log.close()
        queue.close()
        store.close()
        gate.close()
        database.close()
        self.assertTrue(event_log.closed)
        self.assertTrue(queue.closed)
        self.assertTrue(store.closed)
        self.assertTrue(gate.closed)
        self.assertTrue(database.closed)

    def test_bootstrap_result_closes_cleanly(self) -> None:
        summary = bootstrap_os_engine(root=self.root)
        with summary as owned:
            self.assertEqual(owned.executed_jobs, 0)
        summary.close()

    def test_repeated_open_close_cycles_emit_no_resourcewarning(self) -> None:
        code = """
import gc
import tempfile
from pathlib import Path
from kernel.os_engine.database import OSDatabase
from kernel.os_engine.artifact_store import ArtifactStore
from kernel.os_engine.sqlite_job_queue import SQLiteJobQueue

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    for index in range(20):
        root = base / f"cycle_{index}"
        with OSDatabase(root=root, db_path=root / "brain.sqlite3") as database:
            queue = SQLiteJobQueue(database)
            queue.create_job(job_id=f"job_{index}", job_type="git_status", input_manifest={})
            queue.close()
        artifact_root = root / "legacy_artifacts"
        artifact_root.mkdir(parents=True, exist_ok=True)
        artifact_path = artifact_root / "artifact.json"
        artifact_path.write_text("{}", encoding="utf-8")
        legacy_store = ArtifactStore(
            db_path=root / "legacy_artifacts.sqlite3",
            artifact_root=artifact_root,
        )
        legacy_store.register_artifact(job_id=f"job_{index}", local_path=artifact_path)
        legacy_store.get_artifact("missing")
        gc.collect()
"""
        completed = subprocess.run(
            [sys.executable, "-W", "error::ResourceWarning", "-c", code],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_no_global_resourcewarning_suppression_is_used(self) -> None:
        for path in (
            Path("kernel/os_engine/database.py"),
            Path("kernel/os_engine/local_os_runtime.py"),
            Path("kernel/os_engine/artifact_store.py"),
        ):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("filterwarnings", source)
            self.assertNotIn("simplefilter('ignore'", source)
            self.assertNotIn('simplefilter("ignore"', source)


if __name__ == "__main__":
    unittest.main()
