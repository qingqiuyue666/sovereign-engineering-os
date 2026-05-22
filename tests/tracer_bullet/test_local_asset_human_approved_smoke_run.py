import contextlib
from hashlib import sha256
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


APPROVAL_PHRASE = "I_APPROVE_LOCAL_ASSET_SMOKE_RUN"
SCAN_OUTPUTS = (
    "asset_manifest.json",
    "asset_index.json",
    "duplicates_report.json",
    "media_inventory.md",
    "asset_runtime_audit_log.jsonl",
    "asset_runtime_validation_report.json",
    "asset_runtime_quarantine_manifest.json",
    "launcher_summary.md",
    "asset_scan_run_receipt.json",
    "local_asset_index.sqlite",
    "local_asset_sqlite_index_manifest.json",
    "local_asset_sqlite_query_summary.md",
    "local_asset_incremental_scan_plan.json",
    "local_asset_incremental_scan_manifest.json",
    "local_asset_incremental_scan_summary.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LocalAssetHumanApprovedSmokeRunTests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def make_candidate(self, root, *, secret=False, raw_value=b"plate"):
        candidate = root / "candidate"
        nested = candidate / "nested"
        nested.mkdir(parents=True)
        (candidate / "plate.png").write_bytes(raw_value)
        (nested / "clip.mov").write_bytes(b"clip")
        if secret:
            (candidate / "api_key.txt").write_text("SECRET_DO_NOT_COPY\n", encoding="utf-8")
        return candidate

    def run_readiness(
        self,
        candidate,
        output_dir,
        *,
        recursive=True,
        include_hidden=False,
        project_id="human-smoke-test",
    ):
        args = [
            "launch-local-asset-smoke-readiness",
            "--candidate-input-dir",
            Path(candidate).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--project-id",
            project_id,
        ]
        if recursive:
            args.append("--recursive")
        if include_hidden:
            args.append("--include-hidden")
        return self.run_cli(args)

    def run_human_smoke(
        self,
        candidate,
        output_dir,
        readiness_report,
        *,
        phrase=APPROVAL_PHRASE,
        approval_id="approval-1",
        recursive=True,
        include_hidden=False,
        project_id="human-smoke-test",
        max_smoke_files=None,
        max_smoke_bytes=100,
        max_smoke_depth=2,
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
            approval_id,
            "--human-approval-phrase",
            phrase,
            "--project-id",
            project_id,
        ]
        if recursive:
            args.append("--recursive")
        if include_hidden:
            args.append("--include-hidden")
        if max_smoke_files is not None:
            args.extend(["--max-smoke-files", str(max_smoke_files)])
        if max_smoke_bytes is not None:
            args.extend(["--max-smoke-bytes", str(max_smoke_bytes)])
        if max_smoke_depth is not None:
            args.extend(["--max-smoke-depth", str(max_smoke_depth)])
        return self.run_cli(args)

    def write_graph(self, graph_path, nodes, *, graph_id="human-smoke-graph"):
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

    def human_smoke_node(self, *, node_id, candidate, output_dir, readiness_report):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": "launch_local_asset_human_smoke_run",
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "candidate_input_dir": Path(candidate).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "readiness_report": Path(readiness_report).as_posix(),
                "human_approval_id": "graph-approval",
                "human_approval_phrase": APPROVAL_PHRASE,
                "recursive": True,
                "include_hidden": False,
                "project_id": "human-smoke-test",
                "max_smoke_files": 2,
                "max_smoke_bytes": 100,
                "max_smoke_depth": 2,
            },
        }

    def successful_human_smoke(self, root):
        candidate = self.make_candidate(root)
        readiness_output = root / "readiness"
        human_output = root / "human-smoke"
        readiness_output.mkdir()
        human_output.mkdir()
        readiness_code, readiness_payload = self.run_readiness(candidate, readiness_output)
        self.assertEqual(readiness_code, 0)
        readiness_report = Path(readiness_payload["local_asset_smoke_readiness_report_path"])
        exit_code, payload = self.run_human_smoke(
            candidate,
            human_output,
            readiness_report,
            max_smoke_files=2,
        )
        return candidate, human_output, exit_code, payload

    def test_human_approved_smoke_run_writes_control_and_scan_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate, human_output, exit_code, payload = self.successful_human_smoke(root)
            before_files = sorted(path.relative_to(candidate).as_posix() for path in candidate.rglob("*"))

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            self.assertTrue((human_output / "control" / "local_asset_human_smoke_approval.json").exists())
            self.assertTrue((human_output / "control" / "local_asset_human_smoke_admission_receipt.json").exists())
            self.assertTrue((human_output / "local_asset_human_smoke_run_summary.md").exists())
            for filename in SCAN_OUTPUTS:
                self.assertTrue((human_output / "scan" / filename).exists(), filename)
            self.assertTrue((human_output / "artifact_index.json").exists())
            self.assertTrue((human_output / "scan" / "artifact_index.json").exists())
            admission = read_json(human_output / "control" / "local_asset_human_smoke_admission_receipt.json")
            self.assertTrue(admission["scan_complete"])
            self.assertTrue(admission["bounded_smoke_run_performed"])
            self.assertFalse(admission["production_scan_performed"])
            self.assertFalse(admission["input_mutation_performed"])
            after_files = sorted(path.relative_to(candidate).as_posix() for path in candidate.rglob("*"))
            self.assertEqual(after_files, before_files)

    def test_wrong_approval_phrase_fails_before_scan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self.make_candidate(root)
            readiness_output = root / "readiness"
            human_output = root / "human-smoke"
            readiness_output.mkdir()
            human_output.mkdir()
            _, readiness_payload = self.run_readiness(candidate, readiness_output)

            exit_code, payload = self.run_human_smoke(
                candidate,
                human_output,
                readiness_payload["local_asset_smoke_readiness_report_path"],
                phrase="WRONG_PHRASE",
                max_smoke_files=None,
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["scan_launcher_invoked"])
            self.assertFalse(payload["real_scan_performed"])
            self.assertFalse(payload["bounded_smoke_run_performed"])
            self.assertFalse((human_output / "scan" / "asset_manifest.json").exists())
            generated_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in human_output.rglob("*")
                if path.is_file()
            )
            self.assertNotIn("WRONG_PHRASE", generated_text)
            self.assertNotIn(APPROVAL_PHRASE, generated_text)

    def test_blocked_readiness_report_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self.make_candidate(root, secret=True)
            readiness_output = root / "readiness"
            human_output = root / "human-smoke"
            readiness_output.mkdir()
            human_output.mkdir()
            _, readiness_payload = self.run_readiness(candidate, readiness_output)
            readiness_report = read_json(readiness_payload["local_asset_smoke_readiness_report_path"])
            self.assertEqual(readiness_report["readiness_status"], "blocked_safety_risk")

            exit_code, payload = self.run_human_smoke(
                candidate,
                human_output,
                readiness_payload["local_asset_smoke_readiness_report_path"],
                max_smoke_files=None,
            )
            admission = read_json(human_output / "control" / "local_asset_human_smoke_admission_receipt.json")

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["scan_launcher_invoked"])
            self.assertFalse(admission["admitted"])
            self.assertEqual(admission["readiness_status"], "blocked_safety_risk")

    def test_candidate_path_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self.make_candidate(root / "a")
            other_candidate = self.make_candidate(root / "b")
            readiness_output = root / "readiness"
            human_output = root / "human-smoke"
            readiness_output.mkdir()
            human_output.mkdir()
            _, readiness_payload = self.run_readiness(candidate, readiness_output)

            exit_code, payload = self.run_human_smoke(
                other_candidate,
                human_output,
                readiness_payload["local_asset_smoke_readiness_report_path"],
                max_smoke_files=2,
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["scan_launcher_invoked"])
            self.assertFalse((human_output / "scan" / "asset_manifest.json").exists())

    def test_smoke_precheck_limit_exceeded_fails_before_scan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self.make_candidate(root)
            readiness_output = root / "readiness"
            human_output = root / "human-smoke"
            readiness_output.mkdir()
            human_output.mkdir()
            _, readiness_payload = self.run_readiness(candidate, readiness_output)

            exit_code, payload = self.run_human_smoke(
                candidate,
                human_output,
                readiness_payload["local_asset_smoke_readiness_report_path"],
                max_smoke_files=1,
            )
            admission = read_json(human_output / "control" / "local_asset_human_smoke_admission_receipt.json")

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["scan_launcher_invoked"])
            self.assertFalse((human_output / "scan" / "asset_manifest.json").exists())
            self.assertTrue(admission["smoke_precheck_limit_exceeded"])
            self.assertEqual(admission["smoke_precheck_file_count"], 2)

    def test_human_smoke_does_not_persist_approval_phrase_plaintext(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, human_output, exit_code, _payload = self.successful_human_smoke(root)
            approval = read_json(human_output / "control" / "local_asset_human_smoke_approval.json")
            expected_hash = sha256(APPROVAL_PHRASE.encode("utf-8")).hexdigest()
            generated_text = "\n".join(
                path.read_text(encoding="utf-8", errors="ignore")
                for path in human_output.rglob("*")
                if path.is_file() and path.suffix != ".sqlite"
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(approval["human_approval_phrase_sha256"], expected_hash)
            self.assertFalse(approval["approval_phrase_plaintext_persisted"])
            self.assertNotIn(APPROVAL_PHRASE, generated_text)
            self.assertIn(expected_hash, generated_text)

    def test_human_smoke_artifact_index_includes_control_and_scan_refs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_value = b"RAW_PRIVATE_VALUE_DO_NOT_COPY"
            candidate = self.make_candidate(root, raw_value=raw_value)
            readiness_output = root / "readiness"
            human_output = root / "human-smoke"
            readiness_output.mkdir()
            human_output.mkdir()
            _, readiness_payload = self.run_readiness(candidate, readiness_output)
            exit_code, _payload = self.run_human_smoke(
                candidate,
                human_output,
                readiness_payload["local_asset_smoke_readiness_report_path"],
                max_smoke_files=2,
            )
            root_index = read_json(human_output / "artifact_index.json")
            artifact_names = {entry["artifact_name"] for entry in root_index["entries"]}
            root_index_text = (human_output / "artifact_index.json").read_text(encoding="utf-8")

            self.assertEqual(exit_code, 0)
            self.assertIn("local_asset_human_smoke_approval", artifact_names)
            self.assertIn("local_asset_human_smoke_admission_receipt", artifact_names)
            self.assertIn("local_asset_human_smoke_run_summary", artifact_names)
            self.assertIn("local_asset_human_smoke_scan_artifact_index", artifact_names)
            self.assertIn("local_asset_human_smoke_scan_artifact_index_manifest", artifact_names)
            self.assertNotIn(raw_value.decode("utf-8"), root_index_text)
            for entry in root_index["entries"]:
                self.assertFalse(entry["content_indexed"])
                self.assertFalse(entry["raw_content_copied"])

    def test_task_graph_human_smoke_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self.make_candidate(root)
            readiness_output = root / "readiness"
            node_output = root / "node-output"
            graph_output = root / "graph-output"
            readiness_output.mkdir()
            node_output.mkdir()
            graph_output.mkdir()
            _, readiness_payload = self.run_readiness(candidate, readiness_output)
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.human_smoke_node(
                        node_id="human_smoke_assets",
                        candidate=candidate,
                        output_dir=node_output,
                        readiness_report=readiness_payload["local_asset_smoke_readiness_report_path"],
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
                if artifact["node_id"] == "human_smoke_assets"
            }

            self.assertTrue(result.success)
            self.assertIn("local_asset_human_smoke_approval", roles)
            self.assertIn("local_asset_human_smoke_admission_receipt", roles)
            self.assertIn("local_asset_human_smoke_run_summary", roles)
            self.assertIn("local_asset_human_smoke_scan_artifact_index", roles)
            self.assertIn("local_asset_human_smoke_scan_artifact_index_manifest", roles)
            self.assertTrue(node["admitted"])
            self.assertTrue(node["scan_complete"])
            self.assertTrue(node["bounded_smoke_run_performed"])
            self.assertFalse(node["production_scan_performed"])

    def test_human_smoke_fail_closed_on_existing_outputs(self):
        cases = (
            ("root-index", ("artifact_index.json",), "do not overwrite root\n"),
            (
                "control-approval",
                ("control", "local_asset_human_smoke_approval.json"),
                "do not overwrite approval\n",
            ),
        )
        for _case_name, parts, existing_text in cases:
            with self.subTest(parts=parts):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    candidate = self.make_candidate(root)
                    readiness_output = root / "readiness"
                    human_output = root / "human-smoke"
                    readiness_output.mkdir()
                    human_output.mkdir()
                    existing = human_output.joinpath(*parts)
                    existing.parent.mkdir(parents=True, exist_ok=True)
                    existing.write_text(existing_text, encoding="utf-8")
                    _, readiness_payload = self.run_readiness(candidate, readiness_output)

                    exit_code, payload = self.run_human_smoke(
                        candidate,
                        human_output,
                        readiness_payload["local_asset_smoke_readiness_report_path"],
                        max_smoke_files=2,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(existing.read_text(encoding="utf-8"), existing_text)
                    self.assertFalse(payload["scan_launcher_invoked"])
                    self.assertFalse((human_output / "scan" / "asset_manifest.json").exists())

    def test_human_smoke_no_scope_expansion_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate, human_output, exit_code, payload = self.successful_human_smoke(root)
            approval = read_json(human_output / "control" / "local_asset_human_smoke_approval.json")
            admission = read_json(human_output / "control" / "local_asset_human_smoke_admission_receipt.json")
            graph_output = root / "graph-output"
            node_output = root / "node-output"
            graph_output.mkdir()
            node_output.mkdir()
            graph_path = root / "graph.json"
            readiness_report = root / "readiness" / "local_asset_smoke_readiness_report.json"
            self.write_graph(
                graph_path,
                [
                    self.human_smoke_node(
                        node_id="human_smoke_assets",
                        candidate=candidate,
                        output_dir=node_output,
                        readiness_report=readiness_report,
                    )
                ],
                graph_id="boundary-human-smoke-graph",
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            graph_node = read_json(graph_result.execution_manifest_path)["nodes"][0]

            self.assertEqual(exit_code, 0)
            for field in (
                "production_autonomy_granted",
                "input_mutation_allowed",
                "file_move_allowed",
                "file_rename_allowed",
                "file_delete_allowed",
                "network_allowed",
                "model_api_allowed",
                "external_runtime_allowed",
            ):
                self.assertFalse(approval[field], field)
            for payload_like in (admission, payload, graph_node):
                for field in (
                    "production_scan_performed",
                    "input_mutation_performed",
                    "file_move_performed",
                    "file_rename_performed",
                    "file_delete_performed",
                    "media_organizer_behavior_performed",
                    "network_access_performed",
                    "model_api_called",
                    "external_runtime_invoked",
                ):
                    self.assertFalse(payload_like[field], field)

    def test_human_smoke_deterministic_across_runs_for_stable_fields(self):
        with (
            tempfile.TemporaryDirectory() as first_dir,
            tempfile.TemporaryDirectory() as second_dir,
        ):
            first_root = Path(first_dir)
            second_root = Path(second_dir)
            _candidate_a, human_a, code_a, _payload_a = self.successful_human_smoke(first_root)
            _candidate_b, human_b, code_b, _payload_b = self.successful_human_smoke(second_root)
            first_admission = read_json(human_a / "control" / "local_asset_human_smoke_admission_receipt.json")
            second_admission = read_json(human_b / "control" / "local_asset_human_smoke_admission_receipt.json")
            first_index = read_json(human_a / "artifact_index.json")
            second_index = read_json(human_b / "artifact_index.json")
            first_roles = [entry["artifact_role"] for entry in first_index["entries"]]
            second_roles = [entry["artifact_role"] for entry in second_index["entries"]]

            self.assertEqual(code_a, 0)
            self.assertEqual(code_b, 0)
            for field in (
                "admission_reason",
                "readiness_status",
                "readiness_decision",
                "max_smoke_files",
                "max_smoke_bytes",
                "max_smoke_depth",
                "production_scan_performed",
                "input_mutation_performed",
                "network_access_performed",
                "model_api_called",
                "external_runtime_invoked",
                "scan_complete",
            ):
                self.assertEqual(first_admission[field], second_admission[field], field)
            self.assertEqual(first_roles, second_roles)


if __name__ == "__main__":
    unittest.main()
