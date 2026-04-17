"""
Tracer-bullet test: bridged real-fix ValidationReceipt → ReviewArtifact.

Proves that ``RealFixReviewBridge`` takes exactly one
``RealFixValidationBridgeOutcome`` that already came from the verified
real-fix path and produces exactly one schema-valid ``ReviewArtifact``,
with an audit cross-reference that binds the review to the originating
``ValidationReceipt``, ``PatchProposal``, AND the upstream
``InferenceArtifact``. Also proves that every non-admissible input is
rejected fail-closed with no review row written and no bridge
attestation emitted, and that rows for unrelated task ids are not
touched.

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
    RealFixPatchProjector,
)
from kernel.lifecycle.real_fix_recorder import (
    RealFixNarrowPathRecord,
    RealFixNarrowPathRecorder,
)
from kernel.lifecycle.real_fix_review_bridge import (
    RealFixReviewBridge,
    RealFixReviewBridgeOutcome,
    RealFixReviewBridgeRejected,
)
from kernel.lifecycle.real_fix_validation_bridge import (
    RealFixValidationBridge,
    RealFixValidationBridgeOutcome,
)
from kernel.services.review_service import ReviewService
from kernel.services.validation_service import (
    StaticCheckResult,
    ValidationService,
)
from kernel.stores.sqlite.repositories import (
    AuditRepository,
    InferenceArtifactRepository,
    PatchProposalRepository,
    ReviewArtifactRepository,
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
            "id": "msg_fix_review_bridge_test",
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


class RealFixReviewBridgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.inference_repo = InferenceArtifactRepository(self.conn)
        self.patch_repo = PatchProposalRepository(self.conn)
        self.receipt_repo = ValidationReceiptRepository(self.conn)
        self.review_repo = ReviewArtifactRepository(self.conn)
        self.ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="real_fix_review_bridge_test",
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
        self.validation_bridge = RealFixValidationBridge(
            validation_service=self.validation_service,
            patch_reader=self.patch_repo,
            receipt_reader=self.receipt_repo,
            audit_ledger=self.audit,
        )
        self.review_service = ReviewService(
            repository=self.review_repo,
            patch_reader=self.patch_repo,
            receipt_reader=self.receipt_repo,
            audit_ledger=self.audit,
        )
        self.review_bridge = RealFixReviewBridge(
            review_service=self.review_service,
            receipt_reader=self.receipt_repo,
            patch_reader=self.patch_repo,
            review_reader=self.review_repo,
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

    def _bridge_to_receipt(
        self, task_id: str, *, static_result: StaticCheckResult | None = None,
        run: QuarantineRun | None = None,
    ) -> RealFixValidationBridgeOutcome:
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
        projection = self.projector.project(task=task, result=result, record=record)
        return self.validation_bridge.bridge(
            projection=projection, run=run, static_result=static_result
        )

    # ------------------------------------------------------------------
    # Success: bridged receipt → exactly one schema-valid review
    # ------------------------------------------------------------------

    def test_bridge_produces_one_schema_valid_review_linked_to_all_sides(
        self,
    ) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        vb_outcome = self._bridge_to_receipt(task_id)

        outcome = self.review_bridge.bridge(
            outcome=vb_outcome,
            intent_id=f"real-fix::intent::{task_id}",
        )

        self.assertIsInstance(outcome, RealFixReviewBridgeOutcome)
        self.assertTrue(outcome.review_artifact_id.startswith("rv-"))
        self.assertEqual(
            outcome.validation_receipt_id, vb_outcome.validation_receipt_id
        )
        self.assertEqual(
            outcome.patch_proposal_id, vb_outcome.patch_proposal_id
        )
        self.assertEqual(
            outcome.inference_artifact_id, vb_outcome.inference_artifact_id
        )
        self.assertEqual(outcome.task_id, task_id)
        self.assertEqual(
            outcome.root_revision_id, vb_outcome.root_revision_id
        )

        # Exactly one review row.
        self.assertEqual(self._count("review_artifacts"), 1)
        review = self.review_repo.fetch(outcome.review_artifact_id)
        self.assertIsNotNone(review)
        self.assertEqual(review["task_id"], task_id)
        self.assertEqual(review["root_revision_id"], vb_outcome.root_revision_id)
        self.assertEqual(review["patch_proposal_id"], vb_outcome.patch_proposal_id)
        self.assertEqual(review["risk_class"], "low")
        self.assertEqual(review["taint_set"], [])

        # Causal linkage to upstream PatchProposal is preserved on-row.
        # Transitive linkage to the originating InferenceArtifact is
        # preserved via PatchProposal.inference_artifact_id.
        patch_row = self.patch_repo.fetch(vb_outcome.patch_proposal_id)
        self.assertIsNotNone(patch_row)
        self.assertEqual(
            patch_row["inference_artifact_id"], vb_outcome.inference_artifact_id
        )

        # Exactly one bridge attestation audit event, carrying all four
        # upstream ids plus the originating durable intent-anchor id
        # (AUDIT-003 / §22.1): a reviewer reading only this record can
        # recover the originating ``intent_anchor_records.intent_id``
        # without a second fetch.
        expected_intent_id = f"real-fix::intent::{task_id}"
        attested = self._records_of("real_fix_review_bridge_attested")
        self.assertEqual(len(attested), 1)
        a = attested[0]
        self.assertEqual(a["task_id"], task_id)
        self.assertEqual(a["root_revision_id"], vb_outcome.root_revision_id)
        self.assertEqual(
            sorted(a["artifact_refs"]),
            sorted(
                [
                    outcome.review_artifact_id,
                    vb_outcome.validation_receipt_id,
                    vb_outcome.patch_proposal_id,
                    vb_outcome.inference_artifact_id,
                    expected_intent_id,
                ]
            ),
        )
        self.assertIn(expected_intent_id, a["artifact_refs"])
        self.assertEqual(
            a["payload"]["review_artifact_id"], outcome.review_artifact_id
        )
        self.assertEqual(
            a["payload"]["validation_receipt_id"],
            vb_outcome.validation_receipt_id,
        )
        self.assertEqual(
            a["payload"]["patch_proposal_id"], vb_outcome.patch_proposal_id
        )
        self.assertEqual(
            a["payload"]["inference_artifact_id"],
            vb_outcome.inference_artifact_id,
        )
        self.assertEqual(a["payload"]["intent_id"], expected_intent_id)
        self.assertEqual(a["payload"]["risk_class"], "low")
        self.assertEqual(a["payload"]["source"], "real_fix_tracer")

    def test_bridge_audit_chain_is_complete(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        vb_outcome = self._bridge_to_receipt(task_id)
        self.review_bridge.bridge(outcome=vb_outcome)

        # A reviewer can walk the end-to-end chain from a single ordered
        # audit trail: tracer → inference row → verified pass → patch
        # proposal created → validation receipt created → validation
        # bridge attestation → review artifact created → review bridge
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
                "review_artifact_created",
                "real_fix_review_bridge_attested",
            ],
        )

    # ------------------------------------------------------------------
    # Fail-closed: non-admissible inputs must not produce a review row
    # ------------------------------------------------------------------

    def test_bridge_refuses_unknown_validation_receipt_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        vb_outcome = self._bridge_to_receipt(task_id)

        tampered = RealFixValidationBridgeOutcome(
            validation_receipt_id="vr-does-not-exist",
            patch_proposal_id=vb_outcome.patch_proposal_id,
            inference_artifact_id=vb_outcome.inference_artifact_id,
            task_id=vb_outcome.task_id,
            root_revision_id=vb_outcome.root_revision_id,
        )
        with self.assertRaises(RealFixReviewBridgeRejected):
            self.review_bridge.bridge(outcome=tampered)

        self.assertEqual(self._count("review_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_review_bridge_attested"), []
        )
        self.assertEqual(self._records_of("review_artifact_created"), [])

    def test_bridge_refuses_mismatched_task_id_on_receipt(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        vb_outcome = self._bridge_to_receipt(task_id)

        tampered = RealFixValidationBridgeOutcome(
            validation_receipt_id=vb_outcome.validation_receipt_id,
            patch_proposal_id=vb_outcome.patch_proposal_id,
            inference_artifact_id=vb_outcome.inference_artifact_id,
            task_id="fix-other-task",
            root_revision_id=vb_outcome.root_revision_id,
        )
        with self.assertRaises(RealFixReviewBridgeRejected):
            self.review_bridge.bridge(outcome=tampered)

        self.assertEqual(self._count("review_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_review_bridge_attested"), []
        )

    def test_bridge_refuses_mismatched_root_revision_id_on_receipt(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        vb_outcome = self._bridge_to_receipt(task_id)

        tampered = RealFixValidationBridgeOutcome(
            validation_receipt_id=vb_outcome.validation_receipt_id,
            patch_proposal_id=vb_outcome.patch_proposal_id,
            inference_artifact_id=vb_outcome.inference_artifact_id,
            task_id=vb_outcome.task_id,
            root_revision_id="real-fix::root::forged",
        )
        with self.assertRaises(RealFixReviewBridgeRejected):
            self.review_bridge.bridge(outcome=tampered)

        self.assertEqual(self._count("review_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_review_bridge_attested"), []
        )

    def test_bridge_refuses_non_pass_receipt(self) -> None:
        # A quarantined receipt (drift detected) must not cross the
        # review threshold on the minimum honest bridge. The bridge
        # must refuse even though every identity matches.
        task_id = f"fix-{uuid4().hex[:8]}"
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
        vb_outcome = self._bridge_to_receipt(task_id, run=dirty_run)

        receipt = self.receipt_repo.fetch(vb_outcome.validation_receipt_id)
        self.assertIsNotNone(receipt)
        self.assertNotEqual(receipt["result"], "pass")

        with self.assertRaises(RealFixReviewBridgeRejected):
            self.review_bridge.bridge(outcome=vb_outcome)

        self.assertEqual(self._count("review_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_review_bridge_attested"), []
        )
        self.assertEqual(self._records_of("review_artifact_created"), [])

    def test_bridge_refuses_invalidated_receipt(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        vb_outcome = self._bridge_to_receipt(task_id)

        # Manually invalidate the receipt to simulate an upstream
        # drift consequence. The bridge must refuse to render a review
        # over an invalidated receipt even if result == "pass".
        self.assertTrue(
            self.receipt_repo.mark_invalidated(
                validation_receipt_id=vb_outcome.validation_receipt_id,
                invalidation_reason="test_invalidation",
            )
        )

        with self.assertRaises(RealFixReviewBridgeRejected):
            self.review_bridge.bridge(outcome=vb_outcome)

        self.assertEqual(self._count("review_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_review_bridge_attested"), []
        )

    def test_bridge_refuses_mismatched_inference_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        vb_outcome = self._bridge_to_receipt(task_id)

        tampered = RealFixValidationBridgeOutcome(
            validation_receipt_id=vb_outcome.validation_receipt_id,
            patch_proposal_id=vb_outcome.patch_proposal_id,
            inference_artifact_id="inf-tampered",
            task_id=vb_outcome.task_id,
            root_revision_id=vb_outcome.root_revision_id,
        )
        with self.assertRaises(RealFixReviewBridgeRejected):
            self.review_bridge.bridge(outcome=tampered)

        self.assertEqual(self._count("review_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_review_bridge_attested"), []
        )

    def test_bridge_refuses_unknown_patch_proposal_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        vb_outcome = self._bridge_to_receipt(task_id)

        tampered = RealFixValidationBridgeOutcome(
            validation_receipt_id=vb_outcome.validation_receipt_id,
            patch_proposal_id="pp-does-not-exist",
            inference_artifact_id=vb_outcome.inference_artifact_id,
            task_id=vb_outcome.task_id,
            root_revision_id=vb_outcome.root_revision_id,
        )
        with self.assertRaises(RealFixReviewBridgeRejected):
            self.review_bridge.bridge(outcome=tampered)

        self.assertEqual(self._count("review_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_review_bridge_attested"), []
        )

    def test_bridge_refuses_non_realfix_target_file_label(self) -> None:
        # Insert a PatchProposal row directly that does NOT carry the
        # real-fix narrow-path synthetic target label, and write a
        # matching pass-receipt over it. The bridge must refuse even
        # though every on-row id and state is admissible on its own.
        task_id = f"fix-{uuid4().hex[:8]}"
        from kernel.version.version_tuple import compose_version_tuple_hash

        foreign_patch = {
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
        self.patch_repo.insert(foreign_patch)

        foreign_receipt = {
            "validation_receipt_id": f"vr-foreign-{uuid4().hex[:8]}",
            "task_id": task_id,
            "root_revision_id": foreign_patch["root_revision_id"],
            "receipt_type": "static_proposal_check",
            "validator_identity": "foreign_validator",
            "validator_version": "0.0.0",
            "input_hash": "sha256:" + "b" * 64,
            "result": "pass",
            "diagnostics_hash": "sha256:" + "c" * 64,
            "taint_set": [],
            "created_at": "2026-04-14T00:00:01+00:00",
            "version_tuple_hash": compose_version_tuple_hash(),
        }
        self.receipt_repo.insert(foreign_receipt)

        foreign_outcome = RealFixValidationBridgeOutcome(
            validation_receipt_id=foreign_receipt["validation_receipt_id"],
            patch_proposal_id=foreign_patch["patch_proposal_id"],
            inference_artifact_id=foreign_patch["inference_artifact_id"],
            task_id=task_id,
            root_revision_id=foreign_patch["root_revision_id"],
        )

        with self.assertRaises(RealFixReviewBridgeRejected):
            self.review_bridge.bridge(outcome=foreign_outcome)

        self.assertEqual(self._count("review_artifacts"), 0)
        self.assertEqual(
            self._records_of("real_fix_review_bridge_attested"), []
        )

    def test_bridge_does_not_touch_unrelated_rows(self) -> None:
        # Bridge two independent real-fix runs to receipts. Only
        # review-bridge the first. The second receipt, patch row, and
        # inference row must be untouched: no review for them, and no
        # bridge attestation naming them.
        first_task = f"fix-{uuid4().hex[:8]}"
        second_task = f"fix-{uuid4().hex[:8]}"
        vb_a = self._bridge_to_receipt(first_task)
        vb_b = self._bridge_to_receipt(second_task)

        self.review_bridge.bridge(outcome=vb_a)

        # Exactly one review row exists, and it is bound to task A.
        self.assertEqual(self._count("review_artifacts"), 1)
        rows = self.conn.execute(
            "SELECT task_id FROM review_artifacts;"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], [first_task])

        # Receipts, patch rows, and inference rows for task B remain intact.
        self.assertIsNotNone(
            self.receipt_repo.fetch(vb_b.validation_receipt_id)
        )
        self.assertIsNotNone(self.patch_repo.fetch(vb_b.patch_proposal_id))
        self.assertIsNotNone(
            self.inference_repo.fetch(vb_b.inference_artifact_id)
        )

        attested = self._records_of("real_fix_review_bridge_attested")
        self.assertEqual(len(attested), 1)
        self.assertEqual(attested[0]["task_id"], first_task)
        self.assertNotIn(
            vb_b.validation_receipt_id, attested[0]["artifact_refs"]
        )
        self.assertNotIn(
            vb_b.patch_proposal_id, attested[0]["artifact_refs"]
        )
        self.assertNotIn(
            vb_b.inference_artifact_id, attested[0]["artifact_refs"]
        )


if __name__ == "__main__":
    unittest.main()
