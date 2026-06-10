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
ITERATION_OUTPUTS = (
    "control/local_asset_bounded_smoke_iteration_signoff.json",
    "control/local_asset_bounded_smoke_iteration_admission.json",
    "local_asset_bounded_smoke_iteration_result.json",
    "local_asset_bounded_smoke_iteration_manifest.json",
    "local_asset_bounded_smoke_iteration_summary.md",
    "local_asset_bounded_smoke_iteration_human_review_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
    "smoke",
)
ITERATION_ROLES = (
    "local_asset_bounded_smoke_iteration_result",
    "local_asset_bounded_smoke_iteration_manifest",
    "local_asset_bounded_smoke_iteration_summary",
    "local_asset_bounded_smoke_iteration_human_review_checklist",
    "local_asset_bounded_smoke_iteration_signoff",
    "local_asset_bounded_smoke_iteration_admission",
)
BOUNDARY_FIELDS = (
    "production_promotion_granted",
    "production_scan_approved",
    "production_scan_performed",
    "automatic_approval_performed",
    "watcher_daemon_started",
    "raw_candidate_content_read_outside_scan_runtime",
    "candidate_file_hashing_outside_scan_runtime",
    "input_mutation_performed",
    "promotion_output_mutation_performed",
    "review_output_mutation_performed",
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


class LocalAssetBoundedSmokeIterationTests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def make_candidate(self, root, *, duplicate=False):
        candidate = Path(root) / "candidate"
        nested = candidate / "nested"
        nested.mkdir(parents=True)
        (candidate / "plate.png").write_bytes(b"plate")
        (nested / "clip.mov").write_bytes(b"clip")
        if duplicate:
            (candidate / "plate-copy.png").write_bytes(b"plate")
        return candidate

    def snapshot_input(self, candidate):
        return sorted(
            path.relative_to(candidate).as_posix()
            for path in Path(candidate).rglob("*")
        )

    def run_readiness(self, candidate, output_dir, *, project_id="iteration-test"):
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
        project_id="iteration-test",
        max_smoke_files=5,
    ):
        return self.run_cli(
            [
                "launch-local-asset-human-smoke-run",
                "--candidate-input-dir",
                Path(candidate).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--readiness-report",
                Path(readiness_report).as_posix(),
                "--human-approval-id",
                "iteration-smoke-approval",
                "--human-approval-phrase",
                SMOKE_APPROVAL_PHRASE,
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
        )

    def run_review(self, smoke_output_dir, output_dir, *, project_id="iteration-test"):
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
        project_id="iteration-test",
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
        phrase=BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE,
        project_id="iteration-test",
        max_smoke_files=None,
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
            "iteration-signoff-1",
            "--human-signoff-phrase",
            phrase,
            "--recursive",
            "--project-id",
            project_id,
            "--max-smoke-bytes",
            "1000",
            "--max-smoke-depth",
            "3",
        ]
        if max_smoke_files is not None:
            args.extend(["--max-smoke-files", str(max_smoke_files)])
        if previous_scan_output_dir is not None:
            args.extend(
                [
                    "--previous-scan-output-dir",
                    Path(previous_scan_output_dir).as_posix(),
                ]
            )
        return self.run_cli(args)

    def build_chain(self, root, *, duplicate=False):
        candidate = self.make_candidate(root, duplicate=duplicate)
        readiness_output = Path(root) / "readiness"
        smoke_output = Path(root) / "smoke-0"
        review_output = Path(root) / "review"
        promotion_output = Path(root) / "promotion"
        for path in (readiness_output, smoke_output, review_output, promotion_output):
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
            max_smoke_files=5,
        )
        self.assertEqual(smoke_code, 0)
        review_code, _review_payload = self.run_review(smoke_output, review_output)
        self.assertEqual(review_code, 0)
        promotion_code, _promotion_payload = self.run_promotion(
            review_output,
            promotion_output,
        )
        return {
            "candidate": candidate,
            "readiness_output": readiness_output,
            "readiness_report": Path(
                readiness_payload["local_asset_smoke_readiness_report_path"]
            ),
            "smoke_output": smoke_output,
            "review_output": review_output,
            "promotion_output": promotion_output,
            "promotion_code": promotion_code,
        }

    def write_graph(self, graph_path, nodes, *, graph_id="iteration-graph"):
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

    def iteration_node(self, *, node_id, chain, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": "launch_local_asset_bounded_smoke_iteration",
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "promotion_output_dir": chain["promotion_output"].as_posix(),
                "candidate_input_dir": chain["candidate"].as_posix(),
                "readiness_report": chain["readiness_report"].as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "human_signoff_id": "graph-signoff",
                "human_signoff_phrase": BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE,
                "recursive": True,
                "include_hidden": False,
                "project_id": "iteration-test",
                "max_smoke_files": 5,
                "max_smoke_bytes": 1000,
                "max_smoke_depth": 3,
            },
        }

    def test_bounded_smoke_iteration_writes_result_manifest_summary_checklist_control_and_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_chain(root)
            self.assertEqual(chain["promotion_code"], 0)
            iteration_output = root / "iteration"
            iteration_output.mkdir()

            exit_code, payload = self.run_iteration(
                chain["promotion_output"],
                chain["candidate"],
                chain["readiness_report"],
                iteration_output,
                max_smoke_files=5,
            )
            artifact_index = read_json(iteration_output / "artifact_index.json")
            artifact_roles = {
                entry["artifact_role"] for entry in artifact_index["entries"]
            }

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for output in ITERATION_OUTPUTS:
                self.assertTrue((iteration_output / output).exists(), output)
            self.assertTrue(
                (
                    iteration_output
                    / "smoke"
                    / "control"
                    / "local_asset_human_smoke_approval.json"
                ).exists()
            )
            self.assertTrue(
                (
                    iteration_output
                    / "smoke"
                    / "scan"
                    / "artifact_index.json"
                ).exists()
            )
            for role in ITERATION_ROLES:
                self.assertIn(role, artifact_roles)

    def test_bounded_smoke_iteration_requires_promotion_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_chain(root, duplicate=True)
            self.assertEqual(chain["promotion_code"], 1)
            iteration_output = root / "iteration"
            iteration_output.mkdir()

            exit_code, payload = self.run_iteration(
                chain["promotion_output"],
                chain["candidate"],
                chain["readiness_report"],
                iteration_output,
                max_smoke_files=5,
            )
            result = read_json(
                iteration_output / "local_asset_bounded_smoke_iteration_result.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(result["bounded_smoke_iteration_performed"])
            self.assertFalse(result["smoke_launcher_invoked"])
            self.assertFalse((iteration_output / "smoke").exists())
            self.assertFalse(payload["production_scan_approved"])

    def test_bounded_smoke_iteration_requires_valid_signoff_phrase(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_chain(root)
            iteration_output = root / "iteration"
            iteration_output.mkdir()

            exit_code, _payload = self.run_iteration(
                chain["promotion_output"],
                chain["candidate"],
                chain["readiness_report"],
                iteration_output,
                phrase="WRONG_PHRASE",
                max_smoke_files=5,
            )
            signoff = read_json(
                iteration_output
                / "control"
                / "local_asset_bounded_smoke_iteration_signoff.json"
            )
            admission = read_json(
                iteration_output
                / "control"
                / "local_asset_bounded_smoke_iteration_admission.json"
            )
            result = read_json(
                iteration_output / "local_asset_bounded_smoke_iteration_result.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(signoff["signoff_valid"])
            self.assertFalse(admission["admitted"])
            self.assertFalse(result["smoke_launcher_invoked"])
            self.assertFalse((iteration_output / "smoke").exists())
            self.assertNotIn("WRONG_PHRASE", json.dumps(signoff, sort_keys=True))

    def test_bounded_smoke_iteration_does_not_persist_signoff_plaintext(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_chain(root)
            iteration_output = root / "iteration"
            iteration_output.mkdir()

            exit_code, _payload = self.run_iteration(
                chain["promotion_output"],
                chain["candidate"],
                chain["readiness_report"],
                iteration_output,
                max_smoke_files=5,
            )
            signoff_path = (
                iteration_output
                / "control"
                / "local_asset_bounded_smoke_iteration_signoff.json"
            )
            signoff = read_json(signoff_path)

            self.assertEqual(exit_code, 0)
            self.assertRegex(signoff["human_signoff_phrase_sha256"], r"^[0-9a-f]{64}$")
            self.assertNotIn("human_signoff_phrase", signoff)
            self.assertFalse(signoff["human_signoff_phrase_plaintext_persisted"])
            self.assertFalse(signoff["human_signoff_phrase_stored"])
            for path in (
                iteration_output / "local_asset_bounded_smoke_iteration_result.json",
                iteration_output / "local_asset_bounded_smoke_iteration_manifest.json",
                iteration_output / "local_asset_bounded_smoke_iteration_summary.md",
                iteration_output
                / "local_asset_bounded_smoke_iteration_human_review_checklist.md",
            ):
                self.assertNotIn(
                    BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE,
                    path.read_text(encoding="utf-8"),
                    path.name,
                )

    def test_bounded_smoke_iteration_preserves_bounded_limits(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_chain(root)
            iteration_output = root / "iteration"
            iteration_output.mkdir()
            before = self.snapshot_input(chain["candidate"])

            exit_code, payload = self.run_iteration(
                chain["promotion_output"],
                chain["candidate"],
                chain["readiness_report"],
                iteration_output,
                max_smoke_files=1,
            )
            after = self.snapshot_input(chain["candidate"])

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["production_scan_performed"])
            self.assertFalse(payload["scan_complete"])
            self.assertEqual(after, before)

    def test_bounded_smoke_iteration_delegates_to_existing_human_smoke_launcher(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_chain(root)
            iteration_output = root / "iteration"
            iteration_output.mkdir()

            exit_code, payload = self.run_iteration(
                chain["promotion_output"],
                chain["candidate"],
                chain["readiness_report"],
                iteration_output,
                max_smoke_files=5,
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["smoke_launcher_invoked"])
            self.assertTrue(
                (
                    iteration_output
                    / "smoke"
                    / "control"
                    / "local_asset_human_smoke_approval.json"
                ).exists()
            )
            self.assertTrue(
                (
                    iteration_output
                    / "smoke"
                    / "control"
                    / "local_asset_human_smoke_admission_receipt.json"
                ).exists()
            )
            self.assertTrue(
                (iteration_output / "smoke" / "scan" / "artifact_index.json").exists()
            )
            self.assertTrue(
                (
                    iteration_output
                    / "smoke"
                    / "local_asset_human_smoke_run_summary.md"
                ).exists()
            )

    def test_bounded_smoke_iteration_fail_closed_on_existing_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_chain(root)
            for relative in ITERATION_OUTPUTS:
                with self.subTest(relative=relative):
                    output = root / ("iteration-" + relative.replace("/", "-"))
                    output.mkdir()
                    existing = output / relative
                    existing.parent.mkdir(parents=True, exist_ok=True)
                    if relative == "smoke":
                        existing.mkdir()
                    else:
                        existing.write_text("do not overwrite\n", encoding="utf-8")

                    exit_code, _payload = self.run_iteration(
                        chain["promotion_output"],
                        chain["candidate"],
                        chain["readiness_report"],
                        output,
                        max_smoke_files=5,
                    )

                    self.assertEqual(exit_code, 1)
                    if relative != "smoke":
                        self.assertEqual(
                            existing.read_text(encoding="utf-8"),
                            "do not overwrite\n",
                        )

    def test_bounded_smoke_iteration_output_dir_missing_returns_structured_failure_without_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_chain(root)
            missing_output = root / "missing-iteration"

            exit_code, payload = self.run_iteration(
                chain["promotion_output"],
                chain["candidate"],
                chain["readiness_report"],
                missing_output,
                max_smoke_files=5,
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["artifacts_written"])
            self.assertFalse(missing_output.exists())

    def test_bounded_smoke_iteration_input_output_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_chain(root)
            cases = []

            output_inside_candidate = chain["candidate"] / "iteration-output"
            output_inside_candidate.mkdir()
            cases.append(
                (
                    "output_inside_candidate",
                    chain["promotion_output"],
                    chain["candidate"],
                    output_inside_candidate,
                )
            )

            output_with_candidate = root / "iteration-with-candidate"
            nested_candidate = output_with_candidate / "candidate"
            nested_candidate.mkdir(parents=True)
            cases.append(
                (
                    "candidate_inside_output",
                    chain["promotion_output"],
                    nested_candidate,
                    output_with_candidate,
                )
            )

            output_inside_promotion = chain["promotion_output"] / "iteration-output"
            output_inside_promotion.mkdir()
            cases.append(
                (
                    "output_inside_promotion",
                    chain["promotion_output"],
                    chain["candidate"],
                    output_inside_promotion,
                )
            )

            output_with_promotion = root / "iteration-with-promotion"
            nested_promotion = output_with_promotion / "promotion"
            nested_promotion.mkdir(parents=True)
            cases.append(
                (
                    "promotion_inside_output",
                    nested_promotion,
                    chain["candidate"],
                    output_with_promotion,
                )
            )

            output_inside_review = chain["review_output"] / "iteration-output"
            output_inside_review.mkdir()
            cases.append(
                (
                    "output_inside_review",
                    chain["promotion_output"],
                    chain["candidate"],
                    output_inside_review,
                )
            )

            decision_path = (
                chain["promotion_output"]
                / "local_asset_smoke_promotion_decision.json"
            )
            manifest_path = (
                chain["promotion_output"]
                / "local_asset_smoke_promotion_gate_manifest.json"
            )
            decision = read_json(decision_path)
            decision["smoke_output_dir"] = chain["smoke_output"].as_posix()
            write_json(decision_path, decision)
            manifest = read_json(manifest_path)
            manifest["decision_sha256"] = sha256_file(decision_path)
            write_json(manifest_path, manifest)
            output_inside_smoke = chain["smoke_output"] / "iteration-output"
            output_inside_smoke.mkdir()
            cases.append(
                (
                    "output_inside_smoke",
                    chain["promotion_output"],
                    chain["candidate"],
                    output_inside_smoke,
                )
            )

            for name, promotion_output, candidate, output_dir in cases:
                with self.subTest(name=name):
                    before = self.snapshot_input(chain["candidate"])
                    exit_code, payload = self.run_iteration(
                        promotion_output,
                        candidate,
                        chain["readiness_report"],
                        output_dir,
                        max_smoke_files=5,
                    )
                    after = self.snapshot_input(chain["candidate"])

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["bounded_smoke_iteration_performed"])
                    self.assertFalse(payload["smoke_launcher_invoked"])
                    self.assertEqual(after, before)

    def test_task_graph_bounded_smoke_iteration_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_chain(root)
            node_output = root / "iteration"
            graph_output = root / "graph-output"
            node_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.iteration_node(
                        node_id="bounded_iteration",
                        chain=chain,
                        output_dir=node_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "bounded_iteration"
            }

            self.assertTrue(result.success)
            for role in ITERATION_ROLES:
                self.assertIn(role, roles)

    def test_bounded_smoke_iteration_no_scope_expansion_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_chain(root)
            iteration_output = root / "iteration"
            graph_output = root / "graph-output"
            iteration_output.mkdir()
            graph_output.mkdir()
            exit_code, payload = self.run_iteration(
                chain["promotion_output"],
                chain["candidate"],
                chain["readiness_report"],
                iteration_output,
                max_smoke_files=5,
            )
            result_payload = read_json(
                iteration_output / "local_asset_bounded_smoke_iteration_result.json"
            )
            manifest = read_json(
                iteration_output / "local_asset_bounded_smoke_iteration_manifest.json"
            )
            graph_path = root / "graph.json"
            second_output = root / "iteration-graph"
            second_output.mkdir()
            self.write_graph(
                graph_path,
                [
                    self.iteration_node(
                        node_id="bounded_iteration",
                        chain=chain,
                        output_dir=second_output,
                    )
                ],
                graph_id="iteration-boundaries-graph",
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            execution_manifest = read_json(graph_result.execution_manifest_path)
            node = execution_manifest["nodes"][0]

            self.assertEqual(exit_code, 0)
            for source in (payload, result_payload, manifest, node):
                for field in BOUNDARY_FIELDS:
                    self.assertFalse(source[field], field)
                self.assertTrue(source["required_human_approval"])

    def test_bounded_smoke_iteration_deterministic_across_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_chain(root)
            first_output = root / "iteration-one"
            second_output = root / "iteration-two"
            first_output.mkdir()
            second_output.mkdir()

            first_code, _first_payload = self.run_iteration(
                chain["promotion_output"],
                chain["candidate"],
                chain["readiness_report"],
                first_output,
                max_smoke_files=5,
            )
            second_code, _second_payload = self.run_iteration(
                chain["promotion_output"],
                chain["candidate"],
                chain["readiness_report"],
                second_output,
                max_smoke_files=5,
            )
            first_result = read_json(
                first_output / "local_asset_bounded_smoke_iteration_result.json"
            )
            second_result = read_json(
                second_output / "local_asset_bounded_smoke_iteration_result.json"
            )
            first_index = read_json(first_output / "artifact_index.json")
            second_index = read_json(second_output / "artifact_index.json")
            first_checklist = (
                first_output
                / "local_asset_bounded_smoke_iteration_human_review_checklist.md"
            ).read_text(encoding="utf-8")
            second_checklist = (
                second_output
                / "local_asset_bounded_smoke_iteration_human_review_checklist.md"
            ).read_text(encoding="utf-8")

            self.assertEqual(first_code, 0)
            self.assertEqual(second_code, 0)
            for field in (
                "iteration_status",
                "iteration_decision",
                "promotion_validated",
                "human_signoff_valid",
                "bounded_smoke_iteration_allowed",
                "bounded_smoke_iteration_performed",
                "production_promotion_granted",
                "production_scan_approved",
                "production_scan_performed",
                "required_human_approval",
            ):
                self.assertEqual(first_result[field], second_result[field], field)
            self.assertEqual(
                [entry["artifact_role"] for entry in first_index["entries"]],
                [entry["artifact_role"] for entry in second_index["entries"]],
            )
            for option in (
                "generate smoke review packet for this iteration",
                "reject and repair iteration",
                "inspect smoke outputs manually",
            ):
                self.assertIn(option, first_checklist)
                self.assertIn(option, second_checklist)


if __name__ == "__main__":
    unittest.main()
