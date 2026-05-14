import hashlib
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.hash_utils import (
    canonical_json_bytes,
    hash_artifact_set,
    sha256_canonical_json,
    sha256_file,
    sha256_text,
)


class HashUtilsTests(unittest.TestCase):
    def test_sha256_file_is_deterministic(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "artifact.txt"
        path.write_text("deterministic content\n", encoding="utf-8")

        expected = hashlib.sha256(path.read_bytes()).hexdigest()

        self.assertEqual(sha256_file(path), expected)
        self.assertEqual(sha256_file(path), expected)

    def test_sha256_file_rejects_missing_file(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        with self.assertRaisesRegex(ValueError, "missing"):
            sha256_file(Path(temp_dir.name) / "missing.txt")

    def test_sha256_file_rejects_directory(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        with self.assertRaisesRegex(ValueError, "not a file"):
            sha256_file(Path(temp_dir.name))

    def test_canonical_json_hash_is_independent_of_key_order(self):
        first = {"b": 2, "a": {"z": 1, "y": 0}}
        second = {"a": {"y": 0, "z": 1}, "b": 2}

        self.assertEqual(
            sha256_canonical_json(first),
            sha256_canonical_json(second),
        )

    def test_canonical_json_uses_compact_deterministic_encoding(self):
        payload = {"b": "é", "a": [1, 2]}

        self.assertEqual(
            canonical_json_bytes(payload),
            '{"a":[1,2],"b":"é"}'.encode("utf-8"),
        )
        self.assertEqual(
            sha256_text('{"a":[1,2],"b":"é"}'),
            sha256_canonical_json(payload),
        )

    def test_hash_artifact_set_is_sorted_and_deterministic(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        first = root / "first.txt"
        second = root / "second.txt"
        first.write_text("first", encoding="utf-8")
        second.write_text("second", encoding="utf-8")

        hashes = hash_artifact_set({"zeta": second, "alpha": first})

        self.assertEqual(list(hashes), ["alpha", "zeta"])
        self.assertEqual(hashes, hash_artifact_set({"zeta": second, "alpha": first}))

    def test_hash_artifact_set_does_not_return_raw_sentinel_content(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "artifact.txt"
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        path.write_text(sentinel, encoding="utf-8")

        hashes = hash_artifact_set({"artifact": path})

        self.assertEqual(set(hashes), {"artifact"})
        self.assertNotIn(sentinel, str(hashes))


if __name__ == "__main__":
    unittest.main()
