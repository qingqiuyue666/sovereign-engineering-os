"""
Tracer-bullet test: real-fix → narrow-path → patch proposal projection.

Proves that when a ``RealFixNarrowPathRecorder`` produces an authority-
bearing ``InferenceArtifact`` row from a verified real-fix tracer
result, the ``RealFixPatchProjector`` projects that row into exactly one
schema-valid ``PatchProposal`` row on the existing signable-path
surface, with one ``patch_proposal_created`` audit record that cross-
references the originating inference artifact, and that every non-
verified or missing-upstream input is rejected fail-closed with no row
written and no audit event appended.

Scope:
- Exercises ``AnthropicMessagesAdapter`` with a fake transport — no
  network.
- Uses the canonical ``make_add_fix_task`` single-file fix task.
- Uses the real ``PatchProposalRepository`` + schema validator.
- Asserts no ``replay_claim_exact`` appears anywhere; the projector's
  audit record carries the honest ``semantic`` ceiling.
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
    RealFixProjectorRejected,
)
from kernel.lifecycle.real_fix_recorder import (
    RealFixNarrowPathRecord,
    RealFixNarrowPathRecorder,
)
from kernel.stores.sqlite.repositories import (
    AuditRepository,
    InferenceArtifactRepository,
    PatchProposalRepository,
)
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection
from kernel.tracers.real_fix_tracer import (
    RealFixResult,
    RealFixTracer,
    make_add_fix_task,
)


def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj).encode("utf-8")


def _messages_body(text: str, model: str = "claude-sonnet-4-5") -> bytes:
    return _json_bytes(
        {
            "id": "msg_fix_tracer_projection",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 12, "output_tokens": 24},
        }
    )


CORRECT_ADD_BLOCK = (
    "```python\n"
    "def add(a, b):\n"
    "    return a + b\n"
    "```\n"
)

WRONG_ADD_BLOCK = (
    "```python\n"
    "def add(a, b):\n"
    "    return a + b + 1\n"
    "```\n"
)


class _AuditCapture:
    """Wrap the ledger and record appended events for assertions."""

    def __init__(self, ledger: AppendOnlyLedger) -> None:
        self._ledger = ledger
        self.records: list[dict[str, Any]] = []

    def append(
        self,
        *,
        record_type: str,
        task_id: str,
        artifact_refs,
        payload,
    ) -> None:
        self.records.append(
            {
                "record_type": record_type,
                "task_id": task_id,
                "artifact_refs": list(artifact_refs),
                "payload": dict(payload),
            }
        )
        self._ledger.append(
            record_type=record_type,
            task_id=task_id,
            artifact_refs=artifact_refs,
            payload=payload,
        )


class RealFixPatchProjectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.inference_repo = InferenceArtifactRepository(self.conn)
        self.patch_repo = PatchProposalRepository(self.conn)
        self.ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="real_fix_patch_projection_test",
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

    def tearDown(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------

    def _tracer_with_transport(self, transport) -> RealFixTracer:
        adapter = AnthropicMessagesAdapter(
            api_key="sk-test", transport=transport
        )
        return RealFixTracer(
            adapter=adapter,
            audit_ledger=self.audit,
            narrow_path_recorder=self.recorder,
        )

    def _count_patch_rows(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM patch_proposals;"
        ).fetchone()[0]

    def _records_of(self, record_type: str) -> list[dict[str, Any]]:
        return [r for r in self.audit.records if r["record_type"] == record_type]

    def _run_and_record(self, task_id: str):
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        task = make_add_fix_task(task_id=task_id)
        tracer = self._tracer_with_transport(t)
        result = tracer.run(task)
        self.assertTrue(result.verified)
        self.assertTrue(result.inference_artifact_id.startswith("inf-"))

        # Rebuild the record object the projector expects. The
        # tracer/recorder path produced exactly these fields; we read
        # them off the authority-bearing inference row so the test
        # stays faithful to what a real caller would do.
        inf = self.inference_repo.fetch(result.inference_artifact_id)
        self.assertIsNotNone(inf)
        record = RealFixNarrowPathRecord(
            inference_artifact_id=result.inference_artifact_id,
            context_artifact_id=inf["context_artifact_id"],
            root_revision_id=inf["root_revision_id"],
            output_hash=inf["output_hash"],
            replay_ceiling=result.replay_ceiling,
        )
        return task, result, record

    # ------------------------------------------------------------------
    # Success: one verified result → one PatchProposal row
    # ------------------------------------------------------------------

    def test_projection_persists_one_patch_proposal_row(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        task, result, record = self._run_and_record(task_id)

        projection = self.projector.project(
            task=task, result=result, record=record
        )

        # Honest return value carrying the authority-bearing ids.
        self.assertIsInstance(projection, RealFixPatchProjection)
        self.assertTrue(projection.patch_proposal_id.startswith("pp-"))
        self.assertEqual(projection.inference_artifact_id, record.inference_artifact_id)
        self.assertEqual(projection.task_id, task_id)
        self.assertEqual(projection.root_revision_id, record.root_revision_id)
        self.assertEqual(projection.target_file_id, f"real-fix::file::{task_id}")
        self.assertEqual(projection.patch_body_hash, record.output_hash)
        self.assertTrue(projection.patch_group_hash.startswith("sha256:"))

        # Exactly one patch proposal row exists.
        self.assertEqual(self._count_patch_rows(), 1)

        row = self.patch_repo.fetch(projection.patch_proposal_id)
        self.assertIsNotNone(row)
        # Schema-valid shape; single-file phase-1 narrowing.
        self.assertEqual(row["task_id"], task_id)
        self.assertEqual(row["root_revision_id"], record.root_revision_id)
        self.assertEqual(row["inference_artifact_id"], record.inference_artifact_id)
        self.assertEqual(row["target_file_ids"], [f"real-fix::file::{task_id}"])
        self.assertEqual(row["patch_group_hash"], projection.patch_group_hash)
        self.assertEqual(
            row["side_effect_class_proposal"], "local_text_substitution"
        )
        self.assertEqual(row["capability_requirements"], [])
        self.assertEqual(row["taint_set"], [])

        # Audit: one patch_proposal_created linking both sides.
        created_recs = self._records_of("patch_proposal_created")
        self.assertEqual(len(created_recs), 1)
        created = created_recs[0]
        self.assertEqual(created["task_id"], task_id)
        self.assertIn(projection.patch_proposal_id, created["artifact_refs"])
        self.assertIn(record.inference_artifact_id, created["artifact_refs"])
        self.assertEqual(
            created["payload"]["inference_artifact_id"],
            record.inference_artifact_id,
        )
        self.assertEqual(created["payload"]["source"], "real_fix_tracer")
        self.assertEqual(created["payload"]["replay_ceiling"], "semantic")
        self.assertEqual(
            created["payload"]["target_file_ids"],
            [f"real-fix::file::{task_id}"],
        )
        self.assertEqual(
            created["payload"]["patch_group_hash"], projection.patch_group_hash
        )

    def test_projection_audit_ordering_after_tracer_chain(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        task, result, record = self._run_and_record(task_id)
        self.projector.project(task=task, result=result, record=record)

        # The full causal chain a reviewer can walk end-to-end:
        # attempt_started → inference row created → verified_pass →
        # patch_proposal_created.
        types = [r["record_type"] for r in self.audit.records]
        self.assertEqual(
            types,
            [
                "real_fix_attempt_started",
                "inference_artifact_created",
                "real_fix_verified_pass",
                "patch_proposal_created",
            ],
        )

        # No record anywhere claims exact replay; every tracer- or
        # projector-emitted record carries the honest semantic ceiling.
        for rec in self.audit.records:
            self.assertNotIn("replay_claim_exact", rec["payload"])
            self.assertEqual(rec["payload"].get("replay_ceiling"), "semantic")

    # ------------------------------------------------------------------
    # Fail-closed: non-verified outcomes must not produce a row
    # ------------------------------------------------------------------

    def test_projector_refuses_unverified_result(self) -> None:
        task = make_add_fix_task(task_id="fix-proj-reject-unverified")
        unverified = RealFixResult(
            verified=False,
            outcome="real_fix_verified_fail",
            fixed_source="def add(a, b):\n    return 0\n",
            output_hash="sha256:" + "0" * 64,
            failure_class="verification_failed",
            failure_detail="deliberate",
            latency_ms=0,
            replay_ceiling="semantic",
            inference_artifact_id="inf-never-written",
        )
        record = RealFixNarrowPathRecord(
            inference_artifact_id="inf-never-written",
            context_artifact_id=f"real-fix::context::{task.task_id}",
            root_revision_id=f"real-fix::root::{task.task_id}",
            output_hash="sha256:" + "0" * 64,
            replay_ceiling="semantic",
        )

        with self.assertRaises(RealFixProjectorRejected):
            self.projector.project(task=task, result=unverified, record=record)

        # Fail-closed: no row, no audit event.
        self.assertEqual(self._count_patch_rows(), 0)
        self.assertEqual(self._records_of("patch_proposal_created"), [])

    def test_projector_refuses_missing_inference_artifact_id(self) -> None:
        task_id = f"fix-{uuid4().hex[:8]}"
        # Run the tracer without wiring the recorder to produce a
        # verified result that has NO authority-bearing upstream row.
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        adapter = AnthropicMessagesAdapter(api_key="sk-test", transport=t)
        tracer_no_rec = RealFixTracer(
            adapter=adapter,
            audit_ledger=self.audit,
            narrow_path_recorder=None,
        )
        task = make_add_fix_task(task_id=task_id)
        result = tracer_no_rec.run(task)
        self.assertTrue(result.verified)
        self.assertEqual(result.inference_artifact_id, "")

        record_no_upstream = RealFixNarrowPathRecord(
            inference_artifact_id="",  # nothing persisted upstream
            context_artifact_id=f"real-fix::context::{task_id}",
            root_revision_id=f"real-fix::root::{task_id}",
            output_hash=result.output_hash,
            replay_ceiling="semantic",
        )

        with self.assertRaises(RealFixProjectorRejected):
            self.projector.project(
                task=task, result=result, record=record_no_upstream
            )

        # Fail-closed: no patch row written.
        self.assertEqual(self._count_patch_rows(), 0)
        self.assertEqual(self._records_of("patch_proposal_created"), [])

    def test_end_to_end_failed_tracer_produces_no_patch_row(self) -> None:
        # Verified-fail result never reaches the projector in real
        # flow (the tracer returns a non-pass outcome and the caller
        # skips projection). This test walks the realistic shape: the
        # tracer runs with the recorder wired, produces a verified_fail,
        # and the caller never invokes the projector. No patch row, no
        # inference row, no projector audit event.
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(WRONG_ADD_BLOCK))

        task_id = f"fix-{uuid4().hex[:8]}"
        task = make_add_fix_task(task_id=task_id)
        tracer = self._tracer_with_transport(t)

        result = tracer.run(task)

        self.assertFalse(result.verified)
        self.assertEqual(result.outcome, "real_fix_verified_fail")
        self.assertEqual(result.inference_artifact_id, "")
        self.assertEqual(self._count_patch_rows(), 0)
        self.assertEqual(self._records_of("patch_proposal_created"), [])


if __name__ == "__main__":
    unittest.main()
