import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.assets.local_asset_next_bounded_smoke_iteration_runner_admission import (
    REQUIRED_LOCAL_ASSET_BOUNDED_SMOKE_RUNNER_ADMISSION_ACKNOWLEDGEMENT_PHRASE,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture
from tests.tracer_bullet import (
    test_local_asset_next_bounded_smoke_iteration_execution_request as request_helpers,
)


ACK_PHRASE = (
    REQUIRED_LOCAL_ASSET_BOUNDED_SMOKE_RUNNER_ADMISSION_ACKNOWLEDGEMENT_PHRASE
)
ACK_SHA256 = hashlib.sha256(ACK_PHRASE.encode("utf-8")).hexdigest()
RUNNER_ADMISSION_OUTPUTS = (
    "local_asset_next_bounded_smoke_iteration_runner_admission.json",
    "local_asset_next_bounded_smoke_iteration_runner_admission_manifest.json",
    "local_asset_next_bounded_smoke_iteration_runner_admission_summary.md",
    "local_asset_next_bounded_smoke_iteration_runner_admission_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
RUNNER_ADMISSION_ROLES = (
    "local_asset_next_bounded_smoke_iteration_runner_admission",
    "local_asset_next_bounded_smoke_iteration_runner_admission_manifest",
    "local_asset_next_bounded_smoke_iteration_runner_admission_summary",
    "local_asset_next_bounded_smoke_iteration_runner_admission_checklist",
)
BOUNDARY_FIELDS = (
    "runner_execution_allowed",
    "next_bounded_smoke_iteration_execute_allowed",
    "next_bounded_smoke_iteration_executed",
    "next_iteration_output_dir_created",
    "requested_next_iteration_output_dir_created",
    "candidate_input_path_checked",
    "candidate_input_path_listed",
    "candidate_input_file_read",
    "candidate_input_file_hashing_performed",
    "production_scan_approved",
    "production_promotion_granted",
    "automatic_approval_performed",
    "autonomous_execution_performed",
    "scan_performed",
    "readiness_run_performed",
    "human_smoke_run_performed",
    "smoke_review_packet_run_performed",
    "smoke_promotion_gate_run_performed",
    "bounded_smoke_iteration_performed_by_runner_admission",
    "iteration_review_packet_run_performed",
    "iteration_promotion_gate_run_performed",
    "cycle_contract_run_performed",
    "cycle_human_review_run_performed",
    "next_admission_run_performed",
    "execution_request_run_performed",
    "raw_candidate_content_read",
    "candidate_file_hashing_performed",
    "candidate_path_validation_performed",
    "candidate_path_listing_performed",
    "input_mutation_performed",
    "upstream_output_mutation_performed",
    "file_move_performed",
    "file_rename_performed",
    "file_delete_performed",
    "duplicate_deletion_performed",
    "media_organizer_behavior_performed",
    "output_overwrite_performed",
    "network_access_performed",
    "model_api_called",
    "external_runtime_invoked",
    "production_scan_performed",
    "production_scan_recommended",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests(unittest.TestCase):
    make_candidate = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.make_candidate
    )
    run_readiness = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.run_readiness
    )
    run_human_smoke = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.run_human_smoke
    )
    run_smoke_review = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.run_smoke_review
    )
    run_smoke_promotion = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.run_smoke_promotion
    )
    run_iteration = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.run_iteration
    )
    run_iteration_review = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.run_iteration_review
    )
    run_iteration_promotion = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.run_iteration_promotion
    )
    run_cycle_contract = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.run_cycle_contract
    )
    build_full_chain = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.build_full_chain
    )
    run_cycle_human_review = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.run_cycle_human_review
    )
    build_ready_cycle_human_review = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.build_ready_cycle_human_review
    )
    run_admission = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.run_admission
    )
    build_ready_admission = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.build_ready_admission
    )
    build_non_ready_admission = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.build_non_ready_admission
    )
    run_execution_request = (
        request_helpers.LocalAssetNextBoundedSmokeIterationExecutionRequestTests.run_execution_request
    )

    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def build_ready_request(self, root, *, requested_max_files=5):
        admission_output = self.build_ready_admission(root)
        request_output = Path(root) / "execution-request"
        request_output.mkdir()
        request_exit, _request_payload = self.run_execution_request(
            admission_output,
            request_output,
            requested_max_files=requested_max_files,
        )
        self.assertEqual(request_exit, 0)
        return request_output

    def run_runner_admission(
        self,
        execution_request_output,
        output_dir,
        *,
        runner_admission_id="runner-admission-1",
        runner_operator_id="runner-operator-1",
        runner_operator_acknowledgement_phrase=ACK_PHRASE,
        admitted_runner_id="bounded-smoke-runner",
        admitted_runner_version="1.0.0",
        admitted_max_files=5,
        admitted_max_total_bytes=4096,
        admitted_max_depth=2,
        project_id="cycle-test",
        operator_notes="admit runner consumption only",
        runner_environment_label="local-fixture",
    ):
        args = [
            "launch-local-asset-next-bounded-smoke-iteration-runner-admission",
            "--execution-request-output-dir",
            Path(execution_request_output).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--runner-admission-id",
            runner_admission_id,
            "--runner-operator-id",
            runner_operator_id,
            "--runner-operator-acknowledgement-phrase",
            runner_operator_acknowledgement_phrase,
            "--admitted-runner-id",
            admitted_runner_id,
            "--admitted-runner-version",
            admitted_runner_version,
            "--admitted-max-files",
            str(admitted_max_files),
            "--admitted-max-total-bytes",
            str(admitted_max_total_bytes),
            "--admitted-max-depth",
            str(admitted_max_depth),
        ]
        if project_id is not None:
            args.extend(["--project-id", project_id])
        if operator_notes is not None:
            args.extend(["--operator-notes", operator_notes])
        if runner_environment_label is not None:
            args.extend(["--runner-environment-label", runner_environment_label])
        return self.run_cli(args)

    def write_graph(self, graph_path, nodes, *, graph_id="runner-admission-graph"):
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

    def runner_admission_node(self, *, node_id, request_output, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": (
                "launch_local_asset_next_bounded_smoke_iteration_runner_admission"
            ),
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "execution_request_output_dir": Path(request_output).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "project_id": "cycle-test",
                "runner_admission_id": "graph-runner-admission-1",
                "runner_operator_id": "runner-operator-1",
                "runner_operator_acknowledgement_phrase": ACK_PHRASE,
                "admitted_runner_id": "bounded-smoke-runner",
                "admitted_runner_version": "1.0.0",
                "admitted_max_files": 5,
                "admitted_max_total_bytes": 4096,
                "admitted_max_depth": 2,
                "operator_notes": "admit runner consumption only",
                "runner_environment_label": "local-fixture",
            },
        }

    def rewrite_request_manifest_hash(self, request_output):
        request_path = (
            Path(request_output)
            / "local_asset_next_bounded_smoke_iteration_execution_request.json"
        )
        manifest_path = (
            Path(request_output)
            / "local_asset_next_bounded_smoke_iteration_execution_request_manifest.json"
        )
        manifest = read_json(manifest_path)
        manifest["request_sha256"] = sha256_file(request_path)
        write_json(manifest_path, manifest)

    def test_full_chain_writes_runner_admission_outputs_and_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            runner_output = root / "runner-admission"
            runner_output.mkdir()

            exit_code, payload = self.run_runner_admission(
                request_output,
                runner_output,
            )
            artifact_index = read_json(runner_output / "artifact_index.json")
            roles = {entry["artifact_role"] for entry in artifact_index["entries"]}

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in RUNNER_ADMISSION_OUTPUTS:
                self.assertTrue((runner_output / filename).exists(), filename)
            self.assertEqual(roles, set(RUNNER_ADMISSION_ROLES))

    def test_ready_execution_request_admits_runner_consumption_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            runner_output = root / "runner-admission"
            runner_output.mkdir()

            exit_code, payload = self.run_runner_admission(
                request_output,
                runner_output,
            )
            admission = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, admission):
                self.assertEqual(
                    payload_like["admission_status"],
                    "next_bounded_smoke_iteration_runner_admission_ready",
                )
                self.assertEqual(
                    payload_like["admission_decision"],
                    "admit_runner_to_consume_future_execution_request",
                )
                self.assertEqual(
                    payload_like["next_allowed_action"],
                    "await_separate_bounded_smoke_iteration_runner_execution",
                )
                self.assertTrue(payload_like["runner_consume_request_admitted"])
                self.assertFalse(payload_like["runner_execution_allowed"])
                self.assertFalse(
                    payload_like["next_bounded_smoke_iteration_execute_allowed"]
                )
                self.assertFalse(
                    payload_like["next_bounded_smoke_iteration_executed"]
                )
                self.assertFalse(payload_like["next_iteration_output_dir_created"])
                self.assertFalse(
                    payload_like["requested_next_iteration_output_dir_created"]
                )
                self.assertFalse(payload_like["candidate_input_path_checked"])
                self.assertFalse(payload_like["candidate_input_path_listed"])
                self.assertFalse(payload_like["candidate_input_file_read"])
                self.assertFalse(
                    payload_like["candidate_input_file_hashing_performed"]
                )
                self.assertFalse(payload_like["production_scan_approved"])
                self.assertFalse(payload_like["production_promotion_granted"])

    def test_plaintext_runner_acknowledgement_never_persists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            runner_output = root / "runner-admission"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner_admission(
                request_output,
                runner_output,
            )
            combined = ""
            for filename in RUNNER_ADMISSION_OUTPUTS:
                combined += (runner_output / filename).read_text(encoding="utf-8")
            admission = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )

            self.assertEqual(exit_code, 0)
            self.assertNotIn(ACK_PHRASE, combined)
            self.assertEqual(
                admission["runner_operator_acknowledgement_phrase_sha256"],
                ACK_SHA256,
            )
            self.assertIn(ACK_SHA256, combined)

    def test_blocks_invalid_runner_acknowledgement(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            runner_output = root / "runner-admission"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner_admission(
                request_output,
                runner_output,
                runner_operator_acknowledgement_phrase="wrong phrase",
            )
            admission = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_invalid_runner_acknowledgement",
            )
            self.assertFalse(admission["runner_consume_request_admitted"])

    def test_blocks_invalid_runner_metadata(self):
        invalid_cases = (
            ("runner_admission_id", {"runner_admission_id": ""}),
            ("runner_operator_id", {"runner_operator_id": ""}),
            ("admitted_runner_id", {"admitted_runner_id": ""}),
            ("admitted_runner_version", {"admitted_runner_version": ""}),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            for label, kwargs in invalid_cases:
                with self.subTest(label=label):
                    runner_output = root / ("runner-admission-" + label)
                    runner_output.mkdir()
                    exit_code, _payload = self.run_runner_admission(
                        request_output,
                        runner_output,
                        **kwargs,
                    )
                    admission = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
                    )
                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        admission["admission_status"],
                        "blocked_invalid_runner_metadata",
                    )

    def test_blocks_invalid_admitted_limits(self):
        invalid_cases = (
            ("admitted_max_files", {"admitted_max_files": 0}),
            ("admitted_max_total_bytes", {"admitted_max_total_bytes": 0}),
            ("admitted_max_depth", {"admitted_max_depth": -1}),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            for label, kwargs in invalid_cases:
                with self.subTest(label=label):
                    runner_output = root / ("runner-admission-" + label)
                    runner_output.mkdir()
                    exit_code, _payload = self.run_runner_admission(
                        request_output,
                        runner_output,
                        **kwargs,
                    )
                    admission = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
                    )
                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        admission["admission_status"],
                        "blocked_invalid_admitted_limits",
                    )

    def test_blocks_admitted_limits_exceeding_request(self):
        invalid_cases = (
            ("admitted_max_files", {"admitted_max_files": 6}),
            ("admitted_max_total_bytes", {"admitted_max_total_bytes": 4097}),
            ("admitted_max_depth", {"admitted_max_depth": 3}),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            for label, kwargs in invalid_cases:
                with self.subTest(label=label):
                    runner_output = root / ("runner-admission-" + label)
                    runner_output.mkdir()
                    exit_code, _payload = self.run_runner_admission(
                        request_output,
                        runner_output,
                        **kwargs,
                    )
                    admission = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
                    )
                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        admission["admission_status"],
                        "blocked_limits_exceed_request",
                    )

    def test_blocks_missing_required_execution_request_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            (
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            ).unlink()
            runner_output = root / "runner-admission"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner_admission(
                request_output,
                runner_output,
            )
            admission = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_missing_required_artifacts",
            )

    def test_blocks_untrusted_execution_request_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            manifest_path = (
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request_manifest.json"
            )
            manifest = read_json(manifest_path)
            manifest["request_sha256"] = "0" * 64
            write_json(manifest_path, manifest)
            runner_output = root / "runner-admission"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner_admission(
                request_output,
                runner_output,
            )
            admission = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(admission["admission_status"], "blocked_untrusted_artifacts")

    def test_blocks_if_execution_request_not_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            next_admission_output = self.build_non_ready_admission(root)
            request_output = root / "execution-request"
            request_output.mkdir()
            request_exit, _request_payload = self.run_execution_request(
                next_admission_output,
                request_output,
            )
            runner_output = root / "runner-admission"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner_admission(
                request_output,
                runner_output,
            )
            admission = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )

            self.assertEqual(request_exit, 1)
            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_execution_request_not_ready",
            )

    def test_blocks_if_future_request_not_created(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            request_path = (
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )
            request = read_json(request_path)
            request["future_execution_request_created"] = False
            write_json(request_path, request)
            self.rewrite_request_manifest_hash(request_output)
            runner_output = root / "runner-admission"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner_admission(
                request_output,
                runner_output,
            )
            admission = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_future_request_not_created",
            )

    def test_blocks_if_execution_already_allowed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            request_path = (
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )
            request = read_json(request_path)
            request["next_bounded_smoke_iteration_execute_allowed"] = True
            write_json(request_path, request)
            self.rewrite_request_manifest_hash(request_output)
            runner_output = root / "runner-admission"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner_admission(
                request_output,
                runner_output,
            )
            admission = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_execution_already_allowed",
            )

    def test_blocks_if_iteration_already_executed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            request_path = (
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )
            request = read_json(request_path)
            request["next_bounded_smoke_iteration_executed"] = True
            write_json(request_path, request)
            self.rewrite_request_manifest_hash(request_output)
            runner_output = root / "runner-admission"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner_admission(
                request_output,
                runner_output,
            )
            admission = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_iteration_already_executed",
            )

    def test_blocks_if_next_iteration_output_already_created(self):
        cases = (
            "next_iteration_output_dir_created",
            "requested_next_iteration_output_dir_created",
        )
        for field_name in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    request_output = self.build_ready_request(root)
                    request_path = (
                        request_output
                        / "local_asset_next_bounded_smoke_iteration_execution_request.json"
                    )
                    request = read_json(request_path)
                    request[field_name] = True
                    write_json(request_path, request)
                    self.rewrite_request_manifest_hash(request_output)
                    runner_output = root / "runner-admission"
                    runner_output.mkdir()

                    exit_code, _payload = self.run_runner_admission(
                        request_output,
                        runner_output,
                    )
                    admission = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        admission["admission_status"],
                        "blocked_next_iteration_output_already_created",
                    )

    def test_blocks_candidate_path_access_violation(self):
        cases = (
            "candidate_input_path_checked",
            "candidate_input_path_listed",
            "candidate_input_file_read",
            "candidate_input_file_hashing_performed",
        )
        for field_name in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    request_output = self.build_ready_request(root)
                    request_path = (
                        request_output
                        / "local_asset_next_bounded_smoke_iteration_execution_request.json"
                    )
                    request = read_json(request_path)
                    request[field_name] = True
                    write_json(request_path, request)
                    self.rewrite_request_manifest_hash(request_output)
                    runner_output = root / "runner-admission"
                    runner_output.mkdir()

                    exit_code, _payload = self.run_runner_admission(
                        request_output,
                        runner_output,
                    )
                    admission = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        admission["admission_status"],
                        "blocked_candidate_path_access_violation",
                    )

    def test_blocks_production_boundary_violation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            request_path = (
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )
            request = read_json(request_path)
            request["production_scan_approved"] = True
            write_json(request_path, request)
            self.rewrite_request_manifest_hash(request_output)
            runner_output = root / "runner-admission"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner_admission(
                request_output,
                runner_output,
            )
            admission = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_production_boundary_violation",
            )

    def test_blocks_malformed_execution_request_record(self):
        cases = ("wrong_next_allowed_action", "missing_disallowed_action")
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    request_output = self.build_ready_request(root)
                    request_path = (
                        request_output
                        / "local_asset_next_bounded_smoke_iteration_execution_request.json"
                    )
                    request = read_json(request_path)
                    if case == "wrong_next_allowed_action":
                        request["next_allowed_action"] = "execute_now"
                    else:
                        request["disallowed_actions"] = [
                            action
                            for action in request["disallowed_actions"]
                            if action != "production_scan"
                        ]
                    write_json(request_path, request)
                    self.rewrite_request_manifest_hash(request_output)
                    runner_output = root / "runner-admission"
                    runner_output.mkdir()

                    exit_code, _payload = self.run_runner_admission(
                        request_output,
                        runner_output,
                    )
                    admission = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertIn(
                        admission["admission_status"],
                        (
                            "blocked_invalid_execution_request_record",
                            "blocked_production_boundary_violation",
                        ),
                    )

    def test_fail_closed_on_existing_outputs(self):
        for filename in RUNNER_ADMISSION_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    request_output = self.build_ready_request(root)
                    runner_output = root / "runner-admission"
                    runner_output.mkdir()
                    preexisting = runner_output / filename
                    preexisting.write_text("preexisting\n", encoding="utf-8")

                    exit_code, payload = self.run_runner_admission(
                        request_output,
                        runner_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertEqual(
                        preexisting.read_text(encoding="utf-8"),
                        "preexisting\n",
                    )
                    for other_filename in RUNNER_ADMISSION_OUTPUTS:
                        if other_filename != filename:
                            self.assertFalse(
                                (runner_output / other_filename).exists()
                            )

    def test_missing_output_dir_structured_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            runner_output = root / "missing-runner-admission"

            exit_code, payload = self.run_runner_admission(
                request_output,
                runner_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["artifacts_written"])
            self.assertFalse(runner_output.exists())

    def test_input_output_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            cases = [
                (request_output, request_output),
                (request_output, request_output / "nested-runner-admission"),
            ]
            cases[1][1].mkdir()
            parent_output = root / "parent-runner-admission"
            parent_output.mkdir()
            nested_request = parent_output / "nested-execution-request"
            nested_request.mkdir()
            cases.append((nested_request, parent_output))

            for input_dir, runner_output in cases:
                with self.subTest(runner_output=runner_output):
                    exit_code, payload = self.run_runner_admission(
                        input_dir,
                        runner_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertFalse(
                        (
                            runner_output
                            / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
                        ).exists()
                    )

    def test_task_graph_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            runner_output = root / "runner-admission"
            runner_output.mkdir()
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.runner_admission_node(
                        node_id="runner-admission",
                        request_output=request_output,
                        output_dir=runner_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "runner-admission"
            }

            self.assertTrue(result.success)
            for role in RUNNER_ADMISSION_ROLES:
                self.assertIn(role, roles)

    def test_no_scope_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            runner_output = root / "runner-admission"
            runner_output.mkdir()

            exit_code, payload = self.run_runner_admission(
                request_output,
                runner_output,
            )
            admission = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )
            manifest = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission_manifest.json"
            )
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            graph_runner_output = root / "graph-runner-admission"
            graph_runner_output.mkdir()
            self.write_graph(
                graph_path,
                [
                    self.runner_admission_node(
                        node_id="runner-admission",
                        request_output=request_output,
                        output_dir=graph_runner_output,
                    )
                ],
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            execution = read_json(graph_result.execution_manifest_path)
            node = execution["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, admission, manifest, node):
                self.assertTrue(payload_like["required_human_approval"])
                self.assertTrue(payload_like["required_human_review"])
                for field in BOUNDARY_FIELDS:
                    self.assertFalse(payload_like[field], field)

    def test_deterministic_stable_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            request_output = self.build_ready_request(root)
            first_output = root / "runner-admission-1"
            second_output = root / "runner-admission-2"
            first_output.mkdir()
            second_output.mkdir()

            first_exit, _first_payload = self.run_runner_admission(
                request_output,
                first_output,
                runner_admission_id="same-runner-admission",
            )
            second_exit, _second_payload = self.run_runner_admission(
                request_output,
                second_output,
                runner_admission_id="same-runner-admission",
            )
            first_admission = read_json(
                first_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )
            second_admission = read_json(
                second_output
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )

            self.assertEqual(first_exit, 0)
            self.assertEqual(second_exit, 0)
            for field in (
                "admission_status",
                "admission_decision",
                "next_allowed_action",
                "disallowed_actions",
                "requested_limits",
                "admitted_limits",
            ):
                self.assertEqual(first_admission[field], second_admission[field])
            self.assertEqual(
                [
                    item["artifact_role"]
                    for item in first_admission["source_artifacts"]
                ],
                [
                    item["artifact_role"]
                    for item in second_admission["source_artifacts"]
                ],
            )
            self.assertEqual(
                first_admission["runner_admission_checklist"],
                second_admission["runner_admission_checklist"],
            )


if __name__ == "__main__":
    unittest.main()
