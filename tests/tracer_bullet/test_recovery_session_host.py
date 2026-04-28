"""
P0-9 phase 1 — RecoverySessionHost tests.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.5 Replay admission boundary
- v11 §22.10 invariant binding
- foundation §6 (P0 sealing + crash-window proofs)

These tests pin the behaviour of `RecoverySessionHost`:

- The host owns one live `SignablePathOrchestrator` and one
  `RecoveryGate`; restore via the host populates the host-owned
  orchestrator's in-memory `_tasks` and remains visible to
  follow-on admission against the same instance.
- The gate retains authority for `_RESTORE_ALLOWED` membership;
  `NEEDS_MANUAL_REVIEW` and `UNRECOVERABLE` verdicts do not mutate
  the owned orchestrator.
- Restore via the host produces zero durable side effects (the
  orchestrator's `restore_task_from_snapshot` already promises
  this; the host adds no writes of its own).
- Restore is visible only inside the owned orchestrator instance;
  a second fresh orchestrator over the same connection sees no
  restored task. P0-8's ephemerality property is preserved while
  P0-9's value (continuable in-host restore) is also proven.
- `close()` is idempotent, blocks public operations, and invokes
  the optional callback exactly once.
- P0-9 does not introduce a CLI `restore` subcommand.
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import Any
from uuid import uuid4

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle.recovery_cli import build_parser
from kernel.lifecycle.recovery_gate import (
    RecoveryGate,
    build_standard_recovery_gate,
)
from kernel.lifecycle.recovery_session_host import (
    RecoverySessionHost,
    RecoverySessionHostClosed,
)
from kernel.lifecycle.signable_path_orchestrator import (
    OrchestratorRejected,
    SignablePathOrchestrator,
)
from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_recovery import RecoveryClass
from validation.tests.acceptance.conftest import AcceptanceHarness


def _gate_from_harness(harness: AcceptanceHarness) -> RecoveryGate:
    return build_standard_recovery_gate(
        audit_repository=harness.audit_repo,
        intent_anchor_repository=harness.intent_repo,
        context_repository=harness.ctx_repo,
        inference_repository=harness.inf_repo,
        patch_proposal_repository=harness.pp_repo,
        validation_receipt_repository=harness.vr_repo,
        review_repository=harness.rv_repo,
        approval_repository=harness.ap_repo,
        revision_repository=harness.rev_repo,
        replay_anchor_repository=harness.ra_repo,
    )


def _fresh_orchestrator_from_harness(
    harness: AcceptanceHarness,
) -> SignablePathOrchestrator:
    """Build a fresh `SignablePathOrchestrator` over the harness's
    services and connection.

    The fresh instance starts with an empty ``_tasks`` dict — the
    precondition for `restore_task_from_snapshot`. Mirrors the helper
    pattern used by P0-3 / P0-5 / P0-8 tests so the host tests
    exercise the same in-process composition shape.
    """
    return SignablePathOrchestrator(
        capability_service=harness.cap_svc,
        context_service=harness.ctx_svc,
        inference_service=harness.inf_svc,
        patch_proposal_service=harness.pp_svc,
        validation_service=harness.val_svc,
        review_service=harness.rev_svc,
        approval_service=harness.ap_svc,
        revision_seal_service=harness.seal_svc,
        evidence_service=harness.evidence_svc,
        audit_ledger=harness.audit_ledger,
        budget_governor=harness.budget_governor,
        context_repository=harness.ctx_repo,
        intent_anchor_repository=harness.intent_repo,
        connection=harness.conn,
    )


def _audit_count(harness: AcceptanceHarness) -> int:
    return harness.conn.execute(
        "SELECT COUNT(*) FROM audit_records;"
    ).fetchone()[0]


def _intent_anchor_count(harness: AcceptanceHarness) -> int:
    return harness.conn.execute(
        "SELECT COUNT(*) FROM intent_anchor_records;"
    ).fetchone()[0]


class TestRecoverySessionHost(unittest.TestCase):
    """P0-9 phase 1 — RecoverySessionHost behaviour."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    # ------------------------------------------------------------------
    # A. unknown task -> UNRECOVERABLE; no orchestrator mutation
    # ------------------------------------------------------------------

    def test_session_host_evaluate_unknown_task_returns_unrecoverable(
        self,
    ) -> None:
        gate = _gate_from_harness(self.harness)
        fresh_orch = _fresh_orchestrator_from_harness(self.harness)
        host = RecoverySessionHost(
            recovery_gate=gate,
            orchestrator=fresh_orch,
        )
        try:
            result = host.evaluate_task("missing-task")
            self.assertEqual(
                result.recovery_class, RecoveryClass.UNRECOVERABLE
            )
            self.assertFalse(result.restored)
            self.assertIsNone(host.current_stage("missing-task"))
        finally:
            host.close()

    # ------------------------------------------------------------------
    # B. SAFE_TO_RESUME -> stage becomes visible inside host
    # ------------------------------------------------------------------

    def test_session_host_restore_safe_to_resume_keeps_stage_in_host(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)

        gate = _gate_from_harness(self.harness)
        fresh_orch = _fresh_orchestrator_from_harness(self.harness)
        host = RecoverySessionHost(
            recovery_gate=gate,
            orchestrator=fresh_orch,
        )
        try:
            result = host.restore_task(task_id)
            self.assertEqual(
                result.recovery_class, RecoveryClass.SAFE_TO_RESUME
            )
            self.assertTrue(result.restored)
            self.assertEqual(
                host.current_stage(task_id), Stage.INFERENCE
            )
            self.assertEqual(
                host.orchestrator.current_stage(task_id),
                Stage.INFERENCE,
            )
        finally:
            host.close()

    # ------------------------------------------------------------------
    # C. restored task continues admission on the same live orchestrator
    # ------------------------------------------------------------------

    def test_session_host_restored_task_can_continue_next_stage(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)

        gate = _gate_from_harness(self.harness)
        fresh_orch = _fresh_orchestrator_from_harness(self.harness)
        host = RecoverySessionHost(
            recovery_gate=gate,
            orchestrator=fresh_orch,
        )
        try:
            result = host.restore_task(task_id)
            self.assertTrue(result.restored)
            self.assertEqual(
                host.current_stage(task_id), Stage.INFERENCE
            )

            # Issue a real propose_patch capability against the
            # shared capability service and continue admission on
            # the host-owned orchestrator. This is the load-bearing
            # P0-9 property: restore is meaningful because the same
            # live orchestrator instance accepts the next stage.
            cap = self.harness.issue_capability("propose_patch", task_id)
            host.orchestrator.admit_patch_proposal(
                task_id=task_id,
                capability_token=cap,
            )
            self.assertEqual(
                host.current_stage(task_id), Stage.PATCH_PROPOSAL
            )
        finally:
            host.close()

    # ------------------------------------------------------------------
    # D. NEEDS_MANUAL_REVIEW -> no orchestrator mutation
    # ------------------------------------------------------------------

    def test_session_host_restore_needs_manual_review_does_not_mutate_orchestrator(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        # Inject a duplicate intent_anchor_records row for the same
        # task_id; classifier surfaces NEEDS_MANUAL_REVIEW per
        # P0-2/P0-4 semantics, and the gate refuses restore.
        self.harness.intent_repo.insert(
            intent_id=f"intent-dup-{uuid4().hex[:8]}",
            task_id=task_id,
            state="admitted",
        )

        gate = _gate_from_harness(self.harness)
        fresh_orch = _fresh_orchestrator_from_harness(self.harness)
        host = RecoverySessionHost(
            recovery_gate=gate,
            orchestrator=fresh_orch,
        )
        try:
            result = host.restore_task(task_id)
            self.assertEqual(
                result.recovery_class,
                RecoveryClass.NEEDS_MANUAL_REVIEW,
            )
            self.assertFalse(result.restored)
            self.assertIsNone(host.current_stage(task_id))
        finally:
            host.close()

    # ------------------------------------------------------------------
    # E. SEALED -> terminal introspection only
    # ------------------------------------------------------------------

    def test_session_host_restore_sealed_for_introspection(self) -> None:
        ids = self.harness.run_full_happy_path()
        task_id = ids["task_id"]

        gate = _gate_from_harness(self.harness)
        fresh_orch = _fresh_orchestrator_from_harness(self.harness)
        host = RecoverySessionHost(
            recovery_gate=gate,
            orchestrator=fresh_orch,
        )
        try:
            result = host.restore_task(task_id)
            self.assertEqual(
                result.recovery_class, RecoveryClass.SEALED
            )
            self.assertTrue(result.restored)
            self.assertEqual(
                host.current_stage(task_id), Stage.SEALED
            )
        finally:
            host.close()

    # ------------------------------------------------------------------
    # F. ABANDONED -> introspection only; further admission refused
    # ------------------------------------------------------------------

    def test_session_host_restore_abandoned_for_introspection_and_refuses_follow_on(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)
        self.harness.orch.abandon(
            task_id=task_id, reason="p0_9_abandon_test"
        )

        gate = _gate_from_harness(self.harness)
        fresh_orch = _fresh_orchestrator_from_harness(self.harness)
        host = RecoverySessionHost(
            recovery_gate=gate,
            orchestrator=fresh_orch,
        )
        try:
            result = host.restore_task(task_id)
            self.assertEqual(
                result.recovery_class, RecoveryClass.ABANDONED
            )
            self.assertTrue(result.restored)
            self.assertEqual(
                host.current_stage(task_id), Stage.ABANDONED
            )

            # Further admission against an abandoned task must be
            # refused fail-closed by the orchestrator's `_get_task`
            # guard. Token contents are irrelevant: the guard runs
            # before capability verification.
            with self.assertRaises(OrchestratorRejected):
                host.orchestrator.admit_inference(
                    task_id=task_id,
                    capability_token={"capability_token_id": "ignored"},
                    worker_profile="recovery_session_host_test",
                    model_route_id="fake-model-v1",
                )
        finally:
            host.close()

    # ------------------------------------------------------------------
    # G. restore via host writes no durable rows
    # ------------------------------------------------------------------

    def test_session_host_restore_has_no_durable_side_effects(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)

        before_audit = _audit_count(self.harness)
        before_intent = _intent_anchor_count(self.harness)

        gate = _gate_from_harness(self.harness)
        fresh_orch = _fresh_orchestrator_from_harness(self.harness)
        host = RecoverySessionHost(
            recovery_gate=gate,
            orchestrator=fresh_orch,
        )
        try:
            result = host.restore_task(task_id)
            self.assertTrue(result.restored)
        finally:
            host.close()

        self.assertEqual(_audit_count(self.harness), before_audit)
        self.assertEqual(
            _intent_anchor_count(self.harness), before_intent
        )

    # ------------------------------------------------------------------
    # H. restore visibility is bounded by the owned orchestrator
    # ------------------------------------------------------------------

    def test_session_host_restore_is_visible_only_inside_owned_orchestrator_instance(
        self,
    ) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        self.harness.run_through_stage(task_id, Stage.INFERENCE)

        gate = _gate_from_harness(self.harness)
        fresh_orch_1 = _fresh_orchestrator_from_harness(self.harness)
        host = RecoverySessionHost(
            recovery_gate=gate,
            orchestrator=fresh_orch_1,
        )
        try:
            host.restore_task(task_id)
            self.assertEqual(
                host.current_stage(task_id), Stage.INFERENCE
            )

            # A second, distinct orchestrator over the same harness
            # services and connection has its own empty `_tasks`
            # dict. P0-8's ephemerality property still holds: the
            # host's restore is bounded to the instance it owns;
            # P0-9's value is that within the host's lifetime that
            # boundary admits real follow-on work.
            second_fresh_orch = _fresh_orchestrator_from_harness(
                self.harness
            )
            self.assertIsNone(second_fresh_orch.current_stage(task_id))
        finally:
            host.close()

    # ------------------------------------------------------------------
    # I. close() is idempotent, blocks operations, calls callback once
    # ------------------------------------------------------------------

    def test_session_host_close_is_idempotent_and_blocks_operations(
        self,
    ) -> None:
        gate = _gate_from_harness(self.harness)
        fresh_orch = _fresh_orchestrator_from_harness(self.harness)

        callback_calls = {"count": 0}

        def _on_close() -> None:
            callback_calls["count"] += 1

        host = RecoverySessionHost(
            recovery_gate=gate,
            orchestrator=fresh_orch,
            close_callback=_on_close,
        )

        self.assertFalse(host.closed)
        host.close()
        self.assertTrue(host.closed)
        self.assertEqual(callback_calls["count"], 1)

        # Idempotent.
        host.close()
        self.assertTrue(host.closed)
        self.assertEqual(callback_calls["count"], 1)

        with self.assertRaises(RecoverySessionHostClosed):
            host.evaluate_task("any")
        with self.assertRaises(RecoverySessionHostClosed):
            host.restore_task("any")
        with self.assertRaises(RecoverySessionHostClosed):
            host.current_stage("any")
        with self.assertRaises(RecoverySessionHostClosed):
            _ = host.orchestrator

    # ------------------------------------------------------------------
    # I'. close_callback exception leaves host closed; callback runs once
    # ------------------------------------------------------------------

    def test_session_host_close_callback_exception_marks_closed_and_runs_once(
        self,
    ) -> None:
        """A failing close_callback must propagate, leave the host
        closed, run exactly once, and block all subsequent public
        operations.

        Pins the production-code comment that intentionally marks the
        host closed BEFORE invoking the callback so that a callback
        exception does not leave the host in a half-open state.
        """
        gate = _gate_from_harness(self.harness)
        fresh_orch = _fresh_orchestrator_from_harness(self.harness)

        callback_calls = {"count": 0}

        def _on_close() -> None:
            callback_calls["count"] += 1
            raise RuntimeError("close failed")

        host = RecoverySessionHost(
            recovery_gate=gate,
            orchestrator=fresh_orch,
            close_callback=_on_close,
        )

        self.assertFalse(host.closed)

        with self.assertRaises(RuntimeError) as ctx:
            host.close()
        self.assertEqual(str(ctx.exception), "close failed")

        self.assertTrue(host.closed)
        self.assertEqual(callback_calls["count"], 1)

        # Second close() is a no-op even though the first raised.
        host.close()
        self.assertTrue(host.closed)
        self.assertEqual(callback_calls["count"], 1)

        with self.assertRaises(RecoverySessionHostClosed):
            host.evaluate_task("any")
        with self.assertRaises(RecoverySessionHostClosed):
            host.restore_task("any")
        with self.assertRaises(RecoverySessionHostClosed):
            host.current_stage("any")
        with self.assertRaises(RecoverySessionHostClosed):
            _ = host.orchestrator

    # ------------------------------------------------------------------
    # J. P0-9 does not add a CLI `restore` subcommand
    # ------------------------------------------------------------------

    def test_session_host_does_not_require_cli_restore(self) -> None:
        import argparse as _argparse

        parser = build_parser()
        sub_actions = [
            action
            for action in parser._actions
            if isinstance(action, _argparse._SubParsersAction)
        ]
        self.assertEqual(len(sub_actions), 1)
        registered = set(sub_actions[0].choices.keys())
        self.assertEqual(
            registered,
            {"evaluate", "restore-dry-run"},
            "P0-9 must not add a CLI restore subcommand; "
            f"got {sorted(registered)!r}",
        )


if __name__ == "__main__":
    unittest.main()
