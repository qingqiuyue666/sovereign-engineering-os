import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


READINESS_OUTPUTS = (
    "local_asset_smoke_readiness_report.json",
    "local_asset_smoke_readiness_manifest.json",
    "local_asset_smoke_readiness_summary.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LocalAssetRealFolderSmokeReadinessTests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def run_readiness(
        self,
        candidate_input_dir,
        output_dir,
        *,
        recursive=True,
        include_hidden=False,
        project_id="readiness-test",
        max_entries=None,
        max_depth=None,
        max_total_bytes=None,
    ):
        args = [
            "launch-local-asset-smoke-readiness",
            "--candidate-input-dir",
            Path(candidate_input_dir).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--project-id",
            project_id,
        ]
        if recursive:
            args.append("--recursive")
        if include_hidden:
            args.append("--include-hidden")
        if max_entries is not None:
            args.extend(["--max-entries", str(max_entries)])
        if max_depth is not None:
            args.extend(["--max-depth", str(max_depth)])
        if max_total_bytes is not None:
            args.extend(["--max-total-bytes", str(max_total_bytes)])
        return self.run_cli(args)

    def make_candidate(self, root):
        candidate = root / "candidate"
        nested = candidate / "nested"
        nested.mkdir(parents=True)
        (candidate / "plate.png").write_bytes(b"plate")
        (nested / "clip.mov").write_bytes(b"clip")
        return candidate

    def write_graph(self, graph_path, nodes, *, graph_id="smoke-readiness-graph"):
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": graph_id,
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": nodes,
            },
        )

    def smoke_readiness_node(
        self,
        *,
        node_id,
        candidate_input_dir,
        output_dir,
        recursive=True,
        include_hidden=False,
        project_id="graph-readiness-test",
    ):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": "launch_local_asset_smoke_readiness",
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "candidate_input_dir": Path(candidate_input_dir).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "recursive": recursive,
                "include_hidden": include_hidden,
                "project_id": project_id,
                "max_entries": 50000,
                "max_depth": 20,
                "max_total_bytes": 500000000000,
            },
        }

    def test_smoke_readiness_writes_report_manifest_summary_and_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self.make_candidate(root)
            output_dir = root / "output"
            output_dir.mkdir()

            exit_code, payload = self.run_readiness(candidate, output_dir)

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in READINESS_OUTPUTS:
                self.assertTrue((output_dir / filename).exists(), filename)

            report = read_json(output_dir / "local_asset_smoke_readiness_report.json")
            artifact_index = read_json(output_dir / "artifact_index.json")
            artifact_names = {
                entry["artifact_name"] for entry in artifact_index["entries"]
            }
            self.assertIn("local_asset_smoke_readiness_report", artifact_names)
            self.assertIn("local_asset_smoke_readiness_manifest", artifact_names)
            self.assertIn("local_asset_smoke_readiness_summary", artifact_names)
            self.assertFalse(report["real_scan_performed"])
            self.assertFalse(report["file_hashing_performed"])
            self.assertFalse(report["raw_content_read"])
            self.assertFalse(payload["real_scan_performed"])
            self.assertFalse(payload["file_hashing_performed"])
            self.assertFalse(payload["raw_content_read"])

    def test_smoke_readiness_metadata_counts_and_cost_band(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate"
            nested = candidate / "nested"
            nested.mkdir(parents=True)
            (candidate / "plate.png").write_bytes(b"a" * 3)
            (candidate / "clip.mov").write_bytes(b"b" * (1024 * 1024 + 1))
            (nested / "README").write_bytes(b"c" * 4)
            output_dir = root / "output"
            output_dir.mkdir()

            exit_code, payload = self.run_readiness(candidate, output_dir)
            report = read_json(payload["local_asset_smoke_readiness_report_path"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(report["inspected_entry_count"], 4)
            self.assertEqual(report["inspected_file_count"], 3)
            self.assertEqual(report["inspected_directory_count"], 1)
            self.assertEqual(
                report["extension_counts"],
                {".mov": 1, ".png": 1, "[none]": 1},
            )
            self.assertEqual(
                report["media_class_counts"],
                {"image": 1, "unknown": 1, "video": 1},
            )
            self.assertEqual(report["estimated_total_size_bytes"], 1024 * 1024 + 8)
            self.assertEqual(report["estimated_hash_chunks_1mb"], 2)
            self.assertEqual(report["estimated_hash_cost_band"], "tiny")

    def test_smoke_readiness_detects_risks_without_reading_raw_content(self):
        secret_content = "SUPER_SECRET_VALUE_DO_NOT_COPY"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "api_key.txt").write_text(secret_content, encoding="utf-8")
            (candidate / ".hidden.png").write_bytes(b"hidden")
            (candidate / "node_modules").mkdir()
            (candidate / "node_modules" / "dep.js").write_text(
                "ignored\n",
                encoding="utf-8",
            )
            symlink_created = False
            try:
                os.symlink(candidate / "api_key.txt", candidate / "asset-link")
                symlink_created = True
            except (OSError, NotImplementedError):
                symlink_created = False
            output_dir = root / "output"
            output_dir.mkdir()

            exit_code, payload = self.run_readiness(candidate, output_dir)
            report_path = Path(payload["local_asset_smoke_readiness_report_path"])
            report = read_json(report_path)
            combined_artifacts = (
                report_path.read_text(encoding="utf-8")
                + Path(
                    payload["local_asset_smoke_readiness_summary_path"]
                ).read_text(encoding="utf-8")
                + Path(
                    payload["local_asset_smoke_readiness_manifest_path"]
                ).read_text(encoding="utf-8")
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(report["readiness_status"], "blocked_safety_risk")
            self.assertGreaterEqual(report["risk_counts"]["secret_looking_path"], 1)
            self.assertEqual(report["risk_counts"]["unsafe_directory"], 1)
            self.assertGreaterEqual(report["risk_counts"]["hidden_path"], 1)
            if symlink_created:
                self.assertEqual(report["risk_counts"]["symlink"], 1)
            risk_types = {item["risk_type"] for item in report["risk_items"]}
            self.assertIn("secret_looking_path", risk_types)
            self.assertIn("unsafe_directory", risk_types)
            self.assertIn("hidden_path", risk_types)
            self.assertNotIn(secret_content, combined_artifacts)

    def test_smoke_readiness_limit_exceeded_blocks_future_smoke_without_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "a.png").write_bytes(b"a")
            (candidate / "b.png").write_bytes(b"b")
            output_dir = root / "output"
            output_dir.mkdir()

            exit_code, payload = self.run_readiness(
                candidate,
                output_dir,
                max_entries=1,
            )
            report = read_json(payload["local_asset_smoke_readiness_report_path"])

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            self.assertEqual(report["readiness_status"], "blocked_limit_exceeded")
            self.assertEqual(
                report["readiness_decision"],
                "block_future_smoke_until_review",
            )
            self.assertFalse(report["traversal_complete"])
            self.assertFalse(report["real_scan_performed"])

    def test_smoke_readiness_fail_closed_on_existing_outputs(self):
        for filename in READINESS_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    candidate = self.make_candidate(root)
                    source = candidate / "plate.png"
                    before = source.read_bytes()
                    output_dir = root / "output"
                    output_dir.mkdir()
                    existing = output_dir / filename
                    existing.write_text("do not overwrite\n", encoding="utf-8")

                    exit_code, payload = self.run_readiness(candidate, output_dir)

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["complete"])
                    self.assertEqual(
                        existing.read_text(encoding="utf-8"),
                        "do not overwrite\n",
                    )
                    self.assertEqual(source.read_bytes(), before)

    def test_smoke_readiness_output_dir_missing_returns_structured_failure_without_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self.make_candidate(root)
            output_dir = root / "missing-output"

            exit_code, payload = self.run_readiness(candidate, output_dir)

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["complete"])
            self.assertFalse(output_dir.exists())
            self.assertTrue(payload["no_artifacts_written"])
            self.assertIsNone(payload["local_asset_smoke_readiness_report_path"])
            self.assertIn("output_dir is missing", payload["error_message"])

    def test_smoke_readiness_input_output_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cases = []
            candidate = self.make_candidate(root / "case-a")
            output_inside = candidate / "output"
            output_inside.mkdir()
            cases.append((candidate, output_inside))

            output_parent = root / "case-b" / "output"
            candidate_inside = output_parent / "candidate"
            candidate_inside.mkdir(parents=True)
            (candidate_inside / "asset.png").write_bytes(b"asset")
            cases.append((candidate_inside, output_parent))

            same_dir = root / "case-c" / "same"
            same_dir.mkdir(parents=True)
            (same_dir / "asset.png").write_bytes(b"asset")
            cases.append((same_dir, same_dir))

            for candidate_dir, output_dir in cases:
                with self.subTest(candidate=candidate_dir, output=output_dir):
                    before_files = sorted(
                        path.relative_to(candidate_dir).as_posix()
                        for path in candidate_dir.rglob("*")
                    )
                    exit_code, payload = self.run_readiness(candidate_dir, output_dir)
                    after_files = sorted(
                        path.relative_to(candidate_dir).as_posix()
                        for path in candidate_dir.rglob("*")
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["complete"])
                    self.assertEqual(
                        payload["readiness_decision"],
                        "block_future_smoke_until_review",
                    )
                    self.assertFalse(payload["raw_content_read"])
                    self.assertFalse(payload["input_mutation_performed"])
                    self.assertEqual(after_files, before_files)

    def test_task_graph_smoke_readiness_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self.make_candidate(root)
            node_output = root / "node-output"
            graph_output = root / "graph-output"
            node_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.smoke_readiness_node(
                        node_id="preflight_assets",
                        candidate_input_dir=candidate,
                        output_dir=node_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            execution_manifest = read_json(result.execution_manifest_path)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "preflight_assets"
            }
            node = execution_manifest["nodes"][0]

            self.assertTrue(result.success)
            self.assertIn("local_asset_smoke_readiness_report", roles)
            self.assertIn("local_asset_smoke_readiness_manifest", roles)
            self.assertIn("local_asset_smoke_readiness_summary", roles)
            self.assertEqual(node["readiness_status"], "ready")
            self.assertFalse(node["real_scan_performed"])
            self.assertFalse(node["file_hashing_performed"])
            self.assertFalse(node["raw_content_read"])
            self.assertTrue(node["required_human_approval"])

    def test_smoke_readiness_no_scope_expansion_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self.make_candidate(root)
            output_dir = root / "output"
            output_dir.mkdir()

            exit_code, payload = self.run_readiness(candidate, output_dir)
            report = read_json(payload["local_asset_smoke_readiness_report_path"])
            manifest = read_json(payload["local_asset_smoke_readiness_manifest_path"])

            self.assertEqual(exit_code, 0)
            for field in (
                "real_scan_performed",
                "file_hashing_performed",
                "raw_content_read",
                "raw_content_copied",
                "input_mutation_performed",
                "file_move_performed",
                "file_rename_performed",
                "file_delete_performed",
                "media_organizer_behavior_performed",
                "network_access_performed",
                "model_api_called",
                "external_runtime_invoked",
            ):
                self.assertFalse(payload[field], field)
                self.assertFalse(report[field], field)
                self.assertFalse(manifest[field], field)

    def test_smoke_readiness_deterministic_across_runs(self):
        with (
            tempfile.TemporaryDirectory() as first_dir,
            tempfile.TemporaryDirectory() as second_dir,
        ):
            first_root = Path(first_dir)
            second_root = Path(second_dir)
            first_candidate = self.make_candidate(first_root)
            second_candidate = self.make_candidate(second_root)
            (first_candidate / "api_key.txt").write_text("TOKEN1\n", encoding="utf-8")
            (second_candidate / "api_key.txt").write_text("TOKEN2\n", encoding="utf-8")
            first_output = first_root / "output"
            second_output = second_root / "output"
            first_output.mkdir()
            second_output.mkdir()

            first_code, first_payload = self.run_readiness(
                first_candidate,
                first_output,
                project_id="deterministic",
            )
            second_code, second_payload = self.run_readiness(
                second_candidate,
                second_output,
                project_id="deterministic",
            )
            first_report = read_json(
                first_payload["local_asset_smoke_readiness_report_path"]
            )
            second_report = read_json(
                second_payload["local_asset_smoke_readiness_report_path"]
            )

            self.assertEqual(first_code, 0)
            self.assertEqual(second_code, 0)
            for field in (
                "readiness_status",
                "readiness_decision",
                "inspected_entry_count",
                "inspected_file_count",
                "inspected_directory_count",
                "estimated_total_size_bytes",
                "estimated_hash_chunks_1mb",
                "estimated_hash_cost_band",
                "risk_counts",
                "extension_counts",
                "media_class_counts",
                "top_largest_files_by_metadata",
            ):
                self.assertEqual(first_report[field], second_report[field], field)
            first_risks = [
                (
                    item["relative_path"],
                    item["path_type"],
                    item["risk_type"],
                    item["severity"],
                    item["detail"],
                )
                for item in first_report["risk_items"]
            ]
            second_risks = [
                (
                    item["relative_path"],
                    item["path_type"],
                    item["risk_type"],
                    item["severity"],
                    item["detail"],
                )
                for item in second_report["risk_items"]
            ]
            self.assertEqual(first_risks, second_risks)


if __name__ == "__main__":
    unittest.main()
