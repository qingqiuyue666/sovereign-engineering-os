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
ITERATION_PROMOTION_OUTPUTS = (
    "local_asset_iteration_promotion_decision.json",
    "local_asset_iteration_promotion_gate_manifest.json",
    "local_asset_iteration_promotion_summary.md",
    "local_asset_iteration_promotion_human_signoff_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
ITERATION_PROMOTION_ROLES = (
    "local_asset_iteration_promotion_decision",
    "local_asset_iteration_promotion_gate_manifest",
    "local_asset_iteration_promotion_summary",
    "local_asset_iteration_promotion_human_signoff_checklist",
)
BOUNDARY_FIELDS = (
    "production_promotion_granted",
    "production_scan_approved",
    "production_scan_performed",
    "production_scan_recommended",
    "scan_performed",
    "readiness_run_performed",
    "human_smoke_run_performed",
    "bounded_smoke_iteration_performed_by_gate",
    "iteration_review_packet_run_performed",
    "iteration_review_output_mutation_performed",
    "iteration_output_mutation_performed",
    "delegated_smoke_output_mutation_performed",
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


class LocalAssetIterationPromotionGateTests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def make_candidate(self, root):
        candidate = Path(root) / "candidate"
        nested = candidate / "nested"
        nested.mkdir(parents=True)
        (candidate / "plate.png").write_bytes(b"plate")
        (nested / "clip.mov").write_bytes(b"clip")
        return candidate

    def snapshot_tree(self, root):
        return sorted(path.relative_to(root).as_posix() for path in Path(root).rglob("*"))

    def run_readiness(self, candidate, output_dir, *, project_id="iteration-promotion-test"):
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
        project_id="iteration-promotion-test",
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
            "iteration-promotion-smoke-approval",
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

    def run_smoke_review(self, smoke_output_dir, output_dir):
        return self.run_cli(
            [
                "launch-local-asset-smoke-review-packet",
                "--smoke-output-dir",
                Path(smoke_output_dir).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--project-id",
                "iteration-promotion-test",
            ]
        )

    def run_smoke_promotion(self, review_output_dir, output_dir):
        return self.run_cli(
            [
                "launch-local-asset-smoke-promotion-gate",
                "--review-output-dir",
                Path(review_output_dir).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--project-id",
                "iteration-promotion-test",
            ]
        )

    def run_iteration(self, promotion_output_dir, candidate, readiness_report, output_dir):
        return self.run_cli(
            [
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
                "iteration-promotion-signoff",
                "--human-signoff-phrase",
                BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE,
                "--recursive",
                "--project-id",
                "iteration-promotion-test",
                "--max-smoke-files",
                "10",
                "--max-smoke-bytes",
                "2000",
                "--max-smoke-depth",
                "4",
            ]
        )

    def run_iteration_review(self, iteration_output_dir, output_dir):
        return self.run_cli(
            [
                "launch-local-asset-smoke-iteration-review-packet",
                "--iteration-output-dir",
                Path(iteration_output_dir).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--project-id",
                "iteration-promotion-test",
            ]
        )

    def run_iteration_promotion(self, iteration_review_output_dir, output_dir):
        return self.run_cli(
            [
                "launch-local-asset-iteration-promotion-gate",
                "--iteration-review-output-dir",
                Path(iteration_review_output_dir).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--project-id",
                "iteration-promotion-test",
            ]
        )

    def build_full_iteration_review_chain(self, root):
        candidate = self.make_candidate(root)
        readiness_output = Path(root) / "readiness"
        smoke_output = Path(root) / "smoke-0"
        smoke_review_output = Path(root) / "smoke-review"
        smoke_promotion_output = Path(root) / "smoke-promotion"
        iteration_output = Path(root) / "iteration"
        iteration_review_output = Path(root) / "iteration-review"
        for path in (
            readiness_output,
            smoke_output,
            smoke_review_output,
            smoke_promotion_output,
            iteration_output,
            iteration_review_output,
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
            smoke_review_output,
        )
        self.assertEqual(review_code, 0)
        promotion_code, _promotion_payload = self.run_smoke_promotion(
            smoke_review_output,
            smoke_promotion_output,
        )
        self.assertEqual(promotion_code, 0)
        iteration_code, iteration_payload = self.run_iteration(
            smoke_promotion_output,
            candidate,
            readiness_payload["local_asset_smoke_readiness_report_path"],
            iteration_output,
        )
        self.assertEqual(iteration_code, 0)
        iteration_review_code, iteration_review_payload = self.run_iteration_review(
            iteration_output,
            iteration_review_output,
        )
        self.assertEqual(iteration_review_code, 0)
        return {
            "candidate": candidate,
            "readiness_output": readiness_output,
            "smoke_output": smoke_output,
            "smoke_review_output": smoke_review_output,
            "smoke_promotion_output": smoke_promotion_output,
            "iteration_output": iteration_output,
            "iteration_payload": iteration_payload,
            "iteration_review_output": iteration_review_output,
            "iteration_review_payload": iteration_review_payload,
        }

    def write_iteration_review_fixture(self, root, *, packet_updates=None, review_dir=None):
        root = Path(root)
        review_output = Path(review_dir) if review_dir is not None else root / "iteration-review"
        iteration_output = root / "iteration-output"
        candidate_input = root / "candidate-input"
        smoke_output = root / "delegated-smoke-output"
        promotion_output = root / "smoke-promotion-output"
        for path in (
            review_output,
            iteration_output,
            candidate_input,
            smoke_output,
            promotion_output,
        ):
            path.mkdir(parents=True, exist_ok=True)

        packet = {
            "packet_type": "local_asset_smoke_iteration_review_packet_v1",
            "authority": "non_authority",
            "execution_capability": "local_asset_smoke_iteration_review_packet_only",
            "iteration_output_dir": iteration_output.as_posix(),
            "output_dir": review_output.as_posix(),
            "project_id": "iteration-promotion-test",
            "iteration_review_status": "review_ready",
            "recommended_human_decision": "generate_promotion_gate_for_iteration",
            "iteration_summary": {
                "iteration_status": "iteration_completed",
                "iteration_decision": "bounded_smoke_iteration_completed",
                "bounded_smoke_iteration_performed": True,
                "smoke_run_complete": True,
                "scan_complete": True,
            },
            "signoff_summary": {"human_signoff_valid": True},
            "admission_summary": {"admitted": True},
            "promotion_summary": {
                "promotion_gate_status": "promotion_candidate",
                "promotion_decision": "allow_next_bounded_smoke_iteration",
            },
            "delegated_smoke_summary": {
                "bounded_smoke_run_performed": True,
                "scan_complete": True,
                "production_scan_performed": False,
            },
            "delegated_scan_summary": {
                "scan_complete": True,
                "duplicate_group_count": 0,
                "quarantined_path_count": 0,
            },
            "duplicate_summary": {
                "duplicate_group_count": 0,
                "duplicate_asset_count": 0,
                "automatic_dedupe_performed": False,
            },
            "quarantine_summary": {"quarantined_path_count": 0},
            "sqlite_summary": {"database_present": False},
            "incremental_summary": {
                "plan_present": False,
                "plan_mode": None,
                "changed_asset_count": 0,
                "new_asset_count": 0,
                "missing_asset_count": 0,
                "suspicious_change_count": 0,
            },
            "failure_summary": {"iteration_blocker_count": 0},
            "warning_summary": {"warning_count": 0, "warnings": []},
            "iteration_status": "iteration_completed",
            "iteration_decision": "bounded_smoke_iteration_completed",
            "bounded_smoke_iteration_performed": True,
            "smoke_run_complete": True,
            "scan_complete": True,
            "duplicate_group_count": 0,
            "quarantined_path_count": 0,
            "suspicious_change_count": 0,
            "warning_count": 0,
            "production_promotion_granted": False,
            "production_scan_approved": False,
            "production_scan_performed": False,
            "input_mutation_performed": False,
            "duplicate_deletion_performed": False,
            "source_artifacts": [
                {
                    "artifact_role": "smoke_artifact_index",
                    "path": (smoke_output / "artifact_index.json").as_posix(),
                }
            ],
            "deterministic_ordering": True,
        }
        if packet_updates is not None:
            packet_updates(packet)

        packet_path = review_output / "local_asset_smoke_iteration_review_packet.json"
        summary_path = review_output / "local_asset_smoke_iteration_review_summary.md"
        checklist_path = (
            review_output
            / "local_asset_smoke_iteration_human_decision_checklist.md"
        )
        manifest_path = (
            review_output
            / "local_asset_smoke_iteration_review_packet_manifest.json"
        )
        artifact_index_path = review_output / "artifact_index.json"
        artifact_index_manifest_path = review_output / "artifact_index_manifest.json"

        write_json(packet_path, packet)
        summary_path.write_text("# fixture summary\n", encoding="utf-8")
        checklist_path.write_text("# fixture checklist\n", encoding="utf-8")
        write_json(
            manifest_path,
            {
                "manifest_type": "local_asset_smoke_iteration_review_packet_manifest_v1",
                "authority": "non_authority",
                "packet_path": packet_path.as_posix(),
                "summary_path": summary_path.as_posix(),
                "decision_checklist_path": checklist_path.as_posix(),
                "packet_sha256": sha256_file(packet_path),
                "summary_sha256": sha256_file(summary_path),
                "decision_checklist_sha256": sha256_file(checklist_path),
            },
        )
        write_json(
            artifact_index_path,
            {
                "index_type": "local_asset_smoke_iteration_review_packet_artifact_index_v1",
                "authority": "non_authority",
                "entries": [],
            },
        )
        write_json(
            artifact_index_manifest_path,
            {
                "manifest_type": (
                    "local_asset_smoke_iteration_review_packet_artifact_index_manifest_v1"
                ),
                "artifact_index_path": artifact_index_path.as_posix(),
                "artifact_index_sha256": sha256_file(artifact_index_path),
            },
        )
        return {
            "review_output": review_output,
            "iteration_output": iteration_output,
            "candidate_input": candidate_input,
            "smoke_output": smoke_output,
            "promotion_output": promotion_output,
        }

    def write_graph(self, graph_path, nodes, *, graph_id="iteration-promotion-graph"):
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

    def iteration_promotion_node(self, *, node_id, iteration_review_output_dir, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": "launch_local_asset_iteration_promotion_gate",
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "iteration_review_output_dir": Path(
                    iteration_review_output_dir
                ).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "project_id": "iteration-promotion-test",
            },
        }

    def test_iteration_promotion_gate_writes_decision_manifest_summary_checklist_and_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_iteration_review_chain(root)
            promotion_output = root / "iteration-promotion"
            promotion_output.mkdir()

            exit_code, payload = self.run_iteration_promotion(
                chain["iteration_review_output"],
                promotion_output,
            )
            artifact_index = read_json(promotion_output / "artifact_index.json")
            artifact_roles = {
                entry["artifact_role"] for entry in artifact_index["entries"]
            }

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in ITERATION_PROMOTION_OUTPUTS:
                self.assertTrue((promotion_output / filename).exists(), filename)
            for role in ITERATION_PROMOTION_ROLES:
                self.assertIn(role, artifact_roles)

    def test_iteration_promotion_gate_allows_clean_iteration_review_ready_packet_only_for_next_bounded_smoke(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = self.write_iteration_review_fixture(root)
            promotion_output = root / "iteration-promotion"
            promotion_output.mkdir()

            exit_code, payload = self.run_iteration_promotion(
                fixture["review_output"],
                promotion_output,
            )
            decision = read_json(
                promotion_output / "local_asset_iteration_promotion_decision.json"
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                decision["iteration_promotion_gate_status"],
                "iteration_promotion_candidate",
            )
            self.assertEqual(
                decision["iteration_promotion_decision"],
                "allow_next_bounded_smoke_iteration",
            )
            self.assertTrue(decision["next_bounded_smoke_iteration_allowed"])
            self.assertFalse(decision["production_promotion_granted"])
            self.assertFalse(decision["production_scan_approved"])
            self.assertFalse(decision["production_scan_performed"])
            self.assertEqual(payload["allowed_next_action"], "next_bounded_smoke_iteration")

    def test_iteration_promotion_gate_blocks_quarantine(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            def update(packet):
                packet["quarantined_path_count"] = 1
                packet["quarantine_summary"]["quarantined_path_count"] = 1
                packet["recommended_human_decision"] = (
                    "inspect_iteration_quarantine_before_promotion"
                )

            fixture = self.write_iteration_review_fixture(root, packet_updates=update)
            promotion_output = root / "iteration-promotion"
            promotion_output.mkdir()

            exit_code, _payload = self.run_iteration_promotion(
                fixture["review_output"],
                promotion_output,
            )
            decision = read_json(
                promotion_output / "local_asset_iteration_promotion_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(decision["iteration_promotion_gate_status"], "blocked_quarantine")
            self.assertEqual(
                decision["iteration_promotion_decision"],
                "block_until_human_inspects_iteration_quarantine",
            )
            self.assertFalse(decision["next_bounded_smoke_iteration_allowed"])

    def test_iteration_promotion_gate_blocks_duplicates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            def update(packet):
                packet["duplicate_group_count"] = 2
                packet["duplicate_summary"]["duplicate_group_count"] = 2

            fixture = self.write_iteration_review_fixture(root, packet_updates=update)
            promotion_output = root / "iteration-promotion"
            promotion_output.mkdir()

            exit_code, _payload = self.run_iteration_promotion(
                fixture["review_output"],
                promotion_output,
            )
            decision = read_json(
                promotion_output / "local_asset_iteration_promotion_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(decision["iteration_promotion_gate_status"], "blocked_duplicates")
            self.assertEqual(
                decision["iteration_promotion_decision"],
                "block_until_human_inspects_iteration_duplicates",
            )

    def test_iteration_promotion_gate_blocks_incremental_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            def update(packet):
                packet["incremental_summary"]["plan_mode"] = "compare_previous_scan"
                packet["incremental_summary"]["changed_asset_count"] = 1
                packet["changed_asset_count"] = 1

            fixture = self.write_iteration_review_fixture(root, packet_updates=update)
            promotion_output = root / "iteration-promotion"
            promotion_output.mkdir()

            exit_code, _payload = self.run_iteration_promotion(
                fixture["review_output"],
                promotion_output,
            )
            decision = read_json(
                promotion_output / "local_asset_iteration_promotion_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                decision["iteration_promotion_gate_status"],
                "blocked_incremental_changes",
            )
            self.assertEqual(
                decision["iteration_promotion_decision"],
                "block_until_human_inspects_iteration_incremental_changes",
            )

    def test_iteration_promotion_gate_blocks_missing_required_iteration_review_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review_output = root / "iteration-review"
            promotion_output = root / "iteration-promotion"
            review_output.mkdir()
            promotion_output.mkdir()

            exit_code, _payload = self.run_iteration_promotion(
                review_output,
                promotion_output,
            )
            decision = read_json(
                promotion_output / "local_asset_iteration_promotion_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                decision["iteration_promotion_gate_status"],
                "blocked_missing_iteration_review_artifacts",
            )
            self.assertFalse(decision["next_bounded_smoke_iteration_allowed"])

    def test_iteration_promotion_gate_blocks_untrusted_iteration_review_artifacts(self):
        for filename, field in (
            (
                "local_asset_smoke_iteration_review_packet_manifest.json",
                "packet_sha256",
            ),
            ("artifact_index_manifest.json", "artifact_index_sha256"),
        ):
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    fixture = self.write_iteration_review_fixture(root)
                    manifest_path = fixture["review_output"] / filename
                    manifest = read_json(manifest_path)
                    manifest[field] = "0" * 64
                    write_json(manifest_path, manifest)
                    promotion_output = root / "iteration-promotion"
                    promotion_output.mkdir()

                    exit_code, _payload = self.run_iteration_promotion(
                        fixture["review_output"],
                        promotion_output,
                    )
                    decision = read_json(
                        promotion_output
                        / "local_asset_iteration_promotion_decision.json"
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        decision["iteration_promotion_gate_status"],
                        "blocked_untrusted_iteration_review_packet",
                    )
                    self.assertEqual(
                        decision["iteration_promotion_decision"],
                        "block_until_iteration_review_packet_repaired",
                    )

    def test_iteration_promotion_gate_fail_closed_on_existing_outputs(self):
        for filename in ITERATION_PROMOTION_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    fixture = self.write_iteration_review_fixture(root)
                    promotion_output = root / "iteration-promotion"
                    promotion_output.mkdir()
                    preexisting = promotion_output / filename
                    preexisting.write_text("preexisting\n", encoding="utf-8")

                    exit_code, payload = self.run_iteration_promotion(
                        fixture["review_output"],
                        promotion_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(preexisting.read_text(encoding="utf-8"), "preexisting\n")
                    self.assertFalse(payload["artifacts_written"])

    def test_iteration_promotion_gate_output_dir_missing_returns_structured_failure_without_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = self.write_iteration_review_fixture(root)
            promotion_output = root / "missing-output"

            exit_code, payload = self.run_iteration_promotion(
                fixture["review_output"],
                promotion_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(promotion_output.exists())
            self.assertFalse(payload["artifacts_written"])

    def test_iteration_promotion_gate_input_output_overlap_rejected(self):
        cases = (
            ("same_dir", lambda root, fixture: fixture["review_output"]),
            (
                "output_inside_iteration_review_output_dir",
                lambda root, fixture: fixture["review_output"] / "nested-promotion",
            ),
            (
                "iteration_review_output_dir_inside_output_dir",
                lambda root, fixture: fixture["review_output"].parent,
            ),
            (
                "output_inside_iteration_output_dir",
                lambda root, fixture: fixture["iteration_output"] / "promotion",
            ),
            (
                "output_inside_candidate_input_dir",
                lambda root, fixture: fixture["candidate_input"] / "promotion",
            ),
            (
                "output_inside_delegated_smoke_output_dir",
                lambda root, fixture: fixture["smoke_output"] / "promotion",
            ),
            (
                "output_inside_promotion_output_dir",
                lambda root, fixture: fixture["promotion_output"] / "promotion",
            ),
        )
        for case_name, output_factory in cases:
            with self.subTest(case_name=case_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)

                    def update(packet):
                        packet["candidate_input_dir"] = (root / "candidate-input").as_posix()
                        packet["smoke_output_dir"] = (
                            root / "delegated-smoke-output"
                        ).as_posix()
                        packet["promotion_output_dir"] = (
                            root / "smoke-promotion-output"
                        ).as_posix()

                    if case_name == "iteration_review_output_dir_inside_output_dir":
                        outer = root / "outer-output"
                        review_dir = outer / "iteration-review"
                        fixture = self.write_iteration_review_fixture(
                            root,
                            packet_updates=update,
                            review_dir=review_dir,
                        )
                    else:
                        fixture = self.write_iteration_review_fixture(
                            root,
                            packet_updates=update,
                        )
                    output_dir = output_factory(root, fixture)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    review_snapshot = self.snapshot_tree(fixture["review_output"])

                    exit_code, _payload = self.run_iteration_promotion(
                        fixture["review_output"],
                        output_dir,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        self.snapshot_tree(fixture["review_output"]),
                        review_snapshot,
                    )
                    for filename in ITERATION_PROMOTION_OUTPUTS[:4]:
                        self.assertFalse((output_dir / filename).exists(), filename)

    def test_task_graph_iteration_promotion_gate_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = self.write_iteration_review_fixture(root)
            promotion_output = root / "iteration-promotion"
            graph_output = root / "graph-output"
            promotion_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.iteration_promotion_node(
                        node_id="iteration_promotion",
                        iteration_review_output_dir=fixture["review_output"],
                        output_dir=promotion_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            execution_manifest = read_json(result.execution_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "iteration_promotion"
            }
            node = execution_manifest["nodes"][0]

            self.assertTrue(result.success)
            for role in ITERATION_PROMOTION_ROLES:
                self.assertIn(role, roles)
            self.assertEqual(
                node["iteration_promotion_gate_status"],
                "iteration_promotion_candidate",
            )

    def test_iteration_promotion_gate_no_scope_expansion_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = self.write_iteration_review_fixture(root)
            promotion_output = root / "iteration-promotion"
            graph_promotion_output = root / "graph-iteration-promotion"
            graph_output = root / "graph-output"
            promotion_output.mkdir()
            graph_promotion_output.mkdir()
            graph_output.mkdir()

            exit_code, payload = self.run_iteration_promotion(
                fixture["review_output"],
                promotion_output,
            )
            decision = read_json(
                promotion_output / "local_asset_iteration_promotion_decision.json"
            )
            manifest = read_json(
                promotion_output
                / "local_asset_iteration_promotion_gate_manifest.json"
            )
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.iteration_promotion_node(
                        node_id="iteration_promotion",
                        iteration_review_output_dir=fixture["review_output"],
                        output_dir=graph_promotion_output,
                    )
                ],
                graph_id="iteration-promotion-boundaries-graph",
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            node = read_json(graph_result.execution_manifest_path)["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, decision, manifest, node):
                for field in BOUNDARY_FIELDS:
                    self.assertFalse(payload_like[field], field)
                self.assertTrue(payload_like["required_human_approval"])
            self.assertIn("production_scan_recommendation", decision["rejected_next_actions"])

    def test_iteration_promotion_gate_deterministic_across_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_fixture = self.write_iteration_review_fixture(root / "first")
            second_fixture = self.write_iteration_review_fixture(root / "second")
            first_output = root / "first-promotion"
            second_output = root / "second-promotion"
            first_output.mkdir()
            second_output.mkdir()

            first_code, _first_payload = self.run_iteration_promotion(
                first_fixture["review_output"],
                first_output,
            )
            second_code, _second_payload = self.run_iteration_promotion(
                second_fixture["review_output"],
                second_output,
            )
            first_decision = read_json(
                first_output / "local_asset_iteration_promotion_decision.json"
            )
            second_decision = read_json(
                second_output / "local_asset_iteration_promotion_decision.json"
            )

            self.assertEqual(first_code, 0)
            self.assertEqual(second_code, 0)
            for field in (
                "iteration_promotion_gate_status",
                "iteration_promotion_decision",
                "next_bounded_smoke_iteration_allowed",
            ):
                self.assertEqual(first_decision[field], second_decision[field])
            self.assertEqual(
                first_decision["blocker_summary"]["blocker_roles"],
                second_decision["blocker_summary"]["blocker_roles"],
            )
            self.assertEqual(
                [
                    artifact["artifact_role"]
                    for artifact in first_decision["source_artifacts"]
                ],
                [
                    artifact["artifact_role"]
                    for artifact in second_decision["source_artifacts"]
                ],
            )
            self.assertEqual(
                first_decision["human_signoff_checklist"]["decision_options"],
                second_decision["human_signoff_checklist"]["decision_options"],
            )


if __name__ == "__main__":
    unittest.main()
