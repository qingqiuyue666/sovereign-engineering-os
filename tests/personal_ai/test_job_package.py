import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.job_package import (
    LocalJobPackageResult,
    build_local_job_package,
)


EXPECTED_JOB_FILES = {
    "input_snapshot.json",
    "intake_ledger.jsonl",
    "artifact_profile.json",
    "work_order_proposal.json",
    "review_packet.json",
    "pipeline_manifest.json",
    "task_route.json",
    "spreadsheet_processor_plan.json",
    "spreadsheet_readonly_inspection.json",
    "spreadsheet_report_plan.json",
    "spreadsheet_structural_report.json",
    "spreadsheet_structural_report.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
    "final_job_manifest.json",
    "job_summary.json",
    "human_next_steps.md",
    "job_package_validation.json",
}

EXPECTED_BOUNDARIES = {
    "no_runtime_authority",
    "no_execution_capability",
    "no_external_tool_control",
    "no_network",
    "no_api_calls",
    "no_subprocess",
    "no_adapter_implementation",
    "no_ai_classification",
    "no_semantic_classification",
    "no_spreadsheet_output_write",
    "no_issue_severity_assignment",
    "no_business_semantic_interpretation",
    "no_input_file_mutation",
    "no_input_content_copy",
    "no_raw_cell_value_copy",
    "no_destructive_actions",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


class LocalJobPackageTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_root_dir = root / "packages"
        input_dir.mkdir()
        output_root_dir.mkdir()
        return input_dir, output_root_dir

    def test_builds_complete_local_job_package_from_temporary_files(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )

        self.assertIsInstance(result, LocalJobPackageResult)
        self.assertEqual(result.job_id, "job-001")
        self.assertEqual(result.input_dir, input_dir)
        self.assertEqual(result.output_root_dir, output_root_dir)
        self.assertEqual(result.job_dir, output_root_dir / "job-001")
        self.assertEqual(result.input_snapshot_path, result.job_dir / "input_snapshot.json")
        self.assertEqual(result.intake_ledger_path, result.job_dir / "intake_ledger.jsonl")
        self.assertEqual(result.artifact_profile_path, result.job_dir / "artifact_profile.json")
        self.assertEqual(
            result.work_order_proposal_path,
            result.job_dir / "work_order_proposal.json",
        )
        self.assertEqual(result.review_packet_path, result.job_dir / "review_packet.json")
        self.assertEqual(
            result.pipeline_manifest_path,
            result.job_dir / "pipeline_manifest.json",
        )
        self.assertEqual(result.task_route_path, result.job_dir / "task_route.json")
        self.assertEqual(
            result.spreadsheet_processor_plan_path,
            result.job_dir / "spreadsheet_processor_plan.json",
        )
        self.assertEqual(
            result.spreadsheet_readonly_inspection_path,
            result.job_dir / "spreadsheet_readonly_inspection.json",
        )
        self.assertEqual(
            result.spreadsheet_report_plan_path,
            result.job_dir / "spreadsheet_report_plan.json",
        )
        self.assertEqual(
            result.spreadsheet_structural_report_json_path,
            result.job_dir / "spreadsheet_structural_report.json",
        )
        self.assertEqual(
            result.spreadsheet_structural_report_markdown_path,
            result.job_dir / "spreadsheet_structural_report.md",
        )
        self.assertEqual(result.artifact_index_path, result.job_dir / "artifact_index.json")
        self.assertEqual(
            result.artifact_index_manifest_path,
            result.job_dir / "artifact_index_manifest.json",
        )
        self.assertEqual(
            result.final_job_manifest_path,
            result.job_dir / "final_job_manifest.json",
        )
        self.assertEqual(result.job_summary_path, result.job_dir / "job_summary.json")
        self.assertEqual(
            result.human_next_steps_path,
            result.job_dir / "human_next_steps.md",
        )
        self.assertEqual(
            result.job_package_validation_path,
            result.job_dir / "job_package_validation.json",
        )
        self.assertEqual(result.files_recorded, 2)
        self.assertEqual(
            result.candidate_tasks,
            [
                "spreadsheet_review",
                "document_review",
                "mixed_file_inventory",
            ],
        )
        self.assertEqual(result.route_type, "mixed_inventory_route")
        self.assertEqual(
            result.recommended_processor_lane,
            "mixed_file_inventory_planning_only",
        )
        self.assertEqual(result.spreadsheet_plan_status, "planning_ready")
        self.assertEqual(result.spreadsheet_artifact_count, 1)
        self.assertEqual(result.spreadsheet_inspected_files, 1)
        self.assertEqual(result.spreadsheet_unsupported_files, 0)
        self.assertEqual(result.spreadsheet_parse_error_files, 0)
        self.assertEqual(result.spreadsheet_report_status, "report_planning_ready")
        self.assertEqual(
            result.spreadsheet_issue_categories,
            ["no_structural_issues_detected"],
        )
        self.assertEqual(
            result.spreadsheet_structural_report_status,
            "report_planning_ready",
        )
        self.assertIs(result.required_human_approval, True)
        self.assertTrue(result.job_dir.exists())

    def test_creates_exact_required_job_package_files(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )

        self.assertEqual(
            {path.name for path in result.job_dir.iterdir()},
            EXPECTED_JOB_FILES,
        )

    def test_job_package_creates_task_route_json(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        task_route = read_json(result.task_route_path)

        self.assertTrue(result.task_route_path.exists())
        self.assertEqual(task_route["route_type"], "spreadsheet_route")
        self.assertEqual(
            task_route["recommended_processor_lane"],
            "spreadsheet_processor_planning_only",
        )
        self.assertEqual(task_route["authority"], "non_authority")
        self.assertEqual(task_route["execution_capability"], "not_introduced")

    def test_job_package_creates_spreadsheet_processor_plan_json(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        spreadsheet_plan = read_json(result.spreadsheet_processor_plan_path)

        self.assertTrue(result.spreadsheet_processor_plan_path.exists())
        self.assertEqual(
            spreadsheet_plan["plan_type"],
            "personal_ai_local_spreadsheet_processor_plan",
        )
        self.assertEqual(spreadsheet_plan["plan_status"], "planning_ready")
        self.assertEqual(spreadsheet_plan["artifact_count"], 1)

    def test_job_package_creates_spreadsheet_readonly_inspection_json(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        spreadsheet_inspection = read_json(
            result.spreadsheet_readonly_inspection_path
        )

        self.assertTrue(result.spreadsheet_readonly_inspection_path.exists())
        self.assertEqual(
            spreadsheet_inspection["inspection_type"],
            "personal_ai_local_spreadsheet_readonly_inspection",
        )
        self.assertEqual(
            spreadsheet_inspection["summary"]["inspected_files"],
            1,
        )

    def test_job_package_creates_spreadsheet_report_plan_json(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        spreadsheet_report_plan = read_json(result.spreadsheet_report_plan_path)

        self.assertTrue(result.spreadsheet_report_plan_path.exists())
        self.assertEqual(
            spreadsheet_report_plan["plan_type"],
            "personal_ai_local_spreadsheet_report_plan",
        )
        self.assertEqual(
            spreadsheet_report_plan["report_status"],
            "report_planning_ready",
        )

    def test_job_package_creates_spreadsheet_structural_reports(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        spreadsheet_structural_report = read_json(
            result.spreadsheet_structural_report_json_path
        )
        markdown = result.spreadsheet_structural_report_markdown_path.read_text(
            encoding="utf-8",
        )

        self.assertTrue(result.spreadsheet_structural_report_json_path.exists())
        self.assertTrue(
            result.spreadsheet_structural_report_markdown_path.exists()
        )
        self.assertEqual(
            spreadsheet_structural_report["report_type"],
            "personal_ai_local_spreadsheet_structural_report",
        )
        self.assertIn("# Spreadsheet Structural Report", markdown)

    def test_input_snapshot_records_non_authority_metadata_only_capture(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        snapshot = read_json(result.input_snapshot_path)

        self.assertEqual(
            set(snapshot),
            {
                "snapshot_type",
                "authority",
                "execution_capability",
                "input_dir",
                "recursive",
                "include_hidden",
                "captured_by",
                "input_file_contents_copied",
                "input_mutation_performed",
            },
        )
        self.assertEqual(snapshot["authority"], "non_authority")
        self.assertEqual(snapshot["execution_capability"], "not_introduced")
        self.assertEqual(snapshot["captured_by"], "metadata_hash_only")
        self.assertIs(snapshot["input_file_contents_copied"], False)
        self.assertIs(snapshot["input_mutation_performed"], False)

    def test_job_summary_records_boundaries_and_human_review_only_next_action(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        summary = read_json(result.job_summary_path)

        self.assertEqual(
            set(summary),
            {
                "summary_type",
                "authority",
                "execution_capability",
                "job_id",
                "job_dir",
                "input_dir",
                "artifacts",
                "supplemental_artifacts",
                "counts",
                "candidate_tasks",
                "route_type",
                "recommended_processor_lane",
                "spreadsheet_plan_status",
                "spreadsheet_artifact_count",
                "spreadsheet_inspected_files",
                "spreadsheet_unsupported_files",
                "spreadsheet_parse_error_files",
                "spreadsheet_report_status",
                "spreadsheet_issue_categories",
                "spreadsheet_structural_report_status",
                "required_human_approval",
                "boundaries",
                "next_allowed_action",
            },
        )
        self.assertEqual(summary["authority"], "non_authority")
        self.assertEqual(summary["execution_capability"], "not_introduced")
        self.assertEqual(summary["route_type"], "document_route")
        self.assertEqual(
            summary["recommended_processor_lane"],
            "document_processor_planning_only",
        )
        self.assertEqual(summary["spreadsheet_plan_status"], "not_applicable")
        self.assertEqual(summary["spreadsheet_artifact_count"], 0)
        self.assertEqual(summary["spreadsheet_inspected_files"], 0)
        self.assertEqual(summary["spreadsheet_unsupported_files"], 0)
        self.assertEqual(summary["spreadsheet_parse_error_files"], 0)
        self.assertEqual(summary["spreadsheet_report_status"], "no_inspection_data")
        self.assertEqual(
            summary["spreadsheet_issue_categories"],
            ["no_csv_tsv_files_inspected", "no_structural_issues_detected"],
        )
        self.assertEqual(
            summary["spreadsheet_structural_report_status"],
            "no_inspection_data",
        )
        self.assertIs(summary["required_human_approval"], True)
        self.assertEqual(summary["next_allowed_action"], "human_review_only")
        self.assertEqual(set(summary["boundaries"]), EXPECTED_BOUNDARIES)
        self.assertTrue(all(summary["boundaries"].values()))

    def test_task_route_fields_propagate_to_job_summary(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        task_route = read_json(result.task_route_path)
        summary = read_json(result.job_summary_path)

        self.assertEqual(summary["route_type"], task_route["route_type"])
        self.assertEqual(
            summary["recommended_processor_lane"],
            task_route["recommended_processor_lane"],
        )

    def test_spreadsheet_plan_status_propagates_to_job_summary(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        spreadsheet_plan = read_json(result.spreadsheet_processor_plan_path)
        summary = read_json(result.job_summary_path)

        self.assertEqual(
            summary["spreadsheet_plan_status"],
            spreadsheet_plan["plan_status"],
        )
        self.assertEqual(summary["spreadsheet_plan_status"], "planning_ready")

    def test_spreadsheet_artifact_count_propagates_to_job_summary(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        (input_dir / "other.xlsx").write_text("not inspected", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        spreadsheet_plan = read_json(result.spreadsheet_processor_plan_path)
        summary = read_json(result.job_summary_path)

        self.assertEqual(
            summary["spreadsheet_artifact_count"],
            spreadsheet_plan["artifact_count"],
        )
        self.assertEqual(summary["spreadsheet_artifact_count"], 2)

    def test_spreadsheet_inspection_summary_propagates_to_job_summary(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        (input_dir / "bad.csv").write_bytes(b"\xff\xfeinvalid")
        (input_dir / "book.xlsx").write_text("unsupported", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        spreadsheet_inspection = read_json(
            result.spreadsheet_readonly_inspection_path
        )
        summary = read_json(result.job_summary_path)

        self.assertEqual(
            spreadsheet_inspection["summary"]["inspected_files"],
            1,
        )
        self.assertEqual(
            spreadsheet_inspection["summary"]["unsupported_files"],
            1,
        )
        self.assertEqual(
            spreadsheet_inspection["summary"]["parse_error_files"],
            1,
        )
        self.assertEqual(summary["spreadsheet_inspected_files"], 1)
        self.assertEqual(summary["spreadsheet_unsupported_files"], 1)
        self.assertEqual(summary["spreadsheet_parse_error_files"], 1)

    def test_spreadsheet_report_summary_propagates_to_job_summary(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        report_plan = read_json(result.spreadsheet_report_plan_path)
        structural_report = read_json(result.spreadsheet_structural_report_json_path)
        summary = read_json(result.job_summary_path)

        self.assertEqual(
            summary["spreadsheet_report_status"],
            report_plan["report_status"],
        )
        self.assertEqual(
            summary["spreadsheet_issue_categories"],
            report_plan["issue_categories"],
        )
        self.assertEqual(
            summary["spreadsheet_structural_report_status"],
            structural_report["report_status"],
        )

    def test_human_next_steps_records_review_boundary_and_forbidden_actions(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        markdown = result.human_next_steps_path.read_text(encoding="utf-8")

        self.assertIn("# Personal AI Local Job Package Review", markdown)
        self.assertIn("job id: job-001", markdown)
        self.assertIn("non_authority", markdown)
        self.assertIn("not_introduced", markdown)
        self.assertIn("required human approval: true", markdown)
        self.assertIn("human_review_only", markdown)
        self.assertIn("route type: document_route", markdown)
        self.assertIn(
            "recommended processor lane: document_processor_planning_only",
            markdown,
        )
        self.assertIn("spreadsheet plan status: not_applicable", markdown)
        self.assertIn("spreadsheet artifact count: 0", markdown)
        self.assertIn("spreadsheet inspected files: 0", markdown)
        self.assertIn("spreadsheet unsupported files: 0", markdown)
        self.assertIn("spreadsheet parse error files: 0", markdown)
        self.assertIn("spreadsheet report status: no_inspection_data", markdown)
        self.assertIn(
            "spreadsheet issue categories: "
            "no_csv_tsv_files_inspected, no_structural_issues_detected",
            markdown,
        )
        self.assertIn(
            "spreadsheet structural report status: no_inspection_data",
            markdown,
        )
        for action in (
            "modify input files",
            "delete input files",
            "move input files",
            "rename input files",
            "execute files",
            "write spreadsheet outputs",
            "copy raw cell values",
            "infer semantic meaning",
            "assign issue severity",
            "call network",
            "call AI APIs",
            "run subprocess",
            "control external tools",
        ):
            self.assertIn(action, markdown)

    def test_human_next_steps_records_spreadsheet_inspection_summary(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        (input_dir / "book.xlsx").write_text("unsupported", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        markdown = result.human_next_steps_path.read_text(encoding="utf-8")

        self.assertIn("spreadsheet_readonly_inspection.json", markdown)
        self.assertIn("spreadsheet_report_plan.json", markdown)
        self.assertIn("spreadsheet_structural_report.json", markdown)
        self.assertIn("spreadsheet_structural_report.md", markdown)
        self.assertIn("final_job_manifest.json", markdown)
        self.assertIn("spreadsheet inspected files: 1", markdown)
        self.assertIn("spreadsheet unsupported files: 1", markdown)
        self.assertIn("spreadsheet parse error files: 0", markdown)
        self.assertIn("spreadsheet report status: report_planning_ready", markdown)
        self.assertIn(
            "spreadsheet issue categories: unsupported_spreadsheet_extension",
            markdown,
        )
        self.assertIn(
            "spreadsheet structural report status: report_planning_ready",
            markdown,
        )

    def test_candidate_tasks_propagate_to_result_summary_and_human_next_steps(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")
        (input_dir / "tool.py").write_text("print('x')", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        summary = read_json(result.job_summary_path)
        markdown = result.human_next_steps_path.read_text(encoding="utf-8")

        self.assertEqual(summary["candidate_tasks"], result.candidate_tasks)
        for task in result.candidate_tasks:
            self.assertIn(task, markdown)
        self.assertEqual(
            result.candidate_tasks,
            ["document_review", "code_inventory", "mixed_file_inventory"],
        )

    def test_input_files_are_not_modified(self):
        input_dir, output_root_dir = self.build_workspace()
        notes = input_dir / "notes.md"
        data = input_dir / "data.csv"
        notes.write_text("notes", encoding="utf-8")
        data.write_text("a,b\n1,2\n", encoding="utf-8")
        before = {
            path: (path.read_bytes(), path.stat().st_mtime_ns)
            for path in (notes, data)
        }

        build_local_job_package(input_dir, output_root_dir, job_id="job-001")

        for path, (expected_bytes, expected_mtime) in before.items():
            self.assertEqual(path.read_bytes(), expected_bytes)
            self.assertEqual(path.stat().st_mtime_ns, expected_mtime)
            self.assertTrue(path.exists())

    def test_does_not_copy_input_file_contents_into_job_package(self):
        input_dir, output_root_dir = self.build_workspace()
        sentinel = "SECRET_SENTINEL_DO_NOT_COPY_7f5c5e2d"
        (input_dir / "notes.md").write_text("notes", encoding="utf-8")
        (input_dir / "secret.txt").write_text(sentinel, encoding="utf-8")
        (input_dir / "data.csv").write_text(
            f"header\n{sentinel}\n",
            encoding="utf-8",
        )

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )

        for artifact_path in result.job_dir.iterdir():
            self.assertNotIn(
                sentinel,
                artifact_path.read_text(encoding="utf-8"),
                msg=artifact_path.name,
            )

    def test_rejects_output_root_dir_inside_input_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_root_dir = input_dir / "packages"
            output_root_dir.mkdir(parents=True)

            with self.assertRaises(ValueError):
                build_local_job_package(
                    input_dir,
                    output_root_dir,
                    job_id="job-001",
                )

    def test_rejects_missing_input_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root_dir = Path(temp_dir) / "packages"
            output_root_dir.mkdir()

            with self.assertRaises(ValueError):
                build_local_job_package(
                    Path(temp_dir) / "missing",
                    output_root_dir,
                    job_id="job-001",
                )

    def test_rejects_non_directory_input_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_file = root / "input.txt"
            output_root_dir = root / "packages"
            input_file.write_text("not a directory", encoding="utf-8")
            output_root_dir.mkdir()

            with self.assertRaises(ValueError):
                build_local_job_package(
                    input_file,
                    output_root_dir,
                    job_id="job-001",
                )

    def test_rejects_missing_output_root_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            input_dir.mkdir()

            with self.assertRaises(ValueError):
                build_local_job_package(
                    input_dir,
                    Path(temp_dir) / "missing",
                    job_id="job-001",
                )

    def test_rejects_non_directory_output_root_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_file = root / "packages.txt"
            input_dir.mkdir()
            output_file.write_text("not a directory", encoding="utf-8")

            with self.assertRaises(ValueError):
                build_local_job_package(
                    input_dir,
                    output_file,
                    job_id="job-001",
                )

    def test_rejects_invalid_job_id_values(self):
        input_dir, output_root_dir = self.build_workspace()
        invalid_job_ids = [
            "",
            ".hidden",
            "../escape",
            "nested/path",
            "nested\\path",
            "bad space",
            "bad:colon",
        ]

        for invalid_job_id in invalid_job_ids:
            with self.subTest(job_id=invalid_job_id):
                with self.assertRaises(ValueError):
                    build_local_job_package(
                        input_dir,
                        output_root_dir,
                        job_id=invalid_job_id,
                    )

    def test_rejects_existing_job_dir(self):
        input_dir, output_root_dir = self.build_workspace()
        (output_root_dir / "job-001").mkdir()

        with self.assertRaises(ValueError):
            build_local_job_package(input_dir, output_root_dir, job_id="job-001")

    def test_recursive_option_propagates(self):
        input_dir, output_root_dir = self.build_workspace()
        nested = input_dir / "nested"
        nested.mkdir()
        (input_dir / "root.txt").write_text("root", encoding="utf-8")
        (nested / "child.txt").write_text("child", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
            recursive=True,
        )

        snapshot = read_json(result.input_snapshot_path)
        entries = read_jsonl(result.intake_ledger_path)
        self.assertIs(snapshot["recursive"], True)
        self.assertEqual(
            [entry["relative_path"] for entry in entries],
            ["nested/child.txt", "root.txt"],
        )

    def test_include_hidden_option_propagates(self):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / ".hidden.txt").write_text("hidden", encoding="utf-8")
        (input_dir / "visible.txt").write_text("visible", encoding="utf-8")

        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
            include_hidden=True,
        )

        snapshot = read_json(result.input_snapshot_path)
        entries = read_jsonl(result.intake_ledger_path)
        self.assertIs(snapshot["include_hidden"], True)
        self.assertEqual(
            [entry["relative_path"] for entry in entries],
            [".hidden.txt", "visible.txt"],
        )

    def test_deterministic_output_for_same_job_id_with_fresh_output_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            first_output_root = root / "packages-a"
            second_output_root = root / "packages-b"
            input_dir.mkdir()
            first_output_root.mkdir()
            second_output_root.mkdir()
            (input_dir / "b.txt").write_text("b", encoding="utf-8")
            (input_dir / "a.csv").write_text("a,b\n1,2\n", encoding="utf-8")

            first = build_local_job_package(
                input_dir,
                first_output_root,
                job_id="job-001",
            )
            second = build_local_job_package(
                input_dir,
                second_output_root,
                job_id="job-001",
            )

            first_summary = read_json(first.job_summary_path)
            second_summary = read_json(second.job_summary_path)
            self.assertEqual(first.candidate_tasks, second.candidate_tasks)
            self.assertEqual(first.files_recorded, second.files_recorded)
            self.assertEqual(
                first_summary["candidate_tasks"],
                second_summary["candidate_tasks"],
            )
            self.assertEqual(first_summary["counts"], second_summary["counts"])
            self.assertEqual(
                first_summary["boundaries"],
                second_summary["boundaries"],
            )
            self.assertEqual(first_summary["route_type"], second_summary["route_type"])
            self.assertEqual(
                first_summary["recommended_processor_lane"],
                second_summary["recommended_processor_lane"],
            )
            self.assertEqual(
                read_json(first.task_route_path)["route_type"],
                read_json(second.task_route_path)["route_type"],
            )
            self.assertEqual(
                read_json(first.task_route_path)["recommended_processor_lane"],
                read_json(second.task_route_path)["recommended_processor_lane"],
            )
            first_plan = read_json(first.spreadsheet_processor_plan_path)
            second_plan = read_json(second.spreadsheet_processor_plan_path)
            self.assertEqual(
                first_plan["plan_status"],
                second_plan["plan_status"],
            )
            self.assertEqual(
                first_plan["artifact_count"],
                second_plan["artifact_count"],
            )
            self.assertEqual(
                first_plan["selected_spreadsheet_artifacts"],
                second_plan["selected_spreadsheet_artifacts"],
            )
            self.assertEqual(
                first_plan["non_executing_plan"],
                second_plan["non_executing_plan"],
            )
            first_inspection = read_json(
                first.spreadsheet_readonly_inspection_path
            )
            second_inspection = read_json(
                second.spreadsheet_readonly_inspection_path
            )
            self.assertEqual(
                first_inspection["summary"],
                second_inspection["summary"],
            )
            self.assertEqual(
                first_inspection["supported_extensions"],
                second_inspection["supported_extensions"],
            )
            self.assertEqual(
                first_inspection["unsupported_extensions"],
                second_inspection["unsupported_extensions"],
            )
            first_report_plan = read_json(first.spreadsheet_report_plan_path)
            second_report_plan = read_json(second.spreadsheet_report_plan_path)
            self.assertEqual(
                first_report_plan["report_status"],
                second_report_plan["report_status"],
            )
            self.assertEqual(
                first_report_plan["issue_categories"],
                second_report_plan["issue_categories"],
            )
            self.assertEqual(
                first_report_plan["planned_sections"],
                second_report_plan["planned_sections"],
            )
            first_structural_report = read_json(
                first.spreadsheet_structural_report_json_path
            )
            second_structural_report = read_json(
                second.spreadsheet_structural_report_json_path
            )
            self.assertEqual(
                first_structural_report["report_status"],
                second_structural_report["report_status"],
            )
            self.assertEqual(
                first_structural_report["issue_categories"],
                second_structural_report["issue_categories"],
            )
            self.assertEqual(
                first_structural_report["summary"],
                second_structural_report["summary"],
            )
            self.assertEqual(
                first_structural_report["structural_metrics"],
                second_structural_report["structural_metrics"],
            )
            self.assertEqual(
                _stable_ledger(read_jsonl(first.intake_ledger_path)),
                _stable_ledger(read_jsonl(second.intake_ledger_path)),
            )


def _stable_ledger(entries):
    return [
        (
            entry["relative_path"],
            entry["size_bytes"],
            entry["sha256"],
        )
        for entry in entries
    ]


if __name__ == "__main__":
    unittest.main()
