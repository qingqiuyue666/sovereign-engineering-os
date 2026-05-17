import tempfile
import unittest
from pathlib import Path

from kernel.security.repository_hygiene import check_repository_hygiene


class RepositoryHygieneTests(unittest.TestCase):
    def test_blocks_forbidden_repository_paths(self):
        result = check_repository_hygiene([".env", "secrets/api.txt", "build/node_modules/pkg.js", "dump.sqlite"])
        self.assertFalse(result.clean)
        self.assertIn(".env", result.rejected_paths)
        self.assertIn("secrets/api.txt", result.rejected_paths)
        self.assertIn("build/node_modules/pkg.js", result.rejected_paths)
        self.assertIn("dump.sqlite", result.rejected_paths)

    def test_scans_file_contents_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "safe.txt"
            path.write_text("password=abc123456789SECRET", encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            result = check_repository_hygiene([path], scan_file_contents=True)
            self.assertFalse(result.clean)
            self.assertEqual(path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
