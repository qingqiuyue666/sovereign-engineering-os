#!/usr/bin/env python3
"""Validate AOOS Stage 4/5 documentation and interface anchors."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    Path("docs/aoos/README.md"),
    Path("docs/aoos/core-module-map.md"),
    Path("docs/aoos/domain-packs.md"),
    Path("docs/aoos/runtime-backlog.md"),
    Path("docs/aoos/stage-5-interfaces.md"),
    Path("docs/aoos/schemas/learning-promotion-fixture.schema.json"),
    Path("docs/aoos/schemas/real-world-feedback-ingestion-packet.schema.json"),
    Path("docs/aoos/schemas/risk-classifier-fixture.schema.json"),
    Path("docs/aoos/schemas/runtime-backlog.schema.json"),
    Path("docs/aoos/schemas/task-router-fixture.schema.json"),
    Path("templates/aoos/README.md"),
    Path("templates/aoos/mission-brief-template.md"),
    Path("templates/aoos/evidence-report-template.md"),
    Path("templates/aoos/failure-learning-log-template.md"),
    Path("templates/aoos/incident-record-template.md"),
    Path("templates/aoos/reality-validation-log-template.md"),
    Path("templates/aoos/domain-acceptance-rubric-template.md"),
    Path("templates/aoos/tool-roi-review-template.md"),
    Path("templates/aoos/model-tool-routing-decision-template.md"),
    Path("reports/aoos/evidence-ledger-v1.jsonl"),
    Path("reports/aoos/learning-promotion-fixture-v1.json"),
    Path("reports/aoos/real-world-feedback-ingestion-packet-v1.json"),
    Path("reports/aoos/risk-classifier-fixture-v1.json"),
    Path("reports/aoos/runtime-backlog-v1.json"),
    Path("reports/aoos/task-router-fixture-v1.json"),
    Path("reports/checkpoints/aoos-stage45-executable-skeleton-v1.md"),
)

REQUIRED_TERMS = (
    "Strategy / Portfolio Governance",
    "Truth / Evidence Governance",
    "Authority / Risk Governance",
    "Execution State Machine",
    "Observability / Audit",
    "Evaluator / Metrics",
    "Learning / Memory Lifecycle",
    "Tool / Complexity Governance",
    "Security / Threat Model",
    "Reality Validation",
    "Incident Response",
    "Anti-Goodhart / Anti-Delusion",
    "AOOS Mission Brief Template",
    "AOOS Runtime Backlog",
    "evidence-ledger-v1.jsonl",
    "learning-promotion-fixture-v1.json",
    "real-world-feedback-ingestion-packet-v1.json",
    "risk-classifier-fixture-v1.json",
    "runtime-backlog-v1.json",
    "task-router-fixture-v1.json",
    "A0-A6",
    "failure_taxonomy_entry",
    "threat_model_record",
    "Engineering Pack",
    "DCC / Creative Pack",
    "Content Production Pack",
    "Trade / Sales Pack",
    "Business Validation Pack",
    "Research / Intelligence Pack",
    "Security / Compliance Pack",
    "Asset / Supply Chain Pack",
    "Operator UX Pack",
    "Model / Tool Routing Pack",
    "false_done_rate",
    "manual_intervention_rate",
    "retry_success_rate",
    "repeated_failure_rate",
    "cost_per_verified_task",
    "time_to_verified_done",
    "real_world_validation_rate",
    "USE_NOW",
    "USE_LATER",
    "REFERENCE_ONLY",
    "REJECT",
    "memory -> checklist -> playbook -> script -> CI / evaluator / policy",
)

REQUIRED_ROOT_TERMS = (
    ("AGENTS.md", "docs/aoos/"),
    ("README.md", "docs/aoos/"),
    ("ROADMAP.md", "AOOS"),
    ("VALIDATION_REPORT.md", "AOOS"),
)

FORBIDDEN_CLAIMS = (
    "AOOS_STAGE_6_COMPLETE",
    "AOOS_STAGE_7_COMPLETE",
    "customer validation confirmed",
    "paid signal confirmed",
    "production deployment confirmed",
)

LOCAL_PATH_MARKERS = (
    "/Users/",
    "Documents/Codex",
    "files-mentioned-by-the-user",
)

SCHEMA_FIXTURE_MAP = (
    ("observability_event", Path("docs/aoos/schemas/observability-event.schema.json")),
    ("decision_log_entry", Path("docs/aoos/schemas/decision-log-entry.schema.json")),
    ("evidence_ledger_entry", Path("docs/aoos/schemas/evidence-ledger-entry.schema.json")),
    ("evaluator_metrics_snapshot", Path("docs/aoos/schemas/evaluator-metrics-snapshot.schema.json")),
    ("failure_taxonomy_entry", Path("docs/aoos/schemas/failure-taxonomy-entry.schema.json")),
    ("threat_model_record", Path("docs/aoos/schemas/threat-model-record.schema.json")),
    ("incident_record", Path("docs/aoos/schemas/incident-record.schema.json")),
    ("memory_lifecycle_entry", Path("docs/aoos/schemas/memory-lifecycle-entry.schema.json")),
    ("model_tool_routing_decision", Path("docs/aoos/schemas/model-tool-routing-decision.schema.json")),
    ("domain_pack_manifest", Path("docs/aoos/schemas/domain-pack-manifest.schema.json")),
)

FIXTURE_PATH = Path("examples/aoos/stage45-interface-fixture-v1.json")
EVIDENCE_LEDGER_PATH = Path("reports/aoos/evidence-ledger-v1.jsonl")
LEARNING_PROMOTION_PATH = Path("reports/aoos/learning-promotion-fixture-v1.json")
LEARNING_PROMOTION_SCHEMA_PATH = Path("docs/aoos/schemas/learning-promotion-fixture.schema.json")
REAL_WORLD_FEEDBACK_PATH = Path("reports/aoos/real-world-feedback-ingestion-packet-v1.json")
REAL_WORLD_FEEDBACK_SCHEMA_PATH = Path("docs/aoos/schemas/real-world-feedback-ingestion-packet.schema.json")
RISK_CLASSIFIER_PATH = Path("reports/aoos/risk-classifier-fixture-v1.json")
RISK_CLASSIFIER_SCHEMA_PATH = Path("docs/aoos/schemas/risk-classifier-fixture.schema.json")
BACKLOG_PATH = Path("reports/aoos/runtime-backlog-v1.json")
BACKLOG_SCHEMA_PATH = Path("docs/aoos/schemas/runtime-backlog.schema.json")
TASK_ROUTER_PATH = Path("reports/aoos/task-router-fixture-v1.json")
TASK_ROUTER_SCHEMA_PATH = Path("docs/aoos/schemas/task-router-fixture.schema.json")
SCHEMA_VERSION = "aoos-stage5-interface-v1"
LEARNING_PROMOTION_SCHEMA_VERSION = "aoos-learning-promotion-fixture-v1"
REAL_WORLD_FEEDBACK_SCHEMA_VERSION = "aoos-real-world-feedback-ingestion-packet-v1"
RISK_CLASSIFIER_SCHEMA_VERSION = "aoos-risk-classifier-fixture-v1"
BACKLOG_SCHEMA_VERSION = "aoos-runtime-backlog-v1"
TASK_ROUTER_SCHEMA_VERSION = "aoos-task-router-fixture-v1"
JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"

REQUIRED_METRICS = (
    "false_done_rate",
    "manual_intervention_rate",
    "retry_success_rate",
    "repeated_failure_rate",
    "cost_per_verified_task",
    "time_to_verified_done",
    "real_world_validation_rate",
)


def main() -> int:
    errors: list[str] = []
    combined_parts: list[str] = []

    for relative_path in REQUIRED_FILES:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing AOOS file: {relative_path.as_posix()}")
            continue
        combined_parts.append(path.read_text(encoding="utf-8"))

    combined = "\n".join(combined_parts)
    for term in REQUIRED_TERMS:
        if term not in combined:
            errors.append(f"missing AOOS term: {term}")

    for relative_path, term in REQUIRED_ROOT_TERMS:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing root integration file: {relative_path}")
            continue
        if term not in path.read_text(encoding="utf-8"):
            errors.append(f"{relative_path} missing AOOS integration term: {term}")

    lower_combined = combined.lower()
    for forbidden in FORBIDDEN_CLAIMS:
        if forbidden.lower() in lower_combined:
            errors.append(f"forbidden AOOS claim present: {forbidden}")

    for marker in LOCAL_PATH_MARKERS:
        if marker in combined:
            errors.append(f"AOOS docs contain local path marker: {marker}")

    _check_schema_interfaces(errors)
    _check_evidence_ledger_records(errors)
    _check_risk_classifier_fixture(errors)
    _check_backlog_record(errors)
    _check_task_router_fixture(errors)
    _check_learning_promotion_fixture(errors)
    _check_real_world_feedback_packet(errors)

    if errors:
        print("aoos_stage45_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("aoos_stage45_check_v1: PASS")
    return 0


def _check_schema_interfaces(errors: list[str]) -> None:
    fixture = _load_json(FIXTURE_PATH, errors)
    if fixture is None:
        return
    if fixture.get("fixture_version") != "aoos-stage45-interface-fixture-v1":
        errors.append("AOOS fixture_version mismatch")
    if fixture.get("real_world_claimed") is not False:
        errors.append("AOOS fixture must not claim real-world validation")
    _check_json_text_safety(FIXTURE_PATH, errors)

    for fixture_key, schema_path in SCHEMA_FIXTURE_MAP:
        schema = _load_json(schema_path, errors)
        if schema is None:
            continue
        _check_schema_shape(schema_path, schema, errors)
        payload = fixture.get(fixture_key)
        if not isinstance(payload, dict):
            errors.append(f"AOOS fixture missing object: {fixture_key}")
            continue
        _check_payload_against_schema(fixture_key, payload, schema_path, schema, errors)

    metrics_payload = fixture.get("evaluator_metrics_snapshot", {})
    metrics = metrics_payload.get("metrics") if isinstance(metrics_payload, dict) else None
    if not isinstance(metrics, dict):
        errors.append("AOOS fixture metrics must be object")
    else:
        for metric in REQUIRED_METRICS:
            item = metrics.get(metric)
            if not isinstance(item, dict):
                errors.append(f"AOOS fixture missing metric object: {metric}")
                continue
            for field in ("numerator", "denominator", "gaming_risk"):
                if field not in item:
                    errors.append(f"AOOS metric {metric} missing field: {field}")


def _check_evidence_ledger_records(errors: list[str]) -> None:
    path = REPO_ROOT / EVIDENCE_LEDGER_PATH
    if not path.exists():
        errors.append(f"missing AOOS evidence ledger: {EVIDENCE_LEDGER_PATH.as_posix()}")
        return
    _check_json_text_safety(EVIDENCE_LEDGER_PATH, errors)

    schema = _load_json(Path("docs/aoos/schemas/evidence-ledger-entry.schema.json"), errors)
    if schema is None:
        return

    records: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(
                f"{EVIDENCE_LEDGER_PATH.as_posix()} line {line_number} invalid JSON: {exc}"
            )
            continue
        if not isinstance(payload, dict):
            errors.append(
                f"{EVIDENCE_LEDGER_PATH.as_posix()} line {line_number} must be object"
            )
            continue
        _check_payload_against_schema(
            f"evidence_ledger_record[{line_number}]",
            payload,
            Path("docs/aoos/schemas/evidence-ledger-entry.schema.json"),
            schema,
            errors,
        )
        records.append(payload)

    if len(records) < 3:
        errors.append("AOOS evidence ledger must contain at least three seed records")

    seen_ids: set[str] = set()
    allowed_levels = {"L0", "L1", "L2", "L3", "L4", "L5"}
    for record in records:
        evidence_id = record.get("evidence_id")
        if evidence_id in seen_ids:
            errors.append(f"AOOS evidence ledger duplicate evidence_id: {evidence_id}")
        elif isinstance(evidence_id, str):
            seen_ids.add(evidence_id)
        evidence_level = record.get("evidence_level")
        if evidence_level not in allowed_levels:
            errors.append(
                f"AOOS evidence ledger {evidence_id or '<unknown>'} invalid evidence_level: "
                f"{evidence_level}"
            )
        limitations = record.get("limitations")
        if not isinstance(limitations, list) or not limitations:
            errors.append(f"AOOS evidence ledger {evidence_id or '<unknown>'} needs limitations")
        forbidden = record.get("forbidden_stronger_claim")
        if not isinstance(forbidden, str) or not forbidden:
            errors.append(
                f"AOOS evidence ledger {evidence_id or '<unknown>'} needs forbidden stronger claim"
            )
        source_ref = record.get("source_ref")
        if isinstance(source_ref, str) and not source_ref.startswith("https://"):
            if not (REPO_ROOT / source_ref).exists():
                errors.append(
                    f"AOOS evidence ledger {evidence_id or '<unknown>'} source_ref missing: "
                    f"{source_ref}"
                )


def _check_risk_classifier_fixture(errors: list[str]) -> None:
    schema = _load_json(RISK_CLASSIFIER_SCHEMA_PATH, errors)
    if schema is not None:
        _check_schema_shape(RISK_CLASSIFIER_SCHEMA_PATH, schema, errors)
    fixture = _load_json(RISK_CLASSIFIER_PATH, errors)
    if fixture is None:
        return
    _check_json_text_safety(RISK_CLASSIFIER_PATH, errors)

    if fixture.get("schema_version") != RISK_CLASSIFIER_SCHEMA_VERSION:
        errors.append("AOOS risk classifier fixture schema_version mismatch")
    if not fixture.get("claim_boundary"):
        errors.append("AOOS risk classifier fixture must state claim_boundary")

    authority_refs = fixture.get("authority_source_refs")
    if not isinstance(authority_refs, list) or not authority_refs:
        errors.append("AOOS risk classifier fixture must include authority_source_refs")
    else:
        for source_ref in authority_refs:
            if not isinstance(source_ref, str) or not (REPO_ROOT / source_ref).exists():
                errors.append(f"AOOS risk classifier authority ref missing: {source_ref}")

    cases = fixture.get("cases")
    if not isinstance(cases, list):
        errors.append("AOOS risk classifier cases must be array")
        return
    required_classes = {
        "A0_READ_ONLY",
        "A1_SAFE_EDIT",
        "A2_SAFE_PUSH",
        "A3_AUTO_MERGE_ALLOWED",
        "A4_SANDBOX_OPERATION",
        "A5_PROPOSE_REAL_WORLD_ACTION",
        "A6_HUMAN_AUTHORIZED_REAL_WORLD_ACTION",
    }
    required_case_fields = (
        "case_id",
        "action_summary",
        "domain",
        "expected_risk_class",
        "authority_decision",
        "human_gate_required",
        "evidence_requirement",
        "acceptance_gate",
        "rollback_path",
        "forbidden_actions",
        "rationale_refs",
    )
    seen_cases: set[str] = set()
    seen_classes: set[str] = set()
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            errors.append(f"AOOS risk classifier case {index} must be object")
            continue
        for field in required_case_fields:
            if field not in case:
                errors.append(f"AOOS risk classifier case {index} missing field: {field}")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"AOOS risk classifier case {index} id must be non-empty string")
        elif case_id in seen_cases:
            errors.append(f"AOOS risk classifier duplicate case_id: {case_id}")
        else:
            seen_cases.add(case_id)
        risk_class = case.get("expected_risk_class")
        if risk_class not in required_classes:
            errors.append(
                f"AOOS risk classifier case {case_id or index} invalid class: {risk_class}"
            )
        elif isinstance(risk_class, str):
            seen_classes.add(risk_class)
        evidence = case.get("evidence_requirement")
        if not isinstance(evidence, str) or not evidence.startswith("L"):
            errors.append(
                f"AOOS risk classifier case {case_id or index} evidence_requirement must start with L"
            )
        if not isinstance(case.get("human_gate_required"), bool):
            errors.append(
                f"AOOS risk classifier case {case_id or index} human_gate_required must be boolean"
            )
        for list_field in ("forbidden_actions", "rationale_refs"):
            value = case.get(list_field)
            if not isinstance(value, list) or not value:
                errors.append(
                    f"AOOS risk classifier case {case_id or index} {list_field} "
                    "must be non-empty array"
                )
                continue
            if any(not isinstance(entry, str) or not entry for entry in value):
                errors.append(
                    f"AOOS risk classifier case {case_id or index} {list_field} "
                    "entries must be strings"
                )
        for source_ref in case.get("rationale_refs", []):
            if isinstance(source_ref, str) and not (REPO_ROOT / source_ref).exists():
                errors.append(
                    f"AOOS risk classifier case {case_id or index} rationale ref missing: "
                    f"{source_ref}"
                )

    missing_classes = sorted(required_classes - seen_classes)
    if missing_classes:
        errors.append(
            "AOOS risk classifier fixture missing classes: "
            + ", ".join(missing_classes)
        )


def _check_backlog_record(errors: list[str]) -> None:
    schema = _load_json(BACKLOG_SCHEMA_PATH, errors)
    if schema is not None:
        _check_schema_shape(BACKLOG_SCHEMA_PATH, schema, errors)
    backlog = _load_json(BACKLOG_PATH, errors)
    if backlog is None:
        return
    _check_json_text_safety(BACKLOG_PATH, errors)

    if backlog.get("schema_version") != BACKLOG_SCHEMA_VERSION:
        errors.append("AOOS backlog schema_version mismatch")
    if not backlog.get("claim_boundary"):
        errors.append("AOOS backlog must state claim_boundary")
    if not backlog.get("selection_policy"):
        errors.append("AOOS backlog must state selection_policy")

    items = backlog.get("items")
    if not isinstance(items, list) or len(items) < 3:
        errors.append("AOOS backlog must contain at least three items")
        return

    required_fields = (
        "id",
        "title",
        "domain",
        "maturity_target",
        "priority",
        "dependencies",
        "risk_class",
        "evidence_requirement",
        "acceptance_gate",
        "checks_required",
        "rollback_path",
        "status",
        "next_action",
        "owner_role",
        "evaluator_required",
        "promotion_rule_if_repeated_failure",
    )
    risk_prefixes = ("A0_", "A1_", "A2_", "A3_", "A4_", "A5_", "A6_")
    allowed_statuses = {
        "ready_for_review",
        "completed",
        "pending",
        "pending_after_human_review",
        "human_gate_required",
        "blocked",
    }
    seen_ids: set[str] = set()
    has_open_or_gate_item = False
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"AOOS backlog item {index} must be object")
            continue
        for field in required_fields:
            if field not in item:
                errors.append(f"AOOS backlog item {index} missing field: {field}")
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"AOOS backlog item {index} id must be non-empty string")
        elif item_id in seen_ids:
            errors.append(f"AOOS backlog duplicate id: {item_id}")
        else:
            seen_ids.add(item_id)
        priority = item.get("priority")
        if not isinstance(priority, int) or priority < 1:
            errors.append(f"AOOS backlog item {item_id or index} priority must be positive integer")
        for list_field in ("dependencies", "checks_required"):
            value = item.get(list_field)
            if not isinstance(value, list):
                errors.append(f"AOOS backlog item {item_id or index} {list_field} must be array")
            elif any(not isinstance(entry, str) or not entry for entry in value):
                errors.append(
                    f"AOOS backlog item {item_id or index} {list_field} entries must be strings"
                )
        risk_class = item.get("risk_class")
        if not isinstance(risk_class, str) or not risk_class.startswith(risk_prefixes):
            errors.append(f"AOOS backlog item {item_id or index} risk_class must start with A0_ through A6_")
        evidence = item.get("evidence_requirement")
        if not isinstance(evidence, str) or not evidence.startswith("L"):
            errors.append(f"AOOS backlog item {item_id or index} evidence_requirement must start with L")
        status = item.get("status")
        if status not in allowed_statuses:
            errors.append(f"AOOS backlog item {item_id or index} has unsupported status: {status}")
        if status != "completed":
            has_open_or_gate_item = True
        for text_field in (
            "title",
            "domain",
            "maturity_target",
            "acceptance_gate",
            "rollback_path",
            "next_action",
            "owner_role",
            "evaluator_required",
            "promotion_rule_if_repeated_failure",
        ):
            value = item.get(text_field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"AOOS backlog item {item_id or index} {text_field} must be non-empty string")

    if not has_open_or_gate_item:
        errors.append("AOOS backlog must include at least one open item or human gate")


def _check_task_router_fixture(errors: list[str]) -> None:
    schema = _load_json(TASK_ROUTER_SCHEMA_PATH, errors)
    if schema is not None:
        _check_schema_shape(TASK_ROUTER_SCHEMA_PATH, schema, errors)
    fixture = _load_json(TASK_ROUTER_PATH, errors)
    if fixture is None:
        return
    _check_json_text_safety(TASK_ROUTER_PATH, errors)

    if fixture.get("schema_version") != TASK_ROUTER_SCHEMA_VERSION:
        errors.append("AOOS task router fixture schema_version mismatch")
    if not fixture.get("claim_boundary"):
        errors.append("AOOS task router fixture must state claim_boundary")

    rules = fixture.get("routing_rules")
    if not isinstance(rules, list) or len(rules) < 5:
        errors.append("AOOS task router fixture must contain at least five routing rules")
        return

    required_fields = (
        "route_id",
        "task_class",
        "domain",
        "owner_role",
        "risk_class",
        "evidence_requirement",
        "required_inputs",
        "output_records",
        "next_gate",
        "observability_event_refs",
        "decision_refs",
        "forbidden_claims",
    )
    seen_routes: set[str] = set()
    owner_roles: set[str] = set()
    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            errors.append(f"AOOS task router rule {index} must be object")
            continue
        for field in required_fields:
            if field not in rule:
                errors.append(f"AOOS task router rule {index} missing field: {field}")
        route_id = rule.get("route_id")
        if not isinstance(route_id, str) or not route_id:
            errors.append(f"AOOS task router rule {index} route_id must be non-empty string")
        elif route_id in seen_routes:
            errors.append(f"AOOS task router duplicate route_id: {route_id}")
        else:
            seen_routes.add(route_id)
        risk_class = rule.get("risk_class")
        if not isinstance(risk_class, str) or not risk_class.startswith(("A0_", "A1_", "A2_", "A3_", "A4_", "A5_", "A6_")):
            errors.append(f"AOOS task router rule {route_id or index} risk_class must start with A0_ through A6_")
        evidence = rule.get("evidence_requirement")
        if not isinstance(evidence, str) or not evidence.startswith("L"):
            errors.append(f"AOOS task router rule {route_id or index} evidence_requirement must start with L")
        owner_role = rule.get("owner_role")
        if isinstance(owner_role, str) and owner_role:
            owner_roles.add(owner_role)
        else:
            errors.append(f"AOOS task router rule {route_id or index} owner_role must be non-empty string")
        for list_field in (
            "required_inputs",
            "output_records",
            "observability_event_refs",
            "decision_refs",
            "forbidden_claims",
        ):
            value = rule.get(list_field)
            if not isinstance(value, list) or not value:
                errors.append(
                    f"AOOS task router rule {route_id or index} {list_field} must be non-empty array"
                )
                continue
            if any(not isinstance(entry, str) or not entry for entry in value):
                errors.append(
                    f"AOOS task router rule {route_id or index} {list_field} entries must be strings"
                )
        for ref_field in ("observability_event_refs", "decision_refs"):
            for source_ref in rule.get(ref_field, []):
                if isinstance(source_ref, str) and not (REPO_ROOT / source_ref).exists():
                    errors.append(
                        f"AOOS task router rule {route_id or index} {ref_field} missing: {source_ref}"
                    )

    required_roles = {"Builder Agent", "Reviewer Agent", "Policy Agent", "Reality Agent", "Operator Agent"}
    missing_roles = sorted(required_roles - owner_roles)
    if missing_roles:
        errors.append(f"AOOS task router fixture missing owner roles: {', '.join(missing_roles)}")


def _check_learning_promotion_fixture(errors: list[str]) -> None:
    schema = _load_json(LEARNING_PROMOTION_SCHEMA_PATH, errors)
    if schema is not None:
        _check_schema_shape(LEARNING_PROMOTION_SCHEMA_PATH, schema, errors)
    fixture = _load_json(LEARNING_PROMOTION_PATH, errors)
    if fixture is None:
        return
    _check_json_text_safety(LEARNING_PROMOTION_PATH, errors)

    if fixture.get("schema_version") != LEARNING_PROMOTION_SCHEMA_VERSION:
        errors.append("AOOS learning promotion fixture schema_version mismatch")
    if not fixture.get("claim_boundary"):
        errors.append("AOOS learning promotion fixture must state claim_boundary")

    rules = fixture.get("promotion_rules")
    if not isinstance(rules, list) or len(rules) < 5:
        errors.append("AOOS learning promotion fixture must contain at least five promotion rules")
        return

    required_fields = (
        "rule_id",
        "failure_pattern",
        "occurrence_threshold",
        "promotion_target",
        "owner_role",
        "evidence_required",
        "next_action",
        "rollback_path",
        "forbidden_claims",
    )
    allowed_targets = {"checklist", "playbook", "script", "CI", "evaluator", "policy", "backlog"}
    seen_rules: set[str] = set()
    seen_targets: set[str] = set()
    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            errors.append(f"AOOS learning promotion rule {index} must be object")
            continue
        for field in required_fields:
            if field not in rule:
                errors.append(f"AOOS learning promotion rule {index} missing field: {field}")
        rule_id = rule.get("rule_id")
        if not isinstance(rule_id, str) or not rule_id:
            errors.append(f"AOOS learning promotion rule {index} rule_id must be non-empty string")
        elif rule_id in seen_rules:
            errors.append(f"AOOS learning promotion duplicate rule_id: {rule_id}")
        else:
            seen_rules.add(rule_id)
        threshold = rule.get("occurrence_threshold")
        if not isinstance(threshold, int) or threshold < 1:
            errors.append(f"AOOS learning promotion rule {rule_id or index} threshold must be positive integer")
        target = rule.get("promotion_target")
        if target not in allowed_targets:
            errors.append(f"AOOS learning promotion rule {rule_id or index} invalid target: {target}")
        elif isinstance(target, str):
            seen_targets.add(target)
        for list_field in ("evidence_required", "forbidden_claims"):
            value = rule.get(list_field)
            if not isinstance(value, list) or not value:
                errors.append(
                    f"AOOS learning promotion rule {rule_id or index} {list_field} must be non-empty array"
                )
                continue
            if any(not isinstance(entry, str) or not entry for entry in value):
                errors.append(
                    f"AOOS learning promotion rule {rule_id or index} {list_field} entries must be strings"
                )
        for text_field in ("failure_pattern", "owner_role", "next_action", "rollback_path"):
            value = rule.get(text_field)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"AOOS learning promotion rule {rule_id or index} {text_field} must be non-empty string"
                )

    if "script" not in seen_targets or "policy" not in seen_targets or "evaluator" not in seen_targets:
        errors.append("AOOS learning promotion fixture must cover script, policy, and evaluator targets")


def _check_real_world_feedback_packet(errors: list[str]) -> None:
    schema = _load_json(REAL_WORLD_FEEDBACK_SCHEMA_PATH, errors)
    if schema is not None:
        _check_schema_shape(REAL_WORLD_FEEDBACK_SCHEMA_PATH, schema, errors)
    packet = _load_json(REAL_WORLD_FEEDBACK_PATH, errors)
    if packet is None:
        return
    _check_json_text_safety(REAL_WORLD_FEEDBACK_PATH, errors)

    if packet.get("schema_version") != REAL_WORLD_FEEDBACK_SCHEMA_VERSION:
        errors.append("AOOS real-world feedback packet schema_version mismatch")
    if packet.get("status") != "proposal_only":
        errors.append("AOOS real-world feedback packet must remain proposal_only")
    if packet.get("actions_executed") is not False:
        errors.append("AOOS real-world feedback packet must not execute actions")
    if packet.get("human_authorization_required") is not True:
        errors.append("AOOS real-world feedback packet must require human authorization")

    for list_field in (
        "claim_boundary",
        "accepted_source_types",
        "ingestion_flow",
        "evidence_mapping",
        "redaction_rules",
        "forbidden_actions",
        "forbidden_claims",
    ):
        value = packet.get(list_field)
        if not isinstance(value, list) or not value:
            errors.append(f"AOOS real-world feedback packet {list_field} must be non-empty array")

    source_types = packet.get("accepted_source_types", [])
    if isinstance(source_types, list):
        for index, source in enumerate(source_types, start=1):
            if not isinstance(source, dict):
                errors.append(f"AOOS feedback source type {index} must be object")
                continue
            for field in (
                "source_type",
                "minimum_fields",
                "evidence_level_after_review",
                "human_gate",
            ):
                if field not in source:
                    errors.append(f"AOOS feedback source type {index} missing field: {field}")
            if source.get("human_gate") is not True:
                errors.append(f"AOOS feedback source type {index} must require human gate")
            minimum_fields = source.get("minimum_fields")
            if not isinstance(minimum_fields, list) or not minimum_fields:
                errors.append(f"AOOS feedback source type {index} minimum_fields must be non-empty array")

    mappings = packet.get("evidence_mapping", [])
    if isinstance(mappings, list):
        for index, mapping in enumerate(mappings, start=1):
            if not isinstance(mapping, dict):
                errors.append(f"AOOS feedback evidence mapping {index} must be object")
                continue
            for field in ("claim_type", "required_source", "allowed_wording", "forbidden_wording"):
                value = mapping.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"AOOS feedback evidence mapping {index} {field} must be non-empty string")

    forbidden_text = " ".join(packet.get("forbidden_actions", []) + packet.get("forbidden_claims", [])).lower()
    for required_phrase in (
        "claiming real-world validation",
        "customer validation",
        "paid signal",
        "production deployment",
    ):
        if required_phrase not in forbidden_text:
            errors.append(
                f"AOOS real-world feedback packet forbidden boundaries missing: {required_phrase}"
            )

    rollback = packet.get("rollback_path")
    if not isinstance(rollback, str) or not rollback.strip():
        errors.append("AOOS real-world feedback packet rollback_path must be non-empty string")


def _load_json(relative_path: Path, errors: list[str]) -> dict | None:
    path = REPO_ROOT / relative_path
    if not path.exists():
        errors.append(f"missing AOOS JSON file: {relative_path.as_posix()}")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{relative_path.as_posix()} invalid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{relative_path.as_posix()} must be a JSON object")
        return None
    return payload


def _check_schema_shape(relative_path: Path, schema: dict, errors: list[str]) -> None:
    if schema.get("$schema") != JSON_SCHEMA_DRAFT:
        errors.append(f"{relative_path.as_posix()} JSON Schema draft mismatch")
    if schema.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{relative_path.as_posix()} schema_version mismatch")
    if schema.get("type") != "object":
        errors.append(f"{relative_path.as_posix()} schema type must be object")
    if schema.get("additionalProperties") is not False:
        errors.append(f"{relative_path.as_posix()} must reject unknown fields")
    required = schema.get("required")
    properties = schema.get("properties")
    if not isinstance(required, list) or not required:
        errors.append(f"{relative_path.as_posix()} must define required fields")
        return
    if not isinstance(properties, dict) or not properties:
        errors.append(f"{relative_path.as_posix()} must define properties")
        return
    for field in required:
        if field not in properties:
            errors.append(f"{relative_path.as_posix()} required field missing property: {field}")
    _check_json_text_safety(relative_path, errors)


def _check_payload_against_schema(
    fixture_key: str,
    payload: dict,
    schema_path: Path,
    schema: dict,
    errors: list[str],
) -> None:
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    for field in required:
        if field not in payload:
            errors.append(f"AOOS fixture {fixture_key} missing required field: {field}")
    if schema.get("additionalProperties") is False:
        for field in payload:
            if field not in properties:
                errors.append(
                    f"AOOS fixture {fixture_key} has unknown field for "
                    f"{schema_path.as_posix()}: {field}"
                )
    for field, value in payload.items():
        field_schema = properties.get(field)
        if not isinstance(field_schema, dict):
            continue
        expected_type = field_schema.get("type")
        if expected_type == "string" and not isinstance(value, str):
            errors.append(f"AOOS fixture {fixture_key}.{field} must be string")
        elif expected_type == "array" and not isinstance(value, list):
            errors.append(f"AOOS fixture {fixture_key}.{field} must be array")
        elif expected_type == "object" and not isinstance(value, dict):
            errors.append(f"AOOS fixture {fixture_key}.{field} must be object")
        elif expected_type == "boolean" and not isinstance(value, bool):
            errors.append(f"AOOS fixture {fixture_key}.{field} must be boolean")


def _check_json_text_safety(relative_path: Path, errors: list[str]) -> None:
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    for marker in LOCAL_PATH_MARKERS:
        if marker in text:
            errors.append(f"{relative_path.as_posix()} contains local path marker: {marker}")


if __name__ == "__main__":
    raise SystemExit(main())
