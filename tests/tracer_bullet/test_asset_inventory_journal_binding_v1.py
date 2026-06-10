"""Tracer-bullet tests for asset inventory journal binding v1."""

from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile
import unittest

from kernel.runtime.asset_inventory_journal_binding import (
    ASSET_INVENTORY_EVENT_TYPE,
    AssetInventoryJournalBinding,
    AssetInventoryScanJournal,
    compute_aggregate_inventory_hash,
    scan_asset_inventory_to_journal,
)
from kernel.runtime.minimal_asset_inventory import scan_asset_inventory

POLICY_PATH = Path("governance/assets/asset_inventory_journal_binding_v1.json")
SOURCE_PATH = Path("kernel/runtime/asset_inventory_journal_binding.py")


class AssetInventoryJournalBindingTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "asset_inventory_journal_binding_v1")
        self.assertTrue(policy["uses_minimal_asset_inventory"])
        self.assertTrue(policy["uses_sqlite_wal_mode"])
        self.assertEqual(policy["adapter_event_type"], ASSET_INVENTORY_EVENT_TYPE)
        self.assertTrue(policy["append_only"])
        self.assertFalse(policy["home_root_allowed"])
        self.assertFalse(policy["filesystem_root_allowed"])
        self.assertFalse(policy["symlink_escape_allowed"])
        self.assertFalse(policy["embeddings_allowed"])
        self.assertFalse(policy["lancedb_allowed"])
        self.assertFalse(policy["openusd_runtime_allowed"])

    def test_valid_fixture_scan_writes_inventory_journal_event(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "assets"
            root.mkdir()
            (root / "plate.png").write_bytes(b"png")
            (root / "notes.md").write_text("notes", encoding="utf-8")
            journal = AssetInventoryScanJournal(Path(tempdir) / "asset_journal.sqlite3")
            event = scan_asset_inventory_to_journal({"fixture": root}, journal)
            events = journal.list_events()
            journal.close()

        self.assertEqual(event.event_type, ASSET_INVENTORY_EVENT_TYPE)
        self.assertEqual(event.asset_count, 2)
        self.assertEqual(event.root_ids, ("fixture",))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].content_hash, event.content_hash)
        self.assertTrue(event.aggregate_inventory_hash.startswith("sha256:"))
        self.assertEqual(len(event.per_asset_content_hashes), 2)

    def test_aggregate_inventory_hash_deterministic_excluding_timestamp(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "b.txt").write_text("b", encoding="utf-8")
            (root / "a.txt").write_text("a", encoding="utf-8")
            first_records = scan_asset_inventory({"fixture": root})
            second_records = scan_asset_inventory({"fixture": root})
        self.assertEqual(
            compute_aggregate_inventory_hash(first_records),
            compute_aggregate_inventory_hash(second_records),
        )

    def test_per_asset_hashes_deterministic(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "asset.txt").write_text("stable", encoding="utf-8")
            first = scan_asset_inventory({"fixture": root})[0]
            second = scan_asset_inventory({"fixture": root})[0]
        self.assertEqual(first.content_hash, second.content_hash)

    def test_journal_chain_verifies(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "assets"
            root.mkdir()
            (root / "a.txt").write_text("a", encoding="utf-8")
            journal = AssetInventoryScanJournal(Path(tempdir) / "asset_journal.sqlite3")
            scan_asset_inventory_to_journal({"fixture": root}, journal)
            (root / "b.txt").write_text("b", encoding="utf-8")
            AssetInventoryJournalBinding(journal).scan_and_append({"fixture": root})
            verification = journal.verify_chain()
            events = journal.list_events()
            journal.close()
        self.assertTrue(verification.valid, verification.failures)
        self.assertEqual(events[1].previous_hash, events[0].content_hash)

    def test_home_and_root_scan_rejected(self):
        with tempfile.TemporaryDirectory() as tempdir:
            journal = AssetInventoryScanJournal(Path(tempdir) / "asset_journal.sqlite3")
            with self.assertRaises(ValueError):
                scan_asset_inventory_to_journal({"home": Path.home()}, journal)
            with self.assertRaises(ValueError):
                scan_asset_inventory_to_journal({"root": Path("/")}, journal)
            journal.close()

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            journal = AssetInventoryScanJournal(root / "asset_journal.sqlite3")
            with self.assertRaises(ValueError):
                scan_asset_inventory_to_journal({"bad": root / ".." / root.name}, journal)
            journal.close()

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "root"
            outside = Path(tempdir) / "outside.txt"
            root.mkdir()
            outside.write_text("outside", encoding="utf-8")
            os.symlink(outside, root / "escape.txt")
            journal = AssetInventoryScanJournal(Path(tempdir) / "asset_journal.sqlite3")
            with self.assertRaises(ValueError):
                scan_asset_inventory_to_journal({"fixture": root}, journal)
            journal.close()

    def test_source_files_not_mutated(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "assets"
            root.mkdir()
            file_path = root / "asset.txt"
            file_path.write_text("stable", encoding="utf-8")
            before = file_path.stat().st_mtime_ns
            journal = AssetInventoryScanJournal(Path(tempdir) / "asset_journal.sqlite3")
            scan_asset_inventory_to_journal({"fixture": root}, journal)
            journal.close()
            after = file_path.stat().st_mtime_ns
        self.assertEqual(before, after)

    def test_no_heavy_dependency_imports(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        forbidden_imports = (
            "lancedb",
            "numpy",
            "PIL",
            "cv2",
            "pxr",
            "openusd",
        )
        for forbidden in forbidden_imports:
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)
        self.assertNotIn("read_bytes", source)

    def test_no_embeddings_vector_db_or_openusd_runtime(self):
        source = SOURCE_PATH.read_text(encoding="utf-8").lower()
        for forbidden in ("embedding", "vector_db", "lancedb", "openusd runtime"):
            self.assertNotIn(forbidden, source)

    def test_no_network_provider_browser_surface(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in ("requests", "urllib", "socket", "webbrowser", "playwright"):
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)

    def test_no_update_delete_public_method_exists(self):
        journal_methods = {
            name for name in dir(AssetInventoryScanJournal) if not name.startswith("_")
        }
        for forbidden in ("update", "delete", "remove", "truncate", "mutate"):
            for method in journal_methods:
                self.assertFalse(method.startswith(forbidden), method)


if __name__ == "__main__":
    unittest.main()
