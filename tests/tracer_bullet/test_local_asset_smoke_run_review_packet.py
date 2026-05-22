import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


APPROVAL_PHRASE = "I_APPROVE_LOCAL_ASSET_SMOKE_RUN"
REVIEW_OUTPUTS = (
    "local_asset_smoke_review_packet.json",
    "local_asset_smoke_review_packet_manifest.json",
    "local_asset_smoke_review_summary.md",
    "local_asset_smoke_human_decision_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
BOUNDARY_FIELDS = (
    "raw_candidate_content_read",
    "candidate_file_hashing_performed",
    "scan_performed",
    "readiness_run_performed",
    "input_mutation_performed",
    "smoke_output_mutation_performed",
    "file_move_performed",
    "file_rename_performed",
    "file_delete_performed",
    "duplicate_deletion_performed",
    "media_organizer_behavior_performed",
    "output_overwrite_performed",
    "network_access_performed",
    "model_api_called",
    "external_runtime_invoked",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalAssetSmokeRunReviewPacketTests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def make_candidate(
        self,
        root,
        *,
        duplicate=False,
        plate_bytes=b"plate",
        clip_bytes=b"clip",
        extra_file=False,
    ):
        candidate = Path(root) / "candidate"
        nested = candidate / "nested"
        nested.mkdir(parents=True)
        (candidate / "plate.png").write_bytes(plate_bytes)
        (nested / "clip.mov").write_bytes(clip_bytes)
        if duplicate:
            (candidate / "plate-copy.png").write_bytes(plate_bytes)
        if extra_file:
            (candidate / "extra.wav").write_bytes(b"extra")
        return candidate

    def run_readiness(
        self,
        candidate,
        output_dir,
        *,
        project_id="review-packet-test",
    ):
        return self.run_cli(
            [
                "launch-local-asset-smoke-readiness",
                "--candidate-input-dir",
                Path(candidate).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--recursive",
                "--project-id",
                project_id,
            ]
        )

    def run_human_smoke(
        self,
        candidate,
        output_dir,
        readiness_report,
        *,
        project_id="review-packet-test",
        max_smoke_files=4,
        previous_scan_output_dir=None,
    ):
        args = [
            "launch-local-asset-human-smoke-run",
            "--candidate-input-dir",
            Path(candidate).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--readiness-report",
            Path(readiness_report).as_posix(),
            "--human-approval-id",
            "review-packet-approval",
            "--human-approval-phrase",
            APPROVAL_PHRASE,
            "--recursive",
            "--project-id",
            project_id,
            "--max-smoke-files",
            str(max_smoke_files),
            "--max-smoke-bytes",
            "1000",
            "--max-smoke-depth",
            "3",
        ]
        if previous_scan_output_dir is not None:
            args.extend(
                [
                    "--previous-scan-output-dir",
                    Path(previous_scan_output_dir).as_posix(),
                ]
            )
        return self.run_cli(args)

    def run_review(self, smoke_output_dir, output_dir, *, project_id=None):
        args = [
            "launch-local-asset-smoke-review-packet",
            "--smoke-output-dir",
            Path(smoke_output_dir).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
        ]
        if project_id is not None:
            args.extend(["--project-id", project_id])
        return self.run_cli(args)

    def successful_smoke(
        self,
        root,
        *,
        duplicate=False,
        plate_bytes=b"plate",
        clip_bytes=b"clip",
        extra_file=False,
        previous_scan_output_dir=None,
    ):
        candidate = self.make_candidate(
            root,
            duplicate=duplicate,
            plate_bytes=plate_bytes,
            clip_bytes=clip_bytes,
            extra_file=extra_file,
        )
        readiness_output = Path(root) / "readiness"
        smoke_output = Path(root) / "human-smoke"
        readiness_output.mkdir()
        smoke_output.mkdir()
        readiness_code, readiness_payload = self.run_readiness(
            candidate,
            readiness_output,
        )
        self.assertEqual(readiness_code, 0)
        smoke_code, smoke_payload = self.run_human_smoke(
            candidate,
            smoke_output,
            readiness_payload["local_asset_smoke_readiness_report_path"],
            max_smoke_files=5,
            previous_scan_output_dir=previous_scan_output_dir,
        )
        self.assertEqual(smoke_code, 0)
        return candidate, smoke_output, smoke_payload

    def write_graph(self, graph_path, nodes, *, graph_id="review-packet-graph"):
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

    def review_packet_node(self, *, node_id, smoke_output_dir, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": "launch_local_asset_smoke_review_packet",
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "smoke_output_dir": Path(smoke_output_dir).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "project_id": "review-packet-test",
            },
        }

    def test_review_packet_writes_packet_manifest_summary_checklist_and_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _candidate, smoke_output, _smoke_payload = self.successful_smoke(root)
            review_output = root / "review"
            review_output.mkdir()

            exit_code, payload = self.run_review(smoke_output, review_output)
            packet = read_json(review_output / "local_asset_smoke_review_packet.json")
            artifact_index = read_json(review_output / "artifact_index.json")
            artifact_roles = {
                entry["artifact_role"] for entry in artifact_index["entries"]
            }

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in REVIEW_OUTPUTS:
                self.assertTrue((review_output / filename).exists(), filename)
            self.assertEqual(packet["packet_type"], "local_asset_smoke_review_packet_v1")
            for role in (
                "local_asset_smoke_review_packet",
                "local_asset_smoke_review_packet_manifest",
                "local_asset_smoke_review_summary",
                "local_asset_smoke_human_decision_checklist",
            ):
                self.assertIn(role, artifact_roles)

    def test_review_packet_summarizes_successful_smoke_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _candidate, smoke_output, _smoke_payload = self.successful_smoke(root)
            review_output = root / "review"
            review_output.mkdir()

            exit_code, _payload = self.run_review(smoke_output, review_output)
            packet = read_json(review_output / "local_asset_smoke_review_packet.json")

            self.assertEqual(exit_code, 0)
            self.assertTrue(packet["admission_summary"]["admitted"])
            self.assertTrue(packet["admission_summary"]["scan_launcher_invoked"])
            self.assertTrue(packet["admission_summary"]["scan_complete"])
            self.assertTrue(
                packet["admission_summary"]["bounded_smoke_run_performed"]
            )
            self.assertFalse(packet["admission_summary"]["production_scan_performed"])
            self.assertFalse(packet["input_mutation_performed"])
            self.assertEqual(
                packet["recommended_human_decision"],
                "approve_next_bounded_smoke_iteration",
            )

    def test_review_packet_summarizes_quarantine_and_duplicates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_secret = "SECRET_DO_NOT_COPY"
            _candidate, smoke_output, _smoke_payload = self.successful_smoke(
                root,
                duplicate=True,
            )
            quarantine_path = smoke_output / "scan" / "asset_runtime_quarantine_manifest.json"
            quarantine = read_json(quarantine_path)
            quarantine["items"].append(
                {
                    "relative_path": "api_key.txt",
                    "reason": "secret_looking_path",
                    "path_type": "file",
                    "detail": "secret-looking file contents were not read",
                }
            )
            quarantine["counts_by_reason"] = {"secret_looking_path": 1}
            quarantine["quarantined_path_count"] = 1
            write_json(quarantine_path, quarantine)
            review_output = root / "review"
            review_output.mkdir()

            exit_code, _payload = self.run_review(smoke_output, review_output)
            packet_path = review_output / "local_asset_smoke_review_packet.json"
            packet = read_json(packet_path)
            packet_text = packet_path.read_text(encoding="utf-8")

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                packet["recommended_human_decision"],
                "inspect_quarantine_before_next_run",
            )
            self.assertGreater(
                packet["duplicate_summary"]["duplicate_group_count"],
                0,
            )
            self.assertEqual(
                packet["quarantine_summary"]["quarantined_path_count"],
                1,
            )
            self.assertEqual(
                packet["quarantine_summary"]["secret_looking_path_count"],
                1,
            )
            self.assertFalse(packet["duplicate_summary"]["deletion_suggested"])
            self.assertFalse(packet["quarantine_summary"]["deletion_suggested"])
            self.assertNotIn(raw_secret, packet_text)

    def test_review_packet_summarizes_incremental_plan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first_root = Path(temp_dir) / "first"
            second_root = Path(temp_dir) / "second"
            first_root.mkdir()
            second_root.mkdir()
            _candidate_a, smoke_a, _payload_a = self.successful_smoke(
                first_root,
                plate_bytes=b"aaaa",
                clip_bytes=b"clip",
            )
            _candidate_b, smoke_b, _payload_b = self.successful_smoke(
                second_root,
                plate_bytes=b"bbbb",
                clip_bytes=b"clip",
                extra_file=True,
                previous_scan_output_dir=smoke_a / "scan",
            )
            review_output = Path(temp_dir) / "review"
            review_output.mkdir()

            exit_code, _payload = self.run_review(smoke_b, review_output)
            packet = read_json(review_output / "local_asset_smoke_review_packet.json")
            incremental = packet["incremental_summary"]

            self.assertEqual(exit_code, 0)
            self.assertEqual(incremental["plan_mode"], "compare_previous_scan")
            self.assertGreaterEqual(incremental["changed_asset_count"], 1)
            self.assertGreaterEqual(incremental["new_asset_count"], 1)
            self.assertGreaterEqual(incremental["suspicious_change_count"], 1)
            self.assertEqual(
                packet["recommended_human_decision"],
                "inspect_incremental_changes_before_next_run",
            )

    def test_review_packet_blocks_missing_required_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            smoke_output = root / "smoke"
            review_output = root / "review"
            smoke_output.mkdir()
            review_output.mkdir()
            (smoke_output / "local_asset_human_smoke_run_summary.md").write_text(
                "# incomplete\n",
                encoding="utf-8",
            )

            exit_code, payload = self.run_review(smoke_output, review_output)
            packet = read_json(review_output / "local_asset_smoke_review_packet.json")

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["complete"])
            self.assertEqual(
                packet["review_packet_status"],
                "review_blocked_missing_required_artifacts",
            )
            self.assertFalse(packet["scan_performed"])
            self.assertFalse(packet["smoke_output_mutation_performed"])

    def test_review_packet_fail_closed_on_existing_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _candidate, smoke_output, _smoke_payload = self.successful_smoke(root)
            for filename in REVIEW_OUTPUTS:
                with self.subTest(filename=filename):
                    review_output = root / ("review-" + filename.replace(".", "-"))
                    review_output.mkdir()
                    existing = review_output / filename
                    existing.write_text("do not overwrite\n", encoding="utf-8")

                    exit_code, _payload = self.run_review(smoke_output, review_output)

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        existing.read_text(encoding="utf-8"),
                        "do not overwrite\n",
                    )
                    for other_name in REVIEW_OUTPUTS:
                        if other_name != filename:
                            self.assertFalse((review_output / other_name).exists())

    def test_review_packet_output_dir_missing_returns_structured_failure_without_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _candidate, smoke_output, _smoke_payload = self.successful_smoke(root)
            missing_output = root / "missing-review"

            exit_code, payload = self.run_review(smoke_output, missing_output)

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["complete"])
            self.assertFalse(missing_output.exists())

    def test_review_packet_input_output_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate, smoke_output, _smoke_payload = self.successful_smoke(root)
            same_dir_payload_code, _same_dir_payload = self.run_review(
                smoke_output,
                smoke_output,
            )
            output_inside_smoke = smoke_output / "review-output"
            output_inside_smoke.mkdir()
            before_smoke_files = sorted(
                path.relative_to(smoke_output).as_posix()
                for path in smoke_output.rglob("*")
            )
            inside_code, _inside_payload = self.run_review(
                smoke_output,
                output_inside_smoke,
            )
            after_smoke_files = sorted(
                path.relative_to(smoke_output).as_posix()
                for path in smoke_output.rglob("*")
            )
            parent_output = root / "parent-review"
            nested_smoke = parent_output / "smoke"
            nested_smoke.mkdir(parents=True)
            parent_code, _parent_payload = self.run_review(nested_smoke, parent_output)
            candidate_review_output = candidate / "review-output"
            candidate_review_output.mkdir()
            candidate_code, _candidate_payload = self.run_review(
                smoke_output,
                candidate_review_output,
            )

            self.assertEqual(same_dir_payload_code, 1)
            self.assertEqual(inside_code, 1)
            self.assertEqual(before_smoke_files, after_smoke_files)
            self.assertEqual(parent_code, 1)
            self.assertEqual(candidate_code, 1)
            self.assertFalse(
                (candidate_review_output / "local_asset_smoke_review_packet.json").exists()
            )

    def test_task_graph_smoke_review_packet_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _candidate, smoke_output, _smoke_payload = self.successful_smoke(root)
            review_output = root / "review"
            graph_output = root / "graph-output"
            review_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.review_packet_node(
                        node_id="review_smoke",
                        smoke_output_dir=smoke_output,
                        output_dir=review_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            execution_manifest = read_json(result.execution_manifest_path)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            node = execution_manifest["nodes"][0]
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "review_smoke"
            }

            self.assertTrue(result.success)
            for role in (
                "local_asset_smoke_review_packet",
                "local_asset_smoke_review_packet_manifest",
                "local_asset_smoke_review_summary",
                "local_asset_smoke_human_decision_checklist",
            ):
                self.assertIn(role, roles)
            self.assertEqual(node["review_packet_status"], "review_ready")
            self.assertEqual(
                node["recommended_human_decision"],
                "approve_next_bounded_smoke_iteration",
            )
            self.assertFalse(node["scan_performed"])
            self.assertFalse(node["readiness_run_performed"])
            self.assertFalse(node["raw_candidate_content_read"])
            self.assertFalse(node["candidate_file_hashing_performed"])
            self.assertTrue(node["required_human_approval"])

    def test_review_packet_no_scope_expansion_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _candidate, smoke_output, _smoke_payload = self.successful_smoke(root)
            review_output = root / "review"
            graph_review_output = root / "graph-review"
            graph_output = root / "graph-output"
            review_output.mkdir()
            graph_review_output.mkdir()
            graph_output.mkdir()
            exit_code, payload = self.run_review(smoke_output, review_output)
            packet = read_json(review_output / "local_asset_smoke_review_packet.json")
            manifest = read_json(
                review_output / "local_asset_smoke_review_packet_manifest.json"
            )
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.review_packet_node(
                        node_id="review_smoke",
                        smoke_output_dir=smoke_output,
                        output_dir=graph_review_output,
                    )
                ],
                graph_id="review-boundary-graph",
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            node = read_json(graph_result.execution_manifest_path)["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, packet, manifest, node):
                for field in BOUNDARY_FIELDS:
                    self.assertFalse(payload_like[field], field)
                self.assertTrue(payload_like["required_human_approval"])

    def test_review_packet_deterministic_across_runs(self):
        with (
            tempfile.TemporaryDirectory() as first_dir,
            tempfile.TemporaryDirectory() as second_dir,
        ):
            first_root = Path(first_dir)
            second_root = Path(second_dir)
            _candidate_a, smoke_a, _payload_a = self.successful_smoke(first_root)
            _candidate_b, smoke_b, _payload_b = self.successful_smoke(second_root)
            review_a = first_root / "review"
            review_b = second_root / "review"
            review_a.mkdir()
            review_b.mkdir()
            code_a, _cli_a = self.run_review(smoke_a, review_a)
            code_b, _cli_b = self.run_review(smoke_b, review_b)
            packet_a = read_json(review_a / "local_asset_smoke_review_packet.json")
            packet_b = read_json(review_b / "local_asset_smoke_review_packet.json")

            self.assertEqual(code_a, 0)
            self.assertEqual(code_b, 0)
            for field in (
                "review_packet_status",
                "recommended_human_decision",
                "generated_artifacts_read_count",
                "generated_artifacts_missing_count",
            ):
                self.assertEqual(packet_a[field], packet_b[field], field)
            self.assertEqual(
                packet_a["scan_summary"]["files_scanned"],
                packet_b["scan_summary"]["files_scanned"],
            )
            self.assertEqual(
                packet_a["duplicate_summary"]["duplicate_group_count"],
                packet_b["duplicate_summary"]["duplicate_group_count"],
            )
            self.assertEqual(
                [
                    artifact["artifact_role"]
                    for artifact in packet_a["source_artifacts"]
                ],
                [
                    artifact["artifact_role"]
                    for artifact in packet_b["source_artifacts"]
                ],
            )
            self.assertEqual(
                [
                    artifact["artifact_role"]
                    for artifact in packet_a["missing_artifacts"]
                ],
                [
                    artifact["artifact_role"]
                    for artifact in packet_b["missing_artifacts"]
                ],
            )
            self.assertEqual(
                packet_a["decision_checklist"]["decision_options"],
                packet_b["decision_checklist"]["decision_options"],
            )


if __name__ == "__main__":
    unittest.main()
