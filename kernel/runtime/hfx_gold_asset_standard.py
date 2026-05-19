"""Deterministic HFX gold asset standard contract."""

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

__all__ = [
    "GOLD_ASSET_GATES",
    "HFXGoldAssetStandard",
    "build_hfx_gold_asset_standard",
    "default_hfx_gold_asset_standard_material",
    "render_hfx_gold_asset_standard_markdown",
]

_POLICY_VERSION = "hfx-gold-asset-standard-v1"
_CODE_VERSION = "0.1.0"
_GOLD_DECISIONS = ("gold_allowed", "gold_blocked")
_STRING_FIELDS = (
    "standard_id",
    "repository_url",
    "main_commit",
    "gold_status_decision",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = ("standard_notes", "blocked_claims")
_ALLOW_EMPTY_LISTS = ("blocked_claims",)

GOLD_ASSET_GATES: tuple[str, ...] = (
    "real_hip_or_hda_exists",
    "no_zero_byte_critical_files",
    "parameter_interface_documented",
    "input_contract_documented",
    "output_pass_contract_documented",
    "preview_proof_exists",
    "validation_report_exists",
    "manifest_exists",
    "checksum_exists",
    "shot_binding_exists",
    "render_comp_report_exists",
    "known_limitations_documented",
    "rollback_or_quarantine_route_exists",
    "external_asset_dependencies_declared",
    "no_unlicensed_third_party_raw_asset_dependency",
    "no_fake_film_grade_claim",
)

_GATE_DESCRIPTIONS = {
    "real_hip_or_hda_exists": "A real HIP/HDA reusable source exists in the repository.",
    "no_zero_byte_critical_files": "Critical source, manifest, and validation files are non-empty.",
    "parameter_interface_documented": "Artist/operator parameters are documented.",
    "input_contract_documented": "Inputs and per-shot derivation contract are documented.",
    "output_pass_contract_documented": "Outputs, passes, and comp handoff are documented.",
    "preview_proof_exists": "Preview proof exists without claiming final pixels.",
    "validation_report_exists": "Validation report exists and is tied to the asset.",
    "manifest_exists": "Release/package manifest exists.",
    "checksum_exists": "Checksum evidence exists.",
    "shot_binding_exists": "Shot binding or shot-bound template exists.",
    "render_comp_report_exists": "Render/comp contract or report exists.",
    "known_limitations_documented": "Known limitations are explicit.",
    "rollback_or_quarantine_route_exists": "Rollback, quarantine, or derive-only route exists.",
    "external_asset_dependencies_declared": "External asset dependency posture is declared.",
    "no_unlicensed_third_party_raw_asset_dependency": "No unlicensed raw third-party dependency is required.",
    "no_fake_film_grade_claim": "No film-grade/final-pixel claim is made without evidence.",
}


@dataclass(frozen=True)
class HFXGoldAssetStandard:
    """Repository-ready deterministic standard for gold asset claims."""

    standard_id: str
    repository_url: str
    main_commit: str
    gold_gates: dict[str, bool]
    standard_notes: tuple[object, ...]
    blocked_claims: tuple[object, ...]
    gold_status_decision: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_claims": list(self.blocked_claims),
            "code_version": self.code_version,
            "gold_gates": dict(sorted(self.gold_gates.items())),
            "gold_status_decision": self.gold_status_decision,
            "main_commit": self.main_commit,
            "policy_version": self.policy_version,
            "repository_url": self.repository_url,
            "standard_id": self.standard_id,
            "standard_notes": list(self.standard_notes),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def default_hfx_gold_asset_standard_material(
    *,
    repository_url: str,
    main_commit: str,
) -> dict[str, object]:
    """Return the deterministic baseline standard definition."""

    return {
        "standard_id": "hfx-gold-asset-standard-v1",
        "repository_url": repository_url,
        "main_commit": main_commit,
        "gold_gates": {gate: True for gate in GOLD_ASSET_GATES},
        "standard_notes": [_GATE_DESCRIPTIONS[gate] for gate in GOLD_ASSET_GATES],
        "blocked_claims": [
            "Gold status is blocked if any gate is false.",
            "Film-grade or final-pixel status is blocked unless independent evidence exists.",
            "Unlicensed third-party raw assets block gold status.",
        ],
        "gold_status_decision": "gold_allowed",
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
    }


def build_hfx_gold_asset_standard(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> HFXGoldAssetStandard:
    """Build a deterministic gold standard and reject unsafe gold claims."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="hfx_gold_asset_standard_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
    require_valid_choice(
        normalized["gold_status_decision"],
        field="gold_status_decision",
        allowed=_GOLD_DECISIONS,
    )
    gates = require_bool_gate_map(
        normalized.get("gold_gates"),
        field="gold_gates",
        required_gates=GOLD_ASSET_GATES,
    )
    if normalized["gold_status_decision"] == "gold_allowed" and not all_required_gates_true(gates, GOLD_ASSET_GATES):
        raise ValueError("incomplete_gate_blocks_gold")
    if normalized["gold_status_decision"] == "gold_allowed" and not gates["no_unlicensed_third_party_raw_asset_dependency"]:
        raise ValueError("external_unlicensed_dependency_blocks_gold")
    if normalized["gold_status_decision"] == "gold_allowed" and not gates["no_fake_film_grade_claim"]:
        raise ValueError("fake_film_grade_claim_blocks_gold")
    standard = HFXGoldAssetStandard(
        standard_id=normalized["standard_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        gold_gates=dict(sorted(gates.items())),
        standard_notes=tuple(normalized["standard_notes"]),
        blocked_claims=tuple(normalized["blocked_claims"]),
        gold_status_decision=normalized["gold_status_decision"],
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(standard, content_hash=compute_content_hash(standard.deterministic_material()))


def render_hfx_gold_asset_standard_markdown(standard: HFXGoldAssetStandard) -> str:
    """Render deterministic Markdown for the HFX gold asset standard."""

    if not isinstance(standard, HFXGoldAssetStandard):
        raise ValueError("standard_must_be_hfx_gold_asset_standard")
    return render_markdown(
        "HFX Gold Asset Standard",
        metadata_rows=(
            ("standard_id", standard.standard_id),
            ("repository_url", standard.repository_url),
            ("main_commit", standard.main_commit),
            ("gold_status_decision", standard.gold_status_decision),
            ("policy_version", standard.policy_version),
            ("code_version", standard.code_version),
            ("content_hash", standard.content_hash),
            ("observed_at", standard.observed_at),
        ),
        sections=(
            ("Hard Gates", dict(sorted(standard.gold_gates.items()))),
            ("Gate Definitions", dict(sorted(_GATE_DESCRIPTIONS.items()))),
            ("Standard Notes", list(standard.standard_notes)),
            ("Blocked Claims", list(standard.blocked_claims)),
            (
                "Claim Rule",
                "Gold status cannot be claimed unless every hard gate is true.",
            ),
        ),
    )
