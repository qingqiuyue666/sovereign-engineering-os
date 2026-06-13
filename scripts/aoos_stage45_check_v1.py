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
    Path("docs/aoos/stage-5-interfaces.md"),
    Path("templates/aoos/README.md"),
    Path("templates/aoos/evidence-report-template.md"),
    Path("templates/aoos/failure-learning-log-template.md"),
    Path("templates/aoos/incident-record-template.md"),
    Path("templates/aoos/reality-validation-log-template.md"),
    Path("templates/aoos/domain-acceptance-rubric-template.md"),
    Path("templates/aoos/tool-roi-review-template.md"),
    Path("templates/aoos/model-tool-routing-decision-template.md"),
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
    ("incident_record", Path("docs/aoos/schemas/incident-record.schema.json")),
    ("memory_lifecycle_entry", Path("docs/aoos/schemas/memory-lifecycle-entry.schema.json")),
    ("model_tool_routing_decision", Path("docs/aoos/schemas/model-tool-routing-decision.schema.json")),
    ("domain_pack_manifest", Path("docs/aoos/schemas/domain-pack-manifest.schema.json")),
)

FIXTURE_PATH = Path("examples/aoos/stage45-interface-fixture-v1.json")
SCHEMA_VERSION = "aoos-stage5-interface-v1"
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
