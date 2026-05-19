"""Deterministic HFX Core12 completion ledger."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

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
    "HFXCore12CompletionLedger",
    "build_hfx_core12_completion_ledger",
    "render_hfx_core12_completion_ledger_markdown",
]

_POLICY_VERSION = "hfx-core12-completion-ledger-v1"
_CODE_VERSION = "0.1.0"
_COMPLETION_DECISIONS = ("complete", "incomplete", "blocked", "audit_complete_assets_incomplete")
_STRING_FIELDS = (
    "ledger_id",
    "repository_url",
    "main_commit",
    "external_asset_policy",
    "completion_decision",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = (
    "core12_assets",
    "gold_assets",
    "production_candidates",
    "partial_candidates",
    "shell_only_assets",
    "blocked_assets",
    "next_required_actions",
)
_ALLOW_EMPTY_LISTS = (
    "gold_assets",
    "production_candidates",
    "partial_candidates",
    "shell_only_assets",
    "blocked_assets",
)


@dataclass(frozen=True)
class HFXCore12CompletionLedger:
    """Repository-ready deterministic HFX Core12 completion ledger."""

    ledger_id: str
    repository_url: str
    main_commit: str
    core12_assets: tuple[dict[str, object], ...]
    gold_assets: tuple[object, ...]
    production_candidates: tuple[object, ...]
    partial_candidates: tuple[object, ...]
    shell_only_assets: tuple[object, ...]
    blocked_assets: tuple[object, ...]
    external_asset_policy: str
    next_required_actions: tuple[object, ...]
    completion_decision: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_assets": list(self.blocked_assets),
            "code_version": self.code_version,
            "completion_decision": self.completion_decision,
            "core12_assets": [dict(asset) for asset in self.core12_assets],
            "external_asset_policy": self.external_asset_policy,
            "gold_assets": list(self.gold_assets),
            "ledger_id": self.ledger_id,
            "main_commit": self.main_commit,
            "next_required_actions": list(self.next_required_actions),
            "partial_candidates": list(self.partial_candidates),
            "policy_version": self.policy_version,
            "production_candidates": list(self.production_candidates),
            "repository_url": self.repository_url,
            "shell_only_assets": list(self.shell_only_assets),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_hfx_core12_completion_ledger(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> HFXCore12CompletionLedger:
    """Build a deterministic completion ledger and reject over-claimed completion."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="hfx_core12_completion_ledger_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
    require_valid_choice(
        normalized["completion_decision"],
        field="completion_decision",
        allowed=_COMPLETION_DECISIONS,
    )
    core12_assets = _normalize_ledger_assets(normalized["core12_assets"])
    if normalized["completion_decision"] == "complete" and not _all_assets_complete(core12_assets):
        raise ValueError("incomplete_asset_blocks_complete")
    if "deferred" not in normalized["external_asset_policy"].lower():
        raise ValueError("external_asset_policy_must_be_deferred")
    if "no github storage decision" not in normalized["external_asset_policy"].lower():
        raise ValueError("external_asset_policy_must_not_decide_github_storage")
    ledger = HFXCore12CompletionLedger(
        ledger_id=normalized["ledger_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        core12_assets=tuple(core12_assets),
        gold_assets=tuple(normalized["gold_assets"]),
        production_candidates=tuple(normalized["production_candidates"]),
        partial_candidates=tuple(normalized["partial_candidates"]),
        shell_only_assets=tuple(normalized["shell_only_assets"]),
        blocked_assets=tuple(normalized["blocked_assets"]),
        external_asset_policy=normalized["external_asset_policy"],
        next_required_actions=tuple(normalized["next_required_actions"]),
        completion_decision=normalized["completion_decision"],
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(ledger, content_hash=compute_content_hash(ledger.deterministic_material()))


def render_hfx_core12_completion_ledger_markdown(ledger: HFXCore12CompletionLedger) -> str:
    """Render deterministic Markdown for the HFX Core12 completion ledger."""

    if not isinstance(ledger, HFXCore12CompletionLedger):
        raise ValueError("ledger_must_be_hfx_core12_completion_ledger")
    return render_markdown(
        "HFX Core12 Completion Ledger",
        metadata_rows=(
            ("ledger_id", ledger.ledger_id),
            ("repository_url", ledger.repository_url),
            ("main_commit", ledger.main_commit),
            ("completion_decision", ledger.completion_decision),
            ("policy_version", ledger.policy_version),
            ("code_version", ledger.code_version),
            ("content_hash", ledger.content_hash),
            ("observed_at", ledger.observed_at),
        ),
        sections=(
            ("Core12 Assets", [dict(asset) for asset in ledger.core12_assets]),
            ("Gold Assets", list(ledger.gold_assets)),
            ("Production Candidates", list(ledger.production_candidates)),
            ("Partial Candidates", list(ledger.partial_candidates)),
            ("Shell Only Assets", list(ledger.shell_only_assets)),
            ("Blocked Assets", list(ledger.blocked_assets)),
            ("External Asset Policy", ledger.external_asset_policy),
            ("Next Required Actions", list(ledger.next_required_actions)),
            (
                "Completion Rule",
                "complete is allowed only when all 12 assets are gold_complete or production_complete with validated evidence.",
            ),
        ),
    )


def _normalize_ledger_assets(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise ValueError("core12_assets_must_be_nonempty_list")
    required_order = [asset["asset_id"] for asset in HFX_CORE12_ASSETS]
    by_id: dict[str, dict[str, object]] = {}
    for row in value:
        if not isinstance(row, dict):
            raise ValueError("core12_asset_must_be_dict")
        for field in ("asset_id", "asset_name", "completion_status"):
            if field not in row or not isinstance(row[field], str) or not row[field]:
                raise ValueError(f"{field}_missing")
        if "validated_evidence" not in row or not isinstance(row["validated_evidence"], bool):
            raise ValueError("validated_evidence_must_be_bool")
        asset_id = row["asset_id"]
        if asset_id in by_id:
            raise ValueError(f"duplicate_asset:{asset_id}")
        by_id[asset_id] = {
            "asset_id": row["asset_id"],
            "asset_name": row["asset_name"],
            "completion_status": row["completion_status"],
            "validated_evidence": row["validated_evidence"],
        }
    if list(sorted(by_id)) != list(sorted(required_order)):
        raise ValueError("core12_assets_must_list_all_12_assets")
    return [by_id[asset_id] for asset_id in required_order]


def _all_assets_complete(core12_assets: list[dict[str, object]]) -> bool:
    complete_states = {"gold_complete", "production_complete"}
    return all(
        asset.get("completion_status") in complete_states and asset.get("validated_evidence") is True
        for asset in core12_assets
    )
