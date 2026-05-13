import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.io_utils import (
    write_json_atomically,
    write_jsonl_atomically,
)


class IoUtilsTests(unittest.TestCase):
    def test_write_json_atomically_writes_deterministic_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "payload.json"

            write_json_atomically(output, {"z": 1, "a": {"b": 2}})

            self.assertEqual(
                output.read_text(encoding="utf-8"),
                '{\n  "a": {\n    "b": 2\n  },\n  "z": 1\n}\n',
            )

    def test_write_jsonl_atomically_writes_deterministic_jsonl(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "payload.jsonl"

            write_jsonl_atomically(
                output,
                [
                    {"z": 1, "a": 2},
                    {"b": 3, "a": 4},
                ],
            )

            self.assertEqual(
                output.read_text(encoding="utf-8"),
                '{"a":2,"z":1}\n{"a":4,"b":3}\n',
            )

    def test_write_json_atomically_keeps_existing_output_on_invalid_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "payload.json"
            output.write_text('{"old": true}\n', encoding="utf-8")

            with self.assertRaises(TypeError):
                write_json_atomically(output, {"bad": object()})

            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8")),
                {"old": True},
            )

    def test_write_jsonl_atomically_keeps_existing_output_on_invalid_entry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "payload.jsonl"
            output.write_text('{"old":true}\n', encoding="utf-8")

            with self.assertRaises(TypeError):
                write_jsonl_atomically(
                    output,
                    [
                        {"ok": True},
                        {"bad": object()},
                    ],
                )

            self.assertEqual(
                output.read_text(encoding="utf-8"),
                '{"old":true}\n',
            )

    def test_rejects_missing_output_parent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "missing" / "payload.json"

            with self.assertRaises(ValueError):
                write_json_atomically(output, {"ok": True})

            with self.assertRaises(ValueError):
                write_jsonl_atomically(output.with_suffix(".jsonl"), [])

    def test_empty_jsonl_entries_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "payload.jsonl"
            output.write_text("old\n", encoding="utf-8")

            write_jsonl_atomically(output, [])
            first = output.read_text(encoding="utf-8")
            write_jsonl_atomically(output, [])
            second = output.read_text(encoding="utf-8")

            self.assertEqual(first, "")
            self.assertEqual(second, "")


if __name__ == "__main__":
    unittest.main()
