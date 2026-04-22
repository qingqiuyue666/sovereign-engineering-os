"""
Tracer-bullet test: AUDIT-003 / §22.1 parity for the
``inference_failure`` rejection-path audit record emitted by
``InferenceService._emit_failure_bundle``.

When the orchestrator threads the durable
``intent_anchor_records.intent_id`` into
``InferenceService.run_inference`` (as ``admit_inference`` does from
``state.intent_anchor.intent_id``), every ``inference_failure`` audit
record emitted from ``run_inference``'s four fail-closed sites
(pre-flight budget refusal, model-api failure, adapter exception,
post-flight budget refusal) must name the same id in both
``artifact_refs`` and ``payload`` so a reviewer reading only that
rejection record can recover the AUDIT-003 / §22.1 linkage without a
second fetch.

Authoritative fail-closed verification of ``intent_id`` against
``intent_anchor_records`` remains the responsibility of
``RevisionSealService`` downstream; this service performs no
independent verification. Absent / empty ``intent_id`` preserves the
prior audit shape exactly.

The pre-flight budget-refusal path is the simplest way to drive one
of the four sites deterministically through the real orchestrator
surface (no patching, no fault injection): a tight ``hard_budget``
paired with a larger ``max_output_tokens`` causes ``admit_inference``
to raise ``InferenceBudgetExhausted`` before the adapter is invoked.
The other three sites share the same helper and the same threaded
``intent_id`` parameter, so a single-site assertion is a faithful
parity check for the rejection-path sibling.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any, Mapping
from uuid import uuid4

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from kernel.services.inference_service import (
    InferenceBudgetExhausted,
    InferencePolicy,
    InferenceService,
)
from validation.tests.acceptance.conftest import AcceptanceHarness, FakeModelAdapter


class _CountingAdapter(FakeModelAdapter):
    """Fake adapter that counts invocations so pre-flight refusal is provable."""

    def __init__(self, *, output_tokens: int = 20) -> None:
        self.invocations = 0
        self._output_tokens = int(output_tokens)

    def invoke(
        self,
        *,
        prompt_envelope: Mapping[str, Any],
        policy: InferencePolicy,
    ) -> Mapping[str, Any]:
        self.invocations += 1
        return {
            "output_text": "tracer-bullet output text",
            "token_usage": {"input": 100, "output": self._output_tokens},
            "latency_ms": 42,
            "model_route_id": "fake-model-v1",
        }


class TestInferenceFailureNamesIntentId(unittest.TestCase):
    """AUDIT-003 / §22.1 rejection-path parity for ``inference_failure``."""

    def setUp(self) -> None:
        adapter = _CountingAdapter(output_tokens=20)
        self.harness = AcceptanceHarness(
            inference_policy=InferencePolicy(max_output_tokens=50),
            default_hard_budget_tokens=40,
        )
        # Re-wire the inference service with the counting adapter so we
        # can assert the pre-flight refusal path did NOT invoke it.
        self.harness.inf_svc = InferenceService(
            repository=self.harness.inf_repo,
            audit_ledger=self.harness.audit_ledger,
            context_reader=self.harness.ctx_repo,
            adapter=adapter,
            policy=InferencePolicy(max_output_tokens=50),
            budget_governor=self.harness.budget_governor,
            failure_bundle_repository=self.harness.failure_repo,
        )
        self.harness.orch._inference = self.harness.inf_svc  # type: ignore[attr-defined]
        self._adapter = adapter

    def tearDown(self) -> None:
        self.harness.close()

    def test_inference_failure_names_intent_id_on_pre_flight_refusal(self) -> None:
        """Pre-flight budget refusal must emit an ``inference_failure``
        audit row whose ``payload`` and ``artifact_refs`` both name the
        anchor's ``intent_id`` (threaded by ``admit_inference`` from
        ``state.intent_anchor.intent_id``), while preserving the prior
        ``failure_class`` / ``detail`` / ``root_revision_id`` payload
        fields and the prior ``[context_artifact_id]`` refs
        contribution."""
        task_id = f"task-{uuid4().hex[:8]}"
        intent_id = f"intent-{uuid4().hex[:8]}"
        root_revision_id = "rev-genesis-000"
        cap_ctx = self.harness.issue_capability(
            "read_repository_snapshot", task_id
        )
        context_artifact_id = self.harness.orch.admit_context(
            task_id=task_id,
            intent_id=intent_id,
            capability_token=cap_ctx,
            root_revision_id=root_revision_id,
            request={
                "repo_graph_version": "1.0",
                "symbol_index_version": "1.0",
                "candidate_file_ids": ["src/main.py"],
                "symbol_frontier_ids": ["main"],
                "packing_policy_version": "phase1_budget_policy_v1",
                "actual_tokens": 10,
            },
        )

        cap_inf = self.harness.issue_capability("invoke_inference", task_id)
        with self.assertRaises(InferenceBudgetExhausted):
            self.harness.orch.admit_inference(
                task_id=task_id,
                capability_token=cap_inf,
                worker_profile="acceptance_worker",
                model_route_id="fake-model-v1",
            )
        # Pre-flight refusal: the adapter must NOT have been invoked.
        self.assertEqual(self._adapter.invocations, 0)

        row = self.harness.conn.execute(
            "SELECT payload_json, artifact_refs, failure_bundle_id FROM audit_records "
            "WHERE task_id = ? "
            "AND record_type = 'inference_failure' "
            "ORDER BY sequence DESC LIMIT 1;",
            (task_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertEqual(payload["intent_id"], intent_id)
        self.assertIn(intent_id, refs)
        # Prior fields preserved.
        self.assertEqual(payload["failure_class"], "budget_would_be_exceeded")
        self.assertIn("detail", payload)
        self.assertEqual(payload["root_revision_id"], root_revision_id)
        self.assertIn(context_artifact_id, refs)
        self.assertIsNotNone(row["failure_bundle_id"])
        bundle = self.harness.conn.execute(
            "SELECT * FROM failure_bundles WHERE failure_bundle_id = ?;",
            (row["failure_bundle_id"],),
        ).fetchone()
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle["task_id"], task_id)
        self.assertEqual(bundle["root_revision_id"], root_revision_id)
        self.assertEqual(bundle["failure_class"], "budget_would_be_exceeded")
        self.assertEqual(json.loads(bundle["evidence_refs"]), [context_artifact_id])


if __name__ == "__main__":
    unittest.main()
