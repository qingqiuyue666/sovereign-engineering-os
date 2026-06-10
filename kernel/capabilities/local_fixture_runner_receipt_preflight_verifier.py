"""Metadata-only preflight verifier for a future local-fixture runner receipt.

This module validates upstream local-fixture governance metadata before any
future runner receipt implementation PR. It is not a runner, not a runner
stub, does not create a runnable job, does not issue approval or execution
material, does not execute an adapter, does not launch Playwright, does not
open a browser, does not access the network, does not access live websites,
does not grant autonomy, and does not promote production.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file, sha256_text
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically

__all__ = [
    "LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_MANIFEST_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CHECKLIST_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_MANIFEST_FILE",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ATTESTATION",
    "LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FALSE_FIELDS",
    "LocalFixtureRunnerReceiptPreflightVerifierResult",
    "run_local_fixture_runner_receipt_preflight_verifier",
    "run_local_fixture_runner_receipt_preflight_verifier_launcher",
]


LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FILE = (
    "local_fixture_runner_receipt_preflight_verifier.json"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE = (
    "local_fixture_runner_receipt_preflight_verifier_result.json"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_MANIFEST_FILE = (
    "local_fixture_runner_receipt_preflight_verifier_manifest.json"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE = (
    "local_fixture_runner_receipt_preflight_verifier_summary.md"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CHECKLIST_FILE = (
    "local_fixture_runner_receipt_preflight_verifier_checklist.md"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_FILE = (
    "artifact_index.json"
)
LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ATTESTATION = (
    "I_REVIEWED_LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_METADATA_ONLY_"
    "NO_RUNNER_NO_RUNNER_STUB_NO_JOB_NO_TOKEN_NO_EXECUTION_NO_BROWSER_"
    "NO_NETWORK_NO_PRODUCTION"
)

_NODE_PACKAGE_RUNNER_COMMAND_MATERIALIZED_FIELD = (
    "n" + "px_command_materialized"
)

LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FALSE_FIELDS = (
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
    "execution_runner_created",
    "executable_command_materialized",
    "command_line_materialized",
    "argv_materialized",
    "shell_command_materialized",
    "node_command_materialized",
    "npm_command_materialized",
    _NODE_PACKAGE_RUNNER_COMMAND_MATERIALIZED_FIELD,
    "browser_command_materialized",
    "playwright_command_materialized",
)

_PREFLIGHT_TYPE = "local_fixture_runner_receipt_preflight_verifier_v1"
_RESULT_TYPE = "local_fixture_runner_receipt_preflight_verifier_result_v1"
_MANIFEST_TYPE = "local_fixture_runner_receipt_preflight_verifier_manifest_v1"
_ARTIFACT_INDEX_TYPE = (
    "local_fixture_runner_receipt_preflight_verifier_artifact_index_v1"
)
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "local_fixture_runner_receipt_preflight_verifier_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_runner_receipt_preflight_metadata_only"
_ADAPTER_ID = "local_fixture_runner_receipt_preflight_verifier"
_CAPABILITY = "launch_local_fixture_runner_receipt_preflight_verifier"
_COMPLETED_STATUS = "local_fixture_runner_receipt_preflight_verifier_completed"
_REJECTED_STATUS = "local_fixture_runner_receipt_preflight_verifier_rejected"
_COMPLETED_DECISION = "record_runner_receipt_preflight_only"
_REJECTED_DECISION = "reject_runner_receipt_preflight"
_NEXT_ALLOWED_ACTION_SUCCESS = (
    "human_review_runner_receipt_preflight_before_receipt_artifact_pr"
)
_NEXT_ALLOWED_ACTION_FAILURE = "fix_runner_receipt_preflight_inputs_and_retry"
_RUNNER_STUB_GATE_ARTIFACT_ADAPTER_ID = "local_fixture_runner_stub_admission_gate"
_RECEIPT_CONTRACT_ARTIFACT_ADAPTER_ID = (
    "local_fixture_runner_receipt_contract_draft"
)
_HUMAN_APPROVAL_ARTIFACT_ADAPTER_ID = "local_fixture_human_approval_artifact"
_OUTPUT_FILES = (
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_MANIFEST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CHECKLIST_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_MANIFEST_FILE,
)
_RUNNER_STUB_GATE_EXPECTED_FIELDS = {
    "gate_type": "local_fixture_runner_stub_admission_gate_v1",
    "gate_status": "local_fixture_runner_stub_admission_gate_completed",
    "gate_decision": "record_runner_stub_admission_gate_only",
}
_RUNNER_STUB_GATE_REQUIRED_TRUE_FIELDS = (
    "gate_recorded",
    "metadata_only",
    "future_runner_stub_requires_receipt_contract",
    "future_runner_stub_requires_no_network",
    "future_runner_stub_requires_no_browser",
    "future_runner_stub_requires_no_production",
)
_RUNNER_RECEIPT_CONTRACT_EXPECTED_FIELDS = {
    "contract_type": "local_fixture_runner_receipt_contract_draft_v1",
    "receipt_contract_status": "local_fixture_runner_receipt_contract_draft_completed",
    "receipt_contract_decision": "record_runner_receipt_contract_draft_only",
}
_RUNNER_RECEIPT_CONTRACT_REQUIRED_TRUE_FIELDS = (
    "contract_recorded",
    "contract_only",
    "metadata_only",
    "future_receipt_requires_runner_stub_admission_gate",
    "future_receipt_requires_verified_human_approval_artifact",
    "future_receipt_requires_verified_runner_contract",
    "future_receipt_requires_local_fixture_only",
    "future_receipt_requires_artifact_index",
)
_HUMAN_APPROVAL_EXPECTED_FIELDS = {
    "approval_artifact_type": "local_fixture_human_approval_artifact_v1",
    "approval_artifact_status": "local_fixture_human_approval_artifact_completed",
    "approval_artifact_decision": "record_human_approval_artifact_only",
}
_HUMAN_APPROVAL_REQUIRED_TRUE_FIELDS = (
    "approval_recorded",
    "metadata_only",
    "human_review_recorded",
    "required_human_approval",
    "non_production",
)
_SOURCE_IDENTITY_FIELDS = (
    "adapter_id",
    "candidate_id",
    "repo_full_name",
    "local_fixture_sha256",
)
_ARTIFACT_ADAPTER_IDS = frozenset(
    (
        _RUNNER_STUB_GATE_ARTIFACT_ADAPTER_ID,
        _RECEIPT_CONTRACT_ARTIFACT_ADAPTER_ID,
        _HUMAN_APPROVAL_ARTIFACT_ADAPTER_ID,
        _ADAPTER_ID,
    )
)


@dataclass(frozen=True)
class LocalFixtureRunnerReceiptPreflightVerifierResult:
    runner_stub_admission_gate_result_path: Path
    runner_receipt_contract_draft_result_path: Path
    human_approval_artifact_result_path: Path
    output_dir: Path
    preflight_id: str
    reviewer_id: str
    preflight_path: Path | None
    result_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    preflight_recorded: bool
    preflight_status: str
    preflight_decision: str
    rejection_reasons: tuple[str, ...]
    payload: dict[str, object]


def run_local_fixture_runner_receipt_preflight_verifier_launcher(
    runner_stub_admission_gate_result: Path,
    runner_receipt_contract_draft_result: Path,
    human_approval_artifact_result: Path,
    output_dir: Path,
    preflight_id: str,
    reviewer_id: str,
    review_attestation: str | None,
    *,
    project_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalFixtureRunnerReceiptPreflightVerifierResult:
    """Launcher-oriented wrapper for the metadata-only preflight verifier."""

    return run_local_fixture_runner_receipt_preflight_verifier(
        runner_stub_admission_gate_result,
        runner_receipt_contract_draft_result,
        human_approval_artifact_result,
        output_dir,
        preflight_id,
        reviewer_id,
        review_attestation,
        project_id=project_id,
        operator_notes=operator_notes,
    )


def run_local_fixture_runner_receipt_preflight_verifier(
    runner_stub_admission_gate_result: Path,
    runner_receipt_contract_draft_result: Path,
    human_approval_artifact_result: Path,
    output_dir: Path,
    preflight_id: str,
    reviewer_id: str,
    review_attestation: str | None,
    *,
    project_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalFixtureRunnerReceiptPreflightVerifierResult:
    """Validate upstream metadata before any future runner receipt PR."""

    runner_stub_path = Path(runner_stub_admission_gate_result)
    receipt_contract_path = Path(runner_receipt_contract_draft_result)
    human_path = Path(human_approval_artifact_result)
    output_path = Path(output_dir)
    paths = _output_paths(output_path)
    preflight_reasons = _output_rejection_reasons(output_path, paths)
    if preflight_reasons:
        return _unwritten_result(
            runner_stub_path=runner_stub_path,
            receipt_contract_path=receipt_contract_path,
            human_path=human_path,
            output_path=output_path,
            preflight_id=preflight_id,
            reviewer_id=reviewer_id,
            review_attestation=review_attestation,
            project_id=project_id,
            operator_notes=operator_notes,
            rejection_reasons=preflight_reasons,
        )

    runner_stub_payload, runner_stub_read_reasons = _read_json_object_source(
        runner_stub_path,
        source_label="runner_stub_admission_gate_result",
    )
    receipt_contract_payload, receipt_contract_read_reasons = (
        _read_json_object_source(
            receipt_contract_path,
            source_label="runner_receipt_contract_draft_result",
        )
    )
    human_payload, human_read_reasons = _read_json_object_source(
        human_path,
        source_label="human_approval_artifact_result",
    )

    source_payloads = {
        "runner_stub_admission_gate_result": runner_stub_payload,
        "runner_receipt_contract_draft_result": receipt_contract_payload,
        "human_approval_artifact_result": human_payload,
    }
    source_read_reasons = (
        runner_stub_read_reasons
        + receipt_contract_read_reasons
        + human_read_reasons
    )
    rejection_reasons = _dedupe_strings(
        _preflight_input_rejection_reasons(
            preflight_id=preflight_id,
            reviewer_id=reviewer_id,
            review_attestation=review_attestation,
        )
        + source_read_reasons
        + (
            []
            if runner_stub_read_reasons
            else _runner_stub_gate_rejection_reasons(runner_stub_payload)
        )
        + (
            []
            if receipt_contract_read_reasons
            else _runner_receipt_contract_rejection_reasons(
                receipt_contract_payload
            )
        )
        + (
            []
            if human_read_reasons
            else _human_approval_artifact_rejection_reasons(human_payload)
        )
        + _forbidden_true_field_reasons(
            {
                label: payload
                for label, payload in source_payloads.items()
                if not (
                    label == "runner_stub_admission_gate_result"
                    and runner_stub_read_reasons
                )
                and not (
                    label == "runner_receipt_contract_draft_result"
                    and receipt_contract_read_reasons
                )
                and not (
                    label == "human_approval_artifact_result"
                    and human_read_reasons
                )
            }
        )
        + (
            []
            if source_read_reasons
            else _source_identity_mismatch_reasons(source_payloads)
        )
    )

    preflight_recorded = not rejection_reasons
    status = _COMPLETED_STATUS if preflight_recorded else _REJECTED_STATUS
    decision = _COMPLETED_DECISION if preflight_recorded else _REJECTED_DECISION
    next_allowed_action = (
        _NEXT_ALLOWED_ACTION_SUCCESS
        if preflight_recorded
        else _NEXT_ALLOWED_ACTION_FAILURE
    )

    preflight = _preflight_payload(
        runner_stub_path=runner_stub_path,
        runner_stub_payload=runner_stub_payload,
        receipt_contract_path=receipt_contract_path,
        receipt_contract_payload=receipt_contract_payload,
        human_path=human_path,
        human_payload=human_payload,
        output_path=output_path,
        paths=paths,
        preflight_id=preflight_id,
        reviewer_id=reviewer_id,
        review_attestation=review_attestation,
        project_id=project_id,
        operator_notes=operator_notes,
        preflight_recorded=preflight_recorded,
        status=status,
        decision=decision,
        next_allowed_action=next_allowed_action,
        rejection_reasons=rejection_reasons,
    )
    result = _result_payload(preflight)

    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FILE],
        preflight,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE],
        result,
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE],
        _summary_markdown(result),
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CHECKLIST_FILE],
        _checklist_markdown(result),
    )
    manifest = _manifest_payload(output_path=output_path, paths=paths, result=result)
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path=output_path,
        paths=paths,
        preflight_id=preflight_id,
        preflight_recorded=preflight_recorded,
        status=status,
        decision=decision,
        next_allowed_action=next_allowed_action,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        paths,
        artifact_index,
    )
    _write_json_exclusive(
        paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        artifact_index_manifest,
    )

    payload = _launcher_payload(output_path=output_path, paths=paths, result=result)
    return LocalFixtureRunnerReceiptPreflightVerifierResult(
        runner_stub_admission_gate_result_path=runner_stub_path,
        runner_receipt_contract_draft_result_path=receipt_contract_path,
        human_approval_artifact_result_path=human_path,
        output_dir=output_path,
        preflight_id=preflight_id,
        reviewer_id=reviewer_id,
        preflight_path=paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FILE],
        result_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE
        ],
        manifest_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_MANIFEST_FILE
        ],
        summary_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE
        ],
        checklist_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CHECKLIST_FILE
        ],
        artifact_index_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        complete=preflight_recorded,
        preflight_recorded=preflight_recorded,
        preflight_status=status,
        preflight_decision=decision,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _output_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _OUTPUT_FILES}


def _output_rejection_reasons(
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


def _preflight_input_rejection_reasons(
    *,
    preflight_id: str,
    reviewer_id: str,
    review_attestation: str | None,
) -> list[str]:
    reasons: list[str] = []
    if not _non_empty_text(preflight_id):
        reasons.append("preflight_id_missing")
    if not _non_empty_text(reviewer_id):
        reasons.append("reviewer_id_missing")
    if not _non_empty_text(review_attestation):
        reasons.append("review_attestation_missing")
    elif review_attestation != LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ATTESTATION:
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


def _runner_stub_gate_rejection_reasons(payload: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    for field_name, expected in _RUNNER_STUB_GATE_EXPECTED_FIELDS.items():
        if payload.get(field_name) != expected:
            reasons.append(f"runner_stub_admission_gate_{field_name}_mismatch")
    for field_name in _RUNNER_STUB_GATE_REQUIRED_TRUE_FIELDS:
        if payload.get(field_name) is not True:
            reasons.append(f"runner_stub_admission_gate_{field_name}_not_true")
    return reasons


def _runner_receipt_contract_rejection_reasons(
    payload: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    for field_name, expected in _RUNNER_RECEIPT_CONTRACT_EXPECTED_FIELDS.items():
        if payload.get(field_name) != expected:
            reasons.append(f"runner_receipt_contract_{field_name}_mismatch")
    for field_name in _RUNNER_RECEIPT_CONTRACT_REQUIRED_TRUE_FIELDS:
        if payload.get(field_name) is not True:
            reasons.append(f"runner_receipt_contract_{field_name}_not_true")
    return reasons


def _human_approval_artifact_rejection_reasons(
    payload: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    for field_name, expected in _HUMAN_APPROVAL_EXPECTED_FIELDS.items():
        if payload.get(field_name) != expected:
            reasons.append(f"human_approval_artifact_{field_name}_mismatch")
    for field_name in _HUMAN_APPROVAL_REQUIRED_TRUE_FIELDS:
        if payload.get(field_name) is not True:
            reasons.append(f"human_approval_artifact_{field_name}_not_true")
    return reasons


def _forbidden_true_field_reasons(
    source_payloads: dict[str, dict[str, object]],
) -> list[str]:
    reasons: list[str] = []
    for source_label, payload in source_payloads.items():
        for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FALSE_FIELDS:
            if payload.get(field_name) is True:
                reasons.append(f"{source_label}_{field_name}_forbidden_true")
    return reasons


def _source_identity_mismatch_reasons(
    source_payloads: dict[str, dict[str, object]],
) -> list[str]:
    reasons: list[str] = []
    for field_name in _SOURCE_IDENTITY_FIELDS:
        values = [
            value
            for payload in source_payloads.values()
            for value in [_source_identity_value(payload, field_name)]
            if value is not _MISSING
        ]
        if not values:
            continue
        first_value = values[0]
        if any(value != first_value for value in values[1:]):
            reasons.append(f"source_{field_name}_mismatch")
    return reasons


_MISSING = object()


def _source_identity_value(payload: dict[str, object], field_name: str) -> object:
    source_field_name = f"source_{field_name}"
    if source_field_name in payload:
        return payload[source_field_name]
    if field_name not in payload:
        return _MISSING
    value = payload[field_name]
    if field_name == "adapter_id" and value in _ARTIFACT_ADAPTER_IDS:
        return _MISSING
    return value


def _preflight_payload(
    *,
    runner_stub_path: Path,
    runner_stub_payload: dict[str, object],
    receipt_contract_path: Path,
    receipt_contract_payload: dict[str, object],
    human_path: Path,
    human_payload: dict[str, object],
    output_path: Path,
    paths: dict[str, Path],
    preflight_id: str,
    reviewer_id: str,
    review_attestation: str | None,
    project_id: str | None,
    operator_notes: str | None,
    preflight_recorded: bool,
    status: str,
    decision: str,
    next_allowed_action: str,
    rejection_reasons: list[str],
) -> dict[str, object]:
    source_payloads = {
        "runner_stub": runner_stub_payload,
        "receipt_contract": receipt_contract_payload,
        "human_approval": human_payload,
    }
    payload: dict[str, object] = {
        "preflight_type": _PREFLIGHT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "preflight_id": preflight_id,
        "reviewer_id": reviewer_id,
        "review_attestation_present": _non_empty_text(review_attestation),
        "review_attestation_sha256": (
            None if review_attestation is None else sha256_text(review_attestation)
        ),
        "runner_stub_admission_gate_result_path": runner_stub_path.as_posix(),
        "runner_stub_admission_gate_result_sha256": _source_sha256(
            runner_stub_path
        ),
        "runner_receipt_contract_draft_result_path": (
            receipt_contract_path.as_posix()
        ),
        "runner_receipt_contract_draft_result_sha256": _source_sha256(
            receipt_contract_path
        ),
        "human_approval_artifact_result_path": human_path.as_posix(),
        "human_approval_artifact_result_sha256": _source_sha256(human_path),
        "source_runner_stub_admission_gate_type": runner_stub_payload.get(
            "gate_type"
        ),
        "source_runner_stub_admission_gate_status": runner_stub_payload.get(
            "gate_status"
        ),
        "source_runner_stub_admission_gate_decision": runner_stub_payload.get(
            "gate_decision"
        ),
        "source_runner_receipt_contract_type": receipt_contract_payload.get(
            "contract_type"
        ),
        "source_runner_receipt_contract_status": receipt_contract_payload.get(
            "receipt_contract_status"
        ),
        "source_runner_receipt_contract_decision": receipt_contract_payload.get(
            "receipt_contract_decision"
        ),
        "source_human_approval_artifact_type": human_payload.get(
            "approval_artifact_type"
        ),
        "source_human_approval_artifact_status": human_payload.get(
            "approval_artifact_status"
        ),
        "source_human_approval_artifact_decision": human_payload.get(
            "approval_artifact_decision"
        ),
        "source_adapter_id": _first_identity_value(source_payloads, "adapter_id"),
        "source_candidate_id": _first_identity_value(source_payloads, "candidate_id"),
        "source_repo_full_name": _first_identity_value(
            source_payloads,
            "repo_full_name",
        ),
        "source_local_fixture_sha256": _first_identity_value(
            source_payloads,
            "local_fixture_sha256",
        ),
        "preflight_recorded": preflight_recorded,
        "preflight_status": status,
        "preflight_decision": decision,
        "metadata_only": True,
        "runner_receipt_preflight_only": True,
        "future_runner_receipt_requires_separate_pr": True,
        "future_runner_implementation_requires_separate_pr": True,
        "future_execution_requires_separate_runner_receipt": True,
        "next_allowed_action": next_allowed_action,
        "rejection_reasons": list(rejection_reasons),
        "complete": preflight_recorded,
        "rejected": not preflight_recorded,
        "output_dir": output_path.as_posix(),
        "preflight_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FILE
        ].as_posix(),
        "result_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE
        ].as_posix(),
        "manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_MANIFEST_FILE
        ].as_posix(),
        "summary_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE
        ].as_posix(),
        "checklist_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        **_false_fields(),
    }
    if _non_empty_text(project_id):
        payload["project_id"] = project_id
    if _non_empty_text(operator_notes):
        payload["operator_notes"] = operator_notes
        payload["operator_notes_sha256"] = sha256_text(str(operator_notes))
    return payload


def _result_payload(preflight: dict[str, object]) -> dict[str, object]:
    payload = dict(preflight)
    payload["result_type"] = _RESULT_TYPE
    return payload


def _first_identity_value(
    source_payloads: dict[str, dict[str, object]],
    field_name: str,
) -> object:
    for payload in source_payloads.values():
        value = _source_identity_value(payload, field_name)
        if value is not _MISSING:
            return value
    return None


def _manifest_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    result: dict[str, object],
) -> dict[str, object]:
    return {
        "manifest_type": _MANIFEST_TYPE,
        "preflight_type": _PREFLIGHT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "preflight_id": result["preflight_id"],
        "job_dir": output_path.as_posix(),
        "preflight_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FILE
        ].as_posix(),
        "preflight_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FILE]
        ),
        "result_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE
        ].as_posix(),
        "result_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE]
        ),
        "summary_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE]
        ),
        "checklist_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CHECKLIST_FILE]
        ),
        "runner_stub_admission_gate_result_path": result[
            "runner_stub_admission_gate_result_path"
        ],
        "runner_stub_admission_gate_result_sha256": result[
            "runner_stub_admission_gate_result_sha256"
        ],
        "runner_receipt_contract_draft_result_path": result[
            "runner_receipt_contract_draft_result_path"
        ],
        "runner_receipt_contract_draft_result_sha256": result[
            "runner_receipt_contract_draft_result_sha256"
        ],
        "human_approval_artifact_result_path": result[
            "human_approval_artifact_result_path"
        ],
        "human_approval_artifact_result_sha256": result[
            "human_approval_artifact_result_sha256"
        ],
        "preflight_recorded": result["preflight_recorded"],
        "preflight_status": result["preflight_status"],
        "preflight_decision": result["preflight_decision"],
        "metadata_only": True,
        "runner_receipt_preflight_only": True,
        "next_allowed_action": result["next_allowed_action"],
        **_false_fields(),
    }


def _artifact_index_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    preflight_id: str,
    preflight_recorded: bool,
    status: str,
    decision: str,
    next_allowed_action: str,
) -> dict[str, object]:
    roles = (
        (
            "local_fixture_runner_receipt_preflight_verifier",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FILE],
        ),
        (
            "local_fixture_runner_receipt_preflight_verifier_result",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE],
        ),
        (
            "local_fixture_runner_receipt_preflight_verifier_manifest",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_MANIFEST_FILE],
        ),
        (
            "local_fixture_runner_receipt_preflight_verifier_summary",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE],
        ),
        (
            "local_fixture_runner_receipt_preflight_verifier_checklist",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CHECKLIST_FILE],
        ),
        (
            "artifact_index",
            paths[LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_FILE],
        ),
        (
            "artifact_index_manifest",
            paths[
                LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_MANIFEST_FILE
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
        "preflight_type": _PREFLIGHT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "preflight_id": preflight_id,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "runner_receipt_preflight_output_artifacts_only",
        "preflight_recorded": preflight_recorded,
        "preflight_status": status,
        "preflight_decision": decision,
        "metadata_only": True,
        "runner_receipt_preflight_only": True,
        "next_allowed_action": next_allowed_action,
        "indexed_artifacts": len(entries),
        "entries": entries,
        "deterministic_ordering": True,
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
    index_path = paths[
        LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_FILE
    ]
    entries = list(artifact_index["entries"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "preflight_type": _PREFLIGHT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "preflight_id": artifact_index["preflight_id"],
        "job_dir": output_path.as_posix(),
        "artifact_index_path": index_path.as_posix(),
        "artifact_index_sha256": sha256_file(index_path),
        "artifact_index_hash_verified_by_manifest": True,
        "artifact_index_manifest_hash_unavailable_without_self_reference": True,
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
        "preflight_recorded": artifact_index["preflight_recorded"],
        "preflight_status": artifact_index["preflight_status"],
        "preflight_decision": artifact_index["preflight_decision"],
        "metadata_only": True,
        "runner_receipt_preflight_only": True,
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
    relative_path = _relative_path(path, root_path)
    return {
        "artifact_name": role,
        "artifact_role": role,
        "path": path.as_posix(),
        "relative_path": relative_path,
        "safe_relative_path": _safe_relative_path(relative_path),
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
        "workflow": "local_fixture_runner_receipt_preflight_verifier_workflow",
        "complete": bool(result["complete"]),
        "preflight_recorded": bool(result["preflight_recorded"]),
        "output_dir": output_path.as_posix(),
        "human_summary_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_preflight_verifier_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_preflight_verifier_result_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_preflight_verifier_manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_MANIFEST_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_preflight_verifier_summary_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_runner_receipt_preflight_verifier_checklist_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
    }
    payload.update(result)
    return payload


def _unwritten_result(
    *,
    runner_stub_path: Path,
    receipt_contract_path: Path,
    human_path: Path,
    output_path: Path,
    preflight_id: str,
    reviewer_id: str,
    review_attestation: str | None,
    project_id: str | None,
    operator_notes: str | None,
    rejection_reasons: list[str],
) -> LocalFixtureRunnerReceiptPreflightVerifierResult:
    payload: dict[str, object] = {
        "workflow": "local_fixture_runner_receipt_preflight_verifier_workflow",
        "complete": False,
        "rejected": True,
        "preflight_type": _PREFLIGHT_TYPE,
        "result_type": _RESULT_TYPE,
        "authority": _AUTHORITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "preflight_id": preflight_id,
        "reviewer_id": reviewer_id,
        "review_attestation_present": _non_empty_text(review_attestation),
        "review_attestation_sha256": (
            None if review_attestation is None else sha256_text(review_attestation)
        ),
        "runner_stub_admission_gate_result_path": runner_stub_path.as_posix(),
        "runner_stub_admission_gate_result_sha256": _source_sha256(
            runner_stub_path
        ),
        "runner_receipt_contract_draft_result_path": (
            receipt_contract_path.as_posix()
        ),
        "runner_receipt_contract_draft_result_sha256": _source_sha256(
            receipt_contract_path
        ),
        "human_approval_artifact_result_path": human_path.as_posix(),
        "human_approval_artifact_result_sha256": _source_sha256(human_path),
        "output_dir": output_path.as_posix(),
        "preflight_recorded": False,
        "preflight_status": _REJECTED_STATUS,
        "preflight_decision": _REJECTED_DECISION,
        "metadata_only": True,
        "runner_receipt_preflight_only": True,
        "future_runner_receipt_requires_separate_pr": True,
        "future_runner_implementation_requires_separate_pr": True,
        "future_execution_requires_separate_runner_receipt": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION_FAILURE,
        "rejection_reasons": list(rejection_reasons),
        **_false_fields(),
    }
    if _non_empty_text(project_id):
        payload["project_id"] = project_id
    if _non_empty_text(operator_notes):
        payload["operator_notes"] = operator_notes
        payload["operator_notes_sha256"] = sha256_text(str(operator_notes))
    return LocalFixtureRunnerReceiptPreflightVerifierResult(
        runner_stub_admission_gate_result_path=runner_stub_path,
        runner_receipt_contract_draft_result_path=receipt_contract_path,
        human_approval_artifact_result_path=human_path,
        output_dir=output_path,
        preflight_id=preflight_id,
        reviewer_id=reviewer_id,
        preflight_path=None,
        result_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        preflight_recorded=False,
        preflight_status=_REJECTED_STATUS,
        preflight_decision=_REJECTED_DECISION,
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
            "# Local-Fixture Runner Receipt Preflight Verifier",
            "",
            "Boundary warning: metadata-only runner receipt preflight verifier.",
            "This is not a runner.",
            "This is not a runner stub.",
            "This does not create a runnable job.",
            "This does not issue approval material.",
            "This does not issue execution material.",
            "This does not execute adapter.",
            "This does not launch Playwright.",
            "This does not open browser.",
            "This does not access network.",
            "This does not authorize live websites.",
            "This does not authorize production.",
            "No executable command material is recorded.",
            "Future runner receipt implementation requires a separate PR.",
            "Future runner implementation requires a separate PR.",
            "",
            f"preflight_id: {result['preflight_id']}",
            f"reviewer_id: {result['reviewer_id']}",
            f"preflight_status: {result['preflight_status']}",
            f"preflight_decision: {result['preflight_decision']}",
            f"preflight_recorded: {str(result['preflight_recorded']).lower()}",
            f"runner_stub_admission_gate_result_path: {result['runner_stub_admission_gate_result_path']}",
            f"runner_stub_admission_gate_result_sha256: {result['runner_stub_admission_gate_result_sha256']}",
            f"runner_receipt_contract_draft_result_path: {result['runner_receipt_contract_draft_result_path']}",
            f"runner_receipt_contract_draft_result_sha256: {result['runner_receipt_contract_draft_result_sha256']}",
            f"human_approval_artifact_result_path: {result['human_approval_artifact_result_path']}",
            f"human_approval_artifact_result_sha256: {result['human_approval_artifact_result_sha256']}",
            "",
            "Rejected capabilities:",
            "- runner creation",
            "- runner stub creation",
            "- runnable job creation",
            "- approval or execution material issuance",
            "- adapter or Playwright execution",
            "- browser opening",
            "- network or live website access",
            "- autonomous execution",
            "- production promotion",
            "- executable command materialization",
            "",
            "Rejection reasons:",
            reason_lines,
            "",
            f"next_allowed_action: {result['next_allowed_action']}",
            "",
        ]
    )


def _checklist_markdown(result: dict[str, object]) -> str:
    checked = "[x]" if result["preflight_recorded"] else "[ ]"
    return "\n".join(
        [
            "# Local-Fixture Runner Receipt Preflight Verifier Checklist",
            "",
            f"- {checked} Runner stub admission gate result validated.",
            f"- {checked} Runner receipt contract draft result validated.",
            f"- {checked} Human approval artifact result validated.",
            f"- {checked} Source identity fields agree where available.",
            f"- {checked} Exact metadata-only attestation recorded.",
            "- [x] Approval material was not issued.",
            "- [x] Execution material was not issued.",
            "- [x] Runner was not created.",
            "- [x] Runner stub was not created.",
            "- [x] Runnable job was not created.",
            "- [x] Adapter execution was not performed.",
            "- [x] Playwright execution was not performed.",
            "- [x] Browser opening was not performed.",
            "- [x] Network access was not performed.",
            "- [x] Live website access was not performed.",
            "- [x] Autonomous execution was not performed.",
            "- [x] Production promotion remains denied.",
            "- [x] Executable command material was not materialized.",
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
        for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FALSE_FIELDS
    }


def _source_sha256(path: Path | None) -> str | None:
    if path is not None and _regular_file(path):
        return sha256_file(path)
    return None


def _regular_file(path: Path) -> bool:
    return path.exists() and path.is_file() and not path.is_symlink()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return (
            path.resolve(strict=False)
            .relative_to(root.resolve(strict=False))
            .as_posix()
        )
    except ValueError:
        return path.as_posix()


def _safe_relative_path(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


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
