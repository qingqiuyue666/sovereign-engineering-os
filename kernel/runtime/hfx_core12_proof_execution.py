"""Deterministic HFX Core12 proof execution contract."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import contains_text
from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    prepare_material,
    render_markdown,
    require_list_fields,
    require_string_fields,
    require_valid_choice,
)
from kernel.runtime.hfx_core12_reality_audit import HFX_CORE12_ASSETS

__all__ = [
    "ACCEPTANCE_DECISIONS",
    "HFXCore12ProofExecution",
    "HFX_CORE12_PROOF_ASSET_IDS",
    "PROOF_STATUSES",
    "build_hfx_core12_proof_execution",
    "render_hfx_core12_proof_execution_markdown",
]

_POLICY_VERSION = "hfx-core12-proof-execution-v1"
_CODE_VERSION = "0.1.0"
PROOF_STATUSES: tuple[str, ...] = (
    "not_started",
    "package_created",
    "proof_planned",
    "proof_executed",
    "proof_reviewed",
    "accepted",
    "rejected",
    "blocked",
)
ACCEPTANCE_DECISIONS: tuple[str, ...] = (
    "accepted_for_internal_library",
    "accepted_pending_final_render",
    "accepted_pending_comp_review",
    "rejected",
    "blocked",
    "pending_execution",
)
_STRING_FIELDS = (
    "proof_run_id",
    "repository_url",
    "main_commit",
    "shot_proof_status",
    "render_proof_status",
    "comp_proof_status",
    "review_status",
    "acceptance_decision",
    "quarantine_decision",
    "rollback_decision",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = (
    "core12_assets",
    "per_asset_proof_package",
    "rejection_reasons",
    "remaining_gates",
)
_ALLOW_EMPTY_LISTS = ("rejection_reasons",)
_STATUS_FIELDS = (
    "shot_proof_status",
    "render_proof_status",
    "comp_proof_status",
    "review_status",
)
_PACKAGE_STRING_FIELDS = (
    "asset_id",
    "asset_name",
    "proof_package_status",
    "promotion_closure_path",
    "rollback_quarantine_route_path",
    "shot_render_proof_plan_path",
    "shot_proof_status",
    "render_proof_status",
    "comp_proof_status",
    "review_status",
    "acceptance_decision",
    "quarantine_trigger",
    "rollback_trigger",
)
_PACKAGE_OPTIONAL_STRING_FIELDS = (
    "proof_package_path",
    "proof_package_markdown_path",
    "promotion_status",
    "next_required_action",
    "remaining_gate",
)
_PACKAGE_LIST_FIELDS = (
    "expected_artifacts",
    "missing_proof_artifacts",
    "acceptance_criteria",
    "rejection_criteria",
)
_PACKAGE_OPTIONAL_LIST_FIELDS = (
    "minimum_shot_proof_checklist",
    "minimum_render_proof_checklist",
    "minimum_comp_review_checklist",
    "actual_proof_artifacts",
)
_PLANNED_STATUSES = frozenset({"not_started", "package_created", "proof_planned"})
_FINAL_ALLOWED_STATUSES = frozenset({"accepted", "proof_reviewed"})
_ACCEPTED_DECISIONS = frozenset(
    {"accepted_for_internal_library", "accepted_pending_final_render", "accepted_pending_comp_review"}
)
_UNSAFE_FINAL_CLAIM_MARKERS = (
    "film-grade complete",
    "film grade complete",
    "hollywood-grade complete",
    "hollywood grade complete",
    "hollywood final-pixel",
    "hollywood final pixel",
    "final-pixel complete",
    "final pixel complete",
    "final-pixel completion",
    "final pixel completion",
    "final render complete",
    "final comp complete",
    "production final pixels validated",
)
_FORBIDDEN_KEY_MARKERS = (
    "raw",
    "env",
    "secret",
    "credential",
    "token",
    "api_key",
    "password",
    "private_key",
    "authorization",
)
HFX_CORE12_PROOF_ASSET_IDS: tuple[str, ...] = tuple(asset["asset_id"] for asset in HFX_CORE12_ASSETS)
_ASSET_NAMES = {asset["asset_id"]: asset["asset_name"] for asset in HFX_CORE12_ASSETS}


@dataclass(frozen=True)
class HFXCore12ProofExecution:
    """Repository-ready deterministic Core12 proof execution package."""

    proof_run_id: str
    repository_url: str
    main_commit: str
    core12_assets: tuple[dict[str, object], ...]
    per_asset_proof_package: tuple[dict[str, object], ...]
    shot_proof_status: str
    render_proof_status: str
    comp_proof_status: str
    review_status: str
    acceptance_decision: str
    rejection_reasons: tuple[object, ...]
    quarantine_decision: str
    rollback_decision: str
    final_claim_allowed: bool
    remaining_gates: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "acceptance_decision": self.acceptance_decision,
            "code_version": self.code_version,
            "comp_proof_status": self.comp_proof_status,
            "core12_assets": [dict(asset) for asset in self.core12_assets],
            "final_claim_allowed": self.final_claim_allowed,
            "main_commit": self.main_commit,
            "per_asset_proof_package": [dict(package) for package in self.per_asset_proof_package],
            "policy_version": self.policy_version,
            "proof_run_id": self.proof_run_id,
            "quarantine_decision": self.quarantine_decision,
            "rejection_reasons": list(self.rejection_reasons),
            "remaining_gates": list(self.remaining_gates),
            "render_proof_status": self.render_proof_status,
            "repository_url": self.repository_url,
            "review_status": self.review_status,
            "rollback_decision": self.rollback_decision,
            "shot_proof_status": self.shot_proof_status,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_hfx_core12_proof_execution(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> HFXCore12ProofExecution:
    """Build a deterministic proof execution package and reject unsafe final claims."""

    _reject_forbidden_key_markers(material)
    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="hfx_core12_proof_execution_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
    for field in _STATUS_FIELDS:
        require_valid_choice(normalized[field], field=field, allowed=PROOF_STATUSES)
    require_valid_choice(
        normalized["acceptance_decision"],
        field="acceptance_decision",
        allowed=ACCEPTANCE_DECISIONS,
    )
    if not isinstance(normalized.get("final_claim_allowed"), bool):
        raise ValueError("final_claim_allowed_must_be_bool")
    if _contains_unsafe_final_claim(normalized):
        raise ValueError("unsafe_final_claim_blocks_proof_execution")

    core12_assets = _normalize_core12_assets(normalized["core12_assets"])
    proof_packages = _normalize_proof_packages(normalized["per_asset_proof_package"])
    _require_same_asset_set(core12_assets, proof_packages)
    _validate_planned_only_decision(normalized)
    _validate_external_dependency_acceptance(normalized["acceptance_decision"], proof_packages)
    _validate_final_claim_allowed(normalized, proof_packages)

    proof_execution = HFXCore12ProofExecution(
        proof_run_id=normalized["proof_run_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        core12_assets=tuple(core12_assets),
        per_asset_proof_package=tuple(proof_packages),
        shot_proof_status=normalized["shot_proof_status"],
        render_proof_status=normalized["render_proof_status"],
        comp_proof_status=normalized["comp_proof_status"],
        review_status=normalized["review_status"],
        acceptance_decision=normalized["acceptance_decision"],
        rejection_reasons=tuple(normalized["rejection_reasons"]),
        quarantine_decision=normalized["quarantine_decision"],
        rollback_decision=normalized["rollback_decision"],
        final_claim_allowed=normalized["final_claim_allowed"],
        remaining_gates=tuple(normalized["remaining_gates"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(
        proof_execution,
        content_hash=compute_content_hash(proof_execution.deterministic_material()),
    )


def render_hfx_core12_proof_execution_markdown(proof_execution: HFXCore12ProofExecution) -> str:
    """Render deterministic Markdown for the HFX Core12 proof execution package."""

    if not isinstance(proof_execution, HFXCore12ProofExecution):
        raise ValueError("proof_execution_must_be_hfx_core12_proof_execution")
    return render_markdown(
        "HFX Core12 Proof Execution Package",
        metadata_rows=(
            ("proof_run_id", proof_execution.proof_run_id),
            ("repository_url", proof_execution.repository_url),
            ("main_commit", proof_execution.main_commit),
            ("shot_proof_status", proof_execution.shot_proof_status),
            ("render_proof_status", proof_execution.render_proof_status),
            ("comp_proof_status", proof_execution.comp_proof_status),
            ("review_status", proof_execution.review_status),
            ("acceptance_decision", proof_execution.acceptance_decision),
            ("final_claim_allowed", proof_execution.final_claim_allowed),
            ("policy_version", proof_execution.policy_version),
            ("code_version", proof_execution.code_version),
            ("content_hash", proof_execution.content_hash),
            ("observed_at", proof_execution.observed_at),
        ),
        sections=(
            ("Core12 Assets", [dict(asset) for asset in proof_execution.core12_assets]),
            (
                "Per Asset Proof Packages",
                [dict(package) for package in proof_execution.per_asset_proof_package],
            ),
            ("Rejection Reasons", list(proof_execution.rejection_reasons)),
            ("Quarantine Decision", proof_execution.quarantine_decision),
            ("Rollback Decision", proof_execution.rollback_decision),
            ("Remaining Gates", list(proof_execution.remaining_gates)),
            (
                "Final Claim Rule",
                "final_claim_allowed requires accepted shot, render, and comp proof with reviewed acceptance and actual proof artifacts.",
            ),
        ),
    )


def _normalize_core12_assets(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise ValueError("core12_assets_must_be_nonempty_list")
    by_id: dict[str, dict[str, object]] = {}
    for row in value:
        if not isinstance(row, dict):
            raise ValueError("core12_asset_must_be_dict")
        asset_id = _required_string(row, "asset_id")
        asset_name = _required_string(row, "asset_name")
        _validate_asset_identity(asset_id, asset_name)
        if asset_id in by_id:
            raise ValueError(f"duplicate_asset:{asset_id}")
        normalized = {"asset_id": asset_id, "asset_name": asset_name}
        if "proof_package_path" in row:
            normalized["proof_package_path"] = _required_string(row, "proof_package_path")
        by_id[asset_id] = normalized
    if set(by_id) != set(HFX_CORE12_PROOF_ASSET_IDS):
        raise ValueError("core12_assets_must_list_all_12_assets")
    return [by_id[asset_id] for asset_id in HFX_CORE12_PROOF_ASSET_IDS]


def _normalize_proof_packages(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise ValueError("per_asset_proof_package_must_be_nonempty_list")
    by_id: dict[str, dict[str, object]] = {}
    for row in value:
        if not isinstance(row, dict):
            raise ValueError("per_asset_proof_package_entry_must_be_dict")
        normalized = _normalize_proof_package(row)
        asset_id = str(normalized["asset_id"])
        if asset_id in by_id:
            raise ValueError(f"duplicate_proof_package:{asset_id}")
        by_id[asset_id] = normalized
    if set(by_id) != set(HFX_CORE12_PROOF_ASSET_IDS):
        raise ValueError("per_asset_proof_package_must_list_all_12_assets")
    return [by_id[asset_id] for asset_id in HFX_CORE12_PROOF_ASSET_IDS]


def _normalize_proof_package(row: Mapping[str, object]) -> dict[str, object]:
    for field in _PACKAGE_STRING_FIELDS:
        _required_string(row, field)
    asset_id = str(row["asset_id"])
    asset_name = str(row["asset_name"])
    _validate_asset_identity(asset_id, asset_name)
    for field in ("proof_package_status", "shot_proof_status", "render_proof_status", "comp_proof_status", "review_status"):
        require_valid_choice(row[field], field=field, allowed=PROOF_STATUSES)
    require_valid_choice(row["acceptance_decision"], field="acceptance_decision", allowed=ACCEPTANCE_DECISIONS)
    if "final_claim_allowed" not in row or not isinstance(row["final_claim_allowed"], bool):
        raise ValueError("package_final_claim_allowed_must_be_bool")
    normalized: dict[str, object] = {
        field: str(row[field])
        for field in _PACKAGE_STRING_FIELDS
    }
    for field in _PACKAGE_OPTIONAL_STRING_FIELDS:
        if field in row:
            normalized[field] = _required_string(row, field)
    for field in _PACKAGE_LIST_FIELDS:
        normalized[field] = _required_string_list(row, field, allow_empty=False)
    for field in _PACKAGE_OPTIONAL_LIST_FIELDS:
        normalized[field] = _required_json_list(row, field, allow_empty=True)
    normalized["final_claim_allowed"] = row["final_claim_allowed"]
    normalized["external_asset_dependency_status"] = _normalize_external_asset_status(
        row.get("external_asset_dependency_status")
    )
    if _package_is_planned_only(normalized) and normalized["acceptance_decision"] != "pending_execution":
        raise ValueError("planned_only_package_requires_pending_execution")
    if (
        normalized["external_asset_dependency_status"]["unlicensed_external_dependency"] is True
        and normalized["acceptance_decision"] in _ACCEPTED_DECISIONS
    ):
        raise ValueError("unlicensed_external_dependency_blocks_acceptance")
    if normalized["final_claim_allowed"] is True:
        _validate_package_final_claim(normalized)
    return normalized


def _normalize_external_asset_status(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("external_asset_dependency_status_must_be_dict")
    status = _required_string(value, "status")
    declaration = _required_string(value, "declaration")
    if "unlicensed_external_dependency" not in value or not isinstance(
        value["unlicensed_external_dependency"], bool
    ):
        raise ValueError("unlicensed_external_dependency_must_be_bool")
    return {
        "declaration": declaration,
        "status": status,
        "unlicensed_external_dependency": value["unlicensed_external_dependency"],
    }


def _validate_asset_identity(asset_id: str, asset_name: str) -> None:
    if asset_id not in _ASSET_NAMES:
        raise ValueError(f"unknown_asset_id:{asset_id}")
    if _ASSET_NAMES[asset_id] != asset_name:
        raise ValueError(f"asset_name_mismatch:{asset_id}")


def _require_same_asset_set(core12_assets: list[dict[str, object]], packages: list[dict[str, object]]) -> None:
    asset_ids = [str(asset["asset_id"]) for asset in core12_assets]
    package_ids = [str(package["asset_id"]) for package in packages]
    if asset_ids != package_ids:
        raise ValueError("core12_assets_and_packages_must_match")


def _validate_planned_only_decision(material: Mapping[str, object]) -> None:
    statuses = [str(material[field]) for field in ("shot_proof_status", "render_proof_status", "comp_proof_status")]
    if all(status in _PLANNED_STATUSES for status in statuses) and material["acceptance_decision"] != "pending_execution":
        raise ValueError("planned_only_proof_requires_pending_execution")


def _validate_external_dependency_acceptance(
    acceptance_decision: str,
    proof_packages: list[dict[str, object]],
) -> None:
    has_unlicensed_dependency = any(
        package["external_asset_dependency_status"]["unlicensed_external_dependency"] is True
        for package in proof_packages
    )
    if has_unlicensed_dependency and acceptance_decision in _ACCEPTED_DECISIONS:
        raise ValueError("unlicensed_external_dependency_blocks_acceptance")


def _validate_final_claim_allowed(
    material: Mapping[str, object],
    proof_packages: list[dict[str, object]],
) -> None:
    if material["final_claim_allowed"] is False:
        if not material["remaining_gates"]:
            raise ValueError("remaining_gates_required_when_final_claim_blocked")
        return
    statuses = [str(material[field]) for field in ("shot_proof_status", "render_proof_status", "comp_proof_status")]
    if not all(status in _FINAL_ALLOWED_STATUSES for status in statuses):
        raise ValueError("proof_status_blocks_final_claim")
    if material["acceptance_decision"] != "accepted_for_internal_library":
        raise ValueError("explicit_internal_acceptance_required_for_final_claim")
    for package in proof_packages:
        _validate_package_final_claim(package)


def _validate_package_final_claim(package: Mapping[str, object]) -> None:
    statuses = [str(package[field]) for field in ("shot_proof_status", "render_proof_status", "comp_proof_status")]
    if not all(status in _FINAL_ALLOWED_STATUSES for status in statuses):
        raise ValueError("package_proof_status_blocks_final_claim")
    if package["acceptance_decision"] != "accepted_for_internal_library":
        raise ValueError("package_acceptance_required_for_final_claim")
    if package["missing_proof_artifacts"]:
        raise ValueError("missing_proof_artifacts_block_final_claim")
    if not _has_required_actual_artifacts(package["actual_proof_artifacts"]):
        raise ValueError("actual_shot_render_comp_artifacts_required_for_final_claim")


def _package_is_planned_only(package: Mapping[str, object]) -> bool:
    return all(
        str(package[field]) in _PLANNED_STATUSES
        for field in ("shot_proof_status", "render_proof_status", "comp_proof_status")
    )


def _has_required_actual_artifacts(value: object) -> bool:
    if not isinstance(value, list) or not value:
        return False
    artifact_types: set[str] = set()
    for artifact in value:
        if not isinstance(artifact, dict):
            continue
        artifact_type = artifact.get("artifact_type")
        artifact_path = artifact.get("artifact_path")
        if isinstance(artifact_type, str) and artifact_type and isinstance(artifact_path, str) and artifact_path:
            artifact_types.add(artifact_type)
    return {"shot", "render", "comp"}.issubset(artifact_types)


def _contains_unsafe_final_claim(value: object) -> bool:
    return any(contains_text(value, marker) for marker in _UNSAFE_FINAL_CLAIM_MARKERS)


def _reject_forbidden_key_markers(value: object, path: str = "material") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}_field_name_must_be_string")
            normalized = key.lower()
            if any(marker in normalized for marker in _FORBIDDEN_KEY_MARKERS):
                raise ValueError(f"forbidden_field:{path}.{key}")
            _reject_forbidden_key_markers(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_key_markers(child, f"{path}[{index}]")


def _required_string(row: Mapping[str, object], field: str) -> str:
    if field not in row or not isinstance(row[field], str) or not row[field]:
        raise ValueError(f"{field}_missing")
    return str(row[field])


def _required_string_list(row: Mapping[str, object], field: str, *, allow_empty: bool) -> list[str]:
    if field not in row:
        raise ValueError(f"{field}_missing")
    value = row[field]
    if not isinstance(value, list):
        raise ValueError(f"{field}_must_be_list")
    if not allow_empty and not value:
        raise ValueError(f"{field}_must_not_be_empty")
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{field}_must_be_string_list")
    return list(value)


def _required_json_list(row: Mapping[str, object], field: str, *, allow_empty: bool) -> list[object]:
    if field not in row:
        return []
    value = row[field]
    if not isinstance(value, list):
        raise ValueError(f"{field}_must_be_list")
    if not allow_empty and not value:
        raise ValueError(f"{field}_must_not_be_empty")
    return list(value)
