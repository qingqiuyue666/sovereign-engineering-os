"""P2-01 read-only evidence/replay readiness envelope tests."""

from __future__ import annotations

import copy
import inspect
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

import kernel.lifecycle.evidence_replay_readiness as readiness_module
from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.lifecycle.evidence_replay_readiness import (
    EvidenceReplayReadinessEnvelope,
    build_evidence_replay_readiness_envelope,
    evidence_replay_readiness_manifest,
    render_evidence_replay_readiness_envelope,
)
from kernel.stores.sqlite.repositories import AuditRepository
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection


def _item(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "task_id": "task-001",
        "record_type": "evidence_closure",
        "artifact_refs": ["ra-001"],
        "stage": "evidence",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


class TestEvidenceReplayReadinessEnvelope(unittest.TestCase):
    def test_valid_rendered_item_sequence_ready(self) -> None:
        result = build_evidence_replay_readiness_envelope(
            [_item(), _item(record_type="stage_entered", artifact_refs=["ra-002"])]
        )

        self.assertIsInstance(result, EvidenceReplayReadinessEnvelope)
        self.assertTrue(result.ready)
        self.assertEqual(result.reason_code, "ready")
        self.assertEqual(result.failures, ())
        self.assertEqual(result.envelope["item_count"], 2)
        self.assertEqual(result.envelope["unique_task_count"], 1)
        self.assertEqual(result.envelope["task_ids"], ["task-001"])
        self.assertTrue(result.envelope["operator_safe"])

    def test_non_sequence_rejected(self) -> None:
        result = build_evidence_replay_readiness_envelope({"task_id": "x"})

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "invalid_evidence_replay")
        self.assertEqual(result.failures, ("items_not_sequence",))

    def test_string_sequence_rejected(self) -> None:
        result = build_evidence_replay_readiness_envelope("not-items")

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("items_not_sequence",))

    def test_empty_sequence_rejected(self) -> None:
        result = build_evidence_replay_readiness_envelope([])

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "invalid_evidence_replay")
        self.assertEqual(result.failures, ("items_empty",))
        self.assertEqual(result.envelope["item_count"], 0)

    def test_malformed_item_rejected(self) -> None:
        result = build_evidence_replay_readiness_envelope([{"task_id": "x"}])

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "invalid_evidence_replay")
        self.assertEqual(result.failures, ("item_shape_invalid",))

    def test_invalid_item_type_rejected(self) -> None:
        result = build_evidence_replay_readiness_envelope([object()])

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("item_invalid_type",))

    def test_invalid_task_id_rejected(self) -> None:
        result = build_evidence_replay_readiness_envelope(
            [_item(task_id="")]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("task_id_invalid",))

    def test_invalid_record_type_rejected(self) -> None:
        result = build_evidence_replay_readiness_envelope(
            [_item(record_type="")]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("record_type_invalid",))

    def test_invalid_artifact_ref_rejected(self) -> None:
        result = build_evidence_replay_readiness_envelope(
            [_item(artifact_refs=["ra-001", None])]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "invalid_evidence_replay")
        self.assertEqual(result.failures, ("artifact_ref_invalid",))

    def test_duplicate_artifact_ref_detected(self) -> None:
        result = build_evidence_replay_readiness_envelope(
            [_item(), _item(record_type="stage_entered")]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "not_ready")
        self.assertEqual(result.failures, ("duplicate_artifact_ref",))
        self.assertEqual(result.envelope["duplicate_artifact_refs"], ["ra-001"])
        self.assertFalse(result.envelope["operator_safe"])

    def test_missing_artifact_ref_counted_and_not_ready(self) -> None:
        result = build_evidence_replay_readiness_envelope(
            [_item(artifact_refs=[])]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "not_ready")
        self.assertEqual(result.failures, ("missing_artifact_ref",))
        self.assertEqual(result.envelope["missing_artifact_ref_count"], 1)
        self.assertEqual(result.envelope["artifact_ref_count"], 0)

    def test_singular_missing_artifact_ref_counted(self) -> None:
        result = build_evidence_replay_readiness_envelope(
            [
                {
                    "task_id": "task-001",
                    "record_type": "evidence_closure",
                    "artifact_ref": None,
                    "stage": None,
                    "created_at": None,
                }
            ]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("missing_artifact_ref",))
        self.assertEqual(result.envelope["missing_artifact_ref_count"], 1)

    def test_mixed_task_ids_detected(self) -> None:
        result = build_evidence_replay_readiness_envelope(
            [_item(), _item(task_id="task-002", artifact_refs=["ra-002"])]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "not_ready")
        self.assertEqual(result.failures, ("mixed_task_ids",))
        self.assertEqual(result.envelope["task_ids"], ["task-001", "task-002"])

    def test_record_type_counts_deterministic(self) -> None:
        result = build_evidence_replay_readiness_envelope(
            [
                _item(record_type="stage_entered", artifact_refs=["ra-002"]),
                _item(record_type="evidence_closure", artifact_refs=["ra-001"]),
                _item(record_type="stage_entered", artifact_refs=["ra-003"]),
            ]
        )

        self.assertTrue(result.ready)
        self.assertEqual(
            result.envelope["record_type_counts"],
            {"evidence_closure": 1, "stage_entered": 2},
        )

    def test_stage_counts_deterministic(self) -> None:
        result = build_evidence_replay_readiness_envelope(
            [
                _item(stage="sealed", artifact_refs=["ra-002"]),
                _item(stage="evidence", artifact_refs=["ra-001"]),
                _item(
                    stage=None,
                    payload={"stage": "evidence"},
                    artifact_refs=["ra-003"],
                ),
            ]
        )

        self.assertTrue(result.ready)
        self.assertEqual(
            result.envelope["stage_counts"], {"evidence": 2, "sealed": 1}
        )

    def test_invalid_stage_rejected(self) -> None:
        result = build_evidence_replay_readiness_envelope(
            [_item(stage=object())]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("stage_invalid",))

    def test_invalid_created_at_rejected(self) -> None:
        result = build_evidence_replay_readiness_envelope(
            [_item(created_at=object())]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("created_at_invalid",))

    def test_input_not_mutated(self) -> None:
        items = [_item(payload={"stage": "evidence"})]
        original = copy.deepcopy(items)

        build_evidence_replay_readiness_envelope(items)

        self.assertEqual(items, original)

    def test_output_json_safe(self) -> None:
        result = build_evidence_replay_readiness_envelope([_item()])
        rendered = render_evidence_replay_readiness_envelope(result)

        json.dumps(rendered, sort_keys=True)

    def test_no_runtime_repr_leakage(self) -> None:
        result = build_evidence_replay_readiness_envelope([object()])
        rendered = render_evidence_replay_readiness_envelope(result)
        encoded = json.dumps(rendered, sort_keys=True)

        self.assertNotIn("object at 0x", encoded)
        self.assertNotIn("<", encoded)
        self.assertNotIn(">", encoded)


class TestEvidenceReplayReadinessManifestAndRenderer(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            evidence_replay_readiness_manifest(),
            {
                "surface": "evidence_replay_readiness",
                "version": 1,
                "input_shape": (
                    "rendered audit_records rows: task_id, record_type, "
                    "artifact_refs, optional stage, created_at"
                ),
                "restore_supported": False,
                "durable_writes": False,
                "cli_commands": [],
                "runtime_dependencies": [],
                "json_safe": True,
                "reason_codes": [
                    "invalid_evidence_replay",
                    "not_ready",
                    "ready",
                ],
                "failure_values": [
                    "items_not_sequence",
                    "items_empty",
                    "item_invalid_type",
                    "item_shape_invalid",
                    "task_id_invalid",
                    "record_type_invalid",
                    "artifact_ref_invalid",
                    "stage_invalid",
                    "created_at_invalid",
                    "duplicate_artifact_ref",
                    "missing_artifact_ref",
                    "mixed_task_ids",
                ],
            },
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = evidence_replay_readiness_manifest()
        manifest["cli_commands"] = ["bad"]
        manifest["failure_values"].append("bad")  # type: ignore[union-attr]

        fresh = evidence_replay_readiness_manifest()
        self.assertEqual(fresh["cli_commands"], [])
        self.assertNotIn("bad", fresh["failure_values"])

    def test_renderer_exact_shape(self) -> None:
        result = build_evidence_replay_readiness_envelope([_item()])

        rendered = render_evidence_replay_readiness_envelope(result)

        self.assertEqual(
            sorted(rendered.keys()),
            ["envelope", "failures", "ready", "reason_code"],
        )
        self.assertEqual(rendered["ready"], True)
        self.assertEqual(rendered["reason_code"], "ready")
        self.assertEqual(rendered["failures"], [])
        self.assertEqual(rendered["envelope"], result.envelope)

    def test_renderer_defensive_copy(self) -> None:
        result = build_evidence_replay_readiness_envelope([_item()])
        rendered = render_evidence_replay_readiness_envelope(result)

        rendered_envelope = rendered["envelope"]
        self.assertIsInstance(rendered_envelope, dict)
        rendered_envelope["task_ids"] = ["mutated"]  # type: ignore[index]

        self.assertEqual(result.envelope["task_ids"], ["task-001"])

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            readiness_module.__all__,
            [
                "EvidenceReplayReadinessEnvelope",
                "build_evidence_replay_readiness_envelope",
                "evidence_replay_readiness_manifest",
                "render_evidence_replay_readiness_envelope",
            ],
        )

    def test_no_restore_cli_db_or_runtime_source_creep(self) -> None:
        source = inspect.getsource(readiness_module)

        self.assertNotIn("sqlite", source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("os.environ", source)
        self.assertNotIn("open_connection", source)
        self.assertNotIn("AuditRepository", source)
        self.assertNotIn("UnitOfWork", source)
        self.assertNotIn("def restore", source)
        self.assertNotIn("click", source)
        self.assertNotIn("argparse", source)
        self.assertNotIn("asyncio", source)


class TestEvidenceReplayReadinessRealRecordAcceptance(unittest.TestCase):
    def test_real_audit_record_rendered_into_envelope_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "evidence-readiness.db")
            conn = open_connection(db_path)
            try:
                apply_migrations(conn)
                ledger = AppendOnlyLedger(
                    repository=AuditRepository(conn),
                    actor_identity="evidence-readiness-test",
                )
                audit_id = ledger.append(
                    record_type="evidence_closure",
                    task_id="task-real",
                    root_revision_id="rev-real",
                    artifact_refs=["ra-real", "rev-real"],
                    payload={"stage": "evidence"},
                    replay_anchor_id="ra-real",
                )
                before_count = conn.execute(
                    "SELECT COUNT(*) FROM audit_records;"
                ).fetchone()[0]
                row = conn.execute(
                    "SELECT * FROM audit_records WHERE audit_record_id = ?;",
                    (audit_id,),
                ).fetchone()
                self.assertIsNotNone(row)

                payload = json.loads(row["payload_json"])
                rendered = {
                    "task_id": row["task_id"],
                    "record_type": row["record_type"],
                    "artifact_refs": json.loads(row["artifact_refs"]),
                    "stage": payload.get("stage"),
                    "created_at": row["created_at"],
                }
                result = build_evidence_replay_readiness_envelope([rendered])
                after_count = conn.execute(
                    "SELECT COUNT(*) FROM audit_records;"
                ).fetchone()[0]
            finally:
                conn.close()

        self.assertTrue(result.ready)
        self.assertEqual(result.reason_code, "ready")
        self.assertEqual(result.envelope["artifact_ref_count"], 2)
        self.assertEqual(
            result.envelope["record_type_counts"], {"evidence_closure": 1}
        )
        self.assertEqual(result.envelope["stage_counts"], {"evidence": 1})
        self.assertEqual(before_count, after_count)


if __name__ == "__main__":
    unittest.main()
