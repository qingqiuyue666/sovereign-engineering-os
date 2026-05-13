import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.artifact_profiler import build_artifact_profile
from kernel.personal_ai.local_file_intake import build_local_file_intake_ledger
from kernel.personal_ai.review_packet import build_review_packet
from kernel.personal_ai.work_order import build_work_order_proposal


class ReviewPacketTests(unittest.TestCase):
    def build_packet(self, *, remove_original=False):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_dir = root / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        source = input_dir / "notes.md"
        source.write_text("notes", encoding="utf-8")
        ledger = output_dir / "ledger.jsonl"
        profile = output_dir / "profile.json"
        work_order = output_dir / "work_order.json"
        packet = output_dir / "review_packet.json"

        build_local_file_intake_ledger(input_dir, ledger)
        if remove_original:
            source.unlink()
        build_artifact_profile(ledger, profile)
        build_work_order_proposal(profile, work_order)
        result = build_review_packet(ledger, profile, work_order, packet)
        payload = json.loads(packet.read_text(encoding="utf-8"))
        return result, payload

    def test_builds_review_packet_from_intake_profile_and_work_order(self):
        result, payload = self.build_packet()

        self.assertEqual(result.files_recorded, 1)
        self.assertEqual(payload["packet_type"], "personal_ai_local_review_packet")
        self.assertEqual(payload["intake_summary"]["files_recorded"], 1)
        self.assertEqual(payload["artifact_summary"]["total_files"], 1)

    def test_preserves_required_human_approval_true(self):
        result, payload = self.build_packet()

        self.assertIs(result.required_human_approval, True)
        self.assertIs(payload["required_human_approval"], True)

    def test_preserves_candidate_tasks(self):
        result, payload = self.build_packet()

        self.assertEqual(result.candidate_tasks, ["document_review"])
        self.assertEqual(
            payload["proposed_work_order"]["candidate_tasks"],
            ["document_review"],
        )

    def test_marks_authority_non_authority(self):
        _result, payload = self.build_packet()

        self.assertEqual(payload["authority"], "non_authority")

    def test_marks_execution_capability_not_introduced(self):
        _result, payload = self.build_packet()

        self.assertEqual(payload["execution_capability"], "not_introduced")

    def test_sets_next_allowed_action_human_review_only(self):
        _result, payload = self.build_packet()

        self.assertEqual(payload["next_allowed_action"], "human_review_only")

    def test_includes_non_authorization_statement(self):
        _result, payload = self.build_packet()

        self.assertEqual(
            payload["non_authorization_statement"],
            (
                "This review packet does not authorize file mutation, task "
                "execution, API calls, external tool control, runtime "
                "authority, execution capability, or adapter implementation."
            ),
        )

    def test_does_not_require_original_input_files_after_artifacts_exist(self):
        result, payload = self.build_packet(remove_original=True)

        self.assertEqual(result.files_recorded, 1)
        self.assertEqual(payload["artifact_summary"]["total_files"], 1)


if __name__ == "__main__":
    unittest.main()
