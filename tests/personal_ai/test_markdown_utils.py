import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.markdown_utils import write_markdown_atomically


class MarkdownUtilsTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_writes_final_newline(self):
        root = self.build_workspace()
        output_path = root / "artifact.md"

        write_markdown_atomically(output_path, "hello")

        self.assertEqual(output_path.read_text(encoding="utf-8"), "hello\n")

    def test_deterministic_overwrite(self):
        root = self.build_workspace()
        output_path = root / "artifact.md"

        write_markdown_atomically(output_path, "stable\n")
        first_bytes = output_path.read_bytes()
        write_markdown_atomically(output_path, "stable")
        second_bytes = output_path.read_bytes()

        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(second_bytes, b"stable\n")

    def test_invalid_missing_parent_rejected(self):
        root = self.build_workspace()

        with self.assertRaisesRegex(ValueError, "output_path parent is missing"):
            write_markdown_atomically(root / "missing" / "artifact.md", "hello")

    def test_overwrite_does_not_corrupt_existing_file_if_write_fails(self):
        root = self.build_workspace()
        output_path = root / "artifact.md"
        write_markdown_atomically(output_path, "keep")

        with self.assertRaisesRegex(ValueError, "markdown content must be text"):
            write_markdown_atomically(output_path, {"not": "markdown"})

        self.assertEqual(output_path.read_text(encoding="utf-8"), "keep\n")

    def test_production_markdown_outputs_do_not_use_path_write_text(self):
        production_files = sorted(Path("kernel/personal_ai").glob("*.py"))

        for production_file in production_files:
            with self.subTest(production_file=production_file.as_posix()):
                source = production_file.read_text(encoding="utf-8")
                self.assertNotIn(".write_text(", source)


if __name__ == "__main__":
    unittest.main()
