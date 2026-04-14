"""
Tracer-bullet test: projected real-fix PatchProposal → ValidationReceipt.

Proves that ``RealFixValidationBridge`` takes exactly one schema-valid
``PatchProposal`` that already came from the verified real-fix path and
produces exactly one schema-valid ``ValidationReceipt``, with an audit
cross-reference that binds the receipt to the originating
``PatchProposal`` AND the upstream ``InferenceArtifact``. Also proves
that every non-admissible input is rejected fail-closed with no
receipt row written and no bridge attestation emitted, and that rows
for unrelated task ids are not touched.

Scope:
- Uses the real ``AnthropicMessagesAdapter`` with a fake transport —
  no network.
- Uses the canonical ``make_add_fix_task`` single-file fix task.
- Uses the real repositories, schemas, and services end-to-end.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any
from uuid import uuid4

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from kernel.adapters.anthropic_adapter import (
    AnthropicMessagesAdapter,
    _TransportResponse,
)
from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.lifecycle.real_fix_patch_projector import (
    RealFixPatchProjection,
    RealFixPatchProjector,
)
from kernel.lifecycle.real_fix_recorder import (
    RealFixNarrowPathRecord,
    RealFixNarrowPathRecorder,
)
from kernel.lifecycle.real_fix_validation_bridge import (
    RealFixValidationBridge,
    RealFixValidationBridgeOutcome,
    RealFixValidationBridgeRejected,
)
from kernel.services.validation_service import (
    StaticCheckResult,
    ValidationRejected,
    ValidationService,
)
from kernel.stores.sqlite.repositories import (
    AuditRepository,
    InferenceArtifactRepository,
    PatchProposalRepository,
    ValidationReceiptRepository,
)
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection
from kernel.tracers.real_fix_tracer import (
    RealFixTracer,
    make_add_fix_task,
)
from validation.quarantine.runner_adapter import QuarantineRun, QuarantineState


CORRECT_ADD_BLOCK = (
    "```python\n"
    "def add(a, b):\n"
    "    return a + b\n"
    "```\n"
)


def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj).encode("utf-8")


def _messages_body(text: str, model: str = "claude-sonnet-4-5") -> bytes:
    return _json_bytes(
        {
            "id": "msg_fix_bridge_test",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 12, "output_tokens": 24},
        }
    )


class _AuditCapture:
    """Record every ledger append for assertion. Thin passthrough."""

    def __init__(self, ledger: AppendOnlyLedger) -> None:
        self._ledger = ledger
        self.records: list[dict[str, Any]] = []

    def append(
        self,
        *,
        record_type: str,
        task_id: str | None = None,
        root_revision_id: str | None = None,
        artifact_refs=None,
        payload=None,
        **kwargs: Any,
    ) -> None:
        self.records.append(
            {
                "record_type": record_type,
                "task_id": task_id,
                "root_revision_id": root_revision_id,
                "artifact_refs": list(artifact_refs or []),
                "payload": dict(payload or {}),
            }
        )
        self._ledger.append(
            record_type=record_type,
            task_id=task_id,
            root_revision_id=root_revision_id,
            artifact_refs=artifact_refs,
            payload=payload,
            **kwargs,
        )


class RealFixValidationBridgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.inference_repo = InferenceArtifactRepository(self.conn)
        self.patch_repo = PatchProposalRepository(self.conn)
        self.receipt_repo = ValidationReceiptRepository(self.conn)
        self.ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="real_fix_validation_bridge_test",
        )
        self.audit = _AuditCapture(self.ledger)
        self.recorder = RealFixNarrowPathRecorder(
            repository=self.inference_repo,
            audit_ledger=self.audit,
        )
        self.projector = RealFixPatchProjector(
            repository=self.patch_repo,
            audit_ledger=self.audit,
        )
        self.validation_service = ValidationService(
            repository=self.receipt_repo,
            patch_reader=self.patch_repo,
            audit_ledger=self.audit,
        )
        self.bridge = RealFixValidationBridge(
            validation_service=self.validation_service,
            patch_reader=self.patch_repo,
            receipt_reader=self.receipt_repo,
            audit_ledger=self.audit,
        )

    def tearDown(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------

    def _tracer(self, transport) -> RealFixTracer:
        adapter = AnthropicMessagesAdapter(api_key="sk-test", transport=transport)
        return RealFixTracer(
            adapter=adapter,
            audit_ledger=self.audit,
            narrow_path_recorder=self.recorder,
        )

    def _count(self, table: str) -> int:
        return self.conn.execute(
            f"SELECT COUNT(*) FROM {table};"
        ).fetchone()[0]

    def _records_of(self, record_type: str) -> list[dict[str, Any]]:
        return [r for r in self.audit.records if r["record_type"] == record_type]

    def _project(self, task_id: str) -> RealFixPatchProjection:
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        task = make_add_fix_task(task_id=task_id)
        tracer = self._tracer(t)
        result = tracer.run(task)
        self.assertTrue(result.verified)
        inf = self.inference_repo.fetch(result.inference_artifact_id)
        self.assertIsNotNone(inf)
        record = RealFixNarrowPathRecord(
            inference_artifact_id=result.inference_artifact_id,
            context_artifact_id=inf["context_artifact_id"],
            root_revision_id=inf["root_revision_id"],
            output_hash=inf["output_hash"],
            replay_ceiling=result.replay_ceiling,
        )
        return self.projector.project(task=task, result=result, record=record)

    # ------------------------------------------------------------------
    # Success: projected patch → exactly one schema-valid receipt
    # ------------------------------------------------------------------

    def test_bridge_produces_one_schema_valid_receipt_linked_to_both_sides(
        self,
    ) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        projection = self._project(task_id)

        outcome = self.bridge.bridge(projection=projection)

        self.assertIsInstance(outcome, RealFixValidationBridgeOutcome)
        self.assertTrue(outcome.validation_receipt_id.startswith("vr-"))
        self.assertEqual(outcome.patch_proposal_id, projection.patch_proposal_id)
        self.assertEqual(
            outcome.inference_artifact_id, projection.inference_artifact_id
        )
        self.assertEqual(outcome.task_id, task_id)
        self.assertEqual(
            outcome.root_revision_id, projection.root_revision_id
        )

        # Exactly one receipt row.
        self.assertEqual(self._count("validation_receipts"), 1)
        receipt = self.receipt_repo.fetch(outcome.validation_receipt_id)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["task_id"], task_id)
        self.assertEqual(receipt["root_revision_id"], projection.root_revision_id)
        self.assertEqual(receipt["result"], "pass")
        self.assertEqual(receipt["taint_set"], [])

        # On-row link to InferenceArtifact is preserved transitively:
        # receipt → patch_proposal_id → PatchProposal.inference_artifact_id.
        patch_row = self.patch_repo.fetch(projection.patch_proposal_id)
        self.assertIsNotNone(patch_row)
        self.assertEqual(
            patch_row["inference_artifact_id"], projection.inference_artifact_id
        )

        # Exactly one bridge attestation audit event, carrying all three ids.
        attested = self._records_of("real_fix_validation_bridge_attested")
        self.assertEqual(len(attested), 1)
        a = attested[0]
        self.assertEqual(a["task_id"], task_id)
        self.assertEqual(a["root_revision_id"], projection.root_revision_id)
        self.assertEqual(
            sorted(a["artifact_refs"]),
            sorted(
                [
                    outcome.validation_receipt_id,
                    projection.patch_proposal_id,
                    projection.inference_artifact_id,
                ]
            ),
        )
        self.assertEqual(
            a["payload"]["validation_receipt_id"], outcome.validation_receipt_id
        )
        self.assertEqual(
            a["payload"]["patch_proposal_id"], projection.patch_proposal_id
        )
        self.assertEqual(
            a["payload"]["inference_artifact_id"],
            projection.inference_artifact_id,
        )
        self.assertEqual(a["payload"]["receipt_result"], "pass")
        self.assertEqual(a["payload"]["source"], "real_fix_tracer")

    def test_bridge_audit_chain_is_complete(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        projection = self._project(task_id)
        self.bridge.bridge(projection=projection)

        # A reviewer can walk the end-to-end chain from a single ordered
        # audit trail: tracer → inference row → verified pass → patch
        # proposal created → validation receipt created → bridge
        # attestation.
        types = [r["record_type"] for r in self.audit.records]
        self.assertEqual(
            types,
            [
                "real_fix_attempt_started",
                "inference_artifact_created",
                "real_fix_verified_pass",
                "patch_proposal_created",
                "validation_receipt_created",
                "real_fix_validation_bridge_attested",
            ],
        )

    def test_bridge_preserves_taint_downgrade_on_quarantine_drift(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        projection = self._project(task_id)

        dirty_run = QuarantineRun(
            quarantine_run_id=f"qr-{uuid4().hex}",
            state=QuarantineState.EXITED_TAINTED,
            entered_at="2026-04-14T00:00:00+00:00",
            exited_at="2026-04-14T00:00:01+00:00",
            host_pollution_suspected=False,
            workspace_preserved_for_forensics=True,
            env_scrub_violations=("SECRET_LEAKED_ENV",),
            network_attempts=(),
        )

        outcome = self.bridge.bridge(projection=projection, run=dirty_run)
        receipt = self.receipt_repo.fetch(outcome.validation_receipt_id)
        self.assertIsNotNone(receipt)
        # Quarantine drift must downgrade the receipt and the bridge
        # attestation must reflect the downgraded result honestly.
        self.assertIn(receipt["result"], {"quarantined", "fail"})
        attested = self._records_of("real_fix_validation_bridge_attested")[0]
        self.assertEqual(attested["payload"]["receipt_result"], receipt["result"])

    # ------------------------------------------------------------------
    # Fail-closed: non-admissible inputs must not produce a receipt row
    # ------------------------------------------------------------------

    def test_bridge_refuses_unknown_patch_proposal_id(self) -> None:
        fake = RealFixPatchProjection(
            patch_proposal_id="pp-does-not-exist",
            inference_artifact_id="inf-does-not-exist",
            task_id="fix-ghost",
            root_revision_id="real-fix::root::fix-ghost",
            target_file_id="real-fix::file::fix-ghost",
            patch_group_hash="sha256:" + "0" * 64,
            patch_body_hash="sha256:" + "0" * 64,
        )
        with self.assertRaises(RealFixValidationBridgeRejected):
            self.bridge.bridge(projection=fake)

        self.assertEqual(self._count("validation_receipts"), 0)
        self.assertEqual(self._records_of("real_fix_validation_bridge_attested"), [])
        self.assertEqual(self._records_of("validation_receipt_created"), [])

    def test_bridge_refuses_mismatched_inference_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        projection = self._project(task_id)

        tampered = RealFixPatchProjection(
            patch_proposal_id=projection.patch_proposal_id,
            inference_artifact_id="inf-tampered",
            task_id=projection.task_id,
            root_revision_id=projection.root_revision_id,
            target_file_id=projection.target_file_id,
            patch_group_hash=projection.patch_group_hash,
            patch_body_hash=projection.patch_body_hash,
        )

        with self.assertRaises(RealFixValidationBridgeRejected):
            self.bridge.bridge(projection=tampered)

        # No receipt written for the tampered attempt.
        self.assertEqual(self._count("validation_receipts"), 0)
        self.assertEqual(self._records_of("real_fix_validation_bridge_attested"), [])

    def test_bridge_refuses_mismatched_task_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        projection = self._project(task_id)

        tampered = RealFixPatchProjection(
            patch_proposal_id=projection.patch_proposal_id,
            inference_artifact_id=projection.inference_artifact_id,
            task_id="fix-other-task",
            root_revision_id=projection.root_revision_id,
            target_file_id=f"real-fix::file::fix-other-task",
            patch_group_hash=projection.patch_group_hash,
            patch_body_hash=projection.patch_body_hash,
        )

        with self.assertRaises(RealFixValidationBridgeRejected):
            self.bridge.bridge(projection=tampered)

        self.assertEqual(self._count("validation_receipts"), 0)
        self.assertEqual(self._records_of("real_fix_validation_bridge_attested"), [])

    def test_bridge_refuses_non_realfix_target_file_label(self) -> None:
        # Insert a PatchProposal row directly that does NOT carry the
        # real-fix narrow-path synthetic target label. The bridge must
        # refuse it even though every other field is schema-valid.
        task_id = f"fix-{uuid4().hex[:8]}"
        from kernel.version.version_tuple import compose_version_tuple_hash

        foreign_row = {
            "patch_proposal_id": f"pp-foreign-{uuid4().hex[:8]}",
            "task_id": task_id,
            "root_revision_id": f"real-fix::root::{task_id}",
            "inference_artifact_id": f"inf-foreign-{uuid4().hex[:8]}",
            "target_file_ids": ["not-a-real-fix-label.py"],
            "patch_group_hash": "sha256:" + "a" * 64,
            "side_effect_class_proposal": "local_text_substitution",
            "capability_requirements": [],
            "taint_set": [],
            "created_at": "2026-04-14T00:00:00+00:00",
            "version_tuple_hash": compose_version_tuple_hash(),
        }
        self.patch_repo.insert(foreign_row)

        foreign_projection = RealFixPatchProjection(
            patch_proposal_id=foreign_row["patch_proposal_id"],
            inference_artifact_id=foreign_row["inference_artifact_id"],
            task_id=foreign_row["task_id"],
            root_revision_id=foreign_row["root_revision_id"],
            target_file_id="not-a-real-fix-label.py",
            patch_group_hash=foreign_row["patch_group_hash"],
            patch_body_hash="sha256:" + "0" * 64,
        )

        with self.assertRaises(RealFixValidationBridgeRejected):
            self.bridge.bridge(projection=foreign_projection)

        self.assertEqual(self._count("validation_receipts"), 0)
        self.assertEqual(self._records_of("real_fix_validation_bridge_attested"), [])

    def test_bridge_does_not_touch_unrelated_rows(self) -> None:
        # Project two independent real-fix runs. Bridge only the first.
        # The second patch row and its upstream inference row must be
        # untouched: no receipt created for them, and no bridge
        # attestation naming them.
        first_task = f"fix-{uuid4().hex[:8]}"
        second_task = f"fix-{uuid4().hex[:8]}"
        proj_a = self._project(first_task)
        proj_b = self._project(second_task)

        self.bridge.bridge(projection=proj_a)

        # Exactly one receipt row exists, and it is bound to task A.
        self.assertEqual(self._count("validation_receipts"), 1)
        rows = self.conn.execute(
            "SELECT task_id FROM validation_receipts;"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], [first_task])

        # Patch rows and inference rows for task B remain intact.
        self.assertIsNotNone(self.patch_repo.fetch(proj_b.patch_proposal_id))
        self.assertIsNotNone(
            self.inference_repo.fetch(proj_b.inference_artifact_id)
        )

        # No bridge attestation naming task B.
        attested = self._records_of("real_fix_validation_bridge_attested")
        self.assertEqual(len(attested), 1)
        self.assertEqual(attested[0]["task_id"], first_task)
        self.assertNotIn(proj_b.patch_proposal_id, attested[0]["artifact_refs"])
        self.assertNotIn(proj_b.inference_artifact_id, attested[0]["artifact_refs"])

    def test_bridge_forwards_static_check_failure(self) -> None:
        # A failed static-check result must flow through ValidationService
        # and surface on the receipt. The bridge must still produce a
        # schema-valid row and an honest attestation carrying the
        # failing result.
        task_id = f"fix-{uuid4().hex[:8]}"
        projection = self._project(task_id)

        failing = StaticCheckResult(
            passed=False,
            input_hash="sha256:" + "1" * 64,
            diagnostics_hash="sha256:" + "2" * 64,
        )

        outcome = self.bridge.bridge(
            projection=projection, static_result=failing
        )
        receipt = self.receipt_repo.fetch(outcome.validation_receipt_id)
        self.assertIsNotNone(receipt)
        self.assertIn(receipt["result"], {"fail", "quarantined"})
        attested = self._records_of("real_fix_validation_bridge_attested")[0]
        self.assertEqual(attested["payload"]["receipt_result"], receipt["result"])


if __name__ == "__main__":
    unittest.main()
