import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.assets.local_asset_bounded_smoke_iteration import (
    BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


SMOKE_APPROVAL_PHRASE = "I_APPROVE_LOCAL_ASSET_SMOKE_RUN"
ITERATION_SIGNOFF_PHRASE = "I_APPROVE_NEXT_BOUNDED_SMOKE_ITERATION"
ITERATION_REVIEW_OUTPUTS = (
    "local_asset_smoke_iteration_review_packet.json",
    "local_asset_smoke_iteration_review_packet_manifest.json",
    "local_asset_smoke_iteration_review_summary.md",
    "local_asset_smoke_iteration_human_decision_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
ITERATION_REVIEW_ROLES = (
    "local_asset_smoke_iteration_review_packet",
    "local_asset_smoke_iteration_review_packet_manifest",
    "local_asset_smoke_iteration_review_summary",
    "local_asset_smoke_iteration_human_decision_checklist",
)
BOUNDARY_FIELDS = (
    "production_promotion_granted",
    "production_scan_approved",
    "production_scan_performed",
    "raw_candidate_content_read",
    "candidate_file_hashing_performed",
    "scan_performed",
    "readiness_run_performed",
    "human_smoke_run_performed",
    "bounded_smoke_iteration_performed_by_review_packet",
    "promotion_gate_run_performed",
    "input_mutation_performed",
    "iteration_output_mutation_performed",
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


class LocalAssetSmokeIterationReviewPacketTests(unittest.TestCase):
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

    def snapshot_tree(self, root):
        return sorted(path.relative_to(root).as_posix() for path in Path(root).rglob("*"))

    def run_readiness(self, candidate, output_dir, *, project_id="iteration-review-test"):
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
        project_id="iteration-review-test",
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
            "iteration-review-smoke-approval",
            "--human-approval-phrase",
            SMOKE_APPROVAL_PHRASE,
            "--recursive",
            "--project-id",
            project_id,
            "--max-smoke-files",
            "10",
            "--max-smoke-bytes",
            "2000",
            "--max-smoke-depth",
            "4",
        ]
        if previous_scan_output_dir is not None:
            args.extend(
                [
                    "--previous-scan-output-dir",
                    Path(previous_scan_output_dir).as_posix(),
                ]
            )
        return self.run_cli(args)

    def run_smoke_review(
        self,
        smoke_output_dir,
        output_dir,
        *,
        project_id="iteration-review-test",
    ):
        return self.run_cli(
            [
                "launch-local-asset-smoke-review-packet",
                "--smoke-output-dir",
                Path(smoke_output_dir).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--project-id",
                project_id,
            ]
        )

    def run_promotion(
        self,
        review_output_dir,
        output_dir,
        *,
        project_id="iteration-review-test",
    ):
        return self.run_cli(
            [
                "launch-local-asset-smoke-promotion-gate",
                "--review-output-dir",
                Path(review_output_dir).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--project-id",
                project_id,
            ]
        )

    def run_iteration(
        self,
        promotion_output_dir,
        candidate,
        readiness_report,
        output_dir,
        *,
        project_id="iteration-review-test",
        previous_scan_output_dir=None,
    ):
        args = [
            "launch-local-asset-bounded-smoke-iteration",
            "--promotion-output-dir",
            Path(promotion_output_dir).as_posix(),
            "--candidate-input-dir",
            Path(candidate).as_posix(),
            "--readiness-report",
            Path(readiness_report).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--human-signoff-id",
            "iteration-review-signoff",
            "--human-signoff-phrase",
            BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE,
            "--recursive",
            "--project-id",
            project_id,
            "--max-smoke-files",
            "10",
            "--max-smoke-bytes",
            "2000",
            "--max-smoke-depth",
            "4",
        ]
        if previous_scan_output_dir is not None:
            args.extend(
                [
                    "--previous-scan-output-dir",
                    Path(previous_scan_output_dir).as_posix(),
                ]
            )
        return self.run_cli(args)

    def run_iteration_review(
        self,
        iteration_output_dir,
        output_dir,
        *,
        project_id="iteration-review-test",
    ):
        return self.run_cli(
            [
                "launch-local-asset-smoke-iteration-review-packet",
                "--iteration-output-dir",
                Path(iteration_output_dir).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--project-id",
                project_id,
            ]
        )

    def build_iteration_chain(self, root, *, previous_scan_output_dir=None):
        candidate = self.make_candidate(root)
        readiness_output = Path(root) / "readiness"
        smoke_output = Path(root) / "smoke-0"
        review_output = Path(root) / "review"
        promotion_output = Path(root) / "promotion"
        iteration_output = Path(root) / "iteration"
        for path in (
            readiness_output,
            smoke_output,
            review_output,
            promotion_output,
            iteration_output,
        ):
            path.mkdir()
        readiness_code, readiness_payload = self.run_readiness(
            candidate,
            readiness_output,
        )
        self.assertEqual(readiness_code, 0)
        smoke_code, _smoke_payload = self.run_human_smoke(
            candidate,
            smoke_output,
            readiness_payload["local_asset_smoke_readiness_report_path"],
        )
        self.assertEqual(smoke_code, 0)
        review_code, _review_payload = self.run_smoke_review(
            smoke_output,
            review_output,
        )
        self.assertEqual(review_code, 0)
        promotion_code, _promotion_payload = self.run_promotion(
            review_output,
            promotion_output,
        )
        self.assertEqual(promotion_code, 0)
        iteration_code, iteration_payload = self.run_iteration(
            promotion_output,
            candidate,
            readiness_payload["local_asset_smoke_readiness_report_path"],
            iteration_output,
            previous_scan_output_dir=previous_scan_output_dir,
        )
        self.assertEqual(iteration_code, 0)
        return {
            "candidate": candidate,
            "readiness_output": readiness_output,
            "readiness_report": Path(
                readiness_payload["local_asset_smoke_readiness_report_path"]
            ),
            "smoke_output": smoke_output,
            "review_output": review_output,
            "promotion_output": promotion_output,
            "iteration_output": iteration_output,
            "iteration_payload": iteration_payload,
        }

    def write_graph(self, graph_path, nodes, *, graph_id="iteration-review-graph"):
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

    def iteration_review_node(self, *, node_id, iteration_output_dir, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": "launch_local_asset_smoke_iteration_review_packet",
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "iteration_output_dir": Path(iteration_output_dir).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "project_id": "iteration-review-test",
            },
        }

    def test_iteration_review_packet_writes_packet_manifest_summary_checklist_and_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_iteration_chain(root)
            review_output = root / "iteration-review"
            review_output.mkdir()

            exit_code, payload = self.run_iteration_review(
                chain["iteration_output"],
                review_output,
            )
            artifact_index = read_json(review_output / "artifact_index.json")
            artifact_roles = {
                entry["artifact_role"] for entry in artifact_index["entries"]
            }

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in ITERATION_REVIEW_OUTPUTS:
                self.assertTrue((review_output / filename).exists(), filename)
            for role in ITERATION_REVIEW_ROLES:
                self.assertIn(role, artifact_roles)

    def test_iteration_review_packet_summarizes_successful_iteration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_iteration_chain(root)
            review_output = root / "iteration-review"
            review_output.mkdir()

            exit_code, payload = self.run_iteration_review(
                chain["iteration_output"],
                review_output,
            )
            packet = read_json(
                review_output / "local_asset_smoke_iteration_review_packet.json"
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(packet["iteration_status"], "iteration_completed")
            self.assertTrue(packet["bounded_smoke_iteration_performed"])
            self.assertTrue(packet["smoke_launcher_invoked"])
            self.assertTrue(packet["smoke_run_complete"])
            self.assertTrue(packet["scan_complete"])
            self.assertFalse(packet["production_promotion_granted"])
            self.assertFalse(packet["production_scan_approved"])
            self.assertFalse(packet["production_scan_performed"])
            self.assertEqual(
                packet["recommended_human_decision"],
                "generate_promotion_gate_for_iteration",
            )
            self.assertEqual(
                payload["recommended_human_decision"],
                "generate_promotion_gate_for_iteration",
            )

    def test_iteration_review_packet_does_not_persist_signoff_or_approval_plaintext(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_iteration_chain(root)
            review_output = root / "iteration-review"
            review_output.mkdir()

            exit_code, _payload = self.run_iteration_review(
                chain["iteration_output"],
                review_output,
            )
            packet = read_json(
                review_output / "local_asset_smoke_iteration_review_packet.json"
            )

            self.assertEqual(exit_code, 0)
            self.assertFalse(
                packet["signoff_summary"][
                    "human_signoff_phrase_plaintext_persisted"
                ]
            )
            self.assertFalse(
                packet["delegated_smoke_summary"][
                    "delegated_human_approval_phrase_plaintext_persisted"
                ]
            )
            for filename in (
                "local_asset_smoke_iteration_review_packet.json",
                "local_asset_smoke_iteration_review_packet_manifest.json",
                "local_asset_smoke_iteration_review_summary.md",
                "local_asset_smoke_iteration_human_decision_checklist.md",
            ):
                text = (review_output / filename).read_text(encoding="utf-8")
                self.assertNotIn(ITERATION_SIGNOFF_PHRASE, text, filename)
                self.assertNotIn(SMOKE_APPROVAL_PHRASE, text, filename)

    def test_iteration_review_packet_summarizes_quarantine_and_duplicates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_iteration_chain(root)
            scan_output = chain["iteration_output"] / "smoke" / "scan"
            raw_secret = "SECRET_DO_NOT_COPY"
            quarantine_path = scan_output / "asset_runtime_quarantine_manifest.json"
            quarantine = read_json(quarantine_path)
            quarantine["items"] = [
                {
                    "relative_path": "api_key.txt",
                    "reason": "secret_looking_path",
                    "path_type": "file",
                    "detail": "secret-looking file contents were not read",
                }
            ]
            quarantine["counts_by_reason"] = {"secret_looking_path": 1}
            quarantine["quarantined_path_count"] = 1
            write_json(quarantine_path, quarantine)
            duplicates_path = scan_output / "duplicates_report.json"
            duplicates = read_json(duplicates_path)
            duplicates["duplicate_sha256_group_count"] = 1
            duplicates["duplicate_file_count"] = 2
            duplicates["duplicate_groups"] = [{"count": 2}]
            write_json(duplicates_path, duplicates)
            receipt_path = scan_output / "asset_scan_run_receipt.json"
            receipt = read_json(receipt_path)
            receipt["duplicate_groups"] = 1
            write_json(receipt_path, receipt)
            review_output = root / "iteration-review"
            review_output.mkdir()

            exit_code, _payload = self.run_iteration_review(
                chain["iteration_output"],
                review_output,
            )
            packet_path = (
                review_output / "local_asset_smoke_iteration_review_packet.json"
            )
            packet = read_json(packet_path)
            packet_text = packet_path.read_text(encoding="utf-8")

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                packet["recommended_human_decision"],
                "inspect_iteration_quarantine_before_promotion",
            )
            self.assertEqual(packet["duplicate_summary"]["duplicate_group_count"], 1)
            self.assertEqual(packet["duplicate_summary"]["duplicate_asset_count"], 2)
            self.assertEqual(packet["quarantine_summary"]["quarantined_path_count"], 1)
            self.assertEqual(
                packet["quarantine_summary"]["secret_looking_path_count"],
                1,
            )
            self.assertFalse(packet["duplicate_summary"]["deletion_suggested"])
            self.assertFalse(packet["quarantine_summary"]["deletion_suggested"])
            self.assertNotIn(raw_secret, packet_text)

    def test_iteration_review_packet_summarizes_incremental_plan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline = self.build_iteration_chain(root / "baseline")
            current_root = root / "current"
            current_root.mkdir()
            candidate = self.make_candidate(current_root, plate_bytes=b"plate-v1")
            readiness_output = current_root / "readiness"
            smoke_output = current_root / "smoke-0"
            review_output = current_root / "review"
            promotion_output = current_root / "promotion"
            iteration_output = current_root / "iteration"
            for path in (
                readiness_output,
                smoke_output,
                review_output,
                promotion_output,
                iteration_output,
            ):
                path.mkdir()
            readiness_code, readiness_payload = self.run_readiness(
                candidate,
                readiness_output,
            )
            self.assertEqual(readiness_code, 0)
            smoke_code, _smoke_payload = self.run_human_smoke(
                candidate,
                smoke_output,
                readiness_payload["local_asset_smoke_readiness_report_path"],
            )
            self.assertEqual(smoke_code, 0)
            smoke_review_code, _review_payload = self.run_smoke_review(
                smoke_output,
                review_output,
            )
            self.assertEqual(smoke_review_code, 0)
            promotion_code, _promotion_payload = self.run_promotion(
                review_output,
                promotion_output,
            )
            self.assertEqual(promotion_code, 0)
            (candidate / "plate.png").write_bytes(b"plate-v2")
            (candidate / "new.wav").write_bytes(b"new")
            iteration_code, _iteration_payload = self.run_iteration(
                promotion_output,
                candidate,
                readiness_payload["local_asset_smoke_readiness_report_path"],
                iteration_output,
                previous_scan_output_dir=baseline["iteration_output"] / "smoke" / "scan",
            )
            self.assertEqual(iteration_code, 0)
            plan_path = (
                iteration_output
                / "smoke"
                / "scan"
                / "local_asset_incremental_scan_plan.json"
            )
            plan = read_json(plan_path)
            plan["suspicious_change_count"] = 1
            plan["suspicious_changes"] = [{"reason": "fixture_requires_inspection"}]
            write_json(plan_path, plan)
            iteration_review_output = current_root / "iteration-review"
            iteration_review_output.mkdir()

            exit_code, _payload = self.run_iteration_review(
                iteration_output,
                iteration_review_output,
            )
            packet = read_json(
                iteration_review_output
                / "local_asset_smoke_iteration_review_packet.json"
            )
            incremental = packet["incremental_summary"]

            self.assertEqual(exit_code, 0)
            self.assertEqual(incremental["plan_mode"], "compare_previous_scan")
            self.assertGreaterEqual(incremental["changed_asset_count"], 1)
            self.assertGreaterEqual(incremental["new_asset_count"], 1)
            self.assertGreaterEqual(incremental["suspicious_change_count"], 1)
            self.assertFalse(incremental["automatic_skip_performed"])
            self.assertFalse(incremental["cache_execution_performed"])
            self.assertEqual(
                packet["recommended_human_decision"],
                "inspect_iteration_incremental_changes_before_promotion",
            )

    def test_iteration_review_packet_blocks_missing_required_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            iteration_output = root / "iteration"
            review_output = root / "iteration-review"
            iteration_output.mkdir()
            review_output.mkdir()
            (iteration_output / "local_asset_bounded_smoke_iteration_summary.md").write_text(
                "# incomplete\n",
                encoding="utf-8",
            )

            exit_code, payload = self.run_iteration_review(
                iteration_output,
                review_output,
            )
            packet = read_json(
                review_output / "local_asset_smoke_iteration_review_packet.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["complete"])
            self.assertEqual(
                packet["iteration_review_status"],
                "review_blocked_missing_required_artifacts",
            )
            self.assertFalse(packet["scan_performed"])
            self.assertFalse(packet["iteration_output_mutation_performed"])

    def test_iteration_review_packet_blocks_untrusted_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_iteration_chain(root)
            manifest_path = (
                chain["iteration_output"]
                / "local_asset_bounded_smoke_iteration_manifest.json"
            )
            manifest = read_json(manifest_path)
            manifest["result_sha256"] = "0" * 64
            write_json(manifest_path, manifest)
            index_manifest_path = chain["iteration_output"] / "artifact_index_manifest.json"
            index_manifest = read_json(index_manifest_path)
            index_manifest["artifact_index_sha256"] = "1" * 64
            write_json(index_manifest_path, index_manifest)
            review_output = root / "iteration-review"
            review_output.mkdir()

            exit_code, _payload = self.run_iteration_review(
                chain["iteration_output"],
                review_output,
            )
            packet = read_json(
                review_output / "local_asset_smoke_iteration_review_packet.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                packet["iteration_review_status"],
                "review_blocked_untrusted_artifacts",
            )
            self.assertEqual(
                packet["recommended_human_decision"],
                "reject_and_repair_iteration",
            )

    def test_iteration_review_packet_fail_closed_on_existing_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_iteration_chain(root)
            for filename in ITERATION_REVIEW_OUTPUTS:
                with self.subTest(filename=filename):
                    review_output = root / ("review-" + filename.replace(".", "-"))
                    review_output.mkdir()
                    existing = review_output / filename
                    existing.write_text("do not overwrite\n", encoding="utf-8")

                    exit_code, _payload = self.run_iteration_review(
                        chain["iteration_output"],
                        review_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        existing.read_text(encoding="utf-8"),
                        "do not overwrite\n",
                    )
                    for other_name in ITERATION_REVIEW_OUTPUTS:
                        if other_name != filename:
                            self.assertFalse((review_output / other_name).exists())

    def test_iteration_review_packet_output_dir_missing_returns_structured_failure_without_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_iteration_chain(root)
            missing_output = root / "missing-iteration-review"

            exit_code, payload = self.run_iteration_review(
                chain["iteration_output"],
                missing_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["complete"])
            self.assertFalse(missing_output.exists())

    def test_iteration_review_packet_input_output_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_iteration_chain(root)
            cases = []

            cases.append(("same_dir", chain["iteration_output"], chain["iteration_output"]))

            output_inside_iteration = chain["iteration_output"] / "review-output"
            output_inside_iteration.mkdir()
            cases.append(
                (
                    "output_inside_iteration",
                    chain["iteration_output"],
                    output_inside_iteration,
                )
            )

            parent_output = root / "parent-review"
            nested_iteration = parent_output / "iteration"
            nested_iteration.mkdir(parents=True)
            cases.append(("iteration_inside_output", nested_iteration, parent_output))

            output_inside_candidate = chain["candidate"] / "iteration-review"
            output_inside_candidate.mkdir()
            cases.append(
                (
                    "output_inside_candidate",
                    chain["iteration_output"],
                    output_inside_candidate,
                )
            )

            output_inside_smoke = chain["iteration_output"] / "smoke" / "review-output"
            output_inside_smoke.mkdir()
            cases.append(
                (
                    "output_inside_delegated_smoke",
                    chain["iteration_output"],
                    output_inside_smoke,
                )
            )

            output_inside_promotion = chain["promotion_output"] / "iteration-review"
            output_inside_promotion.mkdir()
            cases.append(
                (
                    "output_inside_promotion",
                    chain["iteration_output"],
                    output_inside_promotion,
                )
            )

            for name, iteration_output, output_dir in cases:
                with self.subTest(name=name):
                    before = self.snapshot_tree(iteration_output)
                    exit_code, payload = self.run_iteration_review(
                        iteration_output,
                        output_dir,
                    )
                    after = self.snapshot_tree(iteration_output)

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["complete"])
                    self.assertEqual(before, after)
                    self.assertFalse(
                        (
                            output_dir
                            / "local_asset_smoke_iteration_review_packet.json"
                        ).exists()
                    )

    def test_task_graph_iteration_review_packet_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_iteration_chain(root)
            review_output = root / "iteration-review"
            graph_output = root / "graph-output"
            review_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.iteration_review_node(
                        node_id="iteration_review",
                        iteration_output_dir=chain["iteration_output"],
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
                if artifact["node_id"] == "iteration_review"
            }

            self.assertTrue(result.success)
            for role in ITERATION_REVIEW_ROLES:
                self.assertIn(role, roles)
            self.assertEqual(node["iteration_review_status"], "review_ready")
            self.assertEqual(
                node["recommended_human_decision"],
                "generate_promotion_gate_for_iteration",
            )

    def test_iteration_review_packet_no_scope_expansion_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_iteration_chain(root)
            review_output = root / "iteration-review"
            graph_review_output = root / "graph-iteration-review"
            graph_output = root / "graph-output"
            review_output.mkdir()
            graph_review_output.mkdir()
            graph_output.mkdir()
            exit_code, payload = self.run_iteration_review(
                chain["iteration_output"],
                review_output,
            )
            packet = read_json(
                review_output / "local_asset_smoke_iteration_review_packet.json"
            )
            manifest = read_json(
                review_output
                / "local_asset_smoke_iteration_review_packet_manifest.json"
            )
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.iteration_review_node(
                        node_id="iteration_review",
                        iteration_output_dir=chain["iteration_output"],
                        output_dir=graph_review_output,
                    )
                ],
                graph_id="iteration-review-boundaries-graph",
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            node = read_json(graph_result.execution_manifest_path)["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, packet, manifest, node):
                for field in BOUNDARY_FIELDS:
                    self.assertFalse(payload_like[field], field)
                self.assertTrue(payload_like["required_human_approval"])

    def test_iteration_review_packet_deterministic_across_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_iteration_chain(root)
            second_iteration_output = root / "iteration-two"
            first_review = root / "iteration-review-one"
            second_review = root / "iteration-review-two"
            second_iteration_output.mkdir()
            first_review.mkdir()
            second_review.mkdir()
            second_code, _second_payload = self.run_iteration(
                chain["promotion_output"],
                chain["candidate"],
                chain["readiness_report"],
                second_iteration_output,
            )
            self.assertEqual(second_code, 0)

            first_code, _first_payload = self.run_iteration_review(
                chain["iteration_output"],
                first_review,
            )
            second_code, _second_review_payload = self.run_iteration_review(
                second_iteration_output,
                second_review,
            )
            first_packet = read_json(
                first_review / "local_asset_smoke_iteration_review_packet.json"
            )
            second_packet = read_json(
                second_review / "local_asset_smoke_iteration_review_packet.json"
            )

            self.assertEqual(first_code, 0)
            self.assertEqual(second_code, 0)
            for field in (
                "iteration_review_status",
                "recommended_human_decision",
                "generated_artifacts_missing_count",
            ):
                self.assertEqual(first_packet[field], second_packet[field], field)
            self.assertEqual(
                first_packet["iteration_summary"]["iteration_status"],
                second_packet["iteration_summary"]["iteration_status"],
            )
            self.assertEqual(
                first_packet["duplicate_summary"]["duplicate_group_count"],
                second_packet["duplicate_summary"]["duplicate_group_count"],
            )
            self.assertEqual(
                [
                    artifact["artifact_role"]
                    for artifact in first_packet["source_artifacts"]
                ],
                [
                    artifact["artifact_role"]
                    for artifact in second_packet["source_artifacts"]
                ],
            )
            self.assertEqual(
                [
                    artifact["artifact_role"]
                    for artifact in first_packet["missing_artifacts"]
                ],
                [
                    artifact["artifact_role"]
                    for artifact in second_packet["missing_artifacts"]
                ],
            )
            self.assertEqual(
                first_packet["decision_checklist"]["decision_options"],
                second_packet["decision_checklist"]["decision_options"],
            )


if __name__ == "__main__":
    unittest.main()
