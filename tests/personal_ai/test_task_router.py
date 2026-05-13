import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.task_router import TaskRouteResult, build_task_route


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
    "no_input_file_mutation",
    "no_input_content_copy",
    "no_destructive_actions",
}

EXPECTED_FORBIDDEN_ACTIONS = {
    "modify_input_files",
    "delete_input_files",
    "move_input_files",
    "rename_input_files",
    "execute_files",
    "call_network",
    "call_ai_api",
    "run_subprocess",
    "control_external_tools",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class TaskRouterTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        artifact_profile_path = root / "artifact_profile.json"
        work_order_path = root / "work_order_proposal.json"
        output_task_route_path = root / "task_route.json"
        return artifact_profile_path, work_order_path, output_task_route_path

    def write_inputs(self, candidate_tasks, categories=None):
        artifact_profile_path, work_order_path, output_task_route_path = (
            self.build_workspace()
        )
        profile = {
            "total_files": 1,
            "total_bytes": 10,
            "categories": categories
            or {
                "spreadsheet": 0,
                "document": 0,
                "image": 0,
                "video": 0,
                "audio": 0,
                "archive": 0,
                "code": 0,
                "unknown": 1,
            },
        }
        work_order = {
            "candidate_tasks": list(candidate_tasks),
            "required_human_approval": True,
        }
        artifact_profile_path.write_text(
            json.dumps(profile, sort_keys=True),
            encoding="utf-8",
        )
        work_order_path.write_text(
            json.dumps(work_order, sort_keys=True),
            encoding="utf-8",
        )
        return artifact_profile_path, work_order_path, output_task_route_path

    def build_route(self, candidate_tasks, categories=None):
        artifact_profile_path, work_order_path, output_task_route_path = (
            self.write_inputs(candidate_tasks, categories)
        )
        result = build_task_route(
            artifact_profile_path,
            work_order_path,
            output_task_route_path,
        )
        return result, read_json(output_task_route_path), output_task_route_path

    def assert_route(self, candidate_tasks, expected_route, expected_lane):
        result, route, _ = self.build_route(candidate_tasks)
        self.assertIsInstance(result, TaskRouteResult)
        self.assertEqual(result.route_type, expected_route)
        self.assertEqual(route["route_type"], expected_route)
        self.assertEqual(result.recommended_processor_lane, expected_lane)
        self.assertEqual(route["recommended_processor_lane"], expected_lane)

    def test_generates_mixed_inventory_route_when_mixed_file_inventory_exists(self):
        self.assert_route(
            ["spreadsheet_review", "mixed_file_inventory"],
            "mixed_inventory_route",
            "mixed_file_inventory_planning_only",
        )

    def test_generates_spreadsheet_route_without_mixed_file_inventory(self):
        self.assert_route(
            ["spreadsheet_review", "document_review"],
            "spreadsheet_route",
            "spreadsheet_processor_planning_only",
        )

    def test_generates_document_route_without_higher_priority_route(self):
        self.assert_route(
            ["document_review", "media_inventory"],
            "document_route",
            "document_processor_planning_only",
        )

    def test_generates_media_inventory_route_without_higher_priority_route(self):
        self.assert_route(
            ["media_inventory", "code_inventory"],
            "media_inventory_route",
            "media_inventory_planning_only",
        )

    def test_generates_code_inventory_route_without_higher_priority_route(self):
        self.assert_route(
            ["code_inventory", "archive_inventory"],
            "code_inventory_route",
            "code_inventory_planning_only",
        )

    def test_generates_archive_inventory_route_without_higher_priority_route(self):
        self.assert_route(
            ["archive_inventory"],
            "archive_inventory_route",
            "archive_inventory_planning_only",
        )

    def test_generates_unknown_inventory_route_when_no_known_candidate_task_exists(self):
        self.assert_route(
            ["custom_unrecognized_task"],
            "unknown_inventory_route",
            "unknown_inventory_planning_only",
        )

    def test_writes_non_authority_task_route_json(self):
        result, route, output_task_route_path = self.build_route(
            ["spreadsheet_review"]
        )

        self.assertEqual(result.output_task_route_path, output_task_route_path)
        self.assertEqual(route["authority"], "non_authority")
        self.assertEqual(
            set(route),
            {
                "route_type",
                "authority",
                "execution_capability",
                "required_human_approval",
                "recommended_processor_lane",
                "source_artifacts",
                "candidate_tasks",
                "category_counts",
                "route_reason",
                "non_executing_action_plan",
                "forbidden_actions",
                "boundaries",
                "next_allowed_action",
            },
        )

    def test_writes_execution_capability_not_introduced(self):
        _, route, _ = self.build_route(["spreadsheet_review"])

        self.assertEqual(route["execution_capability"], "not_introduced")

    def test_writes_required_human_approval_true(self):
        result, route, _ = self.build_route(["spreadsheet_review"])

        self.assertIs(result.required_human_approval, True)
        self.assertIs(route["required_human_approval"], True)

    def test_writes_next_allowed_action_human_review_only(self):
        _, route, _ = self.build_route(["spreadsheet_review"])

        self.assertEqual(route["next_allowed_action"], "human_review_only")

    def test_writes_forbidden_actions(self):
        _, route, _ = self.build_route(["spreadsheet_review"])

        self.assertEqual(set(route["forbidden_actions"]), EXPECTED_FORBIDDEN_ACTIONS)

    def test_writes_all_required_boundaries(self):
        _, route, _ = self.build_route(["spreadsheet_review"])

        self.assertEqual(set(route["boundaries"]), EXPECTED_BOUNDARIES)

    def test_rejects_missing_artifact_profile_path(self):
        artifact_profile_path, work_order_path, output_task_route_path = (
            self.build_workspace()
        )
        work_order_path.write_text(
            json.dumps({"candidate_tasks": []}),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_task_route(
                artifact_profile_path,
                work_order_path,
                output_task_route_path,
            )

    def test_rejects_missing_work_order_path(self):
        artifact_profile_path, work_order_path, output_task_route_path = (
            self.build_workspace()
        )
        artifact_profile_path.write_text(
            json.dumps({"categories": {}}),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_task_route(
                artifact_profile_path,
                work_order_path,
                output_task_route_path,
            )

    def test_rejects_missing_output_parent(self):
        artifact_profile_path, work_order_path, output_task_route_path = (
            self.write_inputs(["spreadsheet_review"])
        )

        with self.assertRaises(ValueError):
            build_task_route(
                artifact_profile_path,
                work_order_path,
                output_task_route_path.parent / "missing" / "task_route.json",
            )

    def test_rejects_malformed_profile_missing_categories(self):
        artifact_profile_path, work_order_path, output_task_route_path = (
            self.build_workspace()
        )
        artifact_profile_path.write_text(
            json.dumps({"total_files": 1}),
            encoding="utf-8",
        )
        work_order_path.write_text(
            json.dumps({"candidate_tasks": ["spreadsheet_review"]}),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_task_route(
                artifact_profile_path,
                work_order_path,
                output_task_route_path,
            )

    def test_rejects_malformed_work_order_missing_candidate_tasks(self):
        artifact_profile_path, work_order_path, output_task_route_path = (
            self.build_workspace()
        )
        artifact_profile_path.write_text(
            json.dumps({"categories": {}}),
            encoding="utf-8",
        )
        work_order_path.write_text(
            json.dumps({"required_human_approval": True}),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_task_route(
                artifact_profile_path,
                work_order_path,
                output_task_route_path,
            )

    def test_produces_deterministic_output(self):
        artifact_profile_path, work_order_path, first_output_path = (
            self.write_inputs(["spreadsheet_review", "document_review"])
        )
        second_output_path = first_output_path.parent / "task_route_second.json"

        build_task_route(artifact_profile_path, work_order_path, first_output_path)
        build_task_route(artifact_profile_path, work_order_path, second_output_path)

        self.assertEqual(
            first_output_path.read_text(encoding="utf-8"),
            second_output_path.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
