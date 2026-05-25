"""Human approval token v1.

Defines scoped, expiring, revocable approval artifacts for risky dry-run
actions. Approval decisions do not bypass command admission, tool risk
classification, raw-command prohibitions, or production-autonomy boundaries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Mapping
import hashlib
import json

__all__ = [
    "SUPPORTED_ACTION_TYPES",
    "ApprovalDecision",
    "ApprovalEvaluation",
    "HumanApprovalToken",
    "compute_approval_decision_hash",
    "compute_human_approval_token_hash",
    "create_approval_decision",
    "create_human_approval_token",
    "evaluate_human_approval",
]

SUPPORTED_ACTION_TYPES = frozenset(
    (
        "READ_PATH",
        "WRITE_PATH",
        "LAUNCH_PROCESS",
        "CALL_MCP_TOOL",
        "RUN_COMFYUI",
        "RUN_DCC_APP",
        "RUN_MODEL",
        "RUN_PLUGIN",
        "ACCESS_NETWORK",
        "CALL_PROVIDER",
        "BROWSER_CONTROL",
        "MUTATE_ASSET",
        "OVERWRITE_ARTIFACT",
        "DELETE",
        "RELEASE",
        "DRY_RUN_COMMAND_ID",
    )
)

HIGH_RISK_ACTION_TYPES = frozenset(
    (
        "WRITE_PATH",
        "LAUNCH_PROCESS",
        "CALL_MCP_TOOL",
        "RUN_COMFYUI",
        "RUN_DCC_APP",
        "RUN_MODEL",
        "RUN_PLUGIN",
        "ACCESS_NETWORK",
        "CALL_PROVIDER",
        "BROWSER_CONTROL",
        "MUTATE_ASSET",
        "OVERWRITE_ARTIFACT",
        "DELETE",
        "RELEASE",
        "DRY_RUN_COMMAND_ID",
    )
)

FORBIDDEN_APPROVAL_PAYLOAD_FIELDS = frozenset(
    (
        "raw_command",
        "command",
        "command_line",
        "argv",
        "args",
        "executable",
        "executable_path",
        "cwd",
        "workdir",
        "env",
        "environment",
        "path",
        "path_override",
        "credential",
        "secret",
        "provider_key",
        "bypass_router",
        "bypass_command_envelope_admission_router",
        "bypass_tool_risk_classifier",
        "production_autonomy",
    )
)


@dataclass(frozen=True)
class HumanApprovalToken:
    approval_id: str
    operator_id: str
    scope_id: str
    action_type: str
    target_id: str
    tool_id: str | None
    command_id: str | None
    workflow_id: str | None
    asset_root_id: str | None
    risk_class: str
    issued_at: str
    expires_at: str
    revoked: bool
    reason: str
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ApprovalDecision:
    approval_id: str
    accepted: bool
    rejection_reason: str | None
    decided_at: str
    operator_id: str
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ApprovalEvaluation:
    accepted: bool
    approval_id: str | None
    failures: tuple[str, ...]
    router_admission_still_required: bool
    tool_risk_classifier_still_required: bool
    production_autonomy_allowed: bool


def create_human_approval_token(
    *,
    approval_id: str,
    operator_id: str,
    scope_id: str,
    action_type: str,
    target_id: str,
    risk_class: str,
    issued_at: str,
    expires_at: str,
    reason: str,
    tool_id: str | None = None,
    command_id: str | None = None,
    workflow_id: str | None = None,
    asset_root_id: str | None = None,
    revoked: bool = False,
) -> HumanApprovalToken:
    fields = {
        "approval_id": approval_id,
        "operator_id": operator_id,
        "scope_id": scope_id,
        "action_type": action_type,
        "target_id": target_id,
        "tool_id": tool_id,
        "command_id": command_id,
        "workflow_id": workflow_id,
        "asset_root_id": asset_root_id,
        "risk_class": risk_class,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "revoked": revoked,
        "reason": reason,
    }
    return HumanApprovalToken(
        **fields,
        content_hash=compute_human_approval_token_hash(fields),
    )


def create_approval_decision(
    *,
    approval_id: str,
    accepted: bool,
    operator_id: str,
    decided_at: str,
    rejection_reason: str | None = None,
) -> ApprovalDecision:
    fields = {
        "approval_id": approval_id,
        "accepted": accepted,
        "rejection_reason": rejection_reason,
        "decided_at": decided_at,
        "operator_id": operator_id,
    }
    return ApprovalDecision(
        **fields,
        content_hash=compute_approval_decision_hash(fields),
    )


def evaluate_human_approval(
    token: HumanApprovalToken,
    *,
    action_type: str,
    target_id: str,
    decision: ApprovalDecision | None = None,
    now: str | None = None,
    payload: Mapping[str, object] | None = None,
) -> ApprovalEvaluation:
    failures: list[str] = []
    if not token.approval_id.strip():
        failures.append("approval_id_required")
    if not token.operator_id.strip():
        failures.append("operator_id_required")
    if not token.scope_id.strip():
        failures.append("scope_id_required")
    if token.action_type not in SUPPORTED_ACTION_TYPES:
        failures.append("action_type_not_supported")
    if token.action_type != action_type:
        failures.append("action_type_mismatch")
    if not token.target_id.strip():
        failures.append("target_id_required")
    if token.target_id != target_id:
        failures.append("target_id_mismatch")
    if not token.expires_at.strip():
        failures.append("expires_at_required")
    elif _is_expired(token.expires_at, now or _now()):
        failures.append("approval_expired")
    if token.revoked:
        failures.append("approval_revoked")

    forbidden_fields = _forbidden_fields(payload or {})
    failures.extend(f"{field}_forbidden" for field in forbidden_fields)

    high_risk = token.action_type in HIGH_RISK_ACTION_TYPES or token.risk_class == "HIGH_RISK"
    credential_touching = token.risk_class == "CREDENTIAL_TOUCHING" or any(
        field in forbidden_fields for field in ("credential", "secret", "provider_key")
    )
    if high_risk or credential_touching:
        failures.extend(_decision_failures(token, decision))
    if credential_touching and decision is None:
        failures.append("credential_access_requires_explicit_decision")

    return ApprovalEvaluation(
        accepted=not failures,
        approval_id=token.approval_id,
        failures=tuple(failures),
        router_admission_still_required=True,
        tool_risk_classifier_still_required=True,
        production_autonomy_allowed=False,
    )


def compute_human_approval_token_hash(fields: Mapping[str, object]) -> str:
    stable = {
        key: value
        for key, value in fields.items()
        if key not in {"issued_at", "expires_at", "content_hash"}
    }
    return _sha256(_canonical_json(stable))


def compute_approval_decision_hash(fields: Mapping[str, object]) -> str:
    stable = {
        key: value
        for key, value in fields.items()
        if key not in {"decided_at", "content_hash"}
    }
    return _sha256(_canonical_json(stable))


def _decision_failures(
    token: HumanApprovalToken,
    decision: ApprovalDecision | None,
) -> tuple[str, ...]:
    if decision is None:
        return ("accepted_decision_required_for_high_risk_action",)
    failures: list[str] = []
    if decision.approval_id != token.approval_id:
        failures.append("decision_approval_id_mismatch")
    if decision.operator_id != token.operator_id:
        failures.append("decision_operator_id_mismatch")
    if not decision.accepted:
        failures.append("decision_not_accepted")
    return tuple(failures)


def _forbidden_fields(payload: Mapping[str, object]) -> tuple[str, ...]:
    found: set[str] = set()
    for key, value in payload.items():
        normalized = str(key).lower()
        if normalized in FORBIDDEN_APPROVAL_PAYLOAD_FIELDS:
            found.add(normalized)
        if isinstance(value, Mapping):
            found.update(_forbidden_fields(value))
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, Mapping):
                    found.update(_forbidden_fields(item))
    return tuple(sorted(found))


def _is_expired(expires_at: str, now: str) -> bool:
    return _parse_datetime(now) >= _parse_datetime(expires_at)


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
