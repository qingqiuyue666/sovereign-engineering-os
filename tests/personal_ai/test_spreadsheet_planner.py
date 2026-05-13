import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.spreadsheet_planner import (
    SpreadsheetProcessorPlanResult,
    build_spreadsheet_processor_plan,
)


EXPECTED_KEYS = {
    "plan_type",
    "plan_status",
    "authority",
    "execution_capability",
    "required_human_approval",
    "source_artifacts",
    "compatible_route_types",
    "observed_route_type",
    "recommended_processor_lane",
    "selected_spreadsheet_artifacts",
    "artifact_count",
    "total_bytes",
    "non_executing_plan",
    "forbidden_actions",
    "boundaries",
    "next_allowed_action",
}

EXPECTED_FORBIDDEN_ACTIONS = {
    "modify_input_files",
    "delete_input_files",
    "move_input_files",
    "rename_input_files",
    "execute_files",
    "read_spreadsheet_cell_contents",
    "write_spreadsheet_outputs",
    "call_network",
    "call_ai_api",
    "run_subprocess",
    "control_external_tools",
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
    "no_spreadsheet_content_read",
    "no_spreadsheet_output_write",
    "no_input_file_mutation",
    "no_input_content_copy",
    "no_destructive_actions",
}

SPREADSHEET_EXTENSIONS = [".csv", ".tsv", ".xlsx", ".xlsm", ".xls"]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def profile_entry(
    relative_path,
    *,
    extension,
    category,
    size_bytes=10,
    modified_time_ns=100,
):
    return {
        "relative_path": relative_path,
        "extension": extension,
        "size_bytes": size_bytes,
        "sha256": f"{size_bytes:064x}"[-64:],
        "modified_time_ns": modified_time_ns,
        "category": category,
    }


class SpreadsheetPlannerTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        return (
            root / "artifact_profile.json",
            root / "task_route.json",
            root / "spreadsheet_processor_plan.json",
        )

    def write_inputs(self, entries, route_type, recommended_lane=None):
        artifact_profile_path, task_route_path, output_plan_path = (
            self.build_workspace()
        )
        artifact_profile_path.write_text(
            json.dumps(
                {
                    "total_files": len(entries),
                    "total_bytes": sum(entry["size_bytes"] for entry in entries),
                    "entries": list(entries),
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        task_route_path.write_text(
            json.dumps(
                {
                    "route_type": route_type,
                    "recommended_processor_lane": recommended_lane
                    or f"{route_type}_planning_only",
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return artifact_profile_path, task_route_path, output_plan_path

    def build_plan(self, entries, route_type):
        artifact_profile_path, task_route_path, output_plan_path = (
            self.write_inputs(entries, route_type)
        )
        result = build_spreadsheet_processor_plan(
            artifact_profile_path,
            task_route_path,
            output_plan_path,
        )
        return result, read_json(output_plan_path), output_plan_path

    def test_generates_planning_ready_for_spreadsheet_route_with_spreadsheet_artifacts(self):
        entry = profile_entry(
            "data.csv",
            extension=".csv",
            category="spreadsheet",
            size_bytes=12,
        )

        result, plan, output_plan_path = self.build_plan(
            [entry],
            "spreadsheet_route",
        )

        self.assertIsInstance(result, SpreadsheetProcessorPlanResult)
        self.assertEqual(result.output_plan_path, output_plan_path)
        self.assertEqual(result.plan_status, "planning_ready")
        self.assertEqual(plan["plan_status"], "planning_ready")
        self.assertEqual(plan["artifact_count"], 1)
        self.assertEqual(plan["total_bytes"], 12)
        self.assertEqual(set(plan), EXPECTED_KEYS)
        self.assertEqual(
            plan["plan_type"],
            "personal_ai_local_spreadsheet_processor_plan",
        )

    def test_generates_planning_ready_for_mixed_inventory_route_with_spreadsheet_artifacts(self):
        entries = [
            profile_entry("notes.md", extension=".md", category="document"),
            profile_entry("data.xlsx", extension=".xlsx", category="spreadsheet"),
        ]

        result, plan, _ = self.build_plan(entries, "mixed_inventory_route")

        self.assertEqual(result.plan_status, "planning_ready")
        self.assertEqual(plan["plan_status"], "planning_ready")
        self.assertEqual(plan["observed_route_type"], "mixed_inventory_route")

    def test_generates_not_applicable_for_document_route(self):
        entry = profile_entry(
            "data.csv",
            extension=".csv",
            category="spreadsheet",
        )

        result, plan, _ = self.build_plan([entry], "document_route")

        self.assertEqual(result.plan_status, "not_applicable")
        self.assertEqual(plan["plan_status"], "not_applicable")
        self.assertEqual(plan["selected_spreadsheet_artifacts"], [])
        self.assertEqual(plan["non_executing_plan"], [])
        self.assertIs(plan["required_human_approval"], True)
        self.assertEqual(plan["next_allowed_action"], "human_review_only")

    def test_generates_no_spreadsheet_artifacts_for_compatible_route_without_spreadsheets(self):
        entry = profile_entry("notes.md", extension=".md", category="document")

        result, plan, _ = self.build_plan([entry], "spreadsheet_route")

        self.assertEqual(result.plan_status, "no_spreadsheet_artifacts")
        self.assertEqual(plan["plan_status"], "no_spreadsheet_artifacts")
        self.assertEqual(plan["selected_spreadsheet_artifacts"], [])
        self.assertEqual(plan["non_executing_plan"], [])
        self.assertIs(plan["required_human_approval"], True)
        self.assertEqual(plan["next_allowed_action"], "human_review_only")

    def test_selects_only_spreadsheet_like_artifacts_from_profile_entries(self):
        entries = [
            profile_entry("data.csv", extension=".csv", category="spreadsheet"),
            profile_entry("legacy.data", extension=".data", category="spreadsheet"),
            profile_entry("notes.md", extension=".md", category="document"),
        ]

        _, plan, _ = self.build_plan(entries, "spreadsheet_route")

        self.assertEqual(
            [
                artifact["relative_path"]
                for artifact in plan["selected_spreadsheet_artifacts"]
            ],
            ["data.csv", "legacy.data"],
        )

    def test_supports_all_required_spreadsheet_like_extensions(self):
        entries = [
            profile_entry(f"data{extension}", extension=extension, category="unknown")
            for extension in SPREADSHEET_EXTENSIONS
        ]

        _, plan, _ = self.build_plan(entries, "spreadsheet_route")

        self.assertEqual(
            {
                artifact["extension"]
                for artifact in plan["selected_spreadsheet_artifacts"]
            },
            set(SPREADSHEET_EXTENSIONS),
        )

    def test_does_not_select_non_spreadsheet_artifacts(self):
        entries = [
            profile_entry("notes.md", extension=".md", category="document"),
            profile_entry("image.png", extension=".png", category="image"),
            profile_entry("script.py", extension=".py", category="code"),
        ]

        _, plan, _ = self.build_plan(entries, "spreadsheet_route")

        self.assertEqual(plan["selected_spreadsheet_artifacts"], [])
        self.assertEqual(plan["artifact_count"], 0)

    def test_produces_deterministic_sorted_selected_spreadsheet_artifacts(self):
        entries = [
            profile_entry("z.xlsx", extension=".xlsx", category="spreadsheet"),
            profile_entry("a.csv", extension=".csv", category="spreadsheet"),
            profile_entry("m.tsv", extension=".tsv", category="spreadsheet"),
        ]

        _, plan, _ = self.build_plan(entries, "spreadsheet_route")

        self.assertEqual(
            [
                artifact["relative_path"]
                for artifact in plan["selected_spreadsheet_artifacts"]
            ],
            ["a.csv", "m.tsv", "z.xlsx"],
        )

    def test_writes_non_authority(self):
        _, plan, _ = self.build_plan(
            [profile_entry("data.csv", extension=".csv", category="spreadsheet")],
            "spreadsheet_route",
        )

        self.assertEqual(plan["authority"], "non_authority")

    def test_writes_execution_capability_not_introduced(self):
        _, plan, _ = self.build_plan(
            [profile_entry("data.csv", extension=".csv", category="spreadsheet")],
            "spreadsheet_route",
        )

        self.assertEqual(plan["execution_capability"], "not_introduced")

    def test_writes_required_human_approval_true(self):
        result, plan, _ = self.build_plan(
            [profile_entry("data.csv", extension=".csv", category="spreadsheet")],
            "spreadsheet_route",
        )

        self.assertIs(result.required_human_approval, True)
        self.assertIs(plan["required_human_approval"], True)

    def test_writes_next_allowed_action_human_review_only(self):
        _, plan, _ = self.build_plan(
            [profile_entry("data.csv", extension=".csv", category="spreadsheet")],
            "spreadsheet_route",
        )

        self.assertEqual(plan["next_allowed_action"], "human_review_only")

    def test_writes_forbidden_actions_for_content_read_and_output_write(self):
        _, plan, _ = self.build_plan(
            [profile_entry("data.csv", extension=".csv", category="spreadsheet")],
            "spreadsheet_route",
        )

        self.assertEqual(set(plan["forbidden_actions"]), EXPECTED_FORBIDDEN_ACTIONS)
        self.assertIn(
            "read_spreadsheet_cell_contents",
            plan["forbidden_actions"],
        )
        self.assertIn("write_spreadsheet_outputs", plan["forbidden_actions"])

    def test_writes_all_required_boundaries(self):
        _, plan, _ = self.build_plan(
            [profile_entry("data.csv", extension=".csv", category="spreadsheet")],
            "spreadsheet_route",
        )

        self.assertEqual(set(plan["boundaries"]), EXPECTED_BOUNDARIES)
        self.assertIn("no_spreadsheet_content_read", plan["boundaries"])
        self.assertIn("no_spreadsheet_output_write", plan["boundaries"])

    def test_rejects_missing_artifact_profile_path(self):
        artifact_profile_path, task_route_path, output_plan_path = (
            self.build_workspace()
        )
        task_route_path.write_text(
            json.dumps({"route_type": "spreadsheet_route"}),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_spreadsheet_processor_plan(
                artifact_profile_path,
                task_route_path,
                output_plan_path,
            )

    def test_rejects_missing_task_route_path(self):
        artifact_profile_path, task_route_path, output_plan_path = (
            self.build_workspace()
        )
        artifact_profile_path.write_text(
            json.dumps({"entries": []}),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_spreadsheet_processor_plan(
                artifact_profile_path,
                task_route_path,
                output_plan_path,
            )

    def test_rejects_missing_output_parent(self):
        artifact_profile_path, task_route_path, output_plan_path = self.write_inputs(
            [],
            "spreadsheet_route",
        )

        with self.assertRaises(ValueError):
            build_spreadsheet_processor_plan(
                artifact_profile_path,
                task_route_path,
                output_plan_path.parent / "missing" / "plan.json",
            )

    def test_rejects_malformed_profile_missing_entries(self):
        artifact_profile_path, task_route_path, output_plan_path = (
            self.build_workspace()
        )
        artifact_profile_path.write_text(
            json.dumps({"total_files": 0}),
            encoding="utf-8",
        )
        task_route_path.write_text(
            json.dumps({"route_type": "spreadsheet_route"}),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_spreadsheet_processor_plan(
                artifact_profile_path,
                task_route_path,
                output_plan_path,
            )

    def test_rejects_malformed_task_route_missing_route_type(self):
        artifact_profile_path, task_route_path, output_plan_path = (
            self.build_workspace()
        )
        artifact_profile_path.write_text(
            json.dumps({"entries": []}),
            encoding="utf-8",
        )
        task_route_path.write_text(
            json.dumps({"recommended_processor_lane": "spreadsheet"}),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_spreadsheet_processor_plan(
                artifact_profile_path,
                task_route_path,
                output_plan_path,
            )

    def test_produces_deterministic_output(self):
        artifact_profile_path, task_route_path, first_output_path = self.write_inputs(
            [
                profile_entry(
                    "b.xlsx",
                    extension=".xlsx",
                    category="spreadsheet",
                    size_bytes=20,
                ),
                profile_entry(
                    "a.csv",
                    extension=".csv",
                    category="spreadsheet",
                    size_bytes=10,
                ),
            ],
            "spreadsheet_route",
        )
        second_output_path = first_output_path.parent / "second_plan.json"

        build_spreadsheet_processor_plan(
            artifact_profile_path,
            task_route_path,
            first_output_path,
        )
        build_spreadsheet_processor_plan(
            artifact_profile_path,
            task_route_path,
            second_output_path,
        )

        self.assertEqual(
            first_output_path.read_text(encoding="utf-8"),
            second_output_path.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
