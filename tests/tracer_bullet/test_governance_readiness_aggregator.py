"""P4-01 cross-subsystem governance readiness aggregation tests."""

from __future__ import annotations

import ast
import copy
import inspect
import json
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle import governance_readiness_aggregator as aggregator_module
from kernel.lifecycle.approval_review_readiness import (
    build_approval_review_readiness_envelope,
    render_approval_review_readiness_envelope,
)
from kernel.lifecycle.approval_review_readiness_ci import (
    consume_approval_review_readiness_ci,
)
from kernel.lifecycle.approval_review_readiness_contract import (
    check_approval_review_readiness_contract,
    render_approval_review_readiness_contract_check,
)
from kernel.lifecycle.evidence_replay_readiness import (
    build_evidence_replay_readiness_envelope,
    render_evidence_replay_readiness_envelope,
)
from kernel.lifecycle.evidence_replay_readiness_ci import (
    consume_evidence_replay_readiness_ci,
)
from kernel.lifecycle.evidence_replay_readiness_contract import (
    check_evidence_replay_readiness_contract,
    render_evidence_replay_readiness_contract_check,
)
from kernel.lifecycle.governance_readiness_aggregator import (
    GovernanceReadinessAggregate,
    build_governance_readiness_aggregate,
    governance_readiness_manifest,
    render_governance_readiness_aggregate,
)
from kernel.lifecycle.recovery_session_host_read_only_ci import (
    consume_recovery_session_host_read_only_ci,
)
from kernel.lifecycle.recovery_session_host_verdict_cross_phase_digest_contract import (
    check_recovery_session_host_verdict_cross_phase_digest_contract,
    render_recovery_session_host_verdict_cross_phase_digest_contract_check,
)
from kernel.lifecycle.stage_types import Stage
from kernel.lifecycle.task_lifecycle_journal_snapshot_batch import (
    build_task_lifecycle_journal_snapshot_batch_digest,
    render_task_lifecycle_journal_snapshot_batch_digest,
)
from kernel.lifecycle.task_lifecycle_journal_snapshot_batch_ci import (
    consume_task_lifecycle_journal_snapshot_batch_ci,
)
from kernel.lifecycle.task_lifecycle_journal_snapshot_batch_readiness import (
    check_task_lifecycle_journal_snapshot_batch_readiness,
    render_task_lifecycle_journal_snapshot_batch_readiness_check,
)
from kernel.lifecycle.task_recovery import TaskLifecycleSnapshot


SUBSYSTEMS = [
    "approval_review",
    "evidence_replay",
    "recovery_session_host",
    "task_lifecycle_journal",
]

EXPECTED_MANIFEST = {
    "surface": "governance_readiness_aggregate",
    "version": 1,
    "input_shape": "mapping_of_rendered_read_only_ci_outputs",
    "required_subsystems": SUBSYSTEMS,
    "restore_supported": False,
    "durable_writes": False,
    "cli_commands": [],
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": ["invalid_governance_payload", "not_ready", "ready"],
    "failure_values": [
        "payload_not_mapping",
        "missing_subsystem",
        "unknown_subsystem",
        "subsystem_payload_invalid",
        "subsystem_not_ready",
        "subsystem_restore_supported",
        "subsystem_durable_writes",
        "subsystem_cli_commands",
        "subsystem_runtime_dependencies",
        "subsystem_not_json_safe",
    ],
}

EXPECTED_RENDERED_KEYS = [
    "ready",
    "reason_code",
    "failures",
    "aggregate",
]

EXPECTED_AGGREGATE_KEYS = [
    "surface",
    "version",
    "subsystem_count",
    "ready_count",
    "not_ready_count",
    "invalid_count",
    "ready_subsystems",
    "not_ready_subsystems",
    "invalid_subsystems",
    "reason_counts",
    "failure_counts",
    "subsystem_surfaces",
    "subsystem_versions",
    "operator_safe",
    "restore_supported",
    "durable_writes",
    "cli_command_count",
    "runtime_dependency_count",
    "json_safe",
]

REPR_MARKERS = (
    "GovernanceReadinessAggregate(",
    "TaskLifecycleSnapshot(",
    "<Stage.",
    " object at 0x",
    "<sqlite3.",
)

FORBIDDEN_SOURCE_MARKERS = (
    "sqlite",
    "open_connection",
    "AuditRepository",
    "AppendOnlyLedger",
    "UnitOfWork",
    "KernelUnitOfWork",
    "subprocess",
    "os.environ",
    "argparse",
    "click",
    "socket",
    "queue",
    "threading",
    "asyncio",
    "restore_task",
    "restore_if_allowed",
    "restore_task_from_snapshot",
    "recovery_session_host",
    "task_lifecycle_journal_snapshot",
    "evidence_replay_readiness",
    "approval_review_readiness",
    "apply_migrations",
)


def _valid_ci_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "ci_ok": True,
        "reason_code": "ready",
        "failures": [],
        "surface": "synthetic_read_only_ci",
        "version": 1,
        "contract_ready": True,
        "contract_reason_code": "ready",
        "restore_supported": False,
        "durable_writes": False,
        "cli_command_count": 0,
        "runtime_dependency_count": 0,
        "json_safe": True,
    }
    base.update(overrides)
    return base


def _valid_payloads() -> dict[str, dict[str, object]]:
    return {
        subsystem: _valid_ci_payload(surface=f"{subsystem}_ci")
        for subsystem in SUBSYSTEMS
    }


def _recursive_values(payload: object) -> list[object]:
    values: list[object] = [payload]
    if isinstance(payload, dict):
        for key, value in payload.items():
            values.extend(_recursive_values(key))
            values.extend(_recursive_values(value))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_recursive_values(value))
    return values


def _assert_json_safe(payload: object) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    decoded = json.loads(encoded)
    if decoded != payload:
        raise AssertionError("payload did not round-trip through JSON")
    for value in _recursive_values(payload):
        if isinstance(value, (set, frozenset, tuple)):
            raise AssertionError(
                f"payload leaked runtime collection {type(value).__name__}"
            )


def _assert_no_runtime_repr(payload: object) -> None:
    text = json.dumps(payload, sort_keys=True)
    for marker in REPR_MARKERS:
        if marker in text:
            raise AssertionError(f"runtime repr marker leaked: {marker}")


def _assert_not_ready(
    testcase: unittest.TestCase,
    payloads: dict[str, dict[str, object]],
    expected_failure: str,
) -> GovernanceReadinessAggregate:
    aggregate = build_governance_readiness_aggregate(payloads)
    testcase.assertIs(aggregate.ready, False)
    testcase.assertEqual(aggregate.reason_code, "not_ready")
    testcase.assertIn(expected_failure, aggregate.failures)
    testcase.assertEqual(aggregate.aggregate["operator_safe"], False)
    testcase.assertEqual(aggregate.aggregate["not_ready_count"], 1)
    testcase.assertEqual(aggregate.aggregate["invalid_count"], 0)
    testcase.assertEqual(
        aggregate.aggregate["not_ready_subsystems"],
        ["evidence_replay"],
    )
    return aggregate


def _recovery_safe_digest() -> dict[str, object]:
    return {
        "ok": True,
        "reason_code": "ok",
        "failures": [],
        "digest": {
            "after_manifest_version": 1,
            "after_reason_code": "ok",
            "after_ready": True,
            "before_manifest_version": 1,
            "before_reason_code": "ok",
            "before_ready": True,
            "cli_command_count": 0,
            "comparison_change_count": 0,
            "comparison_changed": False,
            "comparison_failure_count": 0,
            "comparison_ok": True,
            "comparison_reason_code": "ok",
            "contract_failure_count": 0,
            "contract_ready": True,
            "contract_reason_code": "ok",
            "cross_phase_ok": True,
            "durable_writes": False,
            "failures": [],
            "has_cli_commands": False,
            "has_contract_failure": False,
            "has_drift": False,
            "has_restore_or_durable_surface": False,
            "has_runtime_dependencies": False,
            "json_safe": True,
            "manifest_surface": "recovery_session_host_verdict_summary",
            "manifest_version": 1,
            "operator_safe": True,
            "reason_code": "ok",
            "restore_supported": False,
            "runtime_dependency_count": 0,
        },
    }


def _real_recovery_ci_payload() -> dict[str, object]:
    check = check_recovery_session_host_verdict_cross_phase_digest_contract(
        _recovery_safe_digest()
    )
    rendered = render_recovery_session_host_verdict_cross_phase_digest_contract_check(
        check
    )
    return consume_recovery_session_host_read_only_ci(rendered)


def _real_task_lifecycle_ci_payload() -> dict[str, object]:
    snapshot = TaskLifecycleSnapshot(
        task_id="task-001",
        intent_id="intent-001",
        current_stage=Stage.CONTEXT,
        artifact_ids={Stage.CONTEXT: "ctx-001"},
        terminal_state=None,
        last_event_sequence=1,
        lifecycle_record_count=1,
        malformed_event_count=0,
        intent_anchor_count=1,
        intent_created_at="2026-01-01T00:00:00+00:00",
    )
    digest = build_task_lifecycle_journal_snapshot_batch_digest([snapshot])
    rendered_digest = render_task_lifecycle_journal_snapshot_batch_digest(digest)
    check = check_task_lifecycle_journal_snapshot_batch_readiness(
        rendered_digest
    )
    rendered_check = render_task_lifecycle_journal_snapshot_batch_readiness_check(
        check
    )
    return consume_task_lifecycle_journal_snapshot_batch_ci(rendered_check)


def _real_evidence_replay_ci_payload() -> dict[str, object]:
    envelope = build_evidence_replay_readiness_envelope(
        [
            {
                "task_id": "task-001",
                "record_type": "evidence_closure",
                "artifact_refs": ["ra-001"],
                "stage": "evidence",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ]
    )
    rendered_envelope = render_evidence_replay_readiness_envelope(envelope)
    check = check_evidence_replay_readiness_contract(rendered_envelope)
    rendered_check = render_evidence_replay_readiness_contract_check(check)
    return consume_evidence_replay_readiness_ci(rendered_check)


def _real_approval_review_ci_payload() -> dict[str, object]:
    envelope = build_approval_review_readiness_envelope(
        [
            {
                "task_id": "task-001",
                "record_type": "approval_artifact",
                "approval_state": "approved",
                "review_state": "created",
                "revision_id": "rev-001",
                "seal_id": "snap-001",
                "actor_identity": "phase1_approver",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ]
    )
    rendered_envelope = render_approval_review_readiness_envelope(envelope)
    check = check_approval_review_readiness_contract(rendered_envelope)
    rendered_check = render_approval_review_readiness_contract_check(check)
    return consume_approval_review_readiness_ci(rendered_check)


class TestGovernanceReadinessAggregatorHappyPath(unittest.TestCase):
    def test_aggregates_synthetic_valid_payloads_ready(self) -> None:
        aggregate = build_governance_readiness_aggregate(_valid_payloads())

        self.assertIsInstance(aggregate, GovernanceReadinessAggregate)
        self.assertIs(aggregate.ready, True)
        self.assertEqual(aggregate.reason_code, "ready")
        self.assertEqual(aggregate.failures, ())
        self.assertEqual(aggregate.aggregate["subsystem_count"], 4)
        self.assertEqual(aggregate.aggregate["ready_count"], 4)
        self.assertEqual(aggregate.aggregate["not_ready_count"], 0)
        self.assertEqual(aggregate.aggregate["invalid_count"], 0)
        self.assertEqual(aggregate.aggregate["ready_subsystems"], SUBSYSTEMS)
        self.assertEqual(aggregate.aggregate["not_ready_subsystems"], [])
        self.assertEqual(aggregate.aggregate["invalid_subsystems"], [])
        self.assertEqual(aggregate.aggregate["reason_counts"], {"ready": 4})
        self.assertEqual(aggregate.aggregate["failure_counts"], {})
        self.assertIs(aggregate.aggregate["operator_safe"], True)

        rendered = render_governance_readiness_aggregate(aggregate)
        _assert_json_safe(rendered)


class TestGovernanceReadinessAggregatorInvalidPayloads(unittest.TestCase):
    def test_rejects_non_mapping_input(self) -> None:
        aggregate = build_governance_readiness_aggregate("bad")

        self.assertIs(aggregate.ready, False)
        self.assertEqual(aggregate.reason_code, "invalid_governance_payload")
        self.assertEqual(aggregate.failures, ("payload_not_mapping",))
        self.assertEqual(aggregate.aggregate["subsystem_count"], 0)
        self.assertEqual(
            aggregate.aggregate["failure_counts"],
            {"payload_not_mapping": 1},
        )

    def test_detects_missing_subsystem(self) -> None:
        payloads = _valid_payloads()
        del payloads["approval_review"]

        aggregate = build_governance_readiness_aggregate(payloads)

        self.assertIs(aggregate.ready, False)
        self.assertEqual(aggregate.reason_code, "invalid_governance_payload")
        self.assertEqual(aggregate.failures, ("missing_subsystem",))
        self.assertEqual(aggregate.aggregate["invalid_count"], 1)
        self.assertEqual(
            aggregate.aggregate["invalid_subsystems"],
            ["approval_review"],
        )
        self.assertEqual(
            aggregate.aggregate["failure_counts"],
            {"missing_subsystem": 1},
        )

    def test_detects_unknown_subsystem(self) -> None:
        payloads = _valid_payloads()
        payloads["rogue"] = _valid_ci_payload()

        aggregate = build_governance_readiness_aggregate(payloads)

        self.assertIs(aggregate.ready, False)
        self.assertEqual(aggregate.reason_code, "invalid_governance_payload")
        self.assertEqual(aggregate.failures, ("unknown_subsystem",))
        self.assertEqual(aggregate.aggregate["invalid_count"], 1)
        self.assertEqual(aggregate.aggregate["invalid_subsystems"], ["rogue"])
        self.assertEqual(
            aggregate.aggregate["failure_counts"],
            {"unknown_subsystem": 1},
        )

    def test_detects_malformed_subsystem_payload(self) -> None:
        payloads = _valid_payloads()
        payloads["evidence_replay"] = {"ci_ok": True}

        aggregate = build_governance_readiness_aggregate(payloads)

        self.assertIs(aggregate.ready, False)
        self.assertEqual(aggregate.reason_code, "invalid_governance_payload")
        self.assertEqual(aggregate.failures, ("subsystem_payload_invalid",))
        self.assertEqual(
            aggregate.aggregate["invalid_subsystems"],
            ["evidence_replay"],
        )

    def test_rejects_bool_as_int_for_version_and_counters(self) -> None:
        for field in (
            "version",
            "cli_command_count",
            "runtime_dependency_count",
        ):
            with self.subTest(field=field):
                payloads = _valid_payloads()
                payloads["evidence_replay"][field] = True

                aggregate = build_governance_readiness_aggregate(payloads)

                self.assertEqual(
                    aggregate.reason_code,
                    "invalid_governance_payload",
                )
                self.assertIn(
                    "subsystem_payload_invalid",
                    aggregate.failures,
                )

    def test_rejects_invalid_failures_list(self) -> None:
        invalid_values = ("bad", ["ok", 1], ("ok",))
        for failures in invalid_values:
            with self.subTest(failures=failures):
                payloads = _valid_payloads()
                payloads["evidence_replay"]["failures"] = failures

                aggregate = build_governance_readiness_aggregate(payloads)

                self.assertEqual(
                    aggregate.reason_code,
                    "invalid_governance_payload",
                )
                self.assertEqual(
                    aggregate.failures,
                    ("subsystem_payload_invalid",),
                )


class TestGovernanceReadinessAggregatorNotReadyHazards(unittest.TestCase):
    def test_subsystem_ci_not_ready_makes_governance_not_ready(self) -> None:
        payloads = _valid_payloads()
        payloads["evidence_replay"]["ci_ok"] = False
        payloads["evidence_replay"]["reason_code"] = "not_ready"
        payloads["evidence_replay"]["failures"] = ["upstream_failure"]

        aggregate = _assert_not_ready(
            self,
            payloads,
            "subsystem_not_ready",
        )

        self.assertEqual(
            aggregate.aggregate["reason_counts"],
            {"not_ready": 1, "ready": 3},
        )
        self.assertEqual(
            aggregate.aggregate["failure_counts"],
            {"subsystem_not_ready": 1},
        )

    def test_restore_supported_true_makes_governance_not_ready(self) -> None:
        payloads = _valid_payloads()
        payloads["evidence_replay"]["restore_supported"] = True

        _assert_not_ready(
            self,
            payloads,
            "subsystem_restore_supported",
        )

    def test_durable_writes_true_makes_governance_not_ready(self) -> None:
        payloads = _valid_payloads()
        payloads["evidence_replay"]["durable_writes"] = True

        _assert_not_ready(
            self,
            payloads,
            "subsystem_durable_writes",
        )

    def test_cli_command_count_positive_makes_governance_not_ready(self) -> None:
        payloads = _valid_payloads()
        payloads["evidence_replay"]["cli_command_count"] = 1

        aggregate = _assert_not_ready(
            self,
            payloads,
            "subsystem_cli_commands",
        )
        self.assertEqual(aggregate.aggregate["cli_command_count"], 1)

    def test_runtime_dependency_count_positive_makes_governance_not_ready(
        self,
    ) -> None:
        payloads = _valid_payloads()
        payloads["evidence_replay"]["runtime_dependency_count"] = 1

        aggregate = _assert_not_ready(
            self,
            payloads,
            "subsystem_runtime_dependencies",
        )
        self.assertEqual(aggregate.aggregate["runtime_dependency_count"], 1)

    def test_json_safe_false_or_none_makes_governance_not_ready(self) -> None:
        for value in (False, None):
            with self.subTest(value=value):
                payloads = _valid_payloads()
                payloads["evidence_replay"]["json_safe"] = value

                _assert_not_ready(
                    self,
                    payloads,
                    "subsystem_not_json_safe",
                )

    def test_failure_and_reason_counts_are_deterministic(self) -> None:
        payloads = _valid_payloads()
        payloads["approval_review"]["cli_command_count"] = 2
        payloads["evidence_replay"]["ci_ok"] = False
        payloads["evidence_replay"]["reason_code"] = "not_ready"
        payloads["task_lifecycle_journal"]["json_safe"] = False

        aggregate = build_governance_readiness_aggregate(payloads)

        self.assertEqual(
            aggregate.failures,
            (
                "subsystem_not_ready",
                "subsystem_cli_commands",
                "subsystem_not_json_safe",
            ),
        )
        self.assertEqual(
            aggregate.aggregate["failure_counts"],
            {
                "subsystem_not_ready": 1,
                "subsystem_cli_commands": 1,
                "subsystem_not_json_safe": 1,
            },
        )
        self.assertEqual(
            aggregate.aggregate["reason_counts"],
            {"not_ready": 1, "ready": 3},
        )


class TestGovernanceReadinessAggregatorRendererManifest(unittest.TestCase):
    def test_manifest_exact_shape_and_defensive_copy(self) -> None:
        manifest_a = governance_readiness_manifest()
        manifest_b = governance_readiness_manifest()

        self.assertEqual(manifest_a, EXPECTED_MANIFEST)
        self.assertEqual(manifest_b, EXPECTED_MANIFEST)

        manifest_a["restore_supported"] = True
        manifest_a["required_subsystems"].append("rogue")
        manifest_a["failure_values"].append("rogue_failure")

        self.assertEqual(governance_readiness_manifest(), EXPECTED_MANIFEST)
        _assert_json_safe(governance_readiness_manifest())

    def test_renderer_exact_shape_and_defensive_copy(self) -> None:
        aggregate = build_governance_readiness_aggregate(_valid_payloads())

        rendered = render_governance_readiness_aggregate(aggregate)

        self.assertEqual(list(rendered.keys()), EXPECTED_RENDERED_KEYS)
        self.assertEqual(
            list(rendered["aggregate"].keys()),
            EXPECTED_AGGREGATE_KEYS,
        )
        rendered["failures"].append("mutated")
        rendered["aggregate"]["ready_subsystems"].append("mutated")
        rendered["aggregate"]["subsystem_surfaces"]["approval_review"] = (
            "mutated"
        )

        rendered_again = render_governance_readiness_aggregate(aggregate)
        self.assertEqual(rendered_again["failures"], [])
        self.assertEqual(
            rendered_again["aggregate"]["ready_subsystems"],
            SUBSYSTEMS,
        )
        self.assertEqual(
            rendered_again["aggregate"]["subsystem_surfaces"][
                "approval_review"
            ],
            "approval_review_ci",
        )

    def test_input_is_not_mutated(self) -> None:
        payloads = _valid_payloads()
        before = copy.deepcopy(payloads)

        build_governance_readiness_aggregate(payloads)

        self.assertEqual(payloads, before)

    def test_rendered_output_is_json_safe_without_runtime_repr(self) -> None:
        rendered = render_governance_readiness_aggregate(
            build_governance_readiness_aggregate(_valid_payloads())
        )

        _assert_json_safe(rendered)
        _assert_no_runtime_repr(rendered)

    def test_public_api_is_exact(self) -> None:
        self.assertEqual(
            sorted(aggregator_module.__all__),
            [
                "GovernanceReadinessAggregate",
                "build_governance_readiness_aggregate",
                "governance_readiness_manifest",
                "render_governance_readiness_aggregate",
            ],
        )

    def test_production_source_boundary_has_no_creep(self) -> None:
        source = inspect.getsource(aggregator_module)
        for marker in FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_production_imports_no_upstream_modules(self) -> None:
        tree = ast.parse(inspect.getsource(aggregator_module))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)

        self.assertEqual(
            imported,
            {
                "__future__",
                "collections.abc",
                "copy",
                "dataclasses",
            },
        )


class TestGovernanceReadinessAggregatorRealSmoke(unittest.TestCase):
    def test_real_cross_subsystem_rendered_ci_outputs_are_ready(self) -> None:
        payloads = {
            "recovery_session_host": _real_recovery_ci_payload(),
            "task_lifecycle_journal": _real_task_lifecycle_ci_payload(),
            "evidence_replay": _real_evidence_replay_ci_payload(),
            "approval_review": _real_approval_review_ci_payload(),
        }

        aggregate = build_governance_readiness_aggregate(payloads)
        rendered = render_governance_readiness_aggregate(aggregate)

        self.assertIs(aggregate.ready, True)
        self.assertEqual(aggregate.reason_code, "ready")
        self.assertEqual(aggregate.failures, ())
        self.assertEqual(aggregate.aggregate["subsystem_count"], 4)
        self.assertEqual(aggregate.aggregate["ready_count"], 4)
        self.assertEqual(aggregate.aggregate["invalid_count"], 0)
        self.assertEqual(aggregate.aggregate["not_ready_count"], 0)
        self.assertIs(aggregate.aggregate["operator_safe"], True)
        self.assertEqual(aggregate.aggregate["cli_command_count"], 0)
        self.assertEqual(aggregate.aggregate["runtime_dependency_count"], 0)
        _assert_json_safe(rendered)
        _assert_no_runtime_repr(rendered)


if __name__ == "__main__":
    unittest.main()
