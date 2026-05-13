import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernel.personal_ai.io_utils import write_jsonl_atomically
from kernel.personal_ai.local_file_intake import LocalFileIntakeResult
from kernel.personal_ai.local_pipeline import (
    LocalReviewPipelineResult,
    build_local_review_pipeline,
)


EXPECTED_ARTIFACTS = {
    "intake_ledger.jsonl",
    "artifact_profile.json",
    "work_order_proposal.json",
    "review_packet.json",
    "pipeline_manifest.json",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


class LocalPipelineTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_dir = root / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        return input_dir, output_dir

    def test_builds_full_local_review_pipeline_from_temporary_files(self):
        input_dir, output_dir = self.build_workspace()
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")

        result = build_local_review_pipeline(input_dir, output_dir)

        self.assertIsInstance(result, LocalReviewPipelineResult)
        self.assertEqual(result.input_dir, input_dir)
        self.assertEqual(result.output_dir, output_dir)
        self.assertEqual(result.files_recorded, 2)
        self.assertEqual(
            result.candidate_tasks,
            [
                "spreadsheet_review",
                "document_review",
                "mixed_file_inventory",
            ],
        )
        self.assertIs(result.required_human_approval, True)

    def test_creates_exact_output_artifacts(self):
        input_dir, output_dir = self.build_workspace()
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")

        build_local_review_pipeline(input_dir, output_dir)

        self.assertEqual(
            {path.name for path in output_dir.iterdir()},
            EXPECTED_ARTIFACTS,
        )

    def test_manifest_records_non_authority_review_only_boundary(self):
        input_dir, output_dir = self.build_workspace()
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")

        result = build_local_review_pipeline(input_dir, output_dir)
        manifest = read_json(result.pipeline_manifest_path)

        self.assertEqual(manifest["authority"], "non_authority")
        self.assertEqual(
            manifest["execution_capability"],
            "not_introduced",
        )
        self.assertIs(manifest["required_human_approval"], True)
        self.assertEqual(
            manifest["next_allowed_action"],
            "human_review_only",
        )
        self.assertEqual(
            set(manifest["boundaries"]),
            {
                "no_runtime_authority",
                "no_execution_capability",
                "no_external_tool_control",
                "no_network",
                "no_api_calls",
                "no_subprocess",
                "no_adapter_implementation",
                "no_input_file_mutation",
                "no_destructive_actions",
            },
        )

    def test_manifest_artifact_paths_point_to_output_files(self):
        input_dir, output_dir = self.build_workspace()
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")

        result = build_local_review_pipeline(input_dir, output_dir)
        manifest = read_json(result.pipeline_manifest_path)

        self.assertEqual(
            manifest["artifacts"],
            {
                "intake_ledger": result.intake_ledger_path.as_posix(),
                "artifact_profile": result.artifact_profile_path.as_posix(),
                "work_order_proposal": result.work_order_proposal_path.as_posix(),
                "review_packet": result.review_packet_path.as_posix(),
            },
        )
        for artifact_path in manifest["artifacts"].values():
            self.assertTrue(Path(artifact_path).exists())

    def test_candidate_tasks_propagate_to_manifest_and_result(self):
        input_dir, output_dir = self.build_workspace()
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")
        (input_dir / "tool.py").write_text("print('x')", encoding="utf-8")

        result = build_local_review_pipeline(input_dir, output_dir)
        manifest = read_json(result.pipeline_manifest_path)
        work_order = read_json(result.work_order_proposal_path)

        self.assertEqual(result.candidate_tasks, work_order["candidate_tasks"])
        self.assertEqual(manifest["candidate_tasks"], work_order["candidate_tasks"])
        self.assertEqual(
            manifest["counts"]["candidate_tasks"],
            len(work_order["candidate_tasks"]),
        )

    def test_input_files_are_not_modified(self):
        input_dir, output_dir = self.build_workspace()
        source = input_dir / "notes.md"
        source.write_text("notes", encoding="utf-8")
        before_bytes = source.read_bytes()
        before_mtime = source.stat().st_mtime_ns

        build_local_review_pipeline(input_dir, output_dir)

        self.assertEqual(source.read_bytes(), before_bytes)
        self.assertEqual(source.stat().st_mtime_ns, before_mtime)
        self.assertTrue(source.exists())

    def test_rejects_output_dir_inside_input_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = input_dir / "output"
            output_dir.mkdir(parents=True)

            with self.assertRaises(ValueError):
                build_local_review_pipeline(input_dir, output_dir)

    def test_rejects_missing_input_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            output_dir.mkdir()

            with self.assertRaises(ValueError):
                build_local_review_pipeline(Path(temp_dir) / "missing", output_dir)

    def test_rejects_non_directory_input_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_file = root / "input.txt"
            output_dir = root / "output"
            input_file.write_text("not a directory", encoding="utf-8")
            output_dir.mkdir()

            with self.assertRaises(ValueError):
                build_local_review_pipeline(input_file, output_dir)

    def test_rejects_missing_output_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            input_dir.mkdir()

            with self.assertRaises(ValueError):
                build_local_review_pipeline(input_dir, Path(temp_dir) / "missing")

    def test_rejects_non_directory_output_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_file = root / "output.txt"
            input_dir.mkdir()
            output_file.write_text("not a directory", encoding="utf-8")

            with self.assertRaises(ValueError):
                build_local_review_pipeline(input_dir, output_file)

    def test_recursive_option_propagates(self):
        input_dir, output_dir = self.build_workspace()
        nested = input_dir / "nested"
        nested.mkdir()
        (input_dir / "root.txt").write_text("root", encoding="utf-8")
        (nested / "child.txt").write_text("child", encoding="utf-8")

        result = build_local_review_pipeline(
            input_dir,
            output_dir,
            recursive=True,
        )

        entries = read_jsonl(result.intake_ledger_path)
        self.assertEqual(
            [entry["relative_path"] for entry in entries],
            ["nested/child.txt", "root.txt"],
        )
        manifest = read_json(result.pipeline_manifest_path)
        self.assertEqual(manifest["counts"]["files_recorded"], 2)

    def test_include_hidden_option_propagates(self):
        input_dir, output_dir = self.build_workspace()
        (input_dir / ".hidden.txt").write_text("hidden", encoding="utf-8")
        (input_dir / "visible.txt").write_text("visible", encoding="utf-8")

        result = build_local_review_pipeline(
            input_dir,
            output_dir,
            include_hidden=True,
        )

        entries = read_jsonl(result.intake_ledger_path)
        self.assertEqual(
            [entry["relative_path"] for entry in entries],
            [".hidden.txt", "visible.txt"],
        )

    def test_downstream_artifacts_do_not_require_original_input_files(self):
        input_dir, output_dir = self.build_workspace()
        source = input_dir / "notes.md"
        source.write_text("notes", encoding="utf-8")

        def fake_intake(input_path, output_path, *, recursive, include_hidden):
            write_jsonl_atomically(
                output_path,
                [
                    {
                        "relative_path": "notes.md",
                        "size_bytes": 5,
                        "sha256": "0" * 64,
                        "modified_time_ns": 1,
                    }
                ],
            )
            source.unlink()
            return LocalFileIntakeResult(
                input_dir=input_path,
                output_ledger_path=output_path,
                files_seen=1,
                files_recorded=1,
                bytes_recorded=5,
                skipped_hidden=0,
                skipped_symlinks=0,
                recursive=recursive,
                include_hidden=include_hidden,
            )

        with patch(
            "kernel.personal_ai.local_pipeline.build_local_file_intake_ledger",
            fake_intake,
        ):
            result = build_local_review_pipeline(input_dir, output_dir)

        self.assertFalse(source.exists())
        self.assertEqual(result.files_recorded, 1)
        self.assertTrue(result.artifact_profile_path.exists())
        self.assertTrue(result.work_order_proposal_path.exists())
        self.assertTrue(result.review_packet_path.exists())

    def test_pipeline_output_is_deterministic_for_unchanged_files(self):
        input_dir, output_dir = self.build_workspace()
        (input_dir / "b.txt").write_text("b", encoding="utf-8")
        (input_dir / "a.txt").write_text("a", encoding="utf-8")

        build_local_review_pipeline(input_dir, output_dir)
        first = {
            artifact: (output_dir / artifact).read_text(encoding="utf-8")
            for artifact in EXPECTED_ARTIFACTS
        }
        build_local_review_pipeline(input_dir, output_dir)
        second = {
            artifact: (output_dir / artifact).read_text(encoding="utf-8")
            for artifact in EXPECTED_ARTIFACTS
        }

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
