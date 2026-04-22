"""
AT-027: Budget exhaustion governance at the governed inference boundary.

Constitutional anchors:
- v11 §9.8 Budget lifecycle
- v11 §24.1 AT-027 (exceeded budget suspends or downgrades work without
  granting unsafe shortcuts)
- v11 §24.2 INV-021 (budget thresholds must produce visible governance
  actions; enforcement point = budget transition handler)
- foundation §3 item 10 (phase-1 static budget policy) and AUDIT-004
  (BudgetRecord schema is later-stage hardening)

What this test proves:
  When the orchestrator drives the real runtime path, the per-task
  budget envelope is allocated by `admit_context` (from
  `ContextArtifact.hard_budget_tokens`) and enforced by
  `BudgetGovernor` at the inference boundary. The four AT-027 cases:
    1. projected consumption would exceed -> pre-flight refusal, no
       adapter invocation, no InferenceArtifact persisted;
    2. actual post-call consumption exceeds -> post-flight refusal,
       no InferenceArtifact persisted;
    3. budget already suspended -> idempotent fail-closed refusal;
    4. illegal §9.8 transitions are rejected by the governor.
  Each case produces visible governance evidence as AuditRecord rows
  (INV-021): `budget_transition` records (allocated, active,
  exceeded, suspended) and `inference_failure` records carrying the
  governance reason. No unsafe shortcut is granted.
"""

from __future__ import annotations

import json
import unittest
import sys
import os
from typing import Any, Mapping
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from validation.tests.acceptance.conftest import AcceptanceHarness, FakeModelAdapter
from kernel.services.budget_governor import (
    BudgetGovernor,
    BudgetGovernorViolation,
    BudgetState,
)
from kernel.services.inference_service import (
    InferenceBudgetExhausted,
    InferencePolicy,
    InferenceService,
)


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
            "output_text": "acceptance-test output text",
            "token_usage": {"input": 100, "output": self._output_tokens},
            "latency_ms": 42,
            "model_route_id": "fake-model-v1",
        }


def _build_tight_harness(
    *,
    hard_budget_tokens: int,
    max_output_tokens: int,
    adapter: _CountingAdapter,
) -> AcceptanceHarness:
    """Build a harness whose phase-1 static budget is `hard_budget_tokens`.

    The orchestrator's runtime allocation in `admit_context` reads
    `hard_budget_tokens` off the persisted ContextArtifact, so setting
    the harness static budget here drives the same value through the
    real runtime path. The governor itself uses the same default so a
    direct `assert_admissible` call (used in case 3) sees the same
    envelope.
    """
    harness = AcceptanceHarness(
        inference_policy=InferencePolicy(max_output_tokens=max_output_tokens),
        default_hard_budget_tokens=hard_budget_tokens,
    )
    # Re-wire the inference service with the counting adapter so we can
    # assert that a pre-flight refusal does NOT invoke the adapter.
    harness.inf_svc = InferenceService(
        repository=harness.inf_repo,
        audit_ledger=harness.audit_ledger,
        context_reader=harness.ctx_repo,
        adapter=adapter,
        policy=InferencePolicy(max_output_tokens=max_output_tokens),
        budget_governor=harness.budget_governor,
    )
    harness.orch._inference = harness.inf_svc  # type: ignore[attr-defined]
    return harness


def _admit_context(harness: AcceptanceHarness, task_id: str, *, actual_tokens: int = 10) -> None:
    intent_id = f"intent-{uuid4().hex[:8]}"
    root_rev_id = "rev-genesis-000"
    cap_ctx = harness.issue_capability("read_repository_snapshot", task_id)
    harness.orch.admit_context(
        task_id=task_id,
        intent_id=intent_id,
        capability_token=cap_ctx,
        root_revision_id=root_rev_id,
        request={
            "repo_graph_version": "1.0",
            "symbol_index_version": "1.0",
            "candidate_file_ids": ["src/main.py"],
            "symbol_frontier_ids": ["main"],
            "packing_policy_version": "phase1_budget_policy_v1",
            "actual_tokens": actual_tokens,
        },
    )


def _select_records(harness: AcceptanceHarness, record_type: str, task_id: str):
    rows = harness.conn.execute(
        "SELECT audit_record_id, record_type, payload_json, sequence "
        "FROM audit_records WHERE record_type = ? AND task_id = ? "
        "ORDER BY sequence;",
        (record_type, task_id),
    ).fetchall()
    return [dict(r) for r in rows]


def _select_budget_records(harness: AcceptanceHarness, task_id: str):
    rows = harness.conn.execute(
        "SELECT * FROM budget_records WHERE task_id = ? ORDER BY rowid;",
        (task_id,),
    ).fetchall()
    return [dict(r) for r in rows]


class TestAT027BudgetExhaustionGovernance(unittest.TestCase):
    """AT-027 / INV-021 at the governed inference boundary."""

    # ------------------------------------------------------------------
    # Case A: pre-flight refusal — projected consumption would exceed
    # ------------------------------------------------------------------

    def test_pre_flight_refusal_when_projected_exceeds_hard_budget(self) -> None:
        """Hard budget 40, policy max_output_tokens 50 -> pre-flight refuse.

        The orchestrator allocates a 40-token budget at admit_context;
        admit_inference then projects 50 output tokens, which exceeds
        the hard budget, and the governor must refuse before the
        adapter is invoked. No InferenceArtifact is persisted.
        """
        adapter = _CountingAdapter(output_tokens=20)
        harness = _build_tight_harness(
            hard_budget_tokens=40, max_output_tokens=50, adapter=adapter,
        )
        try:
            task_id = f"task-{uuid4().hex[:8]}"
            _admit_context(harness, task_id, actual_tokens=10)

            # Sanity: orchestrator allocated a 40-token budget for this task.
            snap = harness.budget_governor.snapshot(task_id)
            self.assertEqual(snap["hard_budget_tokens"], 40)
            self.assertEqual(snap["state"], BudgetState.ACTIVE.value)

            cap_inf = harness.issue_capability("invoke_inference", task_id)
            with self.assertRaises(InferenceBudgetExhausted) as ctx:
                harness.orch.admit_inference(
                    task_id=task_id,
                    capability_token=cap_inf,
                    worker_profile="acceptance_worker",
                    model_route_id="fake-model-v1",
                )
            self.assertEqual(ctx.exception.reason, "budget_would_be_exceeded")

            # Adapter NOT invoked.
            self.assertEqual(adapter.invocations, 0)

            # No InferenceArtifact persisted.
            row = harness.conn.execute(
                "SELECT COUNT(*) AS n FROM inference_artifacts WHERE task_id = ?;",
                (task_id,),
            ).fetchone()
            self.assertEqual(row["n"], 0)

            self.assertEqual(
                harness.budget_governor.snapshot(task_id)["state"],
                BudgetState.SUSPENDED.value,
            )

            # Visible governance evidence.
            transitions = _select_records(harness, "budget_transition", task_id)
            to_states = [json.loads(r["payload_json"])["to_state"] for r in transitions]
            self.assertIn("exceeded", to_states)
            self.assertIn("suspended", to_states)

            failures = _select_records(harness, "inference_failure", task_id)
            self.assertTrue(failures)
            last = json.loads(failures[-1]["payload_json"])
            self.assertEqual(last["failure_class"], "budget_would_be_exceeded")
        finally:
            harness.close()

    # ------------------------------------------------------------------
    # Case B: post-flight refusal — actual consumption exceeds hard budget
    # ------------------------------------------------------------------

    def test_post_flight_refusal_when_actual_consumption_exceeds(self) -> None:
        """Pre-flight admits; adapter reports input+output > hard budget.

        Hard budget 200, policy projects 50 output tokens (admits),
        but the adapter reports input=100 + output=150 = 250 > 200.
        The governor must transition to suspended and the service
        must refuse to persist the inference artifact.
        """
        adapter = _CountingAdapter(output_tokens=150)
        harness = _build_tight_harness(
            hard_budget_tokens=200, max_output_tokens=50, adapter=adapter,
        )
        try:
            task_id = f"task-{uuid4().hex[:8]}"
            _admit_context(harness, task_id, actual_tokens=20)

            cap_inf = harness.issue_capability("invoke_inference", task_id)
            with self.assertRaises(InferenceBudgetExhausted) as ctx:
                harness.orch.admit_inference(
                    task_id=task_id,
                    capability_token=cap_inf,
                    worker_profile="acceptance_worker",
                    model_route_id="fake-model-v1",
                )
            self.assertEqual(ctx.exception.reason, "budget_exceeded_during_inference")

            # Adapter was called exactly once (pre-flight admitted).
            self.assertEqual(adapter.invocations, 1)

            # No InferenceArtifact persisted — the output is not a "shortcut".
            row = harness.conn.execute(
                "SELECT COUNT(*) AS n FROM inference_artifacts WHERE task_id = ?;",
                (task_id,),
            ).fetchone()
            self.assertEqual(row["n"], 0)

            self.assertEqual(
                harness.budget_governor.snapshot(task_id)["state"],
                BudgetState.SUSPENDED.value,
            )

            failures = _select_records(harness, "inference_failure", task_id)
            self.assertTrue(failures)
            last = json.loads(failures[-1]["payload_json"])
            self.assertEqual(last["failure_class"], "budget_exceeded_during_inference")

            transitions = _select_records(harness, "budget_transition", task_id)
            budget_records = _select_budget_records(harness, task_id)
            self.assertEqual(len(budget_records), len(transitions))
            self.assertEqual(
                [json.loads(r["payload_json"])["to_state"] for r in transitions],
                [r["budget_state"] for r in budget_records],
            )
            self.assertEqual(
                [r["budget_state"] for r in budget_records],
                [
                    BudgetState.ALLOCATED.value,
                    BudgetState.ACTIVE.value,
                    BudgetState.EXCEEDED.value,
                    BudgetState.SUSPENDED.value,
                ],
            )
            suspended = budget_records[-1]
            self.assertEqual(suspended["task_id"], task_id)
            self.assertEqual(suspended["budget_class"], "tokens")
            self.assertEqual(suspended["allocated_amount"], 200)
            self.assertEqual(suspended["consumed_amount"], 250)
            self.assertEqual(suspended["remaining_amount"], -50)
            self.assertIsNotNone(suspended["suspended_at"])
        finally:
            harness.close()

    # ------------------------------------------------------------------
    # Case C: already-suspended task refuses further inference
    # ------------------------------------------------------------------

    def test_already_suspended_task_refuses_further_inference(self) -> None:
        """A first inference exhausts the budget; a second is refused.

        We drive this through the real runtime path twice: a first
        admit_inference triggers post-flight exhaustion (suspending
        the task); a second attempt for the same task must fail-closed
        with `budget_already_suspended` and never invoke the adapter
        again. (The orchestrator's lifecycle would normally not allow
        two inference admissions for one task; we drive the
        InferenceService directly for the second call to assert the
        governance refusal at the boundary.)
        """
        adapter = _CountingAdapter(output_tokens=150)
        harness = _build_tight_harness(
            hard_budget_tokens=200, max_output_tokens=50, adapter=adapter,
        )
        try:
            task_id = f"task-{uuid4().hex[:8]}"
            _admit_context(harness, task_id, actual_tokens=10)

            ctx_id = harness.orch._tasks[task_id].artifact_ids  # type: ignore[attr-defined]
            from kernel.lifecycle.stage_types import Stage
            context_artifact_id = ctx_id[Stage.CONTEXT]

            # First call exhausts the budget post-flight.
            with self.assertRaises(InferenceBudgetExhausted):
                harness.inf_svc.run_inference(
                    task_id=task_id,
                    context_artifact_id=context_artifact_id,
                    worker_profile="acceptance_worker",
                    model_route_id="fake-model-v1",
                )
            self.assertEqual(adapter.invocations, 1)
            self.assertEqual(
                harness.budget_governor.snapshot(task_id)["state"],
                BudgetState.SUSPENDED.value,
            )

            # Second call must fail-closed with already_suspended and
            # MUST NOT invoke the adapter.
            with self.assertRaises(InferenceBudgetExhausted) as ctx:
                harness.inf_svc.run_inference(
                    task_id=task_id,
                    context_artifact_id=context_artifact_id,
                    worker_profile="acceptance_worker",
                    model_route_id="fake-model-v1",
                )
            self.assertEqual(ctx.exception.reason, "budget_already_suspended")
            self.assertEqual(adapter.invocations, 1)

            # Still no persisted artifact for this task.
            row = harness.conn.execute(
                "SELECT COUNT(*) AS n FROM inference_artifacts WHERE task_id = ?;",
                (task_id,),
            ).fetchone()
            self.assertEqual(row["n"], 0)
        finally:
            harness.close()

    # ------------------------------------------------------------------
    # Case D: legal transition graph sanity
    # ------------------------------------------------------------------

    def test_illegal_transition_is_rejected(self) -> None:
        """Governor must reject illegal §9.8 state transitions."""
        harness = AcceptanceHarness()
        try:
            gov = BudgetGovernor(
                audit_ledger=harness.audit_ledger,
                default_hard_budget_tokens=100,
            )
            task_id = f"task-{uuid4().hex[:8]}"
            gov.allocate(task_id=task_id, hard_budget_tokens=100)
            # active -> suspended (without going through exceeded) is illegal.
            with self.assertRaises(BudgetGovernorViolation):
                gov._transition(  # type: ignore[attr-defined]
                    gov._tasks[task_id],  # type: ignore[attr-defined]
                    BudgetState.SUSPENDED,
                    reason="test_illegal",
                )
        finally:
            harness.close()

    # ------------------------------------------------------------------
    # Case E: real runtime allocation evidence
    # ------------------------------------------------------------------

    def test_admit_context_emits_runtime_budget_allocation(self) -> None:
        """`admit_context` must emit budget_transition rows for the new task.

        Proves the runtime allocation is real (not a test-helper
        pre-seed): without invoking any test-side `allocate`, the
        orchestrator drives `allocated -> active` at admit_context.
        """
        harness = AcceptanceHarness(default_hard_budget_tokens=10_000)
        try:
            task_id = f"task-{uuid4().hex[:8]}"
            _admit_context(harness, task_id, actual_tokens=10)

            snap = harness.budget_governor.snapshot(task_id)
            self.assertEqual(snap["state"], BudgetState.ACTIVE.value)
            self.assertEqual(snap["hard_budget_tokens"], 10_000)

            transitions = _select_records(harness, "budget_transition", task_id)
            to_states = [json.loads(r["payload_json"])["to_state"] for r in transitions]
            self.assertEqual(
                to_states[:2],
                [BudgetState.ALLOCATED.value, BudgetState.ACTIVE.value],
            )
            budget_records = _select_budget_records(harness, task_id)
            self.assertEqual([r["budget_state"] for r in budget_records], to_states)
            self.assertEqual(
                [r["allocated_amount"] for r in budget_records],
                [10_000, 10_000],
            )
            self.assertEqual(
                [r["remaining_amount"] for r in budget_records],
                [10_000, 10_000],
            )
        finally:
            harness.close()


if __name__ == "__main__":
    unittest.main()
