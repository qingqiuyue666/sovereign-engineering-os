"""Deterministic research-only macro note contract."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import require_text_terms
from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    prepare_material,
    render_markdown,
    require_list_fields,
    require_string_fields,
)

__all__ = [
    "MacroResearchNote",
    "build_macro_research_note",
    "render_macro_research_note_markdown",
]

_POLICY_VERSION = "macro-research-note-v1"
_CODE_VERSION = "0.1.0"
_STRING_FIELDS = (
    "note_id",
    "research_domain",
    "thesis",
    "uncertainty_level",
    "manual_decision_boundary",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = (
    "evidence_items",
    "contradiction_items",
    "allowed_outputs",
    "forbidden_outputs",
    "no_trade_reasons",
    "blocked_capabilities",
)
_REQUIRED_FORBIDDEN_OUTPUTS = (
    "auto order execution",
    "broker/api execution",
    "leverage",
    "full-position instruction",
    "autonomous trading",
)


@dataclass(frozen=True)
class MacroResearchNote:
    """Repository-ready macro research note that cannot execute trades."""

    note_id: str
    research_domain: str
    thesis: str
    evidence_items: tuple[object, ...]
    contradiction_items: tuple[object, ...]
    uncertainty_level: str
    allowed_outputs: tuple[object, ...]
    forbidden_outputs: tuple[object, ...]
    no_trade_reasons: tuple[object, ...]
    manual_decision_boundary: str
    blocked_capabilities: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "allowed_outputs": list(self.allowed_outputs),
            "blocked_capabilities": list(self.blocked_capabilities),
            "code_version": self.code_version,
            "contradiction_items": list(self.contradiction_items),
            "evidence_items": list(self.evidence_items),
            "forbidden_outputs": list(self.forbidden_outputs),
            "manual_decision_boundary": self.manual_decision_boundary,
            "no_trade_reasons": list(self.no_trade_reasons),
            "note_id": self.note_id,
            "policy_version": self.policy_version,
            "research_domain": self.research_domain,
            "thesis": self.thesis,
            "uncertainty_level": self.uncertainty_level,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_macro_research_note(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> MacroResearchNote:
    """Build a deterministic macro research note from caller-provided material."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="macro_research_note_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS)
    require_text_terms(
        normalized["forbidden_outputs"],
        _REQUIRED_FORBIDDEN_OUTPUTS,
        error="forbidden_outputs_missing_required_boundary",
    )
    require_text_terms(
        normalized["manual_decision_boundary"],
        ("final decision remains manual",),
        error="manual_decision_boundary_missing_required_language",
    )

    note = MacroResearchNote(
        note_id=normalized["note_id"],
        research_domain=normalized["research_domain"],
        thesis=normalized["thesis"],
        evidence_items=tuple(normalized["evidence_items"]),
        contradiction_items=tuple(normalized["contradiction_items"]),
        uncertainty_level=normalized["uncertainty_level"],
        allowed_outputs=tuple(normalized["allowed_outputs"]),
        forbidden_outputs=tuple(normalized["forbidden_outputs"]),
        no_trade_reasons=tuple(normalized["no_trade_reasons"]),
        manual_decision_boundary=normalized["manual_decision_boundary"],
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(note, content_hash=compute_content_hash(note.deterministic_material()))


def render_macro_research_note_markdown(note: MacroResearchNote) -> str:
    """Render deterministic Markdown for a macro research note."""

    if not isinstance(note, MacroResearchNote):
        raise ValueError("note_must_be_macro_research_note")
    material = note.deterministic_material()
    return render_markdown(
        "Macro Research Note",
        metadata_rows=(
            ("note_id", note.note_id),
            ("research_domain", note.research_domain),
            ("uncertainty_level", note.uncertainty_level),
            ("policy_version", note.policy_version),
            ("code_version", note.code_version),
            ("content_hash", note.content_hash),
            ("observed_at", note.observed_at),
        ),
        sections=(
            ("Thesis", note.thesis),
            ("Evidence Items", material["evidence_items"]),
            ("Contradiction Items", material["contradiction_items"]),
            ("Allowed Outputs", material["allowed_outputs"]),
            ("Forbidden Outputs", material["forbidden_outputs"]),
            ("No-Trade Reasons", material["no_trade_reasons"]),
            ("Manual Decision Boundary", note.manual_decision_boundary),
            ("Blocked Capabilities", material["blocked_capabilities"]),
        ),
    )
