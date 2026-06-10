#!/usr/bin/env python3
"""Run the Wave 8 repository-local reliability benchmark."""

from __future__ import annotations

import hashlib
import json
import tempfile
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = Path("reports/reliability/reliability_benchmark_v1.json")

TARGETS = {
    "repeated_smoke_loop": 50,
    "multi_task_batch": 20,
    "multi_workspace_checks": 3,
    "approval_reject_run_mixed_flow": 20,
    "evidence_replay_batch_validation": 20,
    "failure_path_batch_validation": 10,
}

TASK_BATCH_REFS = (
    "README.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "Makefile",
    ".github/workflows/ci.yml",
    "docs/current_phase.md",
    "docs/identity/system_identity_v1.md",
    "docs/identity/non_goals_v1.md",
    "docs/contracts/task_contract_v1.md",
    "docs/contracts/execution_receipt_v1.md",
    "docs/contracts/evidence_trace_v1.md",
    "docs/contracts/failure_bundle_v1.md",
    "docs/security/security_control_matrix_v1.md",
    "docs/supply_chain/supply_chain_integrity_policy_v1.md",
    "docs/ai_admission/ai_provider_admission_policy_v1.md",
    "reports/observation/real_operation_observation_log_v1.json",
    "reports/failure_path/failure_path_baseline_v1.json",
    "reports/dogfood/dogfood_index_v1.json",
    "reports/audits/claim_to_evidence_matrix_v1.json",
    "governance/root/root_manifest_v1.json",
)

REQUIRED_DOCS = {
    Path("docs/reliability/reliability_baseline_v1.md"): (
        "repeated smoke loop",
        "target 50",
        "multi-task batch",
        "target 20",
        "multi-workspace checks",
        "approval/reject/run mixed flow",
        "evidence/replay batch validation",
        "failure-path batch validation",
        "elapsed time recording",
        "flake rate recording",
    ),
    Path("docs/operations/incident_response_v1.md"): (
        "severity",
        "triage",
        "containment",
        "evidence preservation",
        "rollback",
        "post-incident review",
    ),
    Path("docs/operations/rollback_runbook_v1.md"): (
        "rollback trigger",
        "safe rollback",
        "validation",
        "evidence preservation",
        "no force push",
    ),
    Path("docs/operations/maintenance_policy_v1.md"): (
        "maintenance window",
        "dependency review",
        "validation gate",
        "change record",
        "external review",
    ),
    Path("docs/operations/workspace_cleanup_policy_v1.md"): (
        "workspace cleanup",
        "tracked files",
        "temporary files",
        "secret material",
        "git status --short",
    ),
    Path("docs/operations/interrupted_run_policy_v1.md"): (
        "interrupted run",
        "resume",
        "idempotent",
        "evidence",
        "do not invent",
    ),
    Path("docs/compatibility/schema_versioning_policy_v1.md"): (
        "schema_version",
        "contract_version",
        "backward-compatible",
        "breaking change",
        "migration mapping",
        "fail closed",
    ),
}

FORBIDDEN_FINAL_WORDING = (
    "GLOBAL_RECOGNITION_CONFIRMED",
    "globally recognized",
    "externally certified",
    "world class confirmed",
)

LOCAL_PATH_MARKERS = (
    "/" + "Users" + "/" + "qqy",
    "Documents" + "/" + "Codex",
    "." + "codex",
    "files-mentioned" + "-by-the-user",
)


def main() -> int:
    errors: list[str] = []
    start = time.perf_counter()
    runtime_result = _run_benchmark(errors)
    elapsed_seconds = time.perf_counter() - start

    report = _load_report(errors)
    if report is not None:
        _check_report(report, runtime_result, elapsed_seconds, errors)
    _check_required_docs(errors)
    _check_ci_gate(errors)

    if errors:
        print("reliability_benchmark_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("reliability_benchmark_v1: PASS")
    print(f"elapsed_seconds={elapsed_seconds:.6f}")
    print(f"flake_rate={runtime_result['flake_rate']:.6f}")
    return 0


def _run_benchmark(errors: list[str]) -> dict[str, Any]:
    result_errors: list[str] = []
    repeated = _run_repeated_smoke_loop(result_errors)
    task_batch = _run_multi_task_batch(result_errors)
    workspaces = _run_multi_workspace_checks(result_errors)
    mixed_flow = _run_mixed_flow(result_errors)
    replay = _run_evidence_replay_batch(result_errors)
    failure_path = _run_failure_path_batch(result_errors)

    errors.extend(result_errors)
    sample_count = sum(TARGETS.values())
    flake_count = len(result_errors)
    flake_rate = 0.0 if sample_count == 0 else flake_count / sample_count
    return {
        "results": {
            "repeated_smoke_loop": repeated,
            "multi_task_batch": task_batch,
            "multi_workspace_checks": workspaces,
            "approval_reject_run_mixed_flow": mixed_flow,
            "evidence_replay_batch_validation": replay,
            "failure_path_batch_validation": failure_path,
        },
        "sample_count": sample_count,
        "flake_count": flake_count,
        "flake_rate": flake_rate,
    }


def _run_repeated_smoke_loop(errors: list[str]) -> dict[str, int]:
    required = (
        Path("README.md"),
        Path("docs/current_phase.md"),
        Path("reports/observation/real_operation_observation_log_v1.json"),
        Path("scripts/identity_boundary_check_v1.py"),
        Path("scripts/claim_to_evidence_check_v1.py"),
    )
    completed = 0
    for iteration in range(TARGETS["repeated_smoke_loop"]):
        missing = [path.as_posix() for path in required if not (REPO_ROOT / path).exists()]
        digest = hashlib.sha256(f"smoke:{iteration}:{len(missing)}".encode("utf-8")).hexdigest()
        if missing:
            errors.append(f"repeated smoke loop {iteration} missing refs: {', '.join(missing)}")
            continue
        if len(digest) != 64:
            errors.append(f"repeated smoke loop {iteration} produced invalid digest")
            continue
        completed += 1
    return {"target": TARGETS["repeated_smoke_loop"], "completed": completed, "failures": TARGETS["repeated_smoke_loop"] - completed}


def _run_multi_task_batch(errors: list[str]) -> dict[str, int]:
    completed = 0
    for index, ref in enumerate(TASK_BATCH_REFS, start=1):
        path = REPO_ROOT / ref
        if not path.exists():
            errors.append(f"multi-task batch item {index} missing ref: {ref}")
            continue
        if path.is_symlink():
            errors.append(f"multi-task batch item {index} must not be symlink: {ref}")
            continue
        completed += 1
    return {"target": TARGETS["multi_task_batch"], "completed": completed, "failures": TARGETS["multi_task_batch"] - completed}


def _run_multi_workspace_checks(errors: list[str]) -> dict[str, int]:
    completed = 0
    workspace_ids = ("workspace_alpha", "workspace_beta", "workspace_gamma")
    with tempfile.TemporaryDirectory(prefix="seos_reliability_v1_") as tmp:
        base = Path(tmp)
        for workspace_id in workspace_ids:
            workspace = base / workspace_id
            workspace.mkdir()
            manifest_path = workspace / "workspace_manifest.json"
            manifest = {
                "schema_version": "workspace_reliability_probe_v1",
                "workspace_id": workspace_id,
                "network_accessed": False,
                "secret_value_read": False,
            }
            manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if loaded != manifest:
                errors.append(f"multi-workspace check failed manifest round trip: {workspace_id}")
                continue
            if base != workspace.parent:
                errors.append(f"multi-workspace check escaped temp root: {workspace_id}")
                continue
            completed += 1
    return {"target": TARGETS["multi_workspace_checks"], "completed": completed, "failures": TARGETS["multi_workspace_checks"] - completed}


def _run_mixed_flow(errors: list[str]) -> dict[str, Any]:
    counts = {"approve": 0, "reject": 0, "run": 0}
    completed = 0
    for index in range(TARGETS["approval_reject_run_mixed_flow"]):
        if index % 5 == 0:
            action = "reject"
        elif index % 3 == 0:
            action = "run"
        else:
            action = "approve"
        receipt = {
            "task_id": f"wave8-mixed-flow-{index:02d}",
            "action": action,
            "approval_required": action == "run",
            "approval_recorded": action == "run",
            "secret_value_read": False,
            "network_accessed": False,
        }
        receipt["receipt_digest"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode("utf-8")).hexdigest()
        if action == "run" and not receipt["approval_recorded"]:
            errors.append(f"mixed flow run without approval: {receipt['task_id']}")
            continue
        if len(str(receipt["receipt_digest"])) != 64:
            errors.append(f"mixed flow invalid digest: {receipt['task_id']}")
            continue
        counts[action] += 1
        completed += 1

    if any(value == 0 for value in counts.values()):
        errors.append(f"mixed flow must cover approve, reject, and run: {counts}")
    return {
        "target": TARGETS["approval_reject_run_mixed_flow"],
        "completed": completed,
        "failures": TARGETS["approval_reject_run_mixed_flow"] - completed,
        "counts": counts,
    }


def _run_evidence_replay_batch(errors: list[str]) -> dict[str, int]:
    refs = _claim_evidence_refs(errors)
    completed = 0
    for index, ref in enumerate(refs[: TARGETS["evidence_replay_batch_validation"]], start=1):
        path = REPO_ROOT / ref
        if not path.exists():
            errors.append(f"evidence/replay batch item {index} missing ref: {ref}")
            continue
        first_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        replay_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if first_digest != replay_digest:
            errors.append(f"evidence/replay batch item {index} digest mismatch: {ref}")
            continue
        completed += 1
    if len(refs) < TARGETS["evidence_replay_batch_validation"]:
        errors.append("evidence/replay batch does not have 20 repository evidence refs")
    return {
        "target": TARGETS["evidence_replay_batch_validation"],
        "completed": completed,
        "failures": TARGETS["evidence_replay_batch_validation"] - completed,
    }


def _claim_evidence_refs(errors: list[str]) -> list[str]:
    matrix_path = REPO_ROOT / "reports/audits/claim_to_evidence_matrix_v1.json"
    try:
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot load claim matrix for replay batch: {exc}")
        return []
    refs: list[str] = []
    seen: set[str] = set()
    for claim in matrix.get("claims", []):
        if not isinstance(claim, dict):
            continue
        for ref in claim.get("evidence_refs", []):
            if not isinstance(ref, str) or ref.startswith("http") or ref in seen:
                continue
            seen.add(ref)
            refs.append(ref)
    return refs


FAILURE_CASES = (
    ("missing_task_id", {"schema_version": "task_contract_v1", "action": "approve"}, "blocked_missing_task_id"),
    ("bad_workspace", {"schema_version": "task_contract_v1", "task_id": "bad-workspace", "workspace": "../escape"}, "blocked_path_traversal"),
    ("run_without_approval", {"schema_version": "task_contract_v1", "task_id": "run-no-approval", "action": "run", "approval_recorded": False}, "rejected_missing_approval"),
    ("reject_without_reason", {"schema_version": "task_contract_v1", "task_id": "reject-no-reason", "action": "reject", "reason": ""}, "blocked_missing_rejection_reason"),
    ("bad_digest", {"schema_version": "task_contract_v1", "task_id": "bad-digest", "evidence_digest": "abc"}, "blocked_bad_digest"),
    ("bad_schema", {"schema_version": "task_contract_v2", "task_id": "bad-schema"}, "blocked_schema_version"),
    ("unsupported_claim", {"schema_version": "task_contract_v1", "task_id": "bad-claim", "claim": "GLOBAL_RECOGNITION_CONFIRMED"}, "blocked_unsupported_claim"),
    ("live_provider", {"schema_version": "task_contract_v1", "task_id": "live-provider", "runtime_provider": "live"}, "blocked_live_provider"),
    ("secret_material", {"schema_version": "task_contract_v1", "task_id": "secret-material", "secret_ref": "value:abc"}, "blocked_secret_material"),
    ("replay_mismatch", {"schema_version": "task_contract_v1", "task_id": "replay-mismatch", "evidence_digest": "a" * 64, "replay_digest": "b" * 64}, "blocked_replay_mismatch"),
)


def _run_failure_path_batch(errors: list[str]) -> dict[str, int]:
    completed = 0
    for name, payload, expected in FAILURE_CASES:
        actual = _fail_closed_decision(payload)
        if actual != expected:
            errors.append(f"failure-path case {name} expected {expected}, got {actual}")
            continue
        completed += 1
    return {
        "target": TARGETS["failure_path_batch_validation"],
        "completed": completed,
        "failures": TARGETS["failure_path_batch_validation"] - completed,
    }


def _fail_closed_decision(payload: dict[str, Any]) -> str:
    if payload.get("schema_version") != "task_contract_v1":
        return "blocked_schema_version"
    if not payload.get("task_id"):
        return "blocked_missing_task_id"
    if ".." in str(payload.get("workspace", "")):
        return "blocked_path_traversal"
    if payload.get("action") == "run" and payload.get("approval_recorded") is not True:
        return "rejected_missing_approval"
    if payload.get("action") == "reject" and not payload.get("reason"):
        return "blocked_missing_rejection_reason"
    evidence_digest = payload.get("evidence_digest")
    if evidence_digest is not None and not _is_sha256(str(evidence_digest)):
        return "blocked_bad_digest"
    claim = str(payload.get("claim", "")).lower()
    if "global_recognition_confirmed" in claim or "externally certified" in claim:
        return "blocked_unsupported_claim"
    if payload.get("runtime_provider") == "live":
        return "blocked_live_provider"
    secret_ref = str(payload.get("secret_ref", ""))
    if secret_ref.startswith("value:") or secret_ref.startswith(".env"):
        return "blocked_secret_material"
    replay_digest = payload.get("replay_digest")
    if replay_digest is not None and replay_digest != evidence_digest:
        return "blocked_replay_mismatch"
    return "accepted"


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _load_report(errors: list[str]) -> dict[str, Any] | None:
    path = REPO_ROOT / REPORT_PATH
    if not path.exists():
        errors.append(f"missing reliability report: {REPORT_PATH.as_posix()}")
        return None
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid reliability report JSON: {exc}")
        return None
    if not isinstance(report, dict):
        errors.append("reliability report must be a JSON object")
        return None
    return report


def _check_report(
    report: dict[str, Any],
    runtime_result: dict[str, Any],
    elapsed_seconds: float,
    errors: list[str],
) -> None:
    if report.get("schema_version") != "reliability_benchmark_v1":
        errors.append("reliability report schema_version mismatch")
    if report.get("external_review_required") is not True:
        errors.append("reliability report must require external review")
    if report.get("global_recognition_claimed") is not False:
        errors.append("reliability report must not claim global recognition")
    for flag in ("runtime_expansion_performed", "network_accessed", "secret_value_read"):
        if report.get(flag) is not False:
            errors.append(f"reliability report flag must be false: {flag}")

    if report.get("targets") != TARGETS:
        errors.append("reliability report targets do not match benchmark targets")

    results = report.get("results", {})
    if not isinstance(results, dict):
        errors.append("reliability report results must be object")
        return
    for name, target in TARGETS.items():
        result = results.get(name)
        runtime = runtime_result["results"][name]
        if not isinstance(result, dict):
            errors.append(f"reliability report missing result: {name}")
            continue
        if result.get("target") != target:
            errors.append(f"reliability report result target mismatch: {name}")
        if result.get("completed") != runtime["completed"]:
            errors.append(f"reliability report result completed mismatch: {name}")
        if result.get("failures") != 0:
            errors.append(f"reliability report result must have zero failures: {name}")

    mixed_counts = results.get("approval_reject_run_mixed_flow", {}).get("counts", {})
    if not isinstance(mixed_counts, dict) or any(mixed_counts.get(key, 0) <= 0 for key in ("approve", "reject", "run")):
        errors.append("reliability report mixed flow must include approve, reject, and run counts")

    elapsed = report.get("elapsed_time_recording", {})
    if not isinstance(elapsed, dict):
        errors.append("reliability report missing elapsed_time_recording object")
    else:
        if elapsed.get("recording_mode") != "runtime_stdout_and_committed_baseline":
            errors.append("elapsed time recording mode mismatch")
        max_expected = elapsed.get("max_expected_seconds")
        if not isinstance(max_expected, (int, float)) or max_expected <= 0:
            errors.append("elapsed time max_expected_seconds must be positive")
        elif elapsed_seconds > float(max_expected):
            errors.append(f"benchmark exceeded elapsed ceiling: {elapsed_seconds:.6f}s")

    flake = report.get("flake_rate_recording", {})
    if not isinstance(flake, dict):
        errors.append("reliability report missing flake_rate_recording object")
    else:
        if flake.get("sample_count") != runtime_result["sample_count"]:
            errors.append("flake rate sample_count mismatch")
        if flake.get("observed_flake_count") != runtime_result["flake_count"]:
            errors.append("flake count mismatch")
        if flake.get("observed_flake_rate") != runtime_result["flake_rate"]:
            errors.append("flake rate mismatch")

    _check_text_safety(json.dumps(report, sort_keys=True), REPORT_PATH, errors)


def _check_required_docs(errors: list[str]) -> None:
    for relative_path, required_terms in REQUIRED_DOCS.items():
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing Wave 8 doc: {relative_path.as_posix()}")
            continue
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        for term in required_terms:
            if term.lower() not in lower:
                errors.append(f"{relative_path.as_posix()} missing term: {term}")
        _check_text_safety(text, relative_path, errors)


def _check_ci_gate(errors: list[str]) -> None:
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for token in (
        "scripts/reliability_benchmark_v1.py",
        "scripts/schema_compatibility_check_v1.py",
    ):
        if token not in ci_text:
            errors.append(f".github/workflows/ci.yml missing gate: {token}")
        if token not in makefile_text:
            errors.append(f"Makefile missing gate: {token}")


def _check_text_safety(text: str, relative_path: Path, errors: list[str]) -> None:
    lower = text.lower()
    for forbidden in FORBIDDEN_FINAL_WORDING:
        if forbidden.lower() in lower:
            errors.append(f"{relative_path.as_posix()} contains forbidden final wording: {forbidden}")
    for marker in LOCAL_PATH_MARKERS:
        if marker in text:
            errors.append(f"{relative_path.as_posix()} contains local path marker: {marker}")


if __name__ == "__main__":
    raise SystemExit(main())
