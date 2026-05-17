import inspect
import unittest

from kernel.security.wal_integrity_guard import WalIntegrityGuard


class WalIntegrityGuardTests(unittest.TestCase):
    def test_accepts_descriptor_chain(self):
        guard = WalIntegrityGuard()
        first = guard.validate_descriptor(
            {
                "segment_id": "seg-1",
                "sequence": 1,
                "digest": "sha256:aaa",
                "previous_digest": "GENESIS",
            }
        )
        second = guard.validate_descriptor(
            {
                "segment_id": "seg-2",
                "sequence": 2,
                "digest": "sha256:bbb",
                "previous_digest": "sha256:aaa",
            }
        )

        self.assertTrue(first.accepted, first.failures)
        self.assertTrue(second.accepted, second.failures)

    def test_rejects_duplicate_and_sequence_rollback(self):
        guard = WalIntegrityGuard()
        self.assertTrue(
            guard.validate_descriptor(
                {
                    "segment_id": "seg-1",
                    "sequence": 2,
                    "digest": "sha256:aaa",
                    "previous_digest": "GENESIS",
                }
            ).accepted
        )

        result = guard.validate_descriptor(
            {
                "segment_id": "seg-1",
                "sequence": 1,
                "digest": "sha256:bbb",
                "previous_digest": "sha256:aaa",
            }
        )

        self.assertFalse(result.accepted)
        self.assertIn("duplicate_segment_id", result.failures)
        self.assertIn("sequence_rollback", result.failures)

    def test_rejects_hash_mismatch(self):
        guard = WalIntegrityGuard()
        result = guard.validate_descriptor(
            {
                "segment_id": "seg-1",
                "sequence": 1,
                "digest": "sha256:aaa",
                "previous_digest": "sha256:wrong",
                "expected_digest": "sha256:bbb",
            }
        )

        self.assertFalse(result.accepted)
        self.assertIn("wal_hash_mismatch", result.failures)

    def test_source_has_no_sqlite_or_file_io(self):
        source = inspect.getsource(__import__("kernel.security.wal_integrity_guard", fromlist=["x"]))

        self.assertNotIn("sqlite3", source)
        self.assertNotIn("open(", source)
        self.assertNotIn("Path(", source)
        self.assertNotIn(".db-wal", source)


if __name__ == "__main__":
    unittest.main()
