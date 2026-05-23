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
    test_local_asset_next_bounded_smoke_iteration_runner as runner_helpers,
)


REVIEW_OUTPUTS = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet.json",
    "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest.json",
    "local_asset_next_bounded_smoke_iteration_run_review_packet_summary.md",
    "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
REVIEW_ROLES = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet",
    "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest",
    "local_asset_next_bounded_smoke_iteration_run_review_packet_summary",
    "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist",
)
NO_SCOPE_FIELDS = (
    "promotion_approved",
    "production_scan_approved",
    "production_promotion_granted",
    "automatic_approval_performed",
    "autonomous_execution_performed",
    "runner_reexecution_performed",
    "candidate_input_path_checked_by_review",
    "candidate_input_path_listed_by_review",
    "candidate_input_file_read_by_review",
    "candidate_input_file_hashing_performed_by_review",
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


class LocalAssetNextBoundedSmokeIterationRunReviewPacketTests(unittest.TestCase):
    make_candidate = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.make_candidate
    )
    run_readiness = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_readiness
    )
    run_human_smoke = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_human_smoke
    )
    run_smoke_review = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_smoke_review
    )
    run_smoke_promotion = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_smoke_promotion
    )
    run_iteration = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_iteration
    )
    run_iteration_review = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_iteration_review
    )
    run_iteration_promotion = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_iteration_promotion
    )
    run_cycle_contract = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_cycle_contract
    )
    build_full_chain = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.build_full_chain
    )
    run_cycle_human_review = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_cycle_human_review
    )
    build_ready_cycle_human_review = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.build_ready_cycle_human_review
    )
    run_admission = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_admission
    )
    build_ready_admission = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.build_ready_admission
    )
    build_non_ready_admission = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.build_non_ready_admission
    )
    run_execution_request = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_execution_request
    )
    build_ready_request = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.build_ready_request
    )
    run_runner_admission = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_runner_admission
    )
    build_ready_runner_admission = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.build_ready_runner_admission
    )
    make_future_candidate = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.make_future_candidate
    )
    make_actual_output = (
        runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.make_actual_output
    )
    run_runner = runner_helpers.LocalAssetNextBoundedSmokeIterationRunnerTests.run_runner

    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def build_ready_runner(self, root):
        runner_admission = self.build_ready_runner_admission(root)
        self.make_future_candidate(runner_admission)
        actual = self.make_actual_output(runner_admission)
        runner_output = Path(root) / "runner"
        runner_output.mkdir()
        exit_code, _payload = self.run_runner(
            runner_admission,
            runner_output,
            actual,
        )
        self.assertEqual(exit_code, 0)
        return runner_output, actual

    def run_review_packet(
        self,
        runner_output,
        actual,
        output_dir,
        *,
        review_packet_id="run-review-1",
        reviewer_id="reviewer-1",
        project_id="cycle-test",
        operator_notes="review generated runner and run artifacts",
    ):
        args = [
            "launch-local-asset-next-bounded-smoke-iteration-run-review-packet",
            "--runner-output-dir",
            Path(runner_output).as_posix(),
            "--actual-next-iteration-output-dir",
            Path(actual).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--review-packet-id",
            review_packet_id,
        ]
        if project_id is not None:
            args.extend(["--project-id", project_id])
        if reviewer_id is not None:
            args.extend(["--reviewer-id", reviewer_id])
        if operator_notes is not None:
            args.extend(["--operator-notes", operator_notes])
        return self.run_cli(args)

    def rewrite_runner_manifest_hash(self, runner_output):
        runner_path = (
            Path(runner_output)
            / "local_asset_next_bounded_smoke_iteration_runner.json"
        )
        manifest_path = (
            Path(runner_output)
            / "local_asset_next_bounded_smoke_iteration_runner_manifest.json"
        )
        manifest = read_json(manifest_path)
        manifest["runner_sha256"] = sha256_file(runner_path)
        write_json(manifest_path, manifest)

    def rewrite_run_manifest_hashes(self, actual):
        actual = Path(actual)
        manifest_path = (
            actual / "local_asset_next_bounded_smoke_iteration_run_manifest.json"
        )
        manifest = read_json(manifest_path)
        manifest["run_sha256"] = sha256_file(
            actual / "local_asset_next_bounded_smoke_iteration_run.json"
        )
        manifest["candidate_manifest_sha256"] = sha256_file(
            actual
            / "local_asset_next_bounded_smoke_iteration_candidate_manifest.json"
        )
        write_json(manifest_path, manifest)

    def review_packet_node(self, *, node_id, runner_output, actual, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": (
                "launch_local_asset_next_bounded_smoke_iteration_run_review_packet"
            ),
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "runner_output_dir": Path(runner_output).as_posix(),
                "actual_next_iteration_output_dir": Path(actual).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "review_packet_id": "graph-run-review-1",
                "project_id": "cycle-test",
                "reviewer_id": "reviewer-1",
                "operator_notes": "review generated runner and run artifacts",
            },
        }

    def write_graph(self, graph_path, nodes):
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "run-review-graph",
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": nodes,
            },
        )

    def assert_review_artifacts_absent(self, output_dir):
        for filename in REVIEW_OUTPUTS:
            self.assertFalse((Path(output_dir) / filename).exists(), filename)

    def assert_no_scope_false(self, payload_like):
        for field_name in NO_SCOPE_FIELDS:
            self.assertFalse(payload_like[field_name], field_name)

    def test_full_chain_writes_review_packet_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_output, actual = self.build_ready_runner(root)
            review = root / "review"
            review.mkdir()

            exit_code, payload = self.run_review_packet(runner_output, actual, review)
            index = read_json(review / "artifact_index.json")
            roles = {entry["artifact_role"] for entry in index["entries"]}

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in REVIEW_OUTPUTS:
                self.assertTrue((review / filename).exists(), filename)
            self.assertEqual(roles, set(REVIEW_ROLES))

    def test_ready_runner_produces_review_packet_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_output, actual = self.build_ready_runner(root)
            review = root / "review"
            review.mkdir()

            exit_code, payload = self.run_review_packet(runner_output, actual, review)
            packet = read_json(
                review
                / "local_asset_next_bounded_smoke_iteration_run_review_packet.json"
            )

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, packet):
                self.assertEqual(
                    payload_like["review_status"],
                    "next_bounded_smoke_iteration_run_review_packet_ready",
                )
                self.assertEqual(
                    payload_like["review_decision"],
                    "package_next_bounded_smoke_iteration_run_for_promotion_gate_review",
                )
                self.assertEqual(
                    payload_like["next_allowed_action"],
                    "run_next_bounded_smoke_iteration_run_promotion_gate",
                )
                self.assertTrue(payload_like["review_packet_created"])
                self.assert_no_scope_false(payload_like)

    def test_review_packet_does_not_touch_live_candidate_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_output, actual = self.build_ready_runner(root)
            runner = read_json(
                runner_output / "local_asset_next_bounded_smoke_iteration_runner.json"
            )
            candidate = Path(runner["requested_candidate_input_dir"])
            shutil.rmtree(candidate)
            os.symlink("/definitely/not-read-by-review", candidate)
            review = root / "review"
            review.mkdir()

            exit_code, payload = self.run_review_packet(runner_output, actual, review)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                payload["review_status"],
                "next_bounded_smoke_iteration_run_review_packet_ready",
            )
            self.assertFalse(payload["candidate_input_path_checked_by_review"])
            self.assertFalse(payload["candidate_input_path_listed_by_review"])
            self.assertFalse(payload["candidate_input_file_read_by_review"])
            self.assertFalse(
                payload["candidate_input_file_hashing_performed_by_review"]
            )

    def test_blocks_missing_required_runner_artifacts(self):
        for filename in (
            "local_asset_next_bounded_smoke_iteration_runner.json",
            "local_asset_next_bounded_smoke_iteration_runner_manifest.json",
        ):
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    (runner_output / filename).unlink()
                    review = root / "review"
                    review.mkdir()

                    exit_code, payload = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["review_status"],
                        "blocked_missing_required_artifacts",
                    )

    def test_blocks_untrusted_runner_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_output, actual = self.build_ready_runner(root)
            manifest_path = (
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_manifest.json"
            )
            manifest = read_json(manifest_path)
            manifest["runner_sha256"] = "0" * 64
            write_json(manifest_path, manifest)
            review = root / "review"
            review.mkdir()

            exit_code, payload = self.run_review_packet(runner_output, actual, review)

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["review_status"], "blocked_untrusted_artifacts")

    def test_blocks_missing_required_actual_iteration_artifacts(self):
        for filename in (
            "local_asset_next_bounded_smoke_iteration_run.json",
            "local_asset_next_bounded_smoke_iteration_run_manifest.json",
            "local_asset_next_bounded_smoke_iteration_candidate_manifest.json",
            "artifact_index.json",
        ):
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    (actual / filename).unlink()
                    review = root / "review"
                    review.mkdir()

                    exit_code, payload = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["review_status"],
                        "blocked_missing_required_artifacts",
                    )

    def test_blocks_untrusted_actual_iteration_artifacts(self):
        cases = (
            ("run_sha256", "local_asset_next_bounded_smoke_iteration_run_manifest.json"),
            (
                "candidate_manifest_sha256",
                "local_asset_next_bounded_smoke_iteration_run_manifest.json",
            ),
            ("artifact_index_sha256", "artifact_index_manifest.json"),
        )
        for hash_field, filename in cases:
            with self.subTest(hash_field=hash_field):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    manifest_path = actual / filename
                    manifest = read_json(manifest_path)
                    manifest[hash_field] = "0" * 64
                    write_json(manifest_path, manifest)
                    review = root / "review"
                    review.mkdir()

                    exit_code, payload = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["review_status"],
                        "blocked_untrusted_artifacts",
                    )

    def test_blocks_runner_not_completed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_output, actual = self.build_ready_runner(root)
            runner_path = (
                runner_output / "local_asset_next_bounded_smoke_iteration_runner.json"
            )
            runner = read_json(runner_path)
            runner["runner_status"] = "blocked_not_done"
            write_json(runner_path, runner)
            self.rewrite_runner_manifest_hash(runner_output)
            review = root / "review"
            review.mkdir()

            exit_code, payload = self.run_review_packet(runner_output, actual, review)

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["review_status"], "blocked_runner_not_completed")

    def test_blocks_invalid_actual_run_record(self):
        cases = (
            ("next_allowed_action", "wrong_action"),
            ("runner_execution_performed", False),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    run_path = (
                        actual / "local_asset_next_bounded_smoke_iteration_run.json"
                    )
                    run = read_json(run_path)
                    run[field_name] = value
                    write_json(run_path, run)
                    self.rewrite_run_manifest_hashes(actual)
                    review = root / "review"
                    review.mkdir()

                    exit_code, payload = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["review_status"],
                        "blocked_invalid_actual_run_record",
                    )

    def test_blocks_invalid_candidate_manifest(self):
        cases = (
            ("candidate_limit_enforced", False),
            ("symlink_policy", "follow"),
            ("candidate_symlinks_detected", ["link"]),
            ("record_raw_content_copied", True),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    candidate_path = (
                        actual
                        / "local_asset_next_bounded_smoke_iteration_candidate_manifest.json"
                    )
                    candidate = read_json(candidate_path)
                    if field_name == "record_raw_content_copied":
                        candidate["bounded_file_records"][0][
                            "raw_content_copied"
                        ] = value
                    else:
                        candidate[field_name] = value
                    write_json(candidate_path, candidate)
                    self.rewrite_run_manifest_hashes(actual)
                    review = root / "review"
                    review.mkdir()

                    exit_code, payload = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["review_status"],
                        "blocked_invalid_candidate_manifest",
                    )

    def test_blocks_cross_artifact_inconsistency(self):
        cases = (
            ("runner_execution_id", "runner"),
            ("candidate_file_count", "run"),
            ("candidate_total_bytes", "run"),
            ("bounded_file_records", "run"),
            ("actual_next_iteration_output_dir", "run"),
        )
        for field_name, target in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    if target == "runner":
                        path = (
                            runner_output
                            / "local_asset_next_bounded_smoke_iteration_runner.json"
                        )
                        payload = read_json(path)
                        payload[field_name] = "different-runner-execution"
                        write_json(path, payload)
                        self.rewrite_runner_manifest_hash(runner_output)
                    elif target == "run":
                        path = (
                            actual
                            / "local_asset_next_bounded_smoke_iteration_run.json"
                        )
                        payload = read_json(path)
                        payload[field_name] = (
                            "/tmp/different-output"
                            if field_name == "actual_next_iteration_output_dir"
                            else list(reversed(payload[field_name]))
                            if field_name == "bounded_file_records"
                            else payload[field_name] + 1
                        )
                        write_json(path, payload)
                        self.rewrite_run_manifest_hashes(actual)
                    else:
                        path = (
                            actual
                            / "local_asset_next_bounded_smoke_iteration_candidate_manifest.json"
                        )
                        payload = read_json(path)
                        payload[field_name] = list(reversed(payload[field_name]))
                        write_json(path, payload)
                        self.rewrite_run_manifest_hashes(actual)
                    review = root / "review"
                    review.mkdir()

                    exit_code, result = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        result["review_status"],
                        "blocked_cross_artifact_inconsistency",
                    )

    def test_blocks_source_boundary_violation(self):
        cases = (
            ("production_scan_approved", "runner"),
            ("production_promotion_granted", "run"),
            ("file_delete_performed", "runner"),
        )
        for field_name, target in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    if target == "runner":
                        path = (
                            runner_output
                            / "local_asset_next_bounded_smoke_iteration_runner.json"
                        )
                        payload = read_json(path)
                        payload[field_name] = True
                        write_json(path, payload)
                        self.rewrite_runner_manifest_hash(runner_output)
                    else:
                        path = (
                            actual
                            / "local_asset_next_bounded_smoke_iteration_run.json"
                        )
                        payload = read_json(path)
                        payload[field_name] = True
                        write_json(path, payload)
                        self.rewrite_run_manifest_hashes(actual)
                    review = root / "review"
                    review.mkdir()

                    exit_code, result = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        result["review_status"],
                        "blocked_source_boundary_violation",
                    )

    def test_blocks_missing_runner_boundary_booleans(self):
        fields = (
            "production_scan_approved",
            "file_delete_performed",
            "network_access_performed",
            "required_human_approval",
        )
        for field_name in fields:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    runner_path = (
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner.json"
                    )
                    runner = read_json(runner_path)
                    runner.pop(field_name, None)
                    write_json(runner_path, runner)
                    self.rewrite_runner_manifest_hash(runner_output)
                    review = root / "review"
                    review.mkdir()

                    exit_code, payload = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["review_status"],
                        "blocked_source_boundary_violation",
                    )
                    self.assertTrue(payload["review_packet_created"])
                    self.assertFalse(payload["candidate_input_path_checked_by_review"])
                    self.assertFalse(payload["runner_reexecution_performed"])

    def test_blocks_non_boolean_runner_boundary_booleans(self):
        cases = (
            ("production_scan_approved", "false"),
            ("file_delete_performed", "false"),
            ("model_api_called", "false"),
            ("required_human_review", "true"),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    runner_path = (
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner.json"
                    )
                    runner = read_json(runner_path)
                    runner[field_name] = value
                    write_json(runner_path, runner)
                    self.rewrite_runner_manifest_hash(runner_output)
                    review = root / "review"
                    review.mkdir()

                    exit_code, payload = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["review_status"],
                        "blocked_source_boundary_violation",
                    )
                    self.assertTrue(payload["review_packet_created"])
                    self.assertFalse(payload["candidate_input_file_read_by_review"])
                    self.assertFalse(payload["runner_reexecution_performed"])

    def test_blocks_missing_actual_run_boundary_booleans(self):
        fields = (
            "production_promotion_granted",
            "file_move_performed",
            "external_runtime_invoked",
            "required_human_approval",
        )
        for field_name in fields:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    run_path = actual / "local_asset_next_bounded_smoke_iteration_run.json"
                    run = read_json(run_path)
                    run.pop(field_name, None)
                    write_json(run_path, run)
                    self.rewrite_run_manifest_hashes(actual)
                    review = root / "review"
                    review.mkdir()

                    exit_code, payload = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["review_status"],
                        "blocked_source_boundary_violation",
                    )
                    self.assertTrue(payload["review_packet_created"])
                    self.assertFalse(payload["candidate_input_path_listed_by_review"])
                    self.assertFalse(payload["runner_reexecution_performed"])

    def test_blocks_non_boolean_actual_run_boundary_booleans(self):
        cases = (
            ("production_promotion_granted", "false"),
            ("file_move_performed", "false"),
            ("external_runtime_invoked", "false"),
            ("required_human_review", "true"),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    run_path = actual / "local_asset_next_bounded_smoke_iteration_run.json"
                    run = read_json(run_path)
                    run[field_name] = value
                    write_json(run_path, run)
                    self.rewrite_run_manifest_hashes(actual)
                    review = root / "review"
                    review.mkdir()

                    exit_code, payload = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["review_status"],
                        "blocked_source_boundary_violation",
                    )
                    self.assertTrue(payload["review_packet_created"])
                    self.assertFalse(
                        payload[
                            "candidate_input_file_hashing_performed_by_review"
                        ]
                    )
                    self.assertFalse(payload["runner_reexecution_performed"])

    def test_blocks_invalid_review_packet_metadata(self):
        cases = (
            {"review_packet_id": ""},
            {"reviewer_id": ""},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    review = root / "review"
                    review.mkdir()

                    exit_code, payload = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                        **kwargs,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["review_status"],
                        "blocked_invalid_review_packet_metadata",
                    )

    def test_fails_closed_on_existing_review_packet_outputs(self):
        for filename in REVIEW_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    review = root / "review"
                    review.mkdir()
                    existing = review / filename
                    existing.write_text("existing\n", encoding="utf-8")

                    exit_code, payload = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertEqual(existing.read_text(encoding="utf-8"), "existing\n")
                    for other in REVIEW_OUTPUTS:
                        if other != filename:
                            self.assertFalse((review / other).exists(), other)

    def test_missing_output_dir_structured_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_output, actual = self.build_ready_runner(root)
            review = root / "missing-review"

            exit_code, payload = self.run_review_packet(runner_output, actual, review)

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["artifacts_written"])
            self.assertFalse(review.exists())

    def test_input_output_overlap_rejected(self):
        cases = (
            "output_inside_runner",
            "runner_inside_output",
            "output_inside_actual",
            "actual_inside_output",
            "runner_inside_actual",
        )
        for case_name in cases:
            with self.subTest(case_name=case_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_output, actual = self.build_ready_runner(root)
                    if case_name == "output_inside_runner":
                        review = runner_output / "review"
                        review.mkdir()
                    elif case_name == "runner_inside_output":
                        review = root / "review"
                        review.mkdir()
                        runner_output = review / "runner"
                        runner_output.mkdir()
                    elif case_name == "output_inside_actual":
                        review = actual / "review"
                        review.mkdir()
                    elif case_name == "actual_inside_output":
                        review = root / "review"
                        review.mkdir()
                        actual = review / "actual"
                        actual.mkdir()
                    else:
                        review = root / "review"
                        review.mkdir()
                        actual = root / "actual-overlap"
                        actual.mkdir()
                        runner_output = actual / "runner"
                        runner_output.mkdir()

                    exit_code, payload = self.run_review_packet(
                        runner_output,
                        actual,
                        review,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assert_review_artifacts_absent(review)

    def test_task_graph_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_output, actual = self.build_ready_runner(root)
            review = root / "review"
            review.mkdir()
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.review_packet_node(
                        node_id="review_run",
                        runner_output=runner_output,
                        actual=actual,
                        output_dir=review,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "review_run"
            }

            self.assertTrue(result.success)
            for role in REVIEW_ROLES:
                self.assertIn(role, roles)

    def test_no_scope_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_output, actual = self.build_ready_runner(root)
            review = root / "review"
            review.mkdir()
            exit_code, payload = self.run_review_packet(runner_output, actual, review)
            packet = read_json(
                review
                / "local_asset_next_bounded_smoke_iteration_run_review_packet.json"
            )
            manifest = read_json(
                review
                / "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest.json"
            )
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            graph_review = root / "graph-review"
            graph_review.mkdir()
            self.write_graph(
                graph_path,
                [
                    self.review_packet_node(
                        node_id="review_run",
                        runner_output=runner_output,
                        actual=actual,
                        output_dir=graph_review,
                    )
                ],
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            node = read_json(graph_result.execution_manifest_path)["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, packet, manifest, node):
                self.assert_no_scope_false(payload_like)

    def test_deterministic_stable_fields(self):
        packets = []
        checklists = []
        for index in range(2):
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                runner_output, actual = self.build_ready_runner(root)
                review = root / "review"
                review.mkdir()
                exit_code, _payload = self.run_review_packet(
                    runner_output,
                    actual,
                    review,
                    review_packet_id="stable-review-" + str(index),
                )
                self.assertEqual(exit_code, 0)
                packets.append(
                    read_json(
                        review
                        / "local_asset_next_bounded_smoke_iteration_run_review_packet.json"
                    )
                )
                checklists.append(
                    (
                        review
                        / "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist.md"
                    ).read_text(encoding="utf-8")
                )

        self.assertEqual(packets[0]["review_status"], packets[1]["review_status"])
        self.assertEqual(packets[0]["review_decision"], packets[1]["review_decision"])
        self.assertEqual(
            packets[0]["next_allowed_action"],
            packets[1]["next_allowed_action"],
        )
        self.assertEqual(packets[0]["disallowed_actions"], packets[1]["disallowed_actions"])
        self.assertEqual(
            packets[0]["cross_artifact_checks"],
            packets[1]["cross_artifact_checks"],
        )
        self.assertEqual(
            [artifact["role"] for artifact in packets[0]["source_artifacts"]],
            [artifact["role"] for artifact in packets[1]["source_artifacts"]],
        )
        self.assertEqual(checklists[0], checklists[1])


if __name__ == "__main__":
    unittest.main()
