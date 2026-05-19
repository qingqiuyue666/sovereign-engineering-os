"""Deterministic HFX Core12 promotion closure contract."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import all_required_gates_true, json_text
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
    "HFXCore12PromotionClosure",
    "HFX_CORE12_PROMOTION_ASSET_IDS",
    "PROMOTION_DECISIONS",
    "build_hfx_core12_promotion_closure",
    "render_hfx_core12_promotion_closure_markdown",
]

_POLICY_VERSION = "hfx-core12-promotion-closure-v1"
_CODE_VERSION = "0.1.0"
PROMOTION_DECISIONS: tuple[str, ...] = (
    "gold_complete",
    "production_complete",
    "production_complete_pending_shot_proof",
    "production_candidate",
    "partial_candidate",
    "shell_only",
    "blocked",
)
_REALITY_STATUSES = PROMOTION_DECISIONS + ("gold_candidate",)
_STRING_FIELDS = (
    "asset_id",
    "asset_name",
    "current_reality_status",
    "target_promotion_status",
    "promotion_decision",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = ("missing_gates", "next_required_actions")
_ALLOW_EMPTY_LISTS = ("missing_gates",)
_EVIDENCE_FIELDS = (
    "hip_or_hda_evidence",
    "preview_evidence",
    "validation_evidence",
    "checksum_evidence",
    "manifest_evidence",
    "shot_binding_evidence",
    "render_or_comp_evidence",
)
_INTERNAL_COMPLETE_GATES = (
    "hip_or_hda_evidence",
    "validation_evidence",
    "checksum_evidence",
    "manifest_evidence",
)
_GOLD_GATES = _EVIDENCE_FIELDS + ("rollback_route", "quarantine_route")
_CRITICAL_MISSING_GATES = {
    "critical_files_missing",
    "empty_critical_files",
    "unsafe_final_claim",
    "unlicensed_external_asset_dependency",
}
_UNSAFE_FINAL_CLAIM_MARKERS = (
    "film-grade complete",
    "hollywood-grade complete",
    "hollywood final-pixel",
    "final-pixel complete",
    "final pixel complete",
    "final shot complete",
    "final render complete",
    "final comp complete",
    "production final pixels validated",
)
HFX_CORE12_PROMOTION_ASSET_IDS: tuple[str, ...] = tuple(asset["asset_id"] for asset in HFX_CORE12_ASSETS)
_ASSET_NAMES = {asset["asset_id"]: asset["asset_name"] for asset in HFX_CORE12_ASSETS}


@dataclass(frozen=True)
class HFXCore12PromotionClosure:
    """Repository-ready deterministic promotion closure for one Core12 asset."""

    asset_id: str
    asset_name: str
    current_reality_status: str
    target_promotion_status: str
    hip_or_hda_evidence: dict[str, object]
    preview_evidence: dict[str, object]
    validation_evidence: dict[str, object]
    checksum_evidence: dict[str, object]
    manifest_evidence: dict[str, object]
    shot_binding_evidence: dict[str, object]
    render_or_comp_evidence: dict[str, object]
    rollback_route: dict[str, object]
    quarantine_route: dict[str, object]
    external_asset_dependency_status: dict[str, object]
    missing_gates: tuple[str, ...]
    next_required_actions: tuple[object, ...]
    promotion_decision: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "checksum_evidence": dict(self.checksum_evidence),
            "code_version": self.code_version,
            "current_reality_status": self.current_reality_status,
            "external_asset_dependency_status": dict(self.external_asset_dependency_status),
            "hip_or_hda_evidence": dict(self.hip_or_hda_evidence),
            "manifest_evidence": dict(self.manifest_evidence),
            "missing_gates": list(self.missing_gates),
            "next_required_actions": list(self.next_required_actions),
            "policy_version": self.policy_version,
            "preview_evidence": dict(self.preview_evidence),
            "promotion_decision": self.promotion_decision,
            "quarantine_route": dict(self.quarantine_route),
            "render_or_comp_evidence": dict(self.render_or_comp_evidence),
            "rollback_route": dict(self.rollback_route),
            "shot_binding_evidence": dict(self.shot_binding_evidence),
            "target_promotion_status": self.target_promotion_status,
            "validation_evidence": dict(self.validation_evidence),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_hfx_core12_promotion_closure(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> HFXCore12PromotionClosure:
    """Build a deterministic per-asset promotion closure and reject over-claims."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="hfx_core12_promotion_closure_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
    _validate_asset_identity(normalized["asset_id"], normalized["asset_name"])
    require_valid_choice(
        normalized["current_reality_status"],
        field="current_reality_status",
        allowed=_REALITY_STATUSES,
    )
    require_valid_choice(
        normalized["target_promotion_status"],
        field="target_promotion_status",
        allowed=PROMOTION_DECISIONS,
    )
    require_valid_choice(
        normalized["promotion_decision"],
        field="promotion_decision",
        allowed=PROMOTION_DECISIONS,
    )
    if normalized["target_promotion_status"] != normalized["promotion_decision"]:
        raise ValueError("target_promotion_status_must_match_decision")

    evidence = {field: _normalize_evidence(normalized.get(field), field=field) for field in _EVIDENCE_FIELDS}
    rollback_route = _normalize_route(normalized.get("rollback_route"), field="rollback_route")
    quarantine_route = _normalize_route(normalized.get("quarantine_route"), field="quarantine_route")
    external_status = _normalize_external_status(normalized.get("external_asset_dependency_status"))
    missing_gates = _normalize_missing_gates(
        normalized["missing_gates"],
        evidence=evidence,
        rollback_route=rollback_route,
        quarantine_route=quarantine_route,
        external_status=external_status,
        unsafe_final_claim=_contains_unsafe_final_claim(normalized),
    )
    _validate_decision(
        normalized["promotion_decision"],
        evidence=evidence,
        rollback_route=rollback_route,
        quarantine_route=quarantine_route,
        external_status=external_status,
        missing_gates=missing_gates,
    )

    closure = HFXCore12PromotionClosure(
        asset_id=normalized["asset_id"],
        asset_name=normalized["asset_name"],
        current_reality_status=normalized["current_reality_status"],
        target_promotion_status=normalized["target_promotion_status"],
        hip_or_hda_evidence=evidence["hip_or_hda_evidence"],
        preview_evidence=evidence["preview_evidence"],
        validation_evidence=evidence["validation_evidence"],
        checksum_evidence=evidence["checksum_evidence"],
        manifest_evidence=evidence["manifest_evidence"],
        shot_binding_evidence=evidence["shot_binding_evidence"],
        render_or_comp_evidence=evidence["render_or_comp_evidence"],
        rollback_route=rollback_route,
        quarantine_route=quarantine_route,
        external_asset_dependency_status=external_status,
        missing_gates=tuple(missing_gates),
        next_required_actions=tuple(normalized["next_required_actions"]),
        promotion_decision=normalized["promotion_decision"],
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(closure, content_hash=compute_content_hash(closure.deterministic_material()))


def render_hfx_core12_promotion_closure_markdown(closure: HFXCore12PromotionClosure) -> str:
    """Render deterministic Markdown for one Core12 promotion closure."""

    if not isinstance(closure, HFXCore12PromotionClosure):
        raise ValueError("closure_must_be_hfx_core12_promotion_closure")
    return render_markdown(
        f"{closure.asset_id} {closure.asset_name} Promotion Closure",
        metadata_rows=(
            ("asset_id", closure.asset_id),
            ("asset_name", closure.asset_name),
            ("current_reality_status", closure.current_reality_status),
            ("target_promotion_status", closure.target_promotion_status),
            ("promotion_decision", closure.promotion_decision),
            ("policy_version", closure.policy_version),
            ("code_version", closure.code_version),
            ("content_hash", closure.content_hash),
            ("observed_at", closure.observed_at),
        ),
        sections=(
            ("Current Evidence Summary", _evidence_summary(closure)),
            ("Rollback Route", dict(closure.rollback_route)),
            ("Quarantine Route", dict(closure.quarantine_route)),
            ("External Asset Dependency Declaration", dict(closure.external_asset_dependency_status)),
            ("Missing Gates", list(closure.missing_gates)),
            ("Next Required Actions", list(closure.next_required_actions)),
            (
                "Claim Boundary",
                "No final film-grade or Hollywood-grade status is asserted until reviewed shot/render/comp proof exists.",
            ),
        ),
    )


def _validate_asset_identity(asset_id: object, asset_name: object) -> None:
    if asset_id not in _ASSET_NAMES:
        raise ValueError("asset_id_must_be_core12_asset")
    if _ASSET_NAMES[asset_id] != asset_name:
        raise ValueError("asset_name_mismatch")


def _normalize_evidence(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{field}_must_be_dict")
    if "present" not in value or not isinstance(value["present"], bool):
        raise ValueError(f"{field}.present_must_be_bool")
    if "summary" not in value or not isinstance(value["summary"], str) or not value["summary"]:
        raise ValueError(f"{field}.summary_must_be_nonempty_string")
    paths = value.get("paths", [])
    if not isinstance(paths, list) or any(not isinstance(path, str) or not path for path in paths):
        raise ValueError(f"{field}.paths_must_be_string_list")
    return {
        "paths": sorted(paths),
        "present": value["present"],
        "summary": value["summary"],
    }


def _normalize_route(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{field}_must_be_dict")
    required = ("present", "route_id", "trigger", "action", "safe_state")
    for key in required:
        if key not in value:
            raise ValueError(f"{field}.{key}_missing")
    if not isinstance(value["present"], bool):
        raise ValueError(f"{field}.present_must_be_bool")
    normalized: dict[str, object] = {"present": value["present"]}
    for key in required[1:]:
        if not isinstance(value[key], str) or not value[key]:
            raise ValueError(f"{field}.{key}_must_be_nonempty_string")
        normalized[key] = value[key]
    return {
        "action": normalized["action"],
        "present": normalized["present"],
        "route_id": normalized["route_id"],
        "safe_state": normalized["safe_state"],
        "trigger": normalized["trigger"],
    }


def _normalize_external_status(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("external_asset_dependency_status_must_be_dict")
    required = ("status", "declaration", "unlicensed_external_dependency")
    for key in required:
        if key not in value:
            raise ValueError(f"external_asset_dependency_status.{key}_missing")
    if not isinstance(value["status"], str) or not value["status"]:
        raise ValueError("external_asset_dependency_status.status_must_be_nonempty_string")
    if not isinstance(value["declaration"], str) or not value["declaration"]:
        raise ValueError("external_asset_dependency_status.declaration_must_be_nonempty_string")
    if not isinstance(value["unlicensed_external_dependency"], bool):
        raise ValueError("external_asset_dependency_status.unlicensed_external_dependency_must_be_bool")
    return {
        "declaration": value["declaration"],
        "status": value["status"],
        "unlicensed_external_dependency": value["unlicensed_external_dependency"],
    }


def _normalize_missing_gates(
    value: object,
    *,
    evidence: Mapping[str, Mapping[str, object]],
    rollback_route: Mapping[str, object],
    quarantine_route: Mapping[str, object],
    external_status: Mapping[str, object],
    unsafe_final_claim: bool,
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("missing_gates_must_be_list")
    missing: list[str] = []
    for gate in value:
        if not isinstance(gate, str) or not gate:
            raise ValueError("missing_gates_must_be_string_list")
        if gate not in missing:
            missing.append(gate)
    for field in _EVIDENCE_FIELDS:
        if evidence[field]["present"] is not True and field not in missing:
            missing.append(field)
    if rollback_route["present"] is not True and "rollback_route" not in missing:
        missing.append("rollback_route")
    if quarantine_route["present"] is not True and "quarantine_route" not in missing:
        missing.append("quarantine_route")
    if external_status["unlicensed_external_dependency"] is True and "unlicensed_external_asset_dependency" not in missing:
        missing.append("unlicensed_external_asset_dependency")
    if unsafe_final_claim and "unsafe_final_claim" not in missing:
        missing.append("unsafe_final_claim")
    return missing


def _validate_decision(
    decision: str,
    *,
    evidence: Mapping[str, Mapping[str, object]],
    rollback_route: Mapping[str, object],
    quarantine_route: Mapping[str, object],
    external_status: Mapping[str, object],
    missing_gates: tuple[str, ...] | list[str],
) -> None:
    gate_states = {field: evidence[field]["present"] is True for field in _EVIDENCE_FIELDS}
    gate_states["rollback_route"] = rollback_route["present"] is True
    gate_states["quarantine_route"] = quarantine_route["present"] is True
    missing = set(missing_gates)
    if missing & _CRITICAL_MISSING_GATES and decision != "blocked":
        raise ValueError("critical_missing_gate_blocks_nonblocked_decision")
    if external_status["unlicensed_external_dependency"] is True and decision != "blocked":
        raise ValueError("unlicensed_external_dependency_blocks_nonblocked_decision")

    if decision == "gold_complete" and not all_required_gates_true(gate_states, _GOLD_GATES):
        raise ValueError("missing_gate_blocks_gold_complete")
    if decision == "production_complete" and not all_required_gates_true(
        gate_states,
        _INTERNAL_COMPLETE_GATES + ("render_or_comp_evidence", "rollback_route", "quarantine_route"),
    ):
        raise ValueError("missing_gate_blocks_production_complete")
    if decision == "production_complete_pending_shot_proof":
        required = _INTERNAL_COMPLETE_GATES + ("rollback_route", "quarantine_route")
        if not all_required_gates_true(gate_states, required):
            raise ValueError("missing_internal_gate_blocks_pending_shot_proof")
        if gate_states["render_or_comp_evidence"] is True:
            raise ValueError("pending_shot_proof_requires_missing_final_render_comp_proof")
    if decision == "production_candidate" and not any(gate_states.values()):
        raise ValueError("production_candidate_requires_some_evidence")
    if decision == "partial_candidate" and not any(gate_states[field] for field in _EVIDENCE_FIELDS):
        raise ValueError("partial_candidate_requires_some_asset_evidence")
    if decision == "shell_only" and gate_states["hip_or_hda_evidence"]:
        raise ValueError("shell_only_cannot_have_hip_or_hda_evidence")


def _contains_unsafe_final_claim(value: object) -> bool:
    text = json_text(value)
    return any(marker in text for marker in _UNSAFE_FINAL_CLAIM_MARKERS)


def _evidence_summary(closure: HFXCore12PromotionClosure) -> dict[str, object]:
    return {
        "checksum_evidence": dict(closure.checksum_evidence),
        "hip_or_hda_evidence": dict(closure.hip_or_hda_evidence),
        "manifest_evidence": dict(closure.manifest_evidence),
        "preview_evidence": dict(closure.preview_evidence),
        "render_or_comp_evidence": dict(closure.render_or_comp_evidence),
        "shot_binding_evidence": dict(closure.shot_binding_evidence),
        "validation_evidence": dict(closure.validation_evidence),
    }
