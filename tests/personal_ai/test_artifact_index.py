import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.artifact_index import (
    ArtifactIndexResult,
    build_artifact_index,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.job_package import build_local_job_package


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ArtifactIndexTests(unittest.TestCase):
    def build_job(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_root_dir = root / "packages"
        input_dir.mkdir()
        output_root_dir.mkdir()
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        (input_dir / "data.csv").write_text(
            "account,value\n"
            f"alpha,{sentinel}\n",
            encoding="utf-8",
        )
        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        return result, sentinel

    def test_builds_metadata_only_artifact_index(self):
        result, sentinel = self.build_job()
        index = read_json(result.artifact_index_path)
        manifest = read_json(result.artifact_index_manifest_path)

        self.assertIsInstance(result.artifact_index_path, Path)
        self.assertEqual(index["index_type"], "personal_ai_local_v1_artifact_index")
        self.assertEqual(index["authority"], "non_authority")
        self.assertIs(index["content_indexed"], False)
        self.assertIs(index["input_file_contents_copied"], False)
        self.assertIs(index["raw_cell_values_copied"], False)
        self.assertNotIn(sentinel, result.artifact_index_path.read_text(encoding="utf-8"))
        self.assertNotIn(
            sentinel,
            result.artifact_index_manifest_path.read_text(encoding="utf-8"),
        )

        relative_paths = {
            entry["relative_path"]
            for entry in index["entries"]
        }
        self.assertIn("final_job_manifest.json", relative_paths)
        self.assertIn("job_summary.json", relative_paths)
        self.assertNotIn("artifact_index.json", relative_paths)
        self.assertNotIn("artifact_index_manifest.json", relative_paths)
        self.assertNotIn("job_package_validation.json", relative_paths)
        self.assertEqual(manifest["artifact_index_sha256"], sha256_file(result.artifact_index_path))
        self.assertEqual(manifest["indexed_artifacts"], len(index["entries"]))

    def test_rebuild_is_deterministic_for_unchanged_package(self):
        result, _ = self.build_job()
        first_index = result.artifact_index_path.read_text(encoding="utf-8")
        first_manifest = result.artifact_index_manifest_path.read_text(
            encoding="utf-8",
        )

        rebuilt = build_artifact_index(
            result.job_dir,
            result.artifact_index_path,
            result.artifact_index_manifest_path,
        )

        self.assertIsInstance(rebuilt, ArtifactIndexResult)
        self.assertEqual(
            result.artifact_index_path.read_text(encoding="utf-8"),
            first_index,
        )
        self.assertEqual(
            result.artifact_index_manifest_path.read_text(encoding="utf-8"),
            first_manifest,
        )

    def test_rejects_missing_job_dir(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)

        with self.assertRaisesRegex(ValueError, "job_dir is missing"):
            build_artifact_index(root / "missing")
