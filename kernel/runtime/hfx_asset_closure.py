"""Deterministic HFX asset closure contract."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import all_required_gates_true, require_bool_gate_map
from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    prepare_material,
    render_markdown,
    require_list_fields,
    require_string_fields,
    require_valid_choice,
)
from kernel.runtime.hfx_gold_asset_standard import GOLD_ASSET_GATES

__all__ = [
    "HFXAssetClosure",
    "build_hfx_asset_closure",
    "render_hfx_asset_closure_markdown",
]

_POLICY_VERSION = "hfx-asset-closure-v1"
_CODE_VERSION = "0.1.0"
_ALLOWED_STATUS = ("gold_complete", "production_candidate", "partial_candidate", "blocked")
_STRING_FIELDS = (
    "closure_id",
    "asset_id",
    "asset_name",
    "repository_url",
    "main_commit",
    "closure_status",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = ("evidence_notes", "boundary_conditions")
_PRODUCTION_GATES = ("real_hip_or_hda_exists", "validation_report_exists")


@dataclass(frozen=True)
class HFXAssetClosure:
    """Repository-ready deterministic closure for one HFX asset."""

    closure_id: str
    asset_id: str
    asset_name: str
    repository_url: str
    main_commit: str
    closure_status: str
    evidence_gates: dict[str, bool]
    missing_gates: tuple[str, ...]
    evidence_notes: tuple[object, ...]
    boundary_conditions: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "boundary_conditions": list(self.boundary_conditions),
            "closure_id": self.closure_id,
            "closure_status": self.closure_status,
            "code_version": self.code_version,
            "evidence_gates": dict(sorted(self.evidence_gates.items())),
            "evidence_notes": list(self.evidence_notes),
            "main_commit": self.main_commit,
            "missing_gates": list(self.missing_gates),
            "policy_version": self.policy_version,
            "repository_url": self.repository_url,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_hfx_asset_closure(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> HFXAssetClosure:
    """Build a deterministic HFX asset closure and reject unsafe status claims."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="hfx_asset_closure_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS)
    require_valid_choice(normalized["closure_status"], field="closure_status", allowed=_ALLOWED_STATUS)
    gates = require_bool_gate_map(
        normalized.get("evidence_gates"),
        field="evidence_gates",
        required_gates=GOLD_ASSET_GATES,
    )
    missing_gates = tuple(gate for gate in GOLD_ASSET_GATES if gates.get(gate) is not True)
    if normalized["closure_status"] == "gold_complete" and missing_gates:
        raise ValueError("missing_evidence_gate_blocks_gold_complete")
    if normalized["closure_status"] == "production_candidate" and not all_required_gates_true(gates, _PRODUCTION_GATES):
        raise ValueError("production_candidate_missing_required_evidence")
    if normalized["closure_status"] == "partial_candidate" and not (
        gates.get("real_hip_or_hda_exists") or gates.get("manifest_exists") or gates.get("validation_report_exists")
    ):
        raise ValueError("partial_candidate_missing_minimum_evidence")
    closure = HFXAssetClosure(
        closure_id=normalized["closure_id"],
        asset_id=normalized["asset_id"],
        asset_name=normalized["asset_name"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        closure_status=normalized["closure_status"],
        evidence_gates=dict(sorted(gates.items())),
        missing_gates=missing_gates,
        evidence_notes=tuple(normalized["evidence_notes"]),
        boundary_conditions=tuple(normalized["boundary_conditions"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(closure, content_hash=compute_content_hash(closure.deterministic_material()))


def render_hfx_asset_closure_markdown(closure: HFXAssetClosure) -> str:
    """Render deterministic Markdown for one HFX asset closure."""

    if not isinstance(closure, HFXAssetClosure):
        raise ValueError("closure_must_be_hfx_asset_closure")
    return render_markdown(
        f"{closure.asset_id} {closure.asset_name} Closure",
        metadata_rows=(
            ("closure_id", closure.closure_id),
            ("asset_id", closure.asset_id),
            ("asset_name", closure.asset_name),
            ("repository_url", closure.repository_url),
            ("main_commit", closure.main_commit),
            ("closure_status", closure.closure_status),
            ("policy_version", closure.policy_version),
            ("code_version", closure.code_version),
            ("content_hash", closure.content_hash),
            ("observed_at", closure.observed_at),
        ),
        sections=(
            ("Evidence Gates", dict(sorted(closure.evidence_gates.items()))),
            ("Missing Gates", list(closure.missing_gates)),
            ("Evidence Notes", list(closure.evidence_notes)),
            ("Boundary Conditions", list(closure.boundary_conditions)),
            (
                "Gold Rule",
                "gold_complete is allowed only when every HFX gold asset gate is true.",
            ),
        ),
    )
