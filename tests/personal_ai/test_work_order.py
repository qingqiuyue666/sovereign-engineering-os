import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.work_order import build_work_order_proposal


CATEGORIES = (
    "spreadsheet",
    "document",
    "image",
    "video",
    "audio",
    "archive",
    "code",
    "unknown",
)


def write_profile(path, categories):
    complete_categories = {
        category: int(categories.get(category, 0))
        for category in CATEGORIES
    }
    path.write_text(
        json.dumps(
            {
                "total_files": sum(complete_categories.values()),
                "total_bytes": 100,
                "categories": complete_categories,
                "extensions": {},
                "largest_files": [],
                "entries": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )


class WorkOrderTests(unittest.TestCase):
    def build_for_categories(self, categories):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        profile = root / "profile.json"
        output = root / "work_order.json"
        write_profile(profile, categories)
        result = build_work_order_proposal(profile, output)
        payload = json.loads(output.read_text(encoding="utf-8"))
        return result, payload

    def test_generates_spreadsheet_review_when_spreadsheet_files_exist(self):
        result, _payload = self.build_for_categories({"spreadsheet": 1})

        self.assertEqual(result.candidate_tasks, ["spreadsheet_review"])

    def test_generates_document_review_when_document_files_exist(self):
        result, _payload = self.build_for_categories({"document": 1})

        self.assertEqual(result.candidate_tasks, ["document_review"])

    def test_generates_media_inventory_when_media_files_exist(self):
        result, _payload = self.build_for_categories({"image": 1})

        self.assertEqual(result.candidate_tasks, ["media_inventory"])

    def test_generates_code_inventory_when_code_files_exist(self):
        result, _payload = self.build_for_categories({"code": 1})

        self.assertEqual(result.candidate_tasks, ["code_inventory"])

    def test_generates_archive_inventory_when_archive_files_exist(self):
        result, _payload = self.build_for_categories({"archive": 1})

        self.assertEqual(result.candidate_tasks, ["archive_inventory"])

    def test_generates_mixed_file_inventory_when_multiple_categories_exist(self):
        result, _payload = self.build_for_categories(
            {"spreadsheet": 1, "document": 1}
        )

        self.assertEqual(
            result.candidate_tasks,
            [
                "spreadsheet_review",
                "document_review",
                "mixed_file_inventory",
            ],
        )

    def test_generates_unknown_inventory_for_unknown_only_profile(self):
        result, _payload = self.build_for_categories({"unknown": 3})

        self.assertEqual(result.candidate_tasks, ["unknown_inventory"])

    def test_marks_required_human_approval_true(self):
        result, payload = self.build_for_categories({"document": 1})

        self.assertIs(result.required_human_approval, True)
        self.assertIs(payload["required_human_approval"], True)

    def test_marks_authority_non_authority(self):
        _result, payload = self.build_for_categories({"document": 1})

        self.assertEqual(payload["authority"], "non_authority")

    def test_marks_execution_capability_not_introduced(self):
        _result, payload = self.build_for_categories({"document": 1})

        self.assertEqual(payload["execution_capability"], "not_introduced")

    def test_includes_forbidden_actions(self):
        _result, payload = self.build_for_categories({"document": 1})

        self.assertEqual(
            payload["forbidden_actions"],
            [
                "modify_input_files",
                "delete_input_files",
                "move_input_files",
                "rename_input_files",
                "execute_files",
                "call_network",
                "call_ai_api",
                "run_subprocess",
                "control_external_tools",
            ],
        )


if __name__ == "__main__":
    unittest.main()
