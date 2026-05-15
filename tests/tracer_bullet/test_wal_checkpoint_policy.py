import json
import tempfile
import unittest
from pathlib import Path

from kernel.stores.sqlite.wal_checkpoint_policy import (
    WalCheckpointObservation,
    WalCheckpointPolicy,
    build_wal_checkpoint_plan,
    write_wal_checkpoint_plan,
)


class WalCheckpointPolicyPlannerTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def policy(self, **overrides):
        payload = {
            "policy_id": "wal-policy-v1",
            "max_wal_pages": 1000,
            "max_wal_bytes": 4_000_000,
            "max_age_seconds": 600,
            "trigger_on_snapshot": True,
            "manual_checkpoint_allowed": True,
            "truncate_allowed": False,
            "created_at": "2026-05-15T00:00:00Z",
            "version": "v1",
        }
        payload.update(overrides)
        return WalCheckpointPolicy(**payload)

    def observation(self, **overrides):
        payload = {
            "wal_pages": 10,
            "wal_bytes": 1000,
            "age_seconds": 10,
            "snapshot_creation_pending": False,
            "dirty_tail_detected": False,
            "mid_segment_corruption_detected": False,
        }
        payload.update(overrides)
        return WalCheckpointObservation(**payload)

    def test_no_threshold_reached_returns_no_checkpoint_plan(self):
        result = build_wal_checkpoint_plan(self.policy(), self.observation())

        self.assertFalse(result.checkpoint_required)
        self.assertFalse(result.execution_allowed)
        self.assertFalse(result.truncate_allowed)
        self.assertFalse(result.mutating_checkpoint_executed)
        self.assertEqual(result.plan["recommended_mode"], "none")
        self.assertEqual(result.plan["reason_codes"], [])
        self.assertTrue(result.plan["planner_only"])
        self.assertFalse(result.plan["database_opened"])
        self.assertFalse(result.plan["pragma_wal_checkpoint_executed"])
        self.assertFalse(result.plan["wal_truncate_executed"])
        self.assertFalse(result.plan["sqlite_state_mutated"])

    def test_wal_pages_threshold_requires_checkpoint(self):
        result = build_wal_checkpoint_plan(
            self.policy(max_wal_pages=1000),
            self.observation(wal_pages=1000),
        )

        self.assertTrue(result.checkpoint_required)
        self.assertIn("wal_pages_threshold_reached", result.plan["reason_codes"])
        self.assertEqual(result.plan["recommended_mode"], "passive")
        self.assertFalse(result.plan["execution_allowed"])

    def test_wal_bytes_threshold_requires_checkpoint(self):
        result = build_wal_checkpoint_plan(
            self.policy(max_wal_bytes=5000),
            self.observation(wal_bytes=5000),
        )

        self.assertTrue(result.checkpoint_required)
        self.assertIn("wal_bytes_threshold_reached", result.plan["reason_codes"])
        self.assertFalse(result.plan["execution_allowed"])

    def test_age_threshold_requires_checkpoint(self):
        result = build_wal_checkpoint_plan(
            self.policy(max_age_seconds=60),
            self.observation(age_seconds=60),
        )

        self.assertTrue(result.checkpoint_required)
        self.assertIn("wal_age_threshold_reached", result.plan["reason_codes"])
        self.assertFalse(result.plan["execution_allowed"])

    def test_snapshot_trigger_requires_checkpoint(self):
        result = build_wal_checkpoint_plan(
            self.policy(trigger_on_snapshot=True),
            self.observation(snapshot_creation_pending=True),
        )

        self.assertTrue(result.checkpoint_required)
        self.assertIn("snapshot_trigger_pending", result.plan["reason_codes"])
        self.assertFalse(result.plan["execution_allowed"])

    def test_manual_checkpoint_disallowed_recommends_no_execution_mode(self):
        result = build_wal_checkpoint_plan(
            self.policy(manual_checkpoint_allowed=False),
            self.observation(wal_pages=5000),
        )

        self.assertTrue(result.checkpoint_required)
        self.assertEqual(result.plan["recommended_mode"], "none_manual_checkpoint_not_allowed")
        self.assertFalse(result.plan["execution_allowed"])

    def test_recovery_anomalies_require_review_not_checkpoint_execution(self):
        result = build_wal_checkpoint_plan(
            self.policy(),
            self.observation(dirty_tail_detected=True, mid_segment_corruption_detected=True),
        )

        self.assertTrue(result.checkpoint_required)
        self.assertIn("dirty_tail_requires_recovery_review", result.plan["reason_codes"])
        self.assertIn("mid_segment_corruption_requires_recovery_review", result.plan["reason_codes"])
        self.assertEqual(result.plan["recommended_mode"], "none_recovery_review_required")
        self.assertFalse(result.plan["execution_allowed"])

    def test_truncate_allowed_policy_is_rejected_in_foundation(self):
        result = build_wal_checkpoint_plan(
            self.policy(truncate_allowed=True),
            self.observation(wal_pages=5000),
        )

        self.assertFalse(result.plan["complete"])
        self.assertFalse(result.checkpoint_required)
        self.assertIn("truncate_allowed_forbidden_in_foundation", result.plan["failures"])
        self.assertFalse(result.truncate_allowed)
        self.assertFalse(result.plan["wal_truncate_executed"])

    def test_invalid_policy_and_observation_are_reported_deterministically(self):
        result = build_wal_checkpoint_plan(
            self.policy(policy_id="", max_wal_pages=0, max_wal_bytes=0, max_age_seconds=0, created_at=""),
            self.observation(wal_pages=-1, wal_bytes=-1, age_seconds=-1),
        )

        self.assertFalse(result.plan["complete"])
        self.assertEqual(
            result.plan["failures"],
            sorted(
                [
                    "age_seconds_negative",
                    "created_at_missing",
                    "max_age_seconds_must_be_positive",
                    "max_wal_bytes_must_be_positive",
                    "max_wal_pages_must_be_positive",
                    "policy_id_missing",
                    "wal_bytes_negative",
                    "wal_pages_negative",
                ]
            ),
        )

    def test_mapping_inputs_are_supported_and_bool_as_int_is_rejected(self):
        result = build_wal_checkpoint_plan(
            {
                "policy_id": "wal-policy-v1",
                "max_wal_pages": 1000,
                "max_wal_bytes": 4_000_000,
                "max_age_seconds": 600,
                "trigger_on_snapshot": True,
                "manual_checkpoint_allowed": True,
                "truncate_allowed": False,
                "created_at": "2026-05-15T00:00:00Z",
                "version": "v1",
            },
            {
                "wal_pages": 1001,
                "wal_bytes": 1000,
                "age_seconds": 10,
                "snapshot_creation_pending": False,
            },
        )
        self.assertTrue(result.checkpoint_required)

        with self.assertRaisesRegex(ValueError, "max_wal_pages must be integer"):
            build_wal_checkpoint_plan(
                {
                    "policy_id": "wal-policy-v1",
                    "max_wal_pages": True,
                    "max_wal_bytes": 4_000_000,
                    "max_age_seconds": 600,
                    "trigger_on_snapshot": True,
                    "manual_checkpoint_allowed": True,
                    "truncate_allowed": False,
                    "created_at": "2026-05-15T00:00:00Z",
                    "version": "v1",
                },
                self.observation(),
            )

    def test_write_plan_requires_preexisting_output_dir_and_no_overwrite(self):
        root = self.make_output_dir()
        with self.assertRaisesRegex(ValueError, "output_dir is missing"):
            write_wal_checkpoint_plan(self.policy(), self.observation(), root / "missing")

        result = write_wal_checkpoint_plan(self.policy(), self.observation(wal_pages=1000), root)
        self.assertTrue(result.checkpoint_required)
        payload = json.loads((root / "wal_checkpoint_plan.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["plan_type"], "seos_wal_checkpoint_plan_v1")
        self.assertFalse(payload["execution_allowed"])

        with self.assertRaisesRegex(ValueError, "already exists"):
            write_wal_checkpoint_plan(self.policy(), self.observation(), root)

    def test_policy_module_does_not_execute_checkpoint_or_open_database(self):
        module = Path("kernel/stores/sqlite/wal_checkpoint_policy.py").read_text(
            encoding="utf-8"
        )
        forbidden_runtime_markers = (
            "sqlite3.connect",
            "open_connection(",
            "PRAGMA wal_checkpoint",
            "wal_checkpoint(",
            "SQLITE_CHECKPOINT_TRUNCATE",
            ".execute(\"PRAGMA",
            ".executescript",
        )
        for marker in forbidden_runtime_markers:
            self.assertNotIn(marker, module)

    def test_decision_doc_exists_and_records_foundation_posture(self):
        text = Path("docs/decisions/wal_checkpoint_policy_foundation_v1.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "WAL_CHECKPOINT_POLICY_FOUNDATION_READY_FOR_LOCAL_TESTS",
            "planner-only",
            "does not execute checkpoint",
            "does not truncate WAL",
            "execution_allowed: false",
            "mutating_checkpoint_executed: false",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
