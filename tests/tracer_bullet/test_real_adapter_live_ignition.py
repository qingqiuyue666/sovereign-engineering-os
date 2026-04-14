"""
Live (opt-in) real-model ignition tracer.

This test performs ONE real network invocation against the Anthropic
Messages API through `AnthropicMessagesAdapter`, routed through the
real `InferenceService` boundary. It is the honest final proof that the
wiring works against the real provider.

OPT-IN ONLY. This test is skipped unless BOTH of the following are true:
- Environment variable `SOS_RUN_LIVE_ANTHROPIC=1`
- Environment variable `ANTHROPIC_API_KEY` is set to a non-empty value

Default CI / test runs MUST NOT perform network IO. This test is
deliberately narrow:
- single invocation (no retries — policy.max_retries == 0)
- short timeout
- tight max_output_tokens
- asserts: typed response produced, InferenceArtifact persisted,
  audit records the honest `replay_ceiling = "semantic"`.

This test is the ignition tracer itself. A green run proves the narrow
signable path accepts real provider output under the governed boundary.
A failure (network, quota, auth, malformed, etc.) proves the normalized
failure classes route through `_emit_failure_bundle`; it does NOT
silently downgrade.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from kernel.adapters.anthropic_adapter import AnthropicMessagesAdapter
from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.lifecycle.signable_path_orchestrator import IntentCausalAnchor
from kernel.services.context_service import ContextService
from kernel.services.inference_service import (
    InferenceFailure,
    InferencePolicy,
    InferenceService,
)
from kernel.stores.sqlite.repositories import (
    AuditRepository,
    ContextArtifactRepository,
    InferenceArtifactRepository,
)
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection


_LIVE_ENABLED = (
    os.environ.get("SOS_RUN_LIVE_ANTHROPIC") == "1"
    and bool(os.environ.get("ANTHROPIC_API_KEY"))
)
_SKIP_REASON = (
    "live Anthropic tracer disabled: set SOS_RUN_LIVE_ANTHROPIC=1 and "
    "ANTHROPIC_API_KEY to run one real invocation."
)


@unittest.skipUnless(_LIVE_ENABLED, _SKIP_REASON)
class TestLiveAnthropicIgnitionTracer(unittest.TestCase):
    """Single real invocation through the governed boundary. Opt-in only."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.ctx_repo = ContextArtifactRepository(self.conn)
        self.inf_repo = InferenceArtifactRepository(self.conn)
        self.audit = AppendOnlyLedger(
            repository=self.audit_repo, actor_identity="live_tracer"
        )
        self.ctx_svc = ContextService(
            repository=self.ctx_repo, audit_ledger=self.audit
        )

    def tearDown(self) -> None:
        self.conn.close()

    def _make_context(self, task_id: str, root_rev_id: str) -> str:
        intent_anchor = IntentCausalAnchor(
            intent_id=f"intent-{task_id}",
            task_id=task_id,
            state="admitted",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return self.ctx_svc.build_context_artifact(
            task_id=task_id,
            root_revision_id=root_rev_id,
            intent_anchor=intent_anchor,
            request={
                "repo_graph_version": "1.0",
                "symbol_index_version": "1.0",
                "candidate_file_ids": ["src/tracer.py"],
                "symbol_frontier_ids": ["main"],
                "packing_policy_version": "phase1_budget_policy_v1",
                "actual_tokens": 100,
            },
        )

    def test_live_one_shot_ignition(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        ctx_id = self._make_context(task_id, "rev-live-000")

        # Narrow, opt-in live policy. No retries. Tight output budget.
        policy = InferencePolicy(
            max_output_tokens=64,
            timeout_seconds=30.0,
            max_retries=0,
        )
        adapter = AnthropicMessagesAdapter()
        svc = InferenceService(
            repository=self.inf_repo,
            audit_ledger=self.audit,
            context_reader=self.ctx_repo,
            adapter=adapter,
            policy=policy,
        )

        try:
            inf_id = svc.run_inference(
                task_id=task_id,
                context_artifact_id=ctx_id,
                worker_profile="live_tracer",
                model_route_id=adapter._model_route_id,  # transparency
            )
        except InferenceFailure as e:
            # Honest posture: live failure is still useful evidence. Record
            # which normalized class fired so reviewers can see that the
            # failure routed through the governed failure-bundle path.
            fail_rows = self.conn.execute(
                "SELECT payload_json FROM audit_records "
                "WHERE record_type = 'inference_failure';"
            ).fetchall()
            self.assertEqual(
                len(fail_rows),
                1,
                "live failure must produce exactly one inference_failure audit record",
            )
            payload = json.loads(fail_rows[0]["payload_json"])
            self.assertEqual(payload["failure_class"], "model_api_failure")
            self.fail(
                f"live ignition produced a normalized adapter failure: "
                f"{e} (failure_bundle payload={payload})"
            )

        # Happy path: typed artifact persisted, audit records honest ceiling.
        row = self.conn.execute(
            "SELECT * FROM inference_artifacts WHERE inference_artifact_id = ?;",
            (inf_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertTrue(row["output_hash"].startswith("sha256:"))
        self.assertTrue(row["model_route_id"])

        audit_rows = self.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE record_type = 'inference_artifact_created';"
        ).fetchall()
        self.assertEqual(len(audit_rows), 1)
        payload = json.loads(audit_rows[0]["payload_json"])
        self.assertEqual(
            payload.get("replay_ceiling"),
            "semantic",
            "live tracer must record replay_ceiling=semantic; real-model "
            "outputs MUST NOT claim exact replay fidelity",
        )


if __name__ == "__main__":
    unittest.main()
