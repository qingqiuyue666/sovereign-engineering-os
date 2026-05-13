import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.local_file_intake import (
    LocalFileIntakeResult,
    build_local_file_intake_ledger,
)


def read_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


class LocalFileIntakeTests(unittest.TestCase):
    def test_builds_ledger_for_real_temporary_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "a.txt").write_text("alpha", encoding="utf-8")
            (input_dir / "b.txt").write_text("beta", encoding="utf-8")

            result = build_local_file_intake_ledger(
                input_dir,
                output_dir / "ledger.jsonl",
            )

            self.assertIsInstance(result, LocalFileIntakeResult)
            self.assertEqual(result.files_seen, 2)
            self.assertEqual(result.files_recorded, 2)
            self.assertEqual(result.bytes_recorded, 9)
            entries = read_jsonl(result.output_ledger_path)
            self.assertEqual(
                [entry["relative_path"] for entry in entries],
                ["a.txt", "b.txt"],
            )
            self.assertEqual(
                list(entries[0]),
                [
                    "relative_path",
                    "size_bytes",
                    "sha256",
                    "modified_time_ns",
                ],
            )
            self.assertEqual(len(entries[0]["sha256"]), 64)
            self.assertIsInstance(entries[0]["modified_time_ns"], int)

    def test_does_not_modify_input_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            source = input_dir / "source.txt"
            source.write_text("stable", encoding="utf-8")
            before_bytes = source.read_bytes()
            before_mtime = source.stat().st_mtime_ns

            build_local_file_intake_ledger(
                input_dir,
                output_dir / "ledger.jsonl",
            )

            self.assertEqual(source.read_bytes(), before_bytes)
            self.assertEqual(source.stat().st_mtime_ns, before_mtime)
            self.assertTrue(source.exists())

    def test_rejects_output_path_inside_input_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            input_dir.mkdir()

            with self.assertRaises(ValueError):
                build_local_file_intake_ledger(
                    input_dir,
                    input_dir / "ledger.jsonl",
                )

    def test_skips_hidden_files_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / ".hidden.txt").write_text("hidden", encoding="utf-8")
            (input_dir / "visible.txt").write_text("visible", encoding="utf-8")

            result = build_local_file_intake_ledger(
                input_dir,
                output_dir / "ledger.jsonl",
            )

            self.assertEqual(result.skipped_hidden, 1)
            self.assertEqual(
                [entry["relative_path"] for entry in read_jsonl(result.output_ledger_path)],
                ["visible.txt"],
            )

    def test_includes_hidden_files_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / ".hidden.txt").write_text("hidden", encoding="utf-8")

            result = build_local_file_intake_ledger(
                input_dir,
                output_dir / "ledger.jsonl",
                include_hidden=True,
            )

            self.assertEqual(result.skipped_hidden, 0)
            self.assertEqual(
                [entry["relative_path"] for entry in read_jsonl(result.output_ledger_path)],
                [".hidden.txt"],
            )

    def test_skips_symlinks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            target = input_dir / "target.txt"
            target.write_text("target", encoding="utf-8")
            link = input_dir / "link.txt"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")

            result = build_local_file_intake_ledger(
                input_dir,
                output_dir / "ledger.jsonl",
            )

            self.assertEqual(result.skipped_symlinks, 1)
            self.assertEqual(
                [entry["relative_path"] for entry in read_jsonl(result.output_ledger_path)],
                ["target.txt"],
            )

    def test_non_recursive_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            nested = input_dir / "nested"
            nested.mkdir(parents=True)
            output_dir.mkdir()
            (nested / "child.txt").write_text("child", encoding="utf-8")
            (input_dir / "root.txt").write_text("root", encoding="utf-8")

            result = build_local_file_intake_ledger(
                input_dir,
                output_dir / "ledger.jsonl",
            )

            self.assertEqual(
                [entry["relative_path"] for entry in read_jsonl(result.output_ledger_path)],
                ["root.txt"],
            )

    def test_recursive_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            nested = input_dir / "nested"
            nested.mkdir(parents=True)
            output_dir.mkdir()
            (nested / "child.txt").write_text("child", encoding="utf-8")
            (input_dir / "root.txt").write_text("root", encoding="utf-8")

            result = build_local_file_intake_ledger(
                input_dir,
                output_dir / "ledger.jsonl",
                recursive=True,
            )

            self.assertEqual(
                [entry["relative_path"] for entry in read_jsonl(result.output_ledger_path)],
                ["nested/child.txt", "root.txt"],
            )

    def test_rejects_missing_input_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "output"
            output_dir.mkdir()

            with self.assertRaises(ValueError):
                build_local_file_intake_ledger(
                    root / "missing",
                    output_dir / "ledger.jsonl",
                )

    def test_rejects_non_directory_input_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "input.txt"
            output_dir = root / "output"
            source.write_text("not a directory", encoding="utf-8")
            output_dir.mkdir()

            with self.assertRaises(ValueError):
                build_local_file_intake_ledger(
                    source,
                    output_dir / "ledger.jsonl",
                )

    def test_rejects_missing_output_parent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            input_dir.mkdir()

            with self.assertRaises(ValueError):
                build_local_file_intake_ledger(
                    input_dir,
                    Path(temp_dir) / "missing" / "ledger.jsonl",
                )

    def test_atomic_overwrite_behavior(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            ledger = output_dir / "ledger.jsonl"
            ledger.write_text("old ledger\n", encoding="utf-8")
            (input_dir / "new.txt").write_text("new", encoding="utf-8")

            build_local_file_intake_ledger(input_dir, ledger)

            entries = read_jsonl(ledger)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["relative_path"], "new.txt")
            self.assertNotIn("old ledger", ledger.read_text(encoding="utf-8"))

    def test_deterministic_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "b.txt").write_text("b", encoding="utf-8")
            (input_dir / "a.txt").write_text("a", encoding="utf-8")

            first = output_dir / "first.jsonl"
            second = output_dir / "second.jsonl"
            build_local_file_intake_ledger(input_dir, first)
            build_local_file_intake_ledger(input_dir, second)

            self.assertEqual(
                first.read_text(encoding="utf-8"),
                second.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
