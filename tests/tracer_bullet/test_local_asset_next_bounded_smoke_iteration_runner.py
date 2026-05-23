import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.assets.local_asset_next_bounded_smoke_iteration_runner import (
    REQUIRED_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ACKNOWLEDGEMENT_PHRASE,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture
from tests.tracer_bullet import (
    test_local_asset_next_bounded_smoke_iteration_runner_admission as admission_helpers,
)


ACK_PHRASE = (
    REQUIRED_LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ACKNOWLEDGEMENT_PHRASE
)
ACK_SHA256 = hashlib.sha256(ACK_PHRASE.encode("utf-8")).hexdigest()
RUNNER_OUTPUTS = (
    "local_asset_next_bounded_smoke_iteration_runner.json",
    "local_asset_next_bounded_smoke_iteration_runner_manifest.json",
    "local_asset_next_bounded_smoke_iteration_runner_summary.md",
    "local_asset_next_bounded_smoke_iteration_runner_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
RUNNER_ROLES = (
    "local_asset_next_bounded_smoke_iteration_runner",
    "local_asset_next_bounded_smoke_iteration_runner_manifest",
    "local_asset_next_bounded_smoke_iteration_runner_summary",
    "local_asset_next_bounded_smoke_iteration_runner_checklist",
)
ITERATION_OUTPUTS = (
    "local_asset_next_bounded_smoke_iteration_run.json",
    "local_asset_next_bounded_smoke_iteration_run_manifest.json",
    "local_asset_next_bounded_smoke_iteration_candidate_manifest.json",
    "local_asset_next_bounded_smoke_iteration_summary.md",
    "local_asset_next_bounded_smoke_iteration_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
ITERATION_ROLES = (
    "local_asset_next_bounded_smoke_iteration_run",
    "local_asset_next_bounded_smoke_iteration_run_manifest",
    "local_asset_next_bounded_smoke_iteration_candidate_manifest",
    "local_asset_next_bounded_smoke_iteration_summary",
    "local_asset_next_bounded_smoke_iteration_checklist",
)
NO_SCOPE_FIELDS = (
    "production_scan_approved",
    "production_promotion_granted",
    "automatic_approval_performed",
    "autonomous_execution_performed",
    "input_mutation_performed",
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


class LocalAssetNextBoundedSmokeIterationRunnerTests(unittest.TestCase):
    make_candidate = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.make_candidate
    )
    run_readiness = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.run_readiness
    )
    run_human_smoke = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.run_human_smoke
    )
    run_smoke_review = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.run_smoke_review
    )
    run_smoke_promotion = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.run_smoke_promotion
    )
    run_iteration = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.run_iteration
    )
    run_iteration_review = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.run_iteration_review
    )
    run_iteration_promotion = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.run_iteration_promotion
    )
    run_cycle_contract = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.run_cycle_contract
    )
    build_full_chain = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.build_full_chain
    )
    run_cycle_human_review = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.run_cycle_human_review
    )
    build_ready_cycle_human_review = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.build_ready_cycle_human_review
    )
    run_admission = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.run_admission
    )
    build_ready_admission = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.build_ready_admission
    )
    build_non_ready_admission = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.build_non_ready_admission
    )
    run_execution_request = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.run_execution_request
    )
    run_runner_admission = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationRunnerAdmissionTests.run_runner_admission
    )

    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def build_ready_request(
        self,
        root,
        *,
        requested_max_files=5,
        requested_max_total_bytes=4096,
        requested_max_depth=2,
    ):
        admission_output = self.build_ready_admission(root)
        request_output = Path(root) / "execution-request"
        request_output.mkdir()
        request_exit, _request_payload = self.run_execution_request(
            admission_output,
            request_output,
            requested_max_files=requested_max_files,
            requested_max_total_bytes=requested_max_total_bytes,
            requested_max_depth=requested_max_depth,
        )
        self.assertEqual(request_exit, 0)
        return request_output

    def build_ready_runner_admission(
        self,
        root,
        *,
        requested_max_files=5,
        requested_max_total_bytes=4096,
        requested_max_depth=2,
        admitted_max_files=5,
        admitted_max_total_bytes=4096,
        admitted_max_depth=2,
    ):
        request_output = self.build_ready_request(
            root,
            requested_max_files=requested_max_files,
            requested_max_total_bytes=requested_max_total_bytes,
            requested_max_depth=requested_max_depth,
        )
        runner_admission_output = Path(root) / "runner-admission"
        runner_admission_output.mkdir()
        admission_exit, _admission_payload = self.run_runner_admission(
            request_output,
            runner_admission_output,
            admitted_max_files=admitted_max_files,
            admitted_max_total_bytes=admitted_max_total_bytes,
            admitted_max_depth=admitted_max_depth,
        )
        self.assertEqual(admission_exit, 0)
        return runner_admission_output

    def run_runner(
        self,
        runner_admission_output,
        runner_output,
        actual_next_iteration_output,
        *,
        runner_execution_id="runner-execution-1",
        runner_operator_id="runner-operator-1",
        runner_execution_acknowledgement_phrase=ACK_PHRASE,
        project_id="cycle-test",
        operator_notes="execute one bounded next iteration",
    ):
        args = [
            "launch-local-asset-next-bounded-smoke-iteration-runner",
            "--runner-admission-output-dir",
            Path(runner_admission_output).as_posix(),
            "--runner-output-dir",
            Path(runner_output).as_posix(),
            "--actual-next-iteration-output-dir",
            Path(actual_next_iteration_output).as_posix(),
            "--runner-execution-id",
            runner_execution_id,
            "--runner-operator-id",
            runner_operator_id,
            "--runner-execution-acknowledgement-phrase",
            runner_execution_acknowledgement_phrase,
        ]
        if project_id is not None:
            args.extend(["--project-id", project_id])
        if operator_notes is not None:
            args.extend(["--operator-notes", operator_notes])
        return self.run_cli(args)

    def make_future_candidate(self, runner_admission_output, *, extra_files=0):
        admission = read_json(
            Path(runner_admission_output)
            / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
        )
        candidate = Path(admission["requested_candidate_input_dir"])
        nested = candidate / "nested"
        nested.mkdir(parents=True)
        (candidate / "plate.png").write_bytes(b"plate")
        (nested / "clip.mov").write_bytes(b"clip")
        for index in range(extra_files):
            (candidate / ("extra-" + str(index) + ".txt")).write_text(
                "x",
                encoding="utf-8",
            )
        return candidate

    def make_actual_output(self, runner_admission_output):
        admission = read_json(
            Path(runner_admission_output)
            / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
        )
        actual = Path(admission["requested_next_iteration_output_dir"])
        actual.mkdir()
        return actual

    def rewrite_runner_admission_manifest_hash(self, runner_admission_output):
        admission_path = (
            Path(runner_admission_output)
            / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
        )
        manifest_path = (
            Path(runner_admission_output)
            / "local_asset_next_bounded_smoke_iteration_runner_admission_manifest.json"
        )
        manifest = read_json(manifest_path)
        manifest["admission_sha256"] = sha256_file(admission_path)
        write_json(manifest_path, manifest)

    def write_graph(self, graph_path, nodes, *, graph_id="runner-graph"):
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

    def runner_node(self, *, node_id, runner_admission_output, runner_output, actual):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": "launch_local_asset_next_bounded_smoke_iteration_runner",
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "runner_admission_output_dir": Path(
                    runner_admission_output
                ).as_posix(),
                "runner_output_dir": Path(runner_output).as_posix(),
                "actual_next_iteration_output_dir": Path(actual).as_posix(),
                "runner_execution_id": "graph-runner-execution-1",
                "runner_operator_id": "runner-operator-1",
                "runner_execution_acknowledgement_phrase": ACK_PHRASE,
                "project_id": "cycle-test",
                "operator_notes": "execute one bounded next iteration",
            },
        }

    def assert_no_actual_iteration_artifacts(self, actual_output):
        for filename in ITERATION_OUTPUTS:
            self.assertFalse((Path(actual_output) / filename).exists(), filename)

    def test_full_chain_executes_next_bounded_smoke_iteration_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            self.make_future_candidate(runner_admission)
            actual = self.make_actual_output(runner_admission)
            runner_output = root / "runner"
            runner_output.mkdir()

            exit_code, payload = self.run_runner(
                runner_admission,
                runner_output,
                actual,
            )
            runner_index = read_json(runner_output / "artifact_index.json")
            actual_index = read_json(actual / "artifact_index.json")
            runner_roles = {entry["artifact_role"] for entry in runner_index["entries"]}
            actual_roles = {entry["artifact_role"] for entry in actual_index["entries"]}

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in RUNNER_OUTPUTS:
                self.assertTrue((runner_output / filename).exists(), filename)
            for filename in ITERATION_OUTPUTS:
                self.assertTrue((actual / filename).exists(), filename)
            self.assertEqual(runner_roles, set(RUNNER_ROLES))
            for role in ITERATION_ROLES:
                self.assertIn(role, actual_roles)

    def test_runner_executes_only_after_trusted_runner_admission(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            self.make_future_candidate(runner_admission)
            actual = self.make_actual_output(runner_admission)
            runner_output = root / "runner"
            runner_output.mkdir()

            exit_code, payload = self.run_runner(
                runner_admission,
                runner_output,
                actual,
            )
            runner = read_json(
                runner_output / "local_asset_next_bounded_smoke_iteration_runner.json"
            )

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, runner):
                self.assertEqual(
                    payload_like["runner_status"],
                    "next_bounded_smoke_iteration_runner_completed",
                )
                self.assertEqual(
                    payload_like["runner_decision"],
                    "executed_bounded_smoke_iteration_under_admitted_limits",
                )
                self.assertEqual(
                    payload_like["next_allowed_action"],
                    "review_next_bounded_smoke_iteration_run",
                )
                self.assertTrue(payload_like["runner_execution_performed"])
                self.assertTrue(
                    payload_like["next_bounded_smoke_iteration_executed"]
                )
                self.assertFalse(payload_like["next_iteration_output_dir_created"])
                self.assertFalse(
                    payload_like["actual_next_iteration_output_dir_created"]
                )
                self.assertFalse(payload_like["production_scan_approved"])
                self.assertFalse(payload_like["production_promotion_granted"])
                self.assertFalse(payload_like["file_move_performed"])
                self.assertFalse(payload_like["file_rename_performed"])
                self.assertFalse(payload_like["file_delete_performed"])

    def test_plaintext_runner_execution_acknowledgement_never_persists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            self.make_future_candidate(runner_admission)
            actual = self.make_actual_output(runner_admission)
            runner_output = root / "runner"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner(
                runner_admission,
                runner_output,
                actual,
            )
            combined = ""
            for filename in RUNNER_OUTPUTS:
                combined += (runner_output / filename).read_text(encoding="utf-8")
            runner = read_json(
                runner_output / "local_asset_next_bounded_smoke_iteration_runner.json"
            )

            self.assertEqual(exit_code, 0)
            self.assertNotIn(ACK_PHRASE, combined)
            self.assertEqual(
                runner["runner_execution_acknowledgement_phrase_sha256"],
                ACK_SHA256,
            )
            self.assertIn(ACK_SHA256, combined)

    def test_blocks_invalid_execution_acknowledgement(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            actual = self.make_actual_output(runner_admission)
            runner_output = root / "runner"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner(
                runner_admission,
                runner_output,
                actual,
                runner_execution_acknowledgement_phrase="wrong phrase",
            )
            runner = read_json(
                runner_output / "local_asset_next_bounded_smoke_iteration_runner.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                runner["runner_status"],
                "blocked_invalid_runner_execution_acknowledgement",
            )
            self.assertFalse(runner["runner_execution_performed"])
            self.assert_no_actual_iteration_artifacts(actual)

    def test_blocks_invalid_runner_metadata(self):
        cases = (
            ("runner_execution_id", {"runner_execution_id": ""}),
            ("runner_operator_id", {"runner_operator_id": ""}),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            actual = self.make_actual_output(runner_admission)
            for label, kwargs in cases:
                with self.subTest(label=label):
                    runner_output = root / ("runner-" + label)
                    runner_output.mkdir()
                    exit_code, _payload = self.run_runner(
                        runner_admission,
                        runner_output,
                        actual,
                        **kwargs,
                    )
                    runner = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner.json"
                    )
                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        runner["runner_status"],
                        "blocked_invalid_runner_metadata",
                    )

    def test_blocks_missing_required_runner_admission_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            (
                runner_admission
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            ).unlink()
            runner_output = root / "runner"
            runner_output.mkdir()
            actual = root / "actual"

            exit_code, payload = self.run_runner(
                runner_admission,
                runner_output,
                actual,
            )
            runner = read_json(
                runner_output / "local_asset_next_bounded_smoke_iteration_runner.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                runner["runner_status"],
                "blocked_missing_required_artifacts",
            )
            self.assertFalse(payload["candidate_input_path_checked"])

    def test_blocks_untrusted_runner_admission_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            manifest_path = (
                runner_admission
                / "local_asset_next_bounded_smoke_iteration_runner_admission_manifest.json"
            )
            manifest = read_json(manifest_path)
            manifest["admission_sha256"] = "0" * 64
            write_json(manifest_path, manifest)
            runner_output = root / "runner"
            runner_output.mkdir()
            actual = root / "actual"

            exit_code, payload = self.run_runner(
                runner_admission,
                runner_output,
                actual,
            )
            runner = read_json(
                runner_output / "local_asset_next_bounded_smoke_iteration_runner.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(runner["runner_status"], "blocked_untrusted_artifacts")
            self.assertFalse(payload["candidate_input_path_checked"])

    def test_blocks_if_runner_admission_not_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            next_admission_output = self.build_non_ready_admission(root)
            request_output = root / "execution-request"
            request_output.mkdir()
            request_exit, _request_payload = self.run_execution_request(
                next_admission_output,
                request_output,
            )
            runner_admission = root / "runner-admission"
            runner_admission.mkdir()
            admission_exit, _payload = self.run_runner_admission(
                request_output,
                runner_admission,
            )
            runner_output = root / "runner"
            runner_output.mkdir()
            actual = root / "actual"

            exit_code, _runner_payload = self.run_runner(
                runner_admission,
                runner_output,
                actual,
            )
            runner = read_json(
                runner_output / "local_asset_next_bounded_smoke_iteration_runner.json"
            )

            self.assertEqual(request_exit, 1)
            self.assertEqual(admission_exit, 1)
            self.assertEqual(exit_code, 1)
            self.assertEqual(
                runner["runner_status"],
                "blocked_runner_admission_not_ready",
            )

    def test_blocks_if_runner_consumption_not_admitted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            admission_path = (
                runner_admission
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )
            admission = read_json(admission_path)
            admission["runner_consume_request_admitted"] = False
            write_json(admission_path, admission)
            self.rewrite_runner_admission_manifest_hash(runner_admission)
            runner_output = root / "runner"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner(
                runner_admission,
                runner_output,
                root / "actual",
            )
            runner = read_json(
                runner_output / "local_asset_next_bounded_smoke_iteration_runner.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                runner["runner_status"],
                "blocked_runner_consumption_not_admitted",
            )

    def test_blocks_if_source_already_allowed_execution(self):
        cases = ("runner_execution_allowed", "next_bounded_smoke_iteration_execute_allowed")
        for field_name in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_admission = self.build_ready_runner_admission(root)
                    admission_path = (
                        runner_admission
                        / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
                    )
                    admission = read_json(admission_path)
                    admission[field_name] = True
                    write_json(admission_path, admission)
                    self.rewrite_runner_admission_manifest_hash(runner_admission)
                    runner_output = root / "runner"
                    runner_output.mkdir()

                    exit_code, _payload = self.run_runner(
                        runner_admission,
                        runner_output,
                        root / "actual",
                    )
                    runner = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner.json"
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        runner["runner_status"],
                        "blocked_execution_already_allowed",
                    )

    def test_blocks_if_source_already_executed_iteration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            admission_path = (
                runner_admission
                / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
            )
            admission = read_json(admission_path)
            admission["next_bounded_smoke_iteration_executed"] = True
            write_json(admission_path, admission)
            self.rewrite_runner_admission_manifest_hash(runner_admission)
            runner_output = root / "runner"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner(
                runner_admission,
                runner_output,
                root / "actual",
            )
            runner = read_json(
                runner_output / "local_asset_next_bounded_smoke_iteration_runner.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                runner["runner_status"],
                "blocked_iteration_already_executed",
            )

    def test_blocks_if_source_next_iteration_output_already_created(self):
        cases = ("next_iteration_output_dir_created", "requested_next_iteration_output_dir_created")
        for field_name in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_admission = self.build_ready_runner_admission(root)
                    admission_path = (
                        runner_admission
                        / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
                    )
                    admission = read_json(admission_path)
                    admission[field_name] = True
                    write_json(admission_path, admission)
                    self.rewrite_runner_admission_manifest_hash(runner_admission)
                    runner_output = root / "runner"
                    runner_output.mkdir()

                    exit_code, _payload = self.run_runner(
                        runner_admission,
                        runner_output,
                        root / "actual",
                    )
                    runner = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner.json"
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        runner["runner_status"],
                        "blocked_next_iteration_output_already_created",
                    )

    def test_blocks_actual_output_dir_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            mismatch = root / "mismatch-actual"
            mismatch.mkdir()
            runner_output = root / "runner"
            runner_output.mkdir()

            exit_code, _payload = self.run_runner(
                runner_admission,
                runner_output,
                mismatch,
            )
            runner = read_json(
                runner_output / "local_asset_next_bounded_smoke_iteration_runner.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                runner["runner_status"],
                "blocked_actual_output_dir_mismatch",
            )
            self.assert_no_actual_iteration_artifacts(mismatch)

    def test_blocks_missing_or_unsafe_actual_output_dir(self):
        cases = ("missing", "symlink")
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_admission = self.build_ready_runner_admission(root)
                    actual = Path(
                        read_json(
                            runner_admission
                            / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
                        )["requested_next_iteration_output_dir"]
                    )
                    if case == "symlink":
                        target = root / "actual-target"
                        target.mkdir()
                        actual.symlink_to(target, target_is_directory=True)
                    runner_output = root / "runner"
                    runner_output.mkdir()

                    exit_code, _payload = self.run_runner(
                        runner_admission,
                        runner_output,
                        actual,
                    )
                    runner = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner.json"
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        runner["runner_status"],
                        "blocked_actual_output_dir_unsafe",
                    )

    def test_blocks_unsafe_candidate_input_dir(self):
        cases = ("missing", "file", "symlink")
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_admission = self.build_ready_runner_admission(root)
                    actual = self.make_actual_output(runner_admission)
                    candidate = Path(
                        read_json(
                            runner_admission
                            / "local_asset_next_bounded_smoke_iteration_runner_admission.json"
                        )["requested_candidate_input_dir"]
                    )
                    if case == "file":
                        candidate.write_text("not a dir", encoding="utf-8")
                    elif case == "symlink":
                        target = root / "candidate-target"
                        target.mkdir()
                        candidate.symlink_to(target, target_is_directory=True)
                    runner_output = root / "runner"
                    runner_output.mkdir()

                    exit_code, _payload = self.run_runner(
                        runner_admission,
                        runner_output,
                        actual,
                    )
                    runner = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner.json"
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        runner["runner_status"],
                        "blocked_candidate_input_dir_unsafe",
                    )

    def test_blocks_candidate_symlink_detected(self):
        cases = ("file", "directory")
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_admission = self.build_ready_runner_admission(root)
                    candidate = self.make_future_candidate(runner_admission)
                    if case == "file":
                        target = candidate / "plate.png"
                        (candidate / "plate-link.png").symlink_to(target)
                    else:
                        target_dir = candidate / "nested"
                        (candidate / "nested-link").symlink_to(
                            target_dir,
                            target_is_directory=True,
                        )
                    actual = self.make_actual_output(runner_admission)
                    runner_output = root / "runner"
                    runner_output.mkdir()

                    exit_code, _payload = self.run_runner(
                        runner_admission,
                        runner_output,
                        actual,
                    )
                    runner = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner.json"
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        runner["runner_status"],
                        "blocked_candidate_symlink_detected",
                    )
                    self.assert_no_actual_iteration_artifacts(actual)

    def test_blocks_candidate_limits_exceeded(self):
        cases = (
            ("files", {"requested_max_files": 1, "admitted_max_files": 1}),
            (
                "bytes",
                {
                    "requested_max_total_bytes": 4,
                    "admitted_max_total_bytes": 4,
                },
            ),
            ("depth", {"requested_max_depth": 0, "admitted_max_depth": 0}),
        )
        for label, kwargs in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_admission = self.build_ready_runner_admission(
                        root,
                        **kwargs,
                    )
                    self.make_future_candidate(runner_admission)
                    actual = self.make_actual_output(runner_admission)
                    runner_output = root / "runner"
                    runner_output.mkdir()

                    exit_code, _payload = self.run_runner(
                        runner_admission,
                        runner_output,
                        actual,
                    )
                    runner = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner.json"
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        runner["runner_status"],
                        "blocked_candidate_limits_exceeded",
                    )
                    self.assert_no_actual_iteration_artifacts(actual)

    def test_fail_closed_on_existing_runner_outputs(self):
        for filename in RUNNER_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_admission = self.build_ready_runner_admission(root)
                    runner_output = root / "runner"
                    runner_output.mkdir()
                    preexisting = runner_output / filename
                    preexisting.write_text("preexisting\n", encoding="utf-8")

                    exit_code, payload = self.run_runner(
                        runner_admission,
                        runner_output,
                        root / "actual",
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertEqual(
                        preexisting.read_text(encoding="utf-8"),
                        "preexisting\n",
                    )
                    for other_filename in RUNNER_OUTPUTS:
                        if other_filename != filename:
                            self.assertFalse((runner_output / other_filename).exists())

    def test_fail_closed_on_existing_actual_iteration_outputs(self):
        for filename in ITERATION_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    runner_admission = self.build_ready_runner_admission(root)
                    self.make_future_candidate(runner_admission)
                    actual = self.make_actual_output(runner_admission)
                    preexisting = actual / filename
                    preexisting.write_text("preexisting\n", encoding="utf-8")
                    runner_output = root / "runner"
                    runner_output.mkdir()

                    exit_code, _payload = self.run_runner(
                        runner_admission,
                        runner_output,
                        actual,
                    )
                    runner = read_json(
                        runner_output
                        / "local_asset_next_bounded_smoke_iteration_runner.json"
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(runner["runner_status"], "blocked_output_collision")
                    self.assertEqual(
                        preexisting.read_text(encoding="utf-8"),
                        "preexisting\n",
                    )

    def test_missing_runner_output_dir_structured_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            runner_output = root / "missing-runner"

            exit_code, payload = self.run_runner(
                runner_admission,
                runner_output,
                root / "actual",
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["artifacts_written"])
            self.assertFalse(runner_output.exists())

    def test_input_output_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            base_actual = self.make_actual_output(runner_admission)
            cases = []
            runner_inside_admission = runner_admission / "nested-runner"
            runner_inside_admission.mkdir()
            cases.append((runner_admission, runner_inside_admission, base_actual))

            parent_runner = root / "parent-runner"
            parent_runner.mkdir()
            nested_admission = parent_runner / "nested-runner-admission"
            nested_admission.mkdir()
            ready_request = self.build_ready_request(root / "second-chain")
            admission_exit, _payload = self.run_runner_admission(
                ready_request,
                nested_admission,
            )
            self.assertEqual(admission_exit, 0)
            cases.append((nested_admission, parent_runner, root / "unused-actual"))

            runner_output = root / "runner-overlap"
            runner_output.mkdir()
            actual_inside_runner = runner_output / "actual"
            actual_inside_runner.mkdir()
            cases.append((runner_admission, runner_output, actual_inside_runner))

            actual_inside_admission = runner_admission / "actual"
            actual_inside_admission.mkdir()
            runner_distinct = root / "runner-distinct"
            runner_distinct.mkdir()
            cases.append((runner_admission, runner_distinct, actual_inside_admission))

            for admission_dir, runner_dir, actual_dir in cases:
                with self.subTest(runner_dir=runner_dir, actual_dir=actual_dir):
                    exit_code, payload = self.run_runner(
                        admission_dir,
                        runner_dir,
                        actual_dir,
                    )
                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertFalse(
                        (
                            runner_dir
                            / "local_asset_next_bounded_smoke_iteration_runner.json"
                        ).exists()
                    )

    def test_task_graph_node_writes_runner_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            self.make_future_candidate(runner_admission)
            actual = self.make_actual_output(runner_admission)
            runner_output = root / "runner"
            runner_output.mkdir()
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.runner_node(
                        node_id="runner",
                        runner_admission_output=runner_admission,
                        runner_output=runner_output,
                        actual=actual,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "runner"
            }

            self.assertTrue(result.success)
            for role in RUNNER_ROLES:
                self.assertIn(role, roles)

    def test_no_scope_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner_admission = self.build_ready_runner_admission(root)
            self.make_future_candidate(runner_admission)
            actual = self.make_actual_output(runner_admission)
            runner_output = root / "runner"
            runner_output.mkdir()

            exit_code, payload = self.run_runner(
                runner_admission,
                runner_output,
                actual,
            )
            runner = read_json(
                runner_output / "local_asset_next_bounded_smoke_iteration_runner.json"
            )
            manifest = read_json(
                runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_manifest.json"
            )
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            graph_chain = root / "graph-chain"
            graph_chain.mkdir()
            graph_admission = self.build_ready_runner_admission(graph_chain)
            self.make_future_candidate(graph_admission)
            graph_actual = self.make_actual_output(graph_admission)
            graph_runner_output = root / "graph-runner"
            graph_runner_output.mkdir()
            self.write_graph(
                graph_path,
                [
                    self.runner_node(
                        node_id="runner",
                        runner_admission_output=graph_admission,
                        runner_output=graph_runner_output,
                        actual=graph_actual,
                    )
                ],
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            execution = read_json(graph_result.execution_manifest_path)
            node = execution["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, runner, manifest, node):
                self.assertTrue(payload_like["required_human_approval"])
                self.assertTrue(payload_like["required_human_review"])
                for field in NO_SCOPE_FIELDS:
                    self.assertFalse(payload_like[field], field)

    def test_deterministic_stable_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first"
            second = root / "second"
            first.mkdir()
            second.mkdir()
            first_admission = self.build_ready_runner_admission(first)
            second_admission = self.build_ready_runner_admission(second)
            self.make_future_candidate(first_admission)
            self.make_future_candidate(second_admission)
            first_actual = self.make_actual_output(first_admission)
            second_actual = self.make_actual_output(second_admission)
            first_runner_output = root / "runner-first"
            second_runner_output = root / "runner-second"
            first_runner_output.mkdir()
            second_runner_output.mkdir()

            first_exit, _first_payload = self.run_runner(
                first_admission,
                first_runner_output,
                first_actual,
                runner_execution_id="same-runner-execution",
            )
            second_exit, _second_payload = self.run_runner(
                second_admission,
                second_runner_output,
                second_actual,
                runner_execution_id="same-runner-execution",
            )
            first_runner = read_json(
                first_runner_output
                / "local_asset_next_bounded_smoke_iteration_runner.json"
            )
            second_runner = read_json(
                second_runner_output
                / "local_asset_next_bounded_smoke_iteration_runner.json"
            )
            first_checklist = (
                first_runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_checklist.md"
            ).read_text(encoding="utf-8")
            second_checklist = (
                second_runner_output
                / "local_asset_next_bounded_smoke_iteration_runner_checklist.md"
            ).read_text(encoding="utf-8")

            self.assertEqual(first_exit, 0)
            self.assertEqual(second_exit, 0)
            for field in (
                "runner_status",
                "runner_decision",
                "next_allowed_action",
                "disallowed_actions",
                "requested_limits",
                "admitted_limits",
            ):
                self.assertEqual(first_runner[field], second_runner[field])
            self.assertEqual(
                [
                    record["relative_path"]
                    for record in first_runner["bounded_file_records"]
                ],
                [
                    record["relative_path"]
                    for record in second_runner["bounded_file_records"]
                ],
            )
            self.assertEqual(
                [
                    artifact["artifact_role"]
                    for artifact in first_runner["source_artifacts"]
                ],
                [
                    artifact["artifact_role"]
                    for artifact in second_runner["source_artifacts"]
                ],
            )
            self.assertEqual(first_checklist, second_checklist)


if __name__ == "__main__":
    unittest.main()
