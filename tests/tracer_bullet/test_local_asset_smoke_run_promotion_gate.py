import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


APPROVAL_PHRASE = "I_APPROVE_LOCAL_ASSET_SMOKE_RUN"
PROMOTION_OUTPUTS = (
    "local_asset_smoke_promotion_decision.json",
    "local_asset_smoke_promotion_gate_manifest.json",
    "local_asset_smoke_promotion_summary.md",
    "local_asset_smoke_promotion_human_signoff_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
PROMOTION_ROLES = (
    "local_asset_smoke_promotion_decision",
    "local_asset_smoke_promotion_gate_manifest",
    "local_asset_smoke_promotion_summary",
    "local_asset_smoke_promotion_human_signoff_checklist",
)
BOUNDARY_FIELDS = (
    "scan_performed",
    "readiness_run_performed",
    "human_smoke_run_performed",
    "review_packet_mutation_performed",
    "smoke_output_mutation_performed",
    "raw_candidate_content_read",
    "candidate_file_hashing_performed",
    "input_mutation_performed",
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


class LocalAssetSmokeRunPromotionGateTests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def make_candidate(
        self,
        root,
        *,
        plate_bytes=b"plate",
        clip_bytes=b"clip",
        extra_file=False,
    ):
        candidate = Path(root) / "candidate"
        nested = candidate / "nested"
        nested.mkdir(parents=True)
        (candidate / "plate.png").write_bytes(plate_bytes)
        (nested / "clip.mov").write_bytes(clip_bytes)
        if extra_file:
            (candidate / "extra.wav").write_bytes(b"extra")
        return candidate

    def run_readiness(self, candidate, output_dir, *, project_id="promotion-test"):
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
        project_id="promotion-test",
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
            "promotion-gate-approval",
            "--human-approval-phrase",
            APPROVAL_PHRASE,
            "--recursive",
            "--project-id",
            project_id,
            "--max-smoke-files",
            "5",
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

    def run_promotion(self, review_output_dir, output_dir, *, project_id=None):
        args = [
            "launch-local-asset-smoke-promotion-gate",
            "--review-output-dir",
            Path(review_output_dir).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
        ]
        if project_id is not None:
            args.extend(["--project-id", project_id])
        return self.run_cli(args)

    def successful_review(self, root, *, previous_scan_output_dir=None):
        candidate = self.make_candidate(root)
        readiness_output = Path(root) / "readiness"
        smoke_output = Path(root) / "human-smoke"
        review_output = Path(root) / "review"
        readiness_output.mkdir()
        smoke_output.mkdir()
        review_output.mkdir()
        readiness_code, readiness_payload = self.run_readiness(
            candidate,
            readiness_output,
        )
        self.assertEqual(readiness_code, 0)
        smoke_code, _smoke_payload = self.run_human_smoke(
            candidate,
            smoke_output,
            readiness_payload["local_asset_smoke_readiness_report_path"],
            previous_scan_output_dir=previous_scan_output_dir,
        )
        self.assertEqual(smoke_code, 0)
        review_code, _review_payload = self.run_review(smoke_output, review_output)
        self.assertEqual(review_code, 0)
        return candidate, smoke_output, review_output

    def base_review_packet(self, root):
        return {
            "packet_type": "local_asset_smoke_review_packet_v1",
            "authority": "non_authority",
            "execution_capability": "local_asset_smoke_review_packet_only",
            "smoke_output_dir": (Path(root) / "smoke").as_posix(),
            "output_dir": (Path(root) / "review").as_posix(),
            "project_id": "promotion-test",
            "review_packet_status": "review_ready",
            "recommended_human_decision": "approve_next_bounded_smoke_iteration",
            "smoke_run_summary": {
                "smoke_run_complete": True,
                "smoke_run_admitted": True,
                "scan_launcher_invoked": True,
                "scan_complete": True,
                "bounded_smoke_run_performed": True,
                "production_scan_performed": False,
                "failure_stage": None,
            },
            "approval_summary": {
                "approval_artifact_present": True,
                "human_approval_id_present": True,
                "approval_phrase_plaintext_persisted": False,
                "approval_phrase_stored": False,
            },
            "admission_summary": {
                "admitted": True,
                "scan_launcher_invoked": True,
                "scan_complete": True,
                "failure_stage": None,
                "bounded_smoke_run_performed": True,
                "production_scan_performed": False,
            },
            "readiness_summary": {
                "readiness_status": "ready",
                "readiness_decision": "allow_human_review_for_future_smoke",
                "candidate_input_dir": (Path(root) / "candidate").as_posix(),
                "recursive": True,
                "include_hidden": False,
            },
            "scan_summary": {
                "files_scanned": 2,
                "bytes_scanned": 9,
                "duplicate_group_count": 0,
                "quarantined_path_count": 0,
                "scan_complete": True,
                "scan_success_state": "complete",
                "scan_artifact_index_present": True,
            },
            "duplicate_summary": {
                "duplicate_group_count": 0,
                "duplicate_asset_count": 0,
                "deletion_suggested": False,
                "no_deletion_suggested": True,
                "recommended_action": "human_inspect_only",
                "automatic_dedupe_performed": False,
                "relative_paths_included": False,
            },
            "quarantine_summary": {
                "quarantined_path_count": 0,
                "top_reasons": [],
                "secret_looking_path_count": 0,
                "symlink_count": 0,
                "unsafe_path_count": 0,
                "deletion_suggested": False,
                "recommended_action": "human_inspect_only",
                "relative_paths_included": False,
            },
            "sqlite_summary": {
                "database_present": True,
                "manifest_present": True,
                "query_summary_present": True,
                "row_counts": {},
                "database_opened": False,
                "candidate_files_opened": False,
                "global_database_state_used": False,
            },
            "incremental_summary": {
                "plan_present": True,
                "plan_mode": "baseline_no_previous_scan",
                "unchanged_asset_count": 0,
                "changed_asset_count": 0,
                "new_asset_count": 0,
                "missing_asset_count": 0,
                "suspicious_change_count": 0,
                "automatic_skip_performed": False,
                "cache_execution_performed": False,
            },
            "failure_summary": {
                "failure_bundle_present": False,
                "failure_stage": None,
                "safe_to_retry": None,
                "safe_error_message": None,
                "raw_traceback_copied": False,
                "raw_exception_dump_copied": False,
                "secret_value_serialized": False,
            },
            "warning_summary": {
                "warning_count": 0,
                "warnings": [],
                "missing_optional_artifacts": [],
            },
            "source_artifacts": [],
            "missing_artifacts": [],
            "generated_artifacts_read_count": 0,
            "generated_artifacts_missing_count": 0,
            "deterministic_ordering": True,
            "raw_candidate_content_read": False,
            "candidate_file_hashing_performed": False,
            "scan_performed": False,
            "readiness_run_performed": False,
            "input_mutation_performed": False,
            "smoke_output_mutation_performed": False,
            "file_move_performed": False,
            "file_rename_performed": False,
            "file_delete_performed": False,
            "duplicate_deletion_performed": False,
            "media_organizer_behavior_performed": False,
            "output_overwrite_performed": False,
            "network_access_performed": False,
            "model_api_called": False,
            "external_runtime_invoked": False,
            "required_human_approval": True,
            "next_allowed_action": "human_review_smoke_review_packet",
        }

    def write_review_fixture(self, review_output, packet):
        review_path = Path(review_output)
        review_path.mkdir(parents=True, exist_ok=True)
        summary_path = review_path / "local_asset_smoke_review_summary.md"
        checklist_path = review_path / "local_asset_smoke_human_decision_checklist.md"
        packet_path = review_path / "local_asset_smoke_review_packet.json"
        manifest_path = review_path / "local_asset_smoke_review_packet_manifest.json"
        index_path = review_path / "artifact_index.json"
        index_manifest_path = review_path / "artifact_index_manifest.json"
        write_json(packet_path, packet)
        summary_path.write_text("# Review Summary\n", encoding="utf-8")
        checklist_path.write_text("# Review Checklist\n", encoding="utf-8")
        write_json(
            manifest_path,
            {
                "manifest_type": "local_asset_smoke_review_packet_manifest_v1",
                "authority": "non_authority",
                "packet_path": packet_path.as_posix(),
                "summary_path": summary_path.as_posix(),
                "decision_checklist_path": checklist_path.as_posix(),
                "packet_sha256": sha256_file(packet_path),
                "summary_sha256": sha256_file(summary_path),
                "decision_checklist_sha256": sha256_file(checklist_path),
                "source_artifacts": [],
                "review_packet_status": packet["review_packet_status"],
                "recommended_human_decision": packet["recommended_human_decision"],
                "deterministic_ordering": True,
                "raw_candidate_content_read": False,
                "candidate_file_hashing_performed": False,
                "scan_performed": False,
                "readiness_run_performed": False,
                "input_mutation_performed": False,
                "smoke_output_mutation_performed": False,
                "file_move_performed": False,
                "file_rename_performed": False,
                "file_delete_performed": False,
                "duplicate_deletion_performed": False,
                "media_organizer_behavior_performed": False,
                "output_overwrite_performed": False,
                "network_access_performed": False,
                "model_api_called": False,
                "external_runtime_invoked": False,
                "required_human_approval": True,
                "next_allowed_action": "human_review_smoke_review_packet",
            },
        )
        entries = []
        for role, path in (
            ("local_asset_smoke_review_packet", packet_path),
            ("local_asset_smoke_review_packet_manifest", manifest_path),
            ("local_asset_smoke_review_summary", summary_path),
            ("local_asset_smoke_human_decision_checklist", checklist_path),
        ):
            entries.append(
                {
                    "artifact_name": role,
                    "artifact_role": role,
                    "path": path.as_posix(),
                    "relative_path": path.name,
                    "extension": path.suffix,
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "content_indexed": False,
                    "raw_content_copied": False,
                    "required_human_approval": True,
                }
            )
        write_json(
            index_path,
            {
                "index_type": "local_asset_smoke_review_packet_artifact_index_v1",
                "authority": "non_authority",
                "execution_capability": "local_asset_smoke_review_packet_only",
                "job_dir": review_path.as_posix(),
                "artifact_index_strategy": "explicit_review_packet_artifacts_only",
                "indexed_artifacts": len(entries),
                "entries": entries,
                "content_indexed": False,
                "raw_content_copied": False,
                "required_human_approval": True,
                "next_allowed_action": "human_review_smoke_review_packet",
            },
        )
        write_json(
            index_manifest_path,
            {
                "manifest_type": "local_asset_smoke_review_packet_artifact_index_manifest_v1",
                "authority": "non_authority",
                "artifact_index_path": index_path.as_posix(),
                "artifact_index_sha256": sha256_file(index_path),
                "indexed_artifacts": len(entries),
                "artifact_roles": {
                    entry["artifact_role"]: entry["path"] for entry in entries
                },
                "indexed_relative_paths": [
                    entry["relative_path"] for entry in entries
                ],
                "job_dir": review_path.as_posix(),
                "deterministic_ordering": True,
                "content_indexed": False,
                "raw_content_copied": False,
                "required_human_approval": True,
                "next_allowed_action": "human_review_smoke_review_packet",
            },
        )

    def write_graph(self, graph_path, nodes, *, graph_id="promotion-gate-graph"):
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

    def promotion_gate_node(self, *, node_id, review_output_dir, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": "launch_local_asset_smoke_promotion_gate",
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "review_output_dir": Path(review_output_dir).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "project_id": "promotion-test",
            },
        }

    def test_promotion_gate_writes_decision_manifest_summary_checklist_and_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _candidate, _smoke_output, review_output = self.successful_review(root)
            promotion_output = root / "promotion"
            promotion_output.mkdir()

            exit_code, payload = self.run_promotion(review_output, promotion_output)
            decision = read_json(
                promotion_output / "local_asset_smoke_promotion_decision.json"
            )
            artifact_index = read_json(promotion_output / "artifact_index.json")
            artifact_roles = {
                entry["artifact_role"] for entry in artifact_index["entries"]
            }

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            self.assertEqual(
                decision["decision_type"],
                "local_asset_smoke_promotion_decision_v1",
            )
            for filename in PROMOTION_OUTPUTS:
                self.assertTrue((promotion_output / filename).exists(), filename)
            for role in PROMOTION_ROLES:
                self.assertIn(role, artifact_roles)

    def test_promotion_gate_allows_clean_review_ready_packet_only_for_next_bounded_smoke(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _candidate, _smoke_output, review_output = self.successful_review(root)
            promotion_output = root / "promotion"
            promotion_output.mkdir()

            exit_code, payload = self.run_promotion(review_output, promotion_output)
            decision = read_json(
                promotion_output / "local_asset_smoke_promotion_decision.json"
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(decision["promotion_gate_status"], "promotion_candidate")
            self.assertEqual(
                decision["promotion_decision"],
                "allow_next_bounded_smoke_iteration",
            )
            self.assertTrue(decision["next_bounded_smoke_iteration_allowed"])
            self.assertFalse(decision["production_promotion_granted"])
            self.assertFalse(decision["production_scan_approved"])
            self.assertEqual(payload["allowed_next_action"], "next_bounded_smoke_iteration")
            self.assertEqual(
                payload["next_allowed_action"],
                "human_review_smoke_promotion_gate",
            )

    def test_promotion_gate_blocks_quarantine(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self.base_review_packet(root)
            packet["recommended_human_decision"] = "inspect_quarantine_before_next_run"
            packet["quarantine_summary"]["quarantined_path_count"] = 1
            review_output = root / "review"
            promotion_output = root / "promotion"
            promotion_output.mkdir()
            self.write_review_fixture(review_output, packet)

            exit_code, _payload = self.run_promotion(review_output, promotion_output)
            decision = read_json(
                promotion_output / "local_asset_smoke_promotion_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(decision["promotion_gate_status"], "blocked_quarantine")
            self.assertEqual(
                decision["promotion_decision"],
                "block_until_human_inspects_quarantine",
            )
            self.assertFalse(decision["next_bounded_smoke_iteration_allowed"])

    def test_promotion_gate_blocks_duplicates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self.base_review_packet(root)
            packet["recommended_human_decision"] = "inspect_duplicates_before_next_run"
            packet["duplicate_summary"]["duplicate_group_count"] = 1
            review_output = root / "review"
            promotion_output = root / "promotion"
            promotion_output.mkdir()
            self.write_review_fixture(review_output, packet)

            exit_code, _payload = self.run_promotion(review_output, promotion_output)
            decision = read_json(
                promotion_output / "local_asset_smoke_promotion_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(decision["promotion_gate_status"], "blocked_duplicates")
            self.assertEqual(
                decision["promotion_decision"],
                "block_until_human_inspects_duplicates",
            )

    def test_promotion_gate_blocks_incremental_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self.base_review_packet(root)
            packet["recommended_human_decision"] = (
                "inspect_incremental_changes_before_next_run"
            )
            packet["incremental_summary"]["plan_mode"] = "compare_previous_scan"
            packet["incremental_summary"]["changed_asset_count"] = 1
            packet["incremental_summary"]["new_asset_count"] = 1
            packet["incremental_summary"]["suspicious_change_count"] = 1
            review_output = root / "review"
            promotion_output = root / "promotion"
            promotion_output.mkdir()
            self.write_review_fixture(review_output, packet)

            exit_code, _payload = self.run_promotion(review_output, promotion_output)
            decision = read_json(
                promotion_output / "local_asset_smoke_promotion_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                decision["promotion_gate_status"],
                "blocked_incremental_changes",
            )
            self.assertEqual(
                decision["promotion_decision"],
                "block_until_human_inspects_incremental_changes",
            )

    def test_promotion_gate_blocks_missing_required_review_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review_output = root / "review"
            promotion_output = root / "promotion"
            review_output.mkdir()
            promotion_output.mkdir()
            (review_output / "local_asset_smoke_review_summary.md").write_text(
                "# incomplete\n",
                encoding="utf-8",
            )

            exit_code, payload = self.run_promotion(review_output, promotion_output)
            decision = read_json(
                promotion_output / "local_asset_smoke_promotion_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["complete"])
            self.assertEqual(
                decision["promotion_gate_status"],
                "blocked_missing_review_artifacts",
            )
            self.assertFalse(decision["next_bounded_smoke_iteration_allowed"])

    def test_promotion_gate_fail_closed_on_existing_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self.base_review_packet(root)
            review_output = root / "review"
            self.write_review_fixture(review_output, packet)
            for filename in PROMOTION_OUTPUTS:
                with self.subTest(filename=filename):
                    promotion_output = root / ("promotion-" + filename.replace(".", "-"))
                    promotion_output.mkdir()
                    existing = promotion_output / filename
                    existing.write_text("do not overwrite\n", encoding="utf-8")

                    exit_code, _payload = self.run_promotion(
                        review_output,
                        promotion_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        existing.read_text(encoding="utf-8"),
                        "do not overwrite\n",
                    )
                    for other_name in PROMOTION_OUTPUTS:
                        if other_name != filename:
                            self.assertFalse((promotion_output / other_name).exists())

    def test_promotion_gate_output_dir_missing_returns_structured_failure_without_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self.base_review_packet(root)
            review_output = root / "review"
            missing_output = root / "missing-promotion"
            self.write_review_fixture(review_output, packet)

            exit_code, payload = self.run_promotion(review_output, missing_output)

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["complete"])
            self.assertFalse(missing_output.exists())
            self.assertIsNone(payload["local_asset_smoke_promotion_decision_path"])

    def test_promotion_gate_input_output_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self.base_review_packet(root)
            review_output = root / "review"
            self.write_review_fixture(review_output, packet)
            same_code, _same_payload = self.run_promotion(review_output, review_output)
            output_inside_review = review_output / "promotion-output"
            output_inside_review.mkdir()
            before_review_files = sorted(
                path.relative_to(review_output).as_posix()
                for path in review_output.rglob("*")
            )
            inside_code, _inside_payload = self.run_promotion(
                review_output,
                output_inside_review,
            )
            after_review_files = sorted(
                path.relative_to(review_output).as_posix()
                for path in review_output.rglob("*")
            )
            parent_output = root / "parent-promotion"
            nested_review = parent_output / "review"
            nested_review.mkdir(parents=True)
            parent_code, _parent_payload = self.run_promotion(
                nested_review,
                parent_output,
            )
            smoke_output = Path(packet["smoke_output_dir"])
            smoke_output.mkdir()
            output_inside_smoke = smoke_output / "promotion-output"
            output_inside_smoke.mkdir()
            smoke_code, _smoke_payload = self.run_promotion(
                review_output,
                output_inside_smoke,
            )
            candidate_input = Path(packet["readiness_summary"]["candidate_input_dir"])
            candidate_input.mkdir()
            output_inside_candidate = candidate_input / "promotion-output"
            output_inside_candidate.mkdir()
            candidate_code, _candidate_payload = self.run_promotion(
                review_output,
                output_inside_candidate,
            )

            self.assertEqual(same_code, 1)
            self.assertEqual(inside_code, 1)
            self.assertEqual(before_review_files, after_review_files)
            self.assertEqual(parent_code, 1)
            self.assertEqual(smoke_code, 1)
            self.assertEqual(candidate_code, 1)
            self.assertFalse(
                (
                    output_inside_candidate
                    / "local_asset_smoke_promotion_decision.json"
                ).exists()
            )

    def test_task_graph_promotion_gate_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _candidate, _smoke_output, review_output = self.successful_review(root)
            promotion_output = root / "promotion"
            graph_output = root / "graph-output"
            promotion_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.promotion_gate_node(
                        node_id="promote_smoke",
                        review_output_dir=review_output,
                        output_dir=promotion_output,
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
                if artifact["node_id"] == "promote_smoke"
            }

            self.assertTrue(result.success)
            for role in PROMOTION_ROLES:
                self.assertIn(role, roles)
            self.assertEqual(node["promotion_gate_status"], "promotion_candidate")
            self.assertEqual(
                node["promotion_decision"],
                "allow_next_bounded_smoke_iteration",
            )
            self.assertTrue(node["next_bounded_smoke_iteration_allowed"])
            self.assertFalse(node["production_promotion_granted"])
            self.assertFalse(node["production_scan_approved"])
            self.assertFalse(node["scan_performed"])
            self.assertFalse(node["readiness_run_performed"])
            self.assertFalse(node["human_smoke_run_performed"])
            self.assertFalse(node["review_packet_mutation_performed"])
            self.assertFalse(node["raw_candidate_content_read"])
            self.assertFalse(node["candidate_file_hashing_performed"])
            self.assertTrue(node["required_human_approval"])

    def test_promotion_gate_no_scope_expansion_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _candidate, _smoke_output, review_output = self.successful_review(root)
            promotion_output = root / "promotion"
            graph_promotion_output = root / "graph-promotion"
            graph_output = root / "graph-output"
            promotion_output.mkdir()
            graph_promotion_output.mkdir()
            graph_output.mkdir()
            exit_code, payload = self.run_promotion(review_output, promotion_output)
            decision = read_json(
                promotion_output / "local_asset_smoke_promotion_decision.json"
            )
            manifest = read_json(
                promotion_output / "local_asset_smoke_promotion_gate_manifest.json"
            )
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.promotion_gate_node(
                        node_id="promote_smoke",
                        review_output_dir=review_output,
                        output_dir=graph_promotion_output,
                    )
                ],
                graph_id="promotion-boundary-graph",
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            node = read_json(graph_result.execution_manifest_path)["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, decision, manifest, node):
                for field in BOUNDARY_FIELDS:
                    self.assertFalse(payload_like[field], field)
                self.assertFalse(payload_like["production_promotion_granted"])
                self.assertFalse(payload_like["production_scan_approved"])
                self.assertTrue(payload_like["required_human_approval"])

    def test_promotion_gate_deterministic_across_runs(self):
        with (
            tempfile.TemporaryDirectory() as first_dir,
            tempfile.TemporaryDirectory() as second_dir,
        ):
            first_root = Path(first_dir)
            second_root = Path(second_dir)
            packet_a = self.base_review_packet(first_root)
            packet_b = self.base_review_packet(second_root)
            review_a = first_root / "review"
            review_b = second_root / "review"
            promotion_a = first_root / "promotion"
            promotion_b = second_root / "promotion"
            promotion_a.mkdir()
            promotion_b.mkdir()
            self.write_review_fixture(review_a, packet_a)
            self.write_review_fixture(review_b, packet_b)

            code_a, _payload_a = self.run_promotion(review_a, promotion_a)
            code_b, _payload_b = self.run_promotion(review_b, promotion_b)
            decision_a = read_json(
                promotion_a / "local_asset_smoke_promotion_decision.json"
            )
            decision_b = read_json(
                promotion_b / "local_asset_smoke_promotion_decision.json"
            )

            self.assertEqual(code_a, 0)
            self.assertEqual(code_b, 0)
            for field in (
                "promotion_gate_status",
                "promotion_decision",
                "next_bounded_smoke_iteration_allowed",
            ):
                self.assertEqual(decision_a[field], decision_b[field], field)
            self.assertEqual(
                [
                    blocker["blocker_role"]
                    for blocker in decision_a["promotion_blockers"]
                ],
                [
                    blocker["blocker_role"]
                    for blocker in decision_b["promotion_blockers"]
                ],
            )
            self.assertEqual(
                [
                    artifact["artifact_role"]
                    for artifact in decision_a["source_artifacts"]
                ],
                [
                    artifact["artifact_role"]
                    for artifact in decision_b["source_artifacts"]
                ],
            )
            self.assertEqual(
                decision_a["human_signoff_checklist"]["decision_options"],
                decision_b["human_signoff_checklist"]["decision_options"],
            )


if __name__ == "__main__":
    unittest.main()
