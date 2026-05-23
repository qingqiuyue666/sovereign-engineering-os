import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture
from tests.tracer_bullet import (
    test_local_asset_next_bounded_smoke_iteration_run_review_packet as review_helpers,
)


GATE_OUTPUTS = (
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate.json",
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest.json",
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary.md",
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
GATE_ROLES = (
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate",
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest",
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary",
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist",
)
NO_SCOPE_FIELDS = (
    "cycle_contract_generated",
    "production_scan_approved",
    "production_promotion_granted",
    "automatic_approval_performed",
    "autonomous_execution_performed",
    "runner_reexecution_performed",
    "candidate_input_path_checked_by_gate",
    "candidate_input_path_listed_by_gate",
    "candidate_input_file_read_by_gate",
    "candidate_input_file_hashing_performed_by_gate",
    "file_move_performed",
    "file_rename_performed",
    "file_delete_performed",
    "duplicate_deletion_performed",
    "media_organizer_behavior_performed",
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


class LocalAssetNextBoundedSmokeIterationRunPromotionGateTests(unittest.TestCase):
    make_candidate = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.make_candidate
    )
    run_readiness = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_readiness
    )
    run_human_smoke = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_human_smoke
    )
    run_smoke_review = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_smoke_review
    )
    run_smoke_promotion = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_smoke_promotion
    )
    run_iteration = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_iteration
    )
    run_iteration_review = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_iteration_review
    )
    run_iteration_promotion = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_iteration_promotion
    )
    run_cycle_contract = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_cycle_contract
    )
    build_full_chain = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.build_full_chain
    )
    run_cycle_human_review = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_cycle_human_review
    )
    build_ready_cycle_human_review = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.build_ready_cycle_human_review
    )
    run_admission = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_admission
    )
    build_ready_admission = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.build_ready_admission
    )
    build_non_ready_admission = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.build_non_ready_admission
    )
    run_execution_request = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_execution_request
    )
    build_ready_request = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.build_ready_request
    )
    run_runner_admission = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_runner_admission
    )
    build_ready_runner_admission = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.build_ready_runner_admission
    )
    make_future_candidate = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.make_future_candidate
    )
    make_actual_output = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.make_actual_output
    )
    run_runner = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_runner
    )
    build_ready_runner = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.build_ready_runner
    )
    run_review_packet = (
        review_helpers.LocalAssetNextBoundedSmokeIterationRunReviewPacketTests.run_review_packet
    )

    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def build_ready_review_packet(self, root):
        runner_output, actual = self.build_ready_runner(root)
        review = Path(root) / "run-review"
        review.mkdir()
        exit_code, _payload = self.run_review_packet(runner_output, actual, review)
        self.assertEqual(exit_code, 0)
        return review, runner_output, actual

    def run_promotion_gate(
        self,
        review,
        output_dir,
        *,
        promotion_gate_id="run-promotion-gate-1",
        project_id="cycle-test",
        reviewer_id="gate-reviewer-1",
        operator_notes="promote reviewed bounded run only",
    ):
        args = [
            "launch-local-asset-next-bounded-smoke-iteration-run-promotion-gate",
            "--run-review-packet-output-dir",
            Path(review).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--promotion-gate-id",
            promotion_gate_id,
        ]
        if project_id is not None:
            args.extend(["--project-id", project_id])
        if reviewer_id is not None:
            args.extend(["--reviewer-id", reviewer_id])
        if operator_notes is not None:
            args.extend(["--operator-notes", operator_notes])
        return self.run_cli(args)

    def rewrite_review_manifest_hash(self, review):
        review = Path(review)
        packet_path = (
            review
            / "local_asset_next_bounded_smoke_iteration_run_review_packet.json"
        )
        manifest_path = (
            review
            / "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest.json"
        )
        manifest = read_json(manifest_path)
        manifest["review_packet_sha256"] = sha256_file(packet_path)
        write_json(manifest_path, manifest)

    def gate_node(self, *, node_id, review, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": (
                "launch_local_asset_next_bounded_smoke_iteration_run_promotion_gate"
            ),
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "run_review_packet_output_dir": Path(review).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "promotion_gate_id": "graph-run-promotion-gate-1",
                "project_id": "cycle-test",
                "reviewer_id": "gate-reviewer-1",
                "operator_notes": "gate generated run review packet artifacts",
            },
        }

    def write_graph(self, graph_path, nodes):
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "run-promotion-gate-graph",
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": nodes,
            },
        )

    def assert_gate_artifacts_absent(self, output_dir):
        for filename in GATE_OUTPUTS:
            self.assertFalse((Path(output_dir) / filename).exists(), filename)

    def assert_no_scope_false(self, payload_like):
        for field_name in NO_SCOPE_FIELDS:
            self.assertFalse(payload_like[field_name], field_name)

    def test_full_chain_writes_promotion_gate_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review, _runner_output, _actual = self.build_ready_review_packet(root)
            gate_output = root / "gate"
            gate_output.mkdir()

            exit_code, payload = self.run_promotion_gate(review, gate_output)
            index = read_json(gate_output / "artifact_index.json")
            roles = {entry["artifact_role"] for entry in index["entries"]}

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in GATE_OUTPUTS:
                self.assertTrue((gate_output / filename).exists(), filename)
            self.assertEqual(roles, set(GATE_ROLES))

    def test_ready_review_packet_approves_bounded_run_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review, _runner_output, _actual = self.build_ready_review_packet(root)
            gate_output = root / "gate"
            gate_output.mkdir()

            exit_code, payload = self.run_promotion_gate(review, gate_output)
            gate = read_json(
                gate_output
                / "local_asset_next_bounded_smoke_iteration_run_promotion_gate.json"
            )

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, gate):
                self.assertEqual(
                    payload_like["gate_status"],
                    "next_bounded_smoke_iteration_run_promotion_gate_ready",
                )
                self.assertEqual(
                    payload_like["gate_decision"],
                    "approve_next_bounded_smoke_iteration_run_for_cycle_contract",
                )
                self.assertEqual(
                    payload_like["next_allowed_action"],
                    "create_next_bounded_smoke_cycle_contract_from_run",
                )
                self.assertTrue(payload_like["bounded_run_promotion_approved"])
                self.assertTrue(payload_like["cycle_contract_generation_allowed"])
                self.assert_no_scope_false(payload_like)

    def test_promotion_gate_does_not_touch_live_candidate_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review, _runner_output, _actual = self.build_ready_review_packet(root)
            packet = read_json(
                review
                / "local_asset_next_bounded_smoke_iteration_run_review_packet.json"
            )
            candidate = Path(packet["requested_candidate_input_dir"])
            shutil.rmtree(candidate)
            os.symlink("/definitely/not-read-by-promotion-gate", candidate)
            gate_output = root / "gate"
            gate_output.mkdir()

            exit_code, payload = self.run_promotion_gate(review, gate_output)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                payload["gate_status"],
                "next_bounded_smoke_iteration_run_promotion_gate_ready",
            )
            self.assertFalse(payload["candidate_input_path_checked_by_gate"])
            self.assertFalse(payload["candidate_input_path_listed_by_gate"])
            self.assertFalse(payload["candidate_input_file_read_by_gate"])
            self.assertFalse(
                payload["candidate_input_file_hashing_performed_by_gate"]
            )

    def test_blocks_missing_required_review_packet_artifacts(self):
        for filename in (
            "local_asset_next_bounded_smoke_iteration_run_review_packet.json",
            "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest.json",
        ):
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    review, _runner_output, _actual = self.build_ready_review_packet(root)
                    (review / filename).unlink()
                    gate_output = root / "gate"
                    gate_output.mkdir()

                    exit_code, payload = self.run_promotion_gate(
                        review,
                        gate_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["gate_status"],
                        "blocked_missing_required_artifacts",
                    )

    def test_blocks_untrusted_review_packet_artifacts(self):
        cases = (
            (
                "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest.json",
                "review_packet_sha256",
            ),
            ("artifact_index_manifest.json", "artifact_index_sha256"),
        )
        for filename, hash_field in cases:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    review, _runner_output, _actual = self.build_ready_review_packet(root)
                    manifest_path = review / filename
                    manifest = read_json(manifest_path)
                    manifest[hash_field] = "0" * 64
                    write_json(manifest_path, manifest)
                    gate_output = root / "gate"
                    gate_output.mkdir()

                    exit_code, payload = self.run_promotion_gate(
                        review,
                        gate_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["gate_status"],
                        "blocked_untrusted_artifacts",
                    )

    def test_blocks_review_packet_not_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review, _runner_output, _actual = self.build_ready_review_packet(root)
            packet_path = (
                review
                / "local_asset_next_bounded_smoke_iteration_run_review_packet.json"
            )
            packet = read_json(packet_path)
            packet["review_status"] = "review_packet_still_under_repair"
            write_json(packet_path, packet)
            self.rewrite_review_manifest_hash(review)
            gate_output = root / "gate"
            gate_output.mkdir()

            exit_code, payload = self.run_promotion_gate(review, gate_output)

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                payload["gate_status"],
                "blocked_review_packet_not_ready",
            )

    def test_blocks_invalid_review_packet_record(self):
        cases = (
            ("next_allowed_action", "wrong_action"),
            ("review_packet_created", False),
            ("remove_field", "promotion_approved"),
            ("string_false_field", "production_scan_approved"),
        )
        for mutation, value in cases:
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    review, _runner_output, _actual = self.build_ready_review_packet(root)
                    packet_path = (
                        review
                        / "local_asset_next_bounded_smoke_iteration_run_review_packet.json"
                    )
                    packet = read_json(packet_path)
                    if mutation == "remove_field":
                        packet.pop(value, None)
                    elif mutation == "string_false_field":
                        packet[value] = "false"
                    else:
                        packet[mutation] = value
                    write_json(packet_path, packet)
                    self.rewrite_review_manifest_hash(review)
                    gate_output = root / "gate"
                    gate_output.mkdir()

                    exit_code, payload = self.run_promotion_gate(
                        review,
                        gate_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertIn(
                        payload["gate_status"],
                        {
                            "blocked_invalid_review_packet_record",
                            "blocked_source_boundary_violation",
                        },
                    )

    def test_blocks_source_boundary_violation(self):
        fields = (
            "promotion_approved",
            "production_scan_approved",
            "production_promotion_granted",
            "runner_reexecution_performed",
            "candidate_input_file_read_by_review",
            "file_delete_performed",
        )
        for field_name in fields:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    review, _runner_output, _actual = self.build_ready_review_packet(root)
                    packet_path = (
                        review
                        / "local_asset_next_bounded_smoke_iteration_run_review_packet.json"
                    )
                    packet = read_json(packet_path)
                    packet[field_name] = True
                    write_json(packet_path, packet)
                    self.rewrite_review_manifest_hash(review)
                    gate_output = root / "gate"
                    gate_output.mkdir()

                    exit_code, payload = self.run_promotion_gate(
                        review,
                        gate_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["gate_status"],
                        "blocked_source_boundary_violation",
                    )

    def test_blocks_invalid_reviewed_run_facts(self):
        cases = (
            ("runner_execution_performed", False),
            ("next_bounded_smoke_iteration_executed", False),
            ("candidate_limit_enforced", False),
            ("candidate_symlinks_detected", ["link"]),
            ("candidate_file_count", "2"),
            ("bounded_file_records_unsorted", True),
            ("bounded_file_records_raw_content", True),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    review, _runner_output, _actual = self.build_ready_review_packet(root)
                    packet_path = (
                        review
                        / "local_asset_next_bounded_smoke_iteration_run_review_packet.json"
                    )
                    packet = read_json(packet_path)
                    if field_name == "bounded_file_records_unsorted":
                        packet["bounded_file_records"] = list(
                            reversed(packet["bounded_file_records"])
                        )
                    elif field_name == "bounded_file_records_raw_content":
                        packet["bounded_file_records"][0]["raw_content"] = "private"
                    else:
                        packet[field_name] = value
                    write_json(packet_path, packet)
                    self.rewrite_review_manifest_hash(review)
                    gate_output = root / "gate"
                    gate_output.mkdir()

                    exit_code, payload = self.run_promotion_gate(
                        review,
                        gate_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["gate_status"],
                        "blocked_invalid_reviewed_run_facts",
                    )

    def test_blocks_review_packet_contains_blockers(self):
        cases = (
            ("review_blockers", [{"reason": "manual_blocker"}]),
            ("cross_artifact_checks", [{"check": "failed", "passed": False}]),
            ("missing_required_artifacts", [{"artifact_role": "missing"}]),
            ("untrusted_artifacts", [{"artifact_role": "untrusted"}]),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    review, _runner_output, _actual = self.build_ready_review_packet(root)
                    packet_path = (
                        review
                        / "local_asset_next_bounded_smoke_iteration_run_review_packet.json"
                    )
                    packet = read_json(packet_path)
                    packet[field_name] = value
                    write_json(packet_path, packet)
                    self.rewrite_review_manifest_hash(review)
                    gate_output = root / "gate"
                    gate_output.mkdir()

                    exit_code, payload = self.run_promotion_gate(
                        review,
                        gate_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertIn(
                        payload["gate_status"],
                        {
                            "blocked_review_packet_contains_blockers",
                            "blocked_missing_required_artifacts",
                            "blocked_untrusted_artifacts",
                        },
                    )

    def test_blocks_invalid_promotion_gate_metadata(self):
        cases = (
            {"promotion_gate_id": ""},
            {"reviewer_id": ""},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    review, _runner_output, _actual = self.build_ready_review_packet(root)
                    gate_output = root / "gate"
                    gate_output.mkdir()

                    exit_code, payload = self.run_promotion_gate(
                        review,
                        gate_output,
                        **kwargs,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["gate_status"],
                        "blocked_invalid_promotion_gate_metadata",
                    )

    def test_fails_closed_on_existing_promotion_gate_outputs(self):
        for filename in GATE_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    review, _runner_output, _actual = self.build_ready_review_packet(root)
                    gate_output = root / "gate"
                    gate_output.mkdir()
                    existing = gate_output / filename
                    existing.write_text("existing\n", encoding="utf-8")

                    exit_code, payload = self.run_promotion_gate(
                        review,
                        gate_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertEqual(existing.read_text(encoding="utf-8"), "existing\n")
                    for other in GATE_OUTPUTS:
                        if other != filename:
                            self.assertFalse((gate_output / other).exists(), other)

    def test_fails_closed_on_symlink_promotion_gate_output_collision(self):
        for filename in GATE_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    review, _runner_output, _actual = self.build_ready_review_packet(root)
                    gate_output = root / "gate"
                    gate_output.mkdir()
                    os.symlink(root / "target-does-not-need-to-exist", gate_output / filename)

                    exit_code, payload = self.run_promotion_gate(
                        review,
                        gate_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    for other in GATE_OUTPUTS:
                        if other != filename:
                            self.assertFalse((gate_output / other).exists(), other)

    def test_missing_output_dir_structured_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review, _runner_output, _actual = self.build_ready_review_packet(root)
            gate_output = root / "missing-gate"

            exit_code, payload = self.run_promotion_gate(review, gate_output)

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["artifacts_written"])
            self.assertFalse(gate_output.exists())

    def test_input_output_overlap_rejected(self):
        cases = (
            "output_inside_review",
            "review_inside_output",
            "same_dir",
        )
        for case_name in cases:
            with self.subTest(case_name=case_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    review, _runner_output, _actual = self.build_ready_review_packet(root)
                    if case_name == "output_inside_review":
                        gate_output = review / "gate"
                        gate_output.mkdir()
                    elif case_name == "review_inside_output":
                        gate_output = root / "gate"
                        gate_output.mkdir()
                        copied_review = gate_output / "review"
                        shutil.copytree(review, copied_review)
                        review = copied_review
                    else:
                        gate_output = review

                    exit_code, payload = self.run_promotion_gate(
                        review,
                        gate_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertFalse(
                        (
                            gate_output
                            / "local_asset_next_bounded_smoke_iteration_run_promotion_gate.json"
                        ).exists()
                    )

    def test_task_graph_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review, _runner_output, _actual = self.build_ready_review_packet(root)
            gate_output = root / "gate"
            gate_output.mkdir()
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.gate_node(
                        node_id="promote_run",
                        review=review,
                        output_dir=gate_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "promote_run"
            }

            self.assertTrue(result.success)
            for role in GATE_ROLES:
                self.assertIn(role, roles)

    def test_no_scope_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review, _runner_output, _actual = self.build_ready_review_packet(root)
            gate_output = root / "gate"
            gate_output.mkdir()
            exit_code, payload = self.run_promotion_gate(review, gate_output)
            gate = read_json(
                gate_output
                / "local_asset_next_bounded_smoke_iteration_run_promotion_gate.json"
            )
            manifest = read_json(
                gate_output
                / "local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest.json"
            )
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            graph_gate_output = root / "graph-gate"
            graph_gate_output.mkdir()
            self.write_graph(
                graph_path,
                [
                    self.gate_node(
                        node_id="promote_run",
                        review=review,
                        output_dir=graph_gate_output,
                    )
                ],
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            node = read_json(graph_result.execution_manifest_path)["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, gate, manifest, node):
                self.assert_no_scope_false(payload_like)

    def test_deterministic_stable_fields(self):
        gates = []
        checklists = []
        for index in range(2):
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                review, _runner_output, _actual = self.build_ready_review_packet(root)
                gate_output = root / "gate"
                gate_output.mkdir()
                exit_code, _payload = self.run_promotion_gate(
                    review,
                    gate_output,
                    promotion_gate_id="stable-gate-" + str(index),
                )
                self.assertEqual(exit_code, 0)
                gates.append(
                    read_json(
                        gate_output
                        / "local_asset_next_bounded_smoke_iteration_run_promotion_gate.json"
                    )
                )
                checklists.append(
                    (
                        gate_output
                        / "local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist.md"
                    ).read_text(encoding="utf-8")
                )

        self.assertEqual(gates[0]["gate_status"], gates[1]["gate_status"])
        self.assertEqual(gates[0]["gate_decision"], gates[1]["gate_decision"])
        self.assertEqual(gates[0]["next_allowed_action"], gates[1]["next_allowed_action"])
        self.assertEqual(gates[0]["disallowed_actions"], gates[1]["disallowed_actions"])
        self.assertEqual(
            [artifact["role"] for artifact in gates[0]["source_artifacts"]],
            [artifact["role"] for artifact in gates[1]["source_artifacts"]],
        )
        self.assertEqual(checklists[0], checklists[1])


if __name__ == "__main__":
    unittest.main()
