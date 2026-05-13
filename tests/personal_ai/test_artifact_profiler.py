import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.artifact_profiler import build_artifact_profile
from kernel.personal_ai.local_file_intake import build_local_file_intake_ledger


def ledger_entry(relative_path, size_bytes):
    return {
        "relative_path": relative_path,
        "size_bytes": size_bytes,
        "sha256": f"{size_bytes:064x}"[-64:],
        "modified_time_ns": size_bytes,
    }


def write_ledger(path, entries):
    path.write_text(
        "".join(json.dumps(entry) + "\n" for entry in entries),
        encoding="utf-8",
    )


class ArtifactProfilerTests(unittest.TestCase):
    def test_builds_profile_from_real_ledger(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "notes.md").write_text("notes", encoding="utf-8")
            ledger = output_dir / "ledger.jsonl"
            profile_path = output_dir / "profile.json"
            build_local_file_intake_ledger(input_dir, ledger)

            result = build_artifact_profile(ledger, profile_path)

            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertEqual(result.total_files, 1)
            self.assertEqual(profile["entries"][0]["relative_path"], "notes.md")
            self.assertEqual(profile["entries"][0]["extension"], ".md")
            self.assertEqual(profile["entries"][0]["category"], "document")

    def test_classifies_all_required_extension_categories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            ledger = output_dir / "ledger.jsonl"
            profile_path = output_dir / "profile.json"
            write_ledger(
                ledger,
                [
                    ledger_entry("data.csv", 1),
                    ledger_entry("readme.md", 2),
                    ledger_entry("image.png", 3),
                    ledger_entry("movie.mp4", 4),
                    ledger_entry("sound.mp3", 5),
                    ledger_entry("bundle.zip", 6),
                    ledger_entry("script.py", 7),
                    ledger_entry("mystery.bin", 8),
                ],
            )

            build_artifact_profile(ledger, profile_path)

            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            categories = {
                entry["relative_path"]: entry["category"]
                for entry in profile["entries"]
            }
            self.assertEqual(categories["data.csv"], "spreadsheet")
            self.assertEqual(categories["readme.md"], "document")
            self.assertEqual(categories["image.png"], "image")
            self.assertEqual(categories["movie.mp4"], "video")
            self.assertEqual(categories["sound.mp3"], "audio")
            self.assertEqual(categories["bundle.zip"], "archive")
            self.assertEqual(categories["script.py"], "code")
            self.assertEqual(categories["mystery.bin"], "unknown")

    def test_computes_total_files_and_total_bytes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            ledger = output_dir / "ledger.jsonl"
            profile_path = output_dir / "profile.json"
            write_ledger(
                ledger,
                [
                    ledger_entry("a.txt", 10),
                    ledger_entry("b.txt", 15),
                ],
            )

            result = build_artifact_profile(ledger, profile_path)

            self.assertEqual(result.total_files, 2)
            self.assertEqual(result.total_bytes, 25)

    def test_computes_categories_and_extensions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            ledger = output_dir / "ledger.jsonl"
            profile_path = output_dir / "profile.json"
            write_ledger(
                ledger,
                [
                    ledger_entry("a.csv", 1),
                    ledger_entry("b.csv", 2),
                    ledger_entry("c.unknown", 3),
                ],
            )

            result = build_artifact_profile(ledger, profile_path)

            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertEqual(result.categories["spreadsheet"], 2)
            self.assertEqual(result.categories["unknown"], 1)
            self.assertEqual(profile["extensions"], {".csv": 2, ".unknown": 1})

    def test_produces_deterministic_ordering(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            ledger = output_dir / "ledger.jsonl"
            profile_path = output_dir / "profile.json"
            write_ledger(
                ledger,
                [
                    ledger_entry("z.txt", 30),
                    ledger_entry("a.txt", 30),
                    ledger_entry("m.txt", 40),
                ],
            )

            build_artifact_profile(ledger, profile_path)

            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [entry["relative_path"] for entry in profile["entries"]],
                ["a.txt", "m.txt", "z.txt"],
            )
            self.assertEqual(
                [entry["relative_path"] for entry in profile["largest_files"]],
                ["m.txt", "a.txt", "z.txt"],
            )

    def test_does_not_require_original_input_files_after_ledger_created(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            source = input_dir / "gone.txt"
            source.write_text("gone", encoding="utf-8")
            ledger = output_dir / "ledger.jsonl"
            profile_path = output_dir / "profile.json"
            build_local_file_intake_ledger(input_dir, ledger)
            source.unlink()

            result = build_artifact_profile(ledger, profile_path)

            self.assertEqual(result.total_files, 1)
            self.assertTrue(profile_path.exists())

    def test_rejects_missing_ledger(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            with self.assertRaises(ValueError):
                build_artifact_profile(
                    output_dir / "missing.jsonl",
                    output_dir / "profile.json",
                )

    def test_rejects_missing_output_parent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            ledger = output_dir / "ledger.jsonl"
            write_ledger(ledger, [ledger_entry("a.txt", 1)])

            with self.assertRaises(ValueError):
                build_artifact_profile(
                    ledger,
                    output_dir / "missing" / "profile.json",
                )


if __name__ == "__main__":
    unittest.main()
