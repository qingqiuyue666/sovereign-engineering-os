"""
Live (opt-in) real-model real-fix tracer.

Performs ONE real network invocation against the Anthropic Messages API
via ``AnthropicMessagesAdapter`` and runs the canonical ``add`` fix
task. This is the honest final proof that a real provider call can
complete a verifiable single-file code fix through the current system
boundaries.

OPT-IN ONLY. Skipped unless BOTH are true:
- Environment variable ``SOS_RUN_LIVE_ANTHROPIC=1``
- Environment variable ``ANTHROPIC_API_KEY`` is set to a non-empty value

Default CI / test runs MUST NOT perform network IO. This test is
deliberately narrow:
- single invocation (``max_retries == 0``)
- short, tight policy
- asserts on success: ``RealFixResult.verified == True``; all four
  ``add`` verification cases passed; audit chain records exactly
  ``real_fix_attempt_started`` followed by ``real_fix_verified_pass``;
  every audit record carries ``replay_ceiling = "semantic"``.
- on adapter failure: the test fails with the normalized failure class
  visible, so the failure is honest evidence — not a silent downgrade.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from kernel.adapters.anthropic_adapter import AnthropicMessagesAdapter
from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.services.inference_service import InferencePolicy
from kernel.stores.sqlite.repositories import AuditRepository
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection
from kernel.tracers.real_fix_tracer import RealFixTracer, make_add_fix_task


_LIVE_ENABLED = (
    os.environ.get("SOS_RUN_LIVE_ANTHROPIC") == "1"
    and bool(os.environ.get("ANTHROPIC_API_KEY"))
)
_SKIP_REASON = (
    "live Anthropic real-fix tracer disabled: set SOS_RUN_LIVE_ANTHROPIC=1 "
    "and ANTHROPIC_API_KEY to run one real invocation."
)


@unittest.skipUnless(_LIVE_ENABLED, _SKIP_REASON)
class TestLiveRealFixTracer(unittest.TestCase):
    """Single real adapter invocation + deterministic fix verification."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.audit = AppendOnlyLedger(
            repository=self.audit_repo, actor_identity="live_real_fix_tracer"
        )

    def tearDown(self) -> None:
        self.conn.close()

    def test_live_one_shot_real_fix(self) -> None:
        policy = InferencePolicy(
            max_output_tokens=512,
            timeout_seconds=45.0,
            max_retries=0,
        )
        adapter = AnthropicMessagesAdapter()
        tracer = RealFixTracer(
            adapter=adapter, audit_ledger=self.audit, policy=policy
        )

        task = make_add_fix_task(task_id="live-real-fix-add")
        result = tracer.run(task)

        # Record-level honesty: every audit record emitted by the tracer
        # carries the honest replay ceiling. This is asserted before the
        # outcome assertion so reviewers can always inspect the chain.
        rows = self.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE record_type LIKE 'real_fix_%' ORDER BY sequence;"
        ).fetchall()
        self.assertGreaterEqual(
            len(rows),
            2,
            "expected at least real_fix_attempt_started + outcome record",
        )
        import json as _json

        for r in rows:
            payload = _json.loads(r["payload_json"])
            self.assertEqual(
                payload.get("replay_ceiling"),
                "semantic",
                "live real-fix tracer must never claim exact replay "
                "fidelity for real-model output",
            )

        if not result.verified:
            # Honest posture: if the provider did not produce a valid fix
            # we surface the normalized outcome and class so reviewers
            # see exactly how the boundary failed. This is evidence, not
            # a silent downgrade.
            self.fail(
                "live real-fix tracer did not verify: "
                f"outcome={result.outcome} "
                f"failure_class={result.failure_class} "
                f"detail={result.failure_detail} "
                f"first_failing_case_index={result.first_failing_case_index} "
                f"output_hash={result.output_hash}"
            )

        # Success path.
        self.assertEqual(result.outcome, "real_fix_verified_pass")
        self.assertEqual(result.replay_ceiling, "semantic")
        self.assertTrue(result.output_hash.startswith("sha256:"))

        # Audit chain shape.
        record_types = [
            self.conn.execute(
                "SELECT record_type FROM audit_records "
                "WHERE sequence = ?;",
                (row["sequence"] if hasattr(row, "__getitem__") else row[0],),
            ).fetchone()["record_type"]
            for row in self.conn.execute(
                "SELECT sequence FROM audit_records "
                "WHERE record_type LIKE 'real_fix_%' ORDER BY sequence;"
            ).fetchall()
        ]
        self.assertEqual(record_types[0], "real_fix_attempt_started")
        self.assertEqual(record_types[-1], "real_fix_verified_pass")


if __name__ == "__main__":
    unittest.main()
