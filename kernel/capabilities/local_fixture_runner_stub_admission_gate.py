"""Metadata-only admission gate for a future local-fixture runner stub.

This module validates two upstream metadata artifacts and records whether a
future runner-stub PR may be proposed. It does not create a runner, create a
runnable job, issue approval or execution material, execute an adapter, launch
Playwright, open a browser, access the network, grant autonomy, or promote
production.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file, sha256_text
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically

__all__ = [
    "LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FILE",
    "LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE",
    "LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_MANIFEST_FILE",
    "LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE",
    "LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CHECKLIST_FILE",
    "LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_FILE",
    "LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE",
    "LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ATTESTATION",
    "LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FALSE_FIELDS",
    "LocalFixtureRunnerStubAdmissionGateResult",
    "run_local_fixture_runner_stub_admission_gate",
    "run_local_fixture_runner_stub_admission_gate_launcher",
]


LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FILE = (
    "local_fixture_runner_stub_admission_gate.json"
)
LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE = (
    "local_fixture_runner_stub_admission_gate_result.json"
)
LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_MANIFEST_FILE = (
    "local_fixture_runner_stub_admission_gate_manifest.json"
)
LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE = (
    "local_fixture_runner_stub_admission_gate_summary.md"
)
LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CHECKLIST_FILE = (
    "local_fixture_runner_stub_admission_gate_checklist.md"
)
LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_FILE = "artifact_index.json"
LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ATTESTATION = (
    "I_REVIEWED_LOCAL_FIXTURE_HUMAN_APPROVAL_AND_RUNNER_CONTRACT_FOR_METADATA_"
    "ONLY_RUNNER_STUB_ADMISSION_NO_RUNNER_NO_JOB_NO_TOKEN_NO_EXECUTION_NO_"
    "BROWSER_NO_NETWORK_NO_PRODUCTION"
)

LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FALSE_FIELDS = (
    "approval_token_issued",
    "execution_token_issued",
    "runner_created",
    "runnable_job_created",
    "adapter_execution_performed",
    "playwright_execution_performed",
    "browser_open_performed",
    "network_access_performed",
    "live_website_access_performed",
    "autonomous_execution_performed",
    "production_promotion_granted",
)

_GATE_TYPE = "local_fixture_runner_stub_admission_gate_v1"
_MANIFEST_TYPE = "local_fixture_runner_stub_admission_gate_manifest_v1"
_ARTIFACT_INDEX_TYPE = "local_fixture_runner_stub_admission_gate_index_v1"
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "local_fixture_runner_stub_admission_gate_index_manifest_v1"
)
_AUTHORITY = "non_authority_runner_stub_admission_metadata_only"
_ADAPTER_ID = "local_fixture_runner_stub_admission_gate"
_CAPABILITY = "launch_local_fixture_runner_stub_admission_gate"
_COMPLETED_STATUS = "local_fixture_runner_stub_admission_gate_completed"
_REJECTED_STATUS = "local_fixture_runner_stub_admission_gate_rejected"
_COMPLETED_DECISION = "record_runner_stub_admission_gate_only"
_REJECTED_DECISION = "reject_runner_stub_admission_gate"
_NEXT_ALLOWED_ACTION_SUCCESS = (
    "human_review_runner_stub_admission_gate_before_runner_stub_pr"
)
_NEXT_ALLOWED_ACTION_FAILURE = "fix_upstream_artifacts_or_gate_and_retry"
_HUMAN_ARTIFACT_TYPE = "local_fixture_human_approval_artifact_v1"
_HUMAN_COMPLETED_STATUS = "local_fixture_human_approval_artifact_completed"
_HUMAN_COMPLETED_DECISION = "record_human_approval_artifact_only"
_RUNNER_CONTRACT_TYPE = "local_fixture_runner_contract_draft_v1"
_RUNNER_CONTRACT_COMPLETED_STATUS = (
    "local_fixture_runner_contract_draft_completed"
)
_RUNNER_CONTRACT_COMPLETED_DECISION = "record_runner_contract_draft_only"
_RUNNER_CONTRACT_ARTIFACT_ADAPTER_ID = "local_fixture_runner_contract_draft"
_OUTPUT_FILES = (
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CHECKLIST_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE,
)
_HUMAN_EXPECTED_FIELDS = {
    "approval_artifact_type": _HUMAN_ARTIFACT_TYPE,
    "approval_artifact_status": _HUMAN_COMPLETED_STATUS,
    "approval_artifact_decision": _HUMAN_COMPLETED_DECISION,
}
_HUMAN_REQUIRED_TRUE_FIELDS = (
    "approval_recorded",
    "metadata_only",
    "human_review_recorded",
    "required_human_approval",
    "non_production",
    "future_runner_requires_separate_pr",
    "future_execution_requires_separate_runner_receipt",
    "future_execution_requires_explicit_local_fixture_runner_gate",
)
_RUNNER_CONTRACT_EXPECTED_FIELDS = {
    "contract_type": _RUNNER_CONTRACT_TYPE,
    "runner_contract_status": _RUNNER_CONTRACT_COMPLETED_STATUS,
    "runner_contract_decision": _RUNNER_CONTRACT_COMPLETED_DECISION,
}
_RUNNER_CONTRACT_REQUIRED_TRUE_FIELDS = (
    "contract_recorded",
    "contract_only",
    "metadata_only",
    "future_runner_requires_separate_implementation_pr",
    "future_runner_requires_verified_human_approval_artifact",
    "future_runner_requires_verified_execution_gate_plan",
    "future_runner_requires_local_fixture_only",
    "future_runner_requires_runner_receipt",
    "future_runner_requires_artifact_index",
)
_SOURCE_IDENTITY_FIELDS = (
    "adapter_id",
    "candidate_id",
    "repo_full_name",
    "local_fixture_sha256",
)


@dataclass(frozen=True)
class LocalFixtureRunnerStubAdmissionGateResult:
    human_approval_artifact_result_path: Path
    runner_contract_draft_result_path: Path
    output_dir: Path
    gate_id: str
    reviewer_id: str
    gate_path: Path | None
    result_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    gate_recorded: bool
    gate_status: str
    gate_decision: str
    rejection_reasons: tuple[str, ...]
    payload: dict[str, object]


def run_local_fixture_runner_stub_admission_gate_launcher(
    human_approval_artifact_result: Path,
    runner_contract_draft_result: Path,
    output_dir: Path,
    gate_id: str,
    reviewer_id: str,
    review_attestation: str | None,
) -> LocalFixtureRunnerStubAdmissionGateResult:
    """Launcher-oriented wrapper for the metadata-only admission gate."""

    return run_local_fixture_runner_stub_admission_gate(
        human_approval_artifact_result,
        runner_contract_draft_result,
        output_dir,
        gate_id,
        reviewer_id,
        review_attestation,
    )


def run_local_fixture_runner_stub_admission_gate(
    human_approval_artifact_result: Path,
    runner_contract_draft_result: Path,
    output_dir: Path,
    gate_id: str,
    reviewer_id: str,
    review_attestation: str | None,
) -> LocalFixtureRunnerStubAdmissionGateResult:
    """Validate upstream metadata before any future runner-stub PR."""

    human_path = Path(human_approval_artifact_result)
    contract_path = Path(runner_contract_draft_result)
    output_path = Path(output_dir)
    paths = _output_paths(output_path)
    preflight_reasons = _preflight_rejection_reasons(output_path, paths)
    if preflight_reasons:
        return _unwritten_result(
            human_path=human_path,
            contract_path=contract_path,
            output_path=output_path,
            gate_id=gate_id,
            reviewer_id=reviewer_id,
            rejection_reasons=preflight_reasons,
        )

    human_payload, human_read_reasons = _read_json_object_source(
        human_path,
        source_label="human_approval_artifact_result",
    )
    contract_payload, contract_read_reasons = _read_json_object_source(
        contract_path,
        source_label="runner_contract_draft_result",
    )
    rejection_reasons = _dedupe_strings(
        _gate_input_rejection_reasons(gate_id, reviewer_id, review_attestation)
        + human_read_reasons
        + contract_read_reasons
        + (
            []
            if human_read_reasons
            else _human_approval_artifact_rejection_reasons(human_payload)
        )
        + (
            []
            if contract_read_reasons
            else _runner_contract_draft_rejection_reasons(contract_payload)
        )
        + (
            []
            if human_read_reasons or contract_read_reasons
            else _source_identity_mismatch_reasons(human_payload, contract_payload)
        )
    )
    gate_recorded = not rejection_reasons
    status = _COMPLETED_STATUS if gate_recorded else _REJECTED_STATUS
    decision = _COMPLETED_DECISION if gate_recorded else _REJECTED_DECISION
    next_allowed_action = (
        _NEXT_ALLOWED_ACTION_SUCCESS
        if gate_recorded
        else _NEXT_ALLOWED_ACTION_FAILURE
    )

    gate = _gate_payload(
        human_path=human_path,
        human_payload=human_payload,
        contract_path=contract_path,
        contract_payload=contract_payload,
        output_path=output_path,
        paths=paths,
        gate_id=gate_id,
        reviewer_id=reviewer_id,
        review_attestation=review_attestation,
        gate_recorded=gate_recorded,
        status=status,
        decision=decision,
        next_allowed_action=next_allowed_action,
        rejection_reasons=rejection_reasons,
    )
    result = _result_payload(gate)

    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FILE],
        gate,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE],
        result,
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE],
        _summary_markdown(result),
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CHECKLIST_FILE],
        _checklist_markdown(result),
    )
    manifest = _manifest_payload(output_path=output_path, paths=paths, result=result)
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path=output_path,
        paths=paths,
        gate_id=gate_id,
        gate_recorded=gate_recorded,
        status=status,
        decision=decision,
        next_allowed_action=next_allowed_action,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        paths,
        artifact_index,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE],
        artifact_index_manifest,
    )

    payload = _launcher_payload(output_path=output_path, paths=paths, result=result)
    return LocalFixtureRunnerStubAdmissionGateResult(
        human_approval_artifact_result_path=human_path,
        runner_contract_draft_result_path=contract_path,
        output_dir=output_path,
        gate_id=gate_id,
        reviewer_id=reviewer_id,
        gate_path=paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FILE],
        result_path=paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE],
        manifest_path=paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_MANIFEST_FILE],
        summary_path=paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE],
        checklist_path=paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CHECKLIST_FILE],
        artifact_index_path=paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        complete=gate_recorded,
        gate_recorded=gate_recorded,
        gate_status=status,
        gate_decision=decision,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _output_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _OUTPUT_FILES}


def _preflight_rejection_reasons(
    output_path: Path,
    paths: dict[str, Path],
) -> list[str]:
    reasons: list[str] = []
    if output_path.is_symlink():
        reasons.append("output_dir_symlink_rejected")
        return reasons
    if not output_path.exists() or not output_path.is_dir():
        reasons.append("output_dir_missing")
        return reasons
    for candidate in paths.values():
        if candidate.exists() or candidate.is_symlink():
            reasons.append("output_collision")
            break
    return reasons


def _gate_input_rejection_reasons(
    gate_id: str,
    reviewer_id: str,
    review_attestation: str | None,
) -> list[str]:
    reasons: list[str] = []
    if not _non_empty_text(gate_id):
        reasons.append("gate_id_missing")
    if not _non_empty_text(reviewer_id):
        reasons.append("reviewer_id_missing")
    if not _non_empty_text(review_attestation):
        reasons.append("review_attestation_missing")
    elif review_attestation != LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ATTESTATION:
        reasons.append("review_attestation_mismatch")
    return reasons


def _read_json_object_source(
    source_path: Path,
    *,
    source_label: str,
) -> tuple[dict[str, object], list[str]]:
    if source_path.is_symlink():
        return {}, [f"{source_label}_is_symlink"]
    if not source_path.exists():
        return {}, [f"{source_label}_missing"]
    if not source_path.is_file():
        return {}, [f"{source_label}_not_regular_file"]
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}, [f"{source_label}_not_json_object"]
    if not isinstance(payload, dict):
        return {}, [f"{source_label}_not_json_object"]
    return payload, []


def _human_approval_artifact_rejection_reasons(
    payload: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    for field_name, expected in _HUMAN_EXPECTED_FIELDS.items():
        if payload.get(field_name) != expected:
            reasons.append(f"human_{field_name}_mismatch")
    for field_name in _HUMAN_REQUIRED_TRUE_FIELDS:
        if payload.get(field_name) is not True:
            reasons.append(f"human_{field_name}_not_true")
    for field_name in LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FALSE_FIELDS:
        if payload.get(field_name) is True:
            reasons.append(f"human_{field_name}_forbidden_true")
    return _dedupe_strings(reasons)


def _runner_contract_draft_rejection_reasons(
    payload: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    for field_name, expected in _RUNNER_CONTRACT_EXPECTED_FIELDS.items():
        if payload.get(field_name) != expected:
            reasons.append(f"runner_contract_{field_name}_mismatch")
    for field_name in _RUNNER_CONTRACT_REQUIRED_TRUE_FIELDS:
        if payload.get(field_name) is not True:
            reasons.append(f"runner_contract_{field_name}_not_true")
    for field_name in LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FALSE_FIELDS:
        if payload.get(field_name) is True:
            reasons.append(f"runner_contract_{field_name}_forbidden_true")
    return _dedupe_strings(reasons)


def _source_identity_mismatch_reasons(
    human_payload: dict[str, object],
    contract_payload: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    for field_name in _SOURCE_IDENTITY_FIELDS:
        human_value = _source_identity_value(
            human_payload,
            source_kind="human_approval_artifact",
            field_name=field_name,
        )
        contract_value = _source_identity_value(
            contract_payload,
            source_kind="runner_contract_draft",
            field_name=field_name,
        )
        if human_value is _MISSING or contract_value is _MISSING:
            continue
        if human_value != contract_value:
            reasons.append(f"source_{field_name}_mismatch")
    return reasons


_MISSING = object()


def _source_identity_value(
    payload: dict[str, object],
    *,
    source_kind: str,
    field_name: str,
) -> object:
    if field_name not in payload:
        return _MISSING
    value = payload[field_name]
    if (
        source_kind == "runner_contract_draft"
        and field_name == "adapter_id"
        and value == _RUNNER_CONTRACT_ARTIFACT_ADAPTER_ID
    ):
        return _MISSING
    return value


def _gate_payload(
    *,
    human_path: Path,
    human_payload: dict[str, object],
    contract_path: Path,
    contract_payload: dict[str, object],
    output_path: Path,
    paths: dict[str, Path],
    gate_id: str,
    reviewer_id: str,
    review_attestation: str | None,
    gate_recorded: bool,
    status: str,
    decision: str,
    next_allowed_action: str,
    rejection_reasons: list[str],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "gate_type": _GATE_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "gate_id": gate_id,
        "reviewer_id": reviewer_id,
        "review_attestation_present": _non_empty_text(review_attestation),
        "review_attestation_sha256": (
            None if review_attestation is None else sha256_text(review_attestation)
        ),
        "human_approval_artifact_result_path": human_path.as_posix(),
        "human_approval_artifact_result_sha256": _source_sha256(human_path),
        "runner_contract_draft_result_path": contract_path.as_posix(),
        "runner_contract_draft_result_sha256": _source_sha256(contract_path),
        "source_human_approval_artifact_type": human_payload.get(
            "approval_artifact_type"
        ),
        "source_human_approval_artifact_status": human_payload.get(
            "approval_artifact_status"
        ),
        "source_human_approval_artifact_decision": human_payload.get(
            "approval_artifact_decision"
        ),
        "source_runner_contract_type": contract_payload.get("contract_type"),
        "source_runner_contract_status": contract_payload.get(
            "runner_contract_status"
        ),
        "source_runner_contract_decision": contract_payload.get(
            "runner_contract_decision"
        ),
        "source_adapter_id": human_payload.get("adapter_id"),
        "source_candidate_id": human_payload.get("candidate_id"),
        "source_repo_full_name": human_payload.get("repo_full_name"),
        "source_local_fixture_sha256": human_payload.get("local_fixture_sha256"),
        "gate_recorded": gate_recorded,
        "gate_status": status,
        "gate_decision": decision,
        "metadata_only": True,
        "future_runner_stub_requires_separate_pr": True,
        "future_runner_stub_requires_no_network": True,
        "future_runner_stub_requires_no_browser": True,
        "future_runner_stub_requires_no_production": True,
        "future_runner_stub_requires_receipt_contract": True,
        "next_allowed_action": next_allowed_action,
        "rejection_reasons": list(rejection_reasons),
        "complete": gate_recorded,
        "rejected": not gate_recorded,
        "output_dir": output_path.as_posix(),
        "gate_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FILE
        ].as_posix(),
        "result_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE
        ].as_posix(),
        "manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_MANIFEST_FILE
        ].as_posix(),
        "summary_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE
        ].as_posix(),
        "checklist_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        **_false_fields(),
    }
    return payload


def _result_payload(gate: dict[str, object]) -> dict[str, object]:
    payload = dict(gate)
    payload["result_type"] = "local_fixture_runner_stub_admission_gate_result_v1"
    return payload


def _manifest_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    result: dict[str, object],
) -> dict[str, object]:
    return {
        "manifest_type": _MANIFEST_TYPE,
        "gate_type": _GATE_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "gate_id": result["gate_id"],
        "job_dir": output_path.as_posix(),
        "gate_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FILE
        ].as_posix(),
        "gate_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FILE]
        ),
        "result_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE
        ].as_posix(),
        "result_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE]
        ),
        "summary_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE]
        ),
        "checklist_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CHECKLIST_FILE]
        ),
        "human_approval_artifact_result_path": result[
            "human_approval_artifact_result_path"
        ],
        "human_approval_artifact_result_sha256": result[
            "human_approval_artifact_result_sha256"
        ],
        "runner_contract_draft_result_path": result[
            "runner_contract_draft_result_path"
        ],
        "runner_contract_draft_result_sha256": result[
            "runner_contract_draft_result_sha256"
        ],
        "gate_recorded": result["gate_recorded"],
        "gate_status": result["gate_status"],
        "gate_decision": result["gate_decision"],
        "metadata_only": True,
        "next_allowed_action": result["next_allowed_action"],
        **_false_fields(),
    }


def _artifact_index_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    gate_id: str,
    gate_recorded: bool,
    status: str,
    decision: str,
    next_allowed_action: str,
) -> dict[str, object]:
    roles = (
        (
            "local_fixture_runner_stub_admission_gate",
            paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FILE],
        ),
        (
            "local_fixture_runner_stub_admission_gate_result",
            paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE],
        ),
        (
            "local_fixture_runner_stub_admission_gate_manifest",
            paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_MANIFEST_FILE],
        ),
        (
            "local_fixture_runner_stub_admission_gate_summary",
            paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE],
        ),
        (
            "local_fixture_runner_stub_admission_gate_checklist",
            paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CHECKLIST_FILE],
        ),
        (
            "artifact_index",
            paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_FILE],
        ),
        (
            "artifact_index_manifest",
            paths[
                LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE
            ],
        ),
    )
    entries = [
        _generated_artifact_entry(
            output_path,
            role,
            path,
            hash_deferred=role in {"artifact_index", "artifact_index_manifest"},
        )
        for role, path in roles
    ]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "gate_type": _GATE_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "gate_id": gate_id,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "runner_stub_admission_gate_output_artifacts_only",
        "gate_recorded": gate_recorded,
        "gate_status": status,
        "gate_decision": decision,
        "metadata_only": True,
        "next_allowed_action": next_allowed_action,
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        **_false_fields(),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = paths[LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_FILE]
    entries = list(artifact_index["entries"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "gate_type": _GATE_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "gate_id": artifact_index["gate_id"],
        "job_dir": output_path.as_posix(),
        "artifact_index_path": index_path.as_posix(),
        "artifact_index_sha256": sha256_file(index_path),
        "artifact_index_hash_verified_by_manifest": True,
        "indexed_artifacts": len(entries),
        "artifact_roles": {
            str(entry["artifact_role"]): str(entry["path"]) for entry in entries
        },
        "indexed_relative_paths": [str(entry["relative_path"]) for entry in entries],
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "deterministic_ordering": True,
        "content_indexed": False,
        "raw_content_copied": False,
        "gate_recorded": artifact_index["gate_recorded"],
        "gate_status": artifact_index["gate_status"],
        "gate_decision": artifact_index["gate_decision"],
        "metadata_only": True,
        "next_allowed_action": artifact_index["next_allowed_action"],
        **_false_fields(),
    }


def _generated_artifact_entry(
    root_path: Path,
    role: str,
    path: Path,
    *,
    hash_deferred: bool,
) -> dict[str, object]:
    exists = path.exists() and path.is_file() and not path.is_symlink()
    return {
        "artifact_name": role,
        "artifact_role": role,
        "path": path.as_posix(),
        "relative_path": _relative_path(path, root_path),
        "extension": path.suffix,
        "exists": exists or hash_deferred,
        "size_bytes": path.stat().st_size if exists else None,
        "sha256": sha256_file(path) if exists else None,
        "hash_deferred_to_manifest": role == "artifact_index",
        "hash_unavailable_without_self_reference": role == "artifact_index_manifest",
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_repo_file": False,
        "external_candidate_artifact": False,
    }


def _launcher_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    result: dict[str, object],
) -> dict[str, object]:
    payload = {
        "workflow": "local_fixture_runner_stub_admission_gate_workflow",
        "complete": bool(result["complete"]),
        "gate_recorded": bool(result["gate_recorded"]),
        "output_dir": output_path.as_posix(),
        "human_summary_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_runner_stub_admission_gate_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FILE
        ].as_posix(),
        "local_fixture_runner_stub_admission_gate_result_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE
        ].as_posix(),
        "local_fixture_runner_stub_admission_gate_manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_MANIFEST_FILE
        ].as_posix(),
        "local_fixture_runner_stub_admission_gate_summary_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_runner_stub_admission_gate_checklist_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
    }
    payload.update(result)
    return payload


def _unwritten_result(
    *,
    human_path: Path,
    contract_path: Path,
    output_path: Path,
    gate_id: str,
    reviewer_id: str,
    rejection_reasons: list[str],
) -> LocalFixtureRunnerStubAdmissionGateResult:
    payload: dict[str, object] = {
        "workflow": "local_fixture_runner_stub_admission_gate_workflow",
        "complete": False,
        "gate_type": _GATE_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "gate_id": gate_id,
        "reviewer_id": reviewer_id,
        "human_approval_artifact_result_path": human_path.as_posix(),
        "human_approval_artifact_result_sha256": _source_sha256(human_path),
        "runner_contract_draft_result_path": contract_path.as_posix(),
        "runner_contract_draft_result_sha256": _source_sha256(contract_path),
        "output_dir": output_path.as_posix(),
        "gate_recorded": False,
        "gate_status": _REJECTED_STATUS,
        "gate_decision": _REJECTED_DECISION,
        "metadata_only": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION_FAILURE,
        "rejection_reasons": list(rejection_reasons),
        **_false_fields(),
    }
    return LocalFixtureRunnerStubAdmissionGateResult(
        human_approval_artifact_result_path=human_path,
        runner_contract_draft_result_path=contract_path,
        output_dir=output_path,
        gate_id=gate_id,
        reviewer_id=reviewer_id,
        gate_path=None,
        result_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        gate_recorded=False,
        gate_status=_REJECTED_STATUS,
        gate_decision=_REJECTED_DECISION,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _summary_markdown(result: dict[str, object]) -> str:
    reasons = result.get("rejection_reasons")
    if isinstance(reasons, list) and reasons:
        reason_lines = "\n".join("- " + str(reason) for reason in reasons)
    else:
        reason_lines = "- none"
    return "\n".join(
        [
            "# Local-Fixture Runner Stub Admission Gate",
            "",
            "Metadata-only runner-stub admission gate.",
            "This is not a runner.",
            "This does not create a runnable job.",
            "This does not issue approval material.",
            "This does not issue execution material.",
            "This does not execute adapter.",
            "This does not launch Playwright.",
            "This does not open browser.",
            "This does not access network.",
            "This does not authorize live websites.",
            "This does not authorize production.",
            "Future runner stub requires a separate PR after this gate passes.",
            "Future runner stub remains local-fixture metadata until separately reviewed.",
            "",
            f"gate_id: {result['gate_id']}",
            f"reviewer_id: {result['reviewer_id']}",
            f"gate_status: {result['gate_status']}",
            f"gate_decision: {result['gate_decision']}",
            f"gate_recorded: {str(result['gate_recorded']).lower()}",
            f"human_approval_artifact_result_path: {result['human_approval_artifact_result_path']}",
            f"human_approval_artifact_result_sha256: {result['human_approval_artifact_result_sha256']}",
            f"runner_contract_draft_result_path: {result['runner_contract_draft_result_path']}",
            f"runner_contract_draft_result_sha256: {result['runner_contract_draft_result_sha256']}",
            "",
            "Rejected capabilities:",
            "- runner creation",
            "- runnable job creation",
            "- approval or execution material issuance",
            "- adapter or Playwright execution",
            "- browser opening",
            "- network or live website access",
            "- autonomous execution",
            "- production promotion",
            "",
            "Rejection reasons:",
            reason_lines,
            "",
            f"next_allowed_action: {result['next_allowed_action']}",
            "",
        ]
    )


def _checklist_markdown(result: dict[str, object]) -> str:
    checked = "[x]" if result["gate_recorded"] else "[ ]"
    return "\n".join(
        [
            "# Local-Fixture Runner Stub Admission Gate Checklist",
            "",
            f"- {checked} Human approval artifact result validated.",
            f"- {checked} Runner contract draft result validated.",
            f"- {checked} Source identity fields agree where both artifacts carry them.",
            f"- {checked} Exact metadata-only admission attestation recorded.",
            "- [x] Approval material was not issued.",
            "- [x] Execution material was not issued.",
            "- [x] Runner was not created.",
            "- [x] Runnable job was not created.",
            "- [x] Adapter execution was not performed.",
            "- [x] Playwright execution was not performed.",
            "- [x] Browser opening was not performed.",
            "- [x] Network access was not performed.",
            "- [x] Live website access was not performed.",
            "- [x] Autonomous execution was not performed.",
            "- [x] Production promotion remains denied.",
            "",
        ]
    )


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("output_collision")
    write_json_atomically(path, payload)


def _write_markdown_exclusive(path: Path, content: str) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("output_collision")
    write_markdown_atomically(path, content)


def _false_fields() -> dict[str, object]:
    return {
        field_name: False
        for field_name in LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FALSE_FIELDS
    }


def _source_sha256(path: Path | None) -> str | None:
    if path is not None and _regular_file(path):
        return sha256_file(path)
    return None


def _regular_file(path: Path) -> bool:
    return path.exists() and path.is_file() and not path.is_symlink()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _dedupe_strings(values: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped
