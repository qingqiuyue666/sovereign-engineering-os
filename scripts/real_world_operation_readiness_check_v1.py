#!/usr/bin/env python3
"""Validate AI Agent Control Plane V4-V7 operation-readiness artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

DOC_FILES = {
    "registry": Path("docs/control-plane/full-stack-operation-registry-v1.md"),
    "task_schema": Path("docs/control-plane/task-input-model-v1.schema.json"),
    "classifier": Path("docs/control-plane/classifier-policy-gate-v1.md"),
    "matrix": Path("docs/control-plane/external-absorption-operation-matrix-v1.md"),
    "operator": Path("docs/control-plane/operator-runbook-v1.md"),
    "demo": Path("docs/control-plane/demo-operation-workflow-v1.md"),
    "pilot": Path("docs/control-plane/pilot-operation-workflow-v1.md"),
    "feedback": Path("docs/control-plane/customer-feedback-intake-v1.md"),
    "benchmark": Path("docs/control-plane/benchmark-operation-workflow-v1.md"),
    "security": Path("docs/control-plane/security-review-response-workflow-v1.md"),
    "incident": Path("docs/control-plane/incident-operation-workflow-v1.md"),
    "paid_pilot": Path("docs/control-plane/paid-pilot-readiness-gate-v1.md"),
    "compliance": Path("docs/control-plane/compliance-readiness-map-v1.md"),
    "buyer": Path("docs/control-plane/buyer-one-pager-v1.md"),
    "audit_export": Path("docs/control-plane/audit-log-export-v1.md"),
}

JSON_FILES = {
    "task_fixtures": Path("reports/control-plane/task-fixtures-v1.json"),
    "first_cycle": Path("reports/control-plane/first-controlled-cycle-v1.json"),
    "resume": Path("reports/control-plane/resume-point-v1.json"),
    "queue": Path("reports/control-plane/recurring-queue-v1.json"),
    "health": Path("reports/control-plane/health-check-v1.json"),
    "commercial": Path("reports/control-plane/commercial-readiness-package-v1.json"),
    "validation_tracker": Path("reports/control-plane/real-world-validation-tracker-v1.json"),
    "external_ledger": Path("reports/control-plane/external-evidence-ledger-v1.json"),
    "long_running": Path("reports/control-plane/long-running-operation-tracker-v1.json"),
    "production_blockers": Path("reports/control-plane/production-operation-blocker-ledger-v1.json"),
    "pricing": Path("reports/control-plane/pricing-packaging-iteration-tracker-v1.json"),
    "issue_queue": Path("reports/control-plane/issue-pr-operating-queue-v1.json"),
    "non_claim": Path("reports/control-plane/non-claim-audit-v1.json"),
    "scorecard": Path("reports/control-plane/final-scorecard-v1.json"),
}

JSONL_FILES = {
    "evidence": Path("reports/control-plane/evidence-ledger-v1.jsonl"),
    "failure": Path("reports/control-plane/failure-ledger-v1.jsonl"),
}

MD_REPORTS = {
    "rollback": Path("reports/control-plane/rollback-recovery-note-v1.md"),
    "index": Path("reports/control-plane/full-stack-operation-readiness-index-v1.md"),
}

REQUIRED_REFERENCE_FAMILIES = (
    "OpenHands",
    "SWE-agent",
    "LangGraph",
    "MCP ecosystem",
    "OWASP LLM Top 10",
    "OpenTelemetry",
    "GitHub Actions",
    "Temporal",
    "Docker",
    "GitGuardian",
    "Aider",
    "AutoGen",
    "Enterprise SaaS",
    "Compliance operation",
    "Customer validation",
)

REQUIRED_MAKE_TARGETS = (
    "controlled-execution-check:",
    "commercial-readiness-check:",
    "real-world-validation-check:",
    "real-world-operation-check:",
    "full-stack-operation-readiness-check:",
    "scripts/real_world_operation_readiness_check_v1.py",
)

REQUIRED_WORKFLOW_TERMS = (
    "Run AI Agent Control Plane full-stack operation readiness check",
    "python scripts/real_world_operation_readiness_check_v1.py --stage all",
)

FORBIDDEN_SUPPORTED_CLAIMS = (
    "customer-validated",
    "production-ready",
    "enterprise-ready",
    "paid customer",
    "certified",
    "external benchmark-proven",
    "long-term stability",
    "commercially deployed",
    "global maturity",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=("all", "v4", "v5", "v6", "v7"),
        default="all",
        help="Subset of the readiness package to validate.",
    )
    args = parser.parse_args()

    errors: list[str] = []
    texts = _load_texts(errors)
    payloads = _load_jsons(errors)
    ledgers = _load_jsonl(errors)

    if args.stage in ("all", "v4"):
        _check_v4(texts, payloads, ledgers, errors)
    if args.stage in ("all", "v5"):
        _check_v5(texts, payloads, errors)
    if args.stage in ("all", "v6"):
        _check_v6(texts, payloads, errors)
    if args.stage in ("all", "v7"):
        _check_v7(texts, payloads, ledgers, errors)
    if args.stage == "all":
        _check_makefile(errors)
        _check_workflow(errors)

    if errors:
        print("real_world_operation_readiness_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"real_world_operation_readiness_check_v1: PASS ({args.stage})")
    return 0


def _load_texts(errors: list[str]) -> dict[Path, str]:
    texts: dict[Path, str] = {}
    for path in (*DOC_FILES.values(), *MD_REPORTS.values()):
        full = REPO_ROOT / path
        if not full.exists():
            errors.append(f"missing text artifact: {path.as_posix()}")
            continue
        texts[path] = full.read_text(encoding="utf-8")
    return texts


def _load_jsons(errors: list[str]) -> dict[Path, dict[str, Any]]:
    payloads: dict[Path, dict[str, Any]] = {}
    for path in JSON_FILES.values():
        full = REPO_ROOT / path
        if not full.exists():
            errors.append(f"missing JSON artifact: {path.as_posix()}")
            continue
        try:
            loaded = json.loads(full.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON in {path.as_posix()}: {exc}")
            continue
        if not isinstance(loaded, dict):
            errors.append(f"JSON artifact must be object: {path.as_posix()}")
            continue
        payloads[path] = loaded
    return payloads


def _load_jsonl(errors: list[str]) -> dict[Path, list[dict[str, Any]]]:
    ledgers: dict[Path, list[dict[str, Any]]] = {}
    for path in JSONL_FILES.values():
        full = REPO_ROOT / path
        if not full.exists():
            errors.append(f"missing JSONL artifact: {path.as_posix()}")
            continue
        rows: list[dict[str, Any]] = []
        for index, line in enumerate(full.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                loaded = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSONL in {path.as_posix()} line {index}: {exc}")
                continue
            if not isinstance(loaded, dict):
                errors.append(f"JSONL line must be object: {path.as_posix()} line {index}")
                continue
            rows.append(loaded)
        ledgers[path] = rows
    return ledgers


def _check_v4(
    texts: dict[Path, str],
    payloads: dict[Path, dict[str, Any]],
    ledgers: dict[Path, list[dict[str, Any]]],
    errors: list[str],
) -> None:
    registry = texts.get(DOC_FILES["registry"], "")
    classifier = texts.get(DOC_FILES["classifier"], "")
    for term in (
        "AI Agent Execution Control Plane",
        "ALLOW",
        "DRY_RUN_ONLY",
        "REQUIRE_HUMAN",
        "DENY",
        "evidence ledger",
        "failure ledger",
        "recurring queue",
        "non-claim audit",
    ):
        if term not in registry + classifier:
            errors.append(f"V4 registry/classifier missing term: {term}")

    schema = payloads.get(DOC_FILES["task_schema"])
    if schema is None:
        _load_standalone_json(DOC_FILES["task_schema"], errors)
    else:
        errors.append("internal error: task schema loaded from wrong collection")
    task_schema = _load_standalone_json(DOC_FILES["task_schema"], errors)
    if task_schema and "task_id" not in task_schema.get("properties", {}):
        errors.append("task schema missing task_id")

    fixtures = payloads.get(JSON_FILES["task_fixtures"], {})
    fixture_rows = fixtures.get("fixtures")
    if not isinstance(fixture_rows, list) or len(fixture_rows) < 4:
        errors.append("V4 task fixtures must include at least four fixtures")
        fixture_rows = []
    decisions = {row.get("expected_policy_decision") for row in fixture_rows if isinstance(row, dict)}
    for decision in ("ALLOW", "DRY_RUN_ONLY", "DENY"):
        if decision not in decisions:
            errors.append(f"V4 fixtures missing decision: {decision}")
    if not any("untrusted_tool_instruction" in row.get("risk_hints", []) for row in fixture_rows if isinstance(row, dict)):
        errors.append("V4 fixtures missing prompt-injection/tool-poisoning-like sample")

    cycle = payloads.get(JSON_FILES["first_cycle"], {})
    tasks = cycle.get("tasks")
    if not isinstance(tasks, list) or len(tasks) < 4:
        errors.append("first controlled cycle must record at least four tasks")
    else:
        cycle_decisions = {task.get("policy_decision") for task in tasks if isinstance(task, dict)}
        for decision in ("ALLOW", "DRY_RUN_ONLY", "DENY"):
            if decision not in cycle_decisions:
                errors.append(f"first controlled cycle missing policy decision: {decision}")

    evidence_rows = ledgers.get(JSONL_FILES["evidence"], [])
    failure_rows = ledgers.get(JSONL_FILES["failure"], [])
    if not any(row.get("stage") == "V4" and row.get("policy_decision") == "ALLOW" for row in evidence_rows):
        errors.append("evidence ledger missing V4 ALLOW entry")
    if not any(row.get("result") == "DENY" for row in failure_rows):
        errors.append("failure ledger missing DENY entry")
    if not any(row.get("result") == "DRY_RUN_ONLY" for row in failure_rows):
        errors.append("failure ledger missing DRY_RUN_ONLY entry")
    if not any("tool" in str(row.get("failed_gate", "")).lower() for row in failure_rows):
        errors.append("failure ledger missing tool-risk failure")

    resume = payloads.get(JSON_FILES["resume"], {})
    if resume.get("chat_memory_required") is not False:
        errors.append("resume point must not require chat memory")
    queue = payloads.get(JSON_FILES["queue"], {})
    if not isinstance(queue.get("items"), list) or len(queue["items"]) < 5:
        errors.append("recurring queue must contain health, benchmark, security, feedback, and commercial items")
    health = payloads.get(JSON_FILES["health"], {})
    state = health.get("control_plane_state", {})
    if not isinstance(state, dict) or state.get("tool_risk_registry_exists") is not True:
        errors.append("health check must record tool-risk registry")


def _check_v5(
    texts: dict[Path, str],
    payloads: dict[Path, dict[str, Any]],
    errors: list[str],
) -> None:
    matrix = texts.get(DOC_FILES["matrix"], "")
    for family in REQUIRED_REFERENCE_FAMILIES:
        if family not in matrix:
            errors.append(f"external matrix missing reference family: {family}")

    commercial = payloads.get(JSON_FILES["commercial"], {})
    components = commercial.get("components")
    if not isinstance(components, list) or len(components) < 20:
        errors.append("commercial readiness package must include at least 20 components")
        components = []
    component_names = " ".join(str(component.get("name", "")) for component in components if isinstance(component, dict))
    for term in (
        "operator runbook",
        "demo scenario pack",
        "customer pilot package",
        "enterprise buyer one-pager",
        "pricing/package hypothesis",
        "security review pack",
        "compliance readiness map",
        "incident response plan",
        "audit log export path",
        "external benchmark readiness path",
        "non-claim audit",
    ):
        if term not in component_names:
            errors.append(f"commercial package missing component: {term}")
    if commercial.get("unsupported_claims_blocked") is not True:
        errors.append("commercial package must block unsupported claims")


def _check_v6(texts: dict[Path, str], payloads: dict[Path, dict[str, Any]], errors: list[str]) -> None:
    tracker = payloads.get(JSON_FILES["validation_tracker"], {})
    if tracker.get("no_fabrication_rule") is not True:
        errors.append("V6 tracker must enforce no-fabrication rule")
    tracks = tracker.get("external_tracks")
    if not isinstance(tracks, list) or len(tracks) < 6:
        errors.append("V6 tracker must include demo, customer, benchmark, security, production, and paid-pilot tracks")
        tracks = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        if track.get("current_entries") != []:
            errors.append(f"V6 track must not fabricate entries: {track.get('track')}")
        for field in ("required_actor", "required_evidence", "blocker", "safe_substitute", "resume_point"):
            if not track.get(field):
                errors.append(f"V6 track missing {field}: {track.get('track')}")

    external = payloads.get(JSON_FILES["external_ledger"], {})
    if external.get("entries") != []:
        errors.append("external evidence ledger must remain empty until real evidence exists")
    required_fields = set(external.get("required_fields", []))
    for field in ("source", "actor", "date", "artifact", "claim_supported", "claim_not_supported", "confidence", "next_action"):
        if field not in required_fields:
            errors.append(f"external evidence ledger missing required field: {field}")

    feedback = texts.get(DOC_FILES["feedback"], "")
    if "fabricated ledger is forbidden" not in feedback:
        errors.append("customer feedback intake must explicitly forbid fabricated ledger")
    benchmark = texts.get(DOC_FILES["benchmark"], "")
    if "externally benchmark-proven" not in benchmark or "external evidence ledger" not in benchmark:
        errors.append("benchmark workflow missing external claim policy")


def _check_v7(
    texts: dict[Path, str],
    payloads: dict[Path, dict[str, Any]],
    ledgers: dict[Path, list[dict[str, Any]]],
    errors: list[str],
) -> None:
    for key in ("demo", "pilot", "security", "incident", "paid_pilot"):
        text = texts.get(DOC_FILES[key], "")
        if "Status:" not in text:
            errors.append(f"V7 workflow missing status: {DOC_FILES[key].as_posix()}")

    long_running = payloads.get(JSON_FILES["long_running"], {})
    if long_running.get("long_term_stability_claim_supported") is not False:
        errors.append("long-running tracker must not support long-term stability claim")
    production = payloads.get(JSON_FILES["production_blockers"], {})
    blockers = production.get("blockers")
    if not isinstance(blockers, list) or len(blockers) < 9:
        errors.append("production blocker ledger must include required production blockers")
    issue_queue = payloads.get(JSON_FILES["issue_queue"], {})
    if not isinstance(issue_queue.get("queue"), list) or len(issue_queue["queue"]) < 7:
        errors.append("issue/PR operating queue must include feedback, benchmark, security, stability, commercial, pricing, and deployment items")

    non_claim = payloads.get(JSON_FILES["non_claim"], {})
    if non_claim.get("audit_result") != "unsupported external claims are blocked":
        errors.append("non-claim audit result mismatch")
    for item in non_claim.get("unsupported_claims", []):
        if isinstance(item, dict) and item.get("supported") is not False:
            errors.append(f"unsupported claim marked supported: {item.get('claim')}")
    claims = {item.get("claim") for item in non_claim.get("unsupported_claims", []) if isinstance(item, dict)}
    for claim in FORBIDDEN_SUPPORTED_CLAIMS:
        if claim not in claims:
            errors.append(f"non-claim audit missing unsupported claim: {claim}")

    scorecard = payloads.get(JSON_FILES["scorecard"], {})
    if scorecard.get("terminal_status") != "CONTROLLED_AUTONOMOUS_ENGINEERING_OS_FULL_STACK_OPERATION_READY":
        errors.append("final scorecard terminal status mismatch")
    rows = scorecard.get("scorecard")
    if not isinstance(rows, list) or len(rows) < 14:
        errors.append("final scorecard must include V4, V5, V6, V7, operations, claims, and blockers")
    evidence_rows = ledgers.get(JSONL_FILES["evidence"], [])
    stages = {row.get("stage") for row in evidence_rows if isinstance(row, dict)}
    for stage in ("V4", "V5", "V6", "V7"):
        if stage not in stages:
            errors.append(f"evidence ledger missing stage: {stage}")


def _check_makefile(errors: list[str]) -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in REQUIRED_MAKE_TARGETS:
        if target not in makefile:
            errors.append(f"Makefile missing target/gate: {target}")


def _check_workflow(errors: list[str]) -> None:
    workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for term in REQUIRED_WORKFLOW_TERMS:
        if term not in workflow:
            errors.append(f"CI workflow missing operation readiness hook: {term}")


def _load_standalone_json(relative_path: Path, errors: list[str]) -> dict[str, Any] | None:
    path = REPO_ROOT / relative_path
    if not path.exists():
        errors.append(f"missing standalone JSON: {relative_path.as_posix()}")
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid standalone JSON in {relative_path.as_posix()}: {exc}")
        return None
    if not isinstance(loaded, dict):
        errors.append(f"standalone JSON must be object: {relative_path.as_posix()}")
        return None
    return loaded


if __name__ == "__main__":
    raise SystemExit(main())

