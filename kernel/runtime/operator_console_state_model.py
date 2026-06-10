"""Operator console state model v1.

Defines a future UI-consumable cockpit state model without creating a UI
runtime. The model permits only structured actions and rejects raw command,
argv, executable path, cwd/env/path override, direct tool launch, file write,
network, browser, provider, or credential surfaces.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

__all__ = [
    "ALLOWED_UI_ACTION_TYPES",
    "FORBIDDEN_UI_ACTION_FIELDS",
    "REQUIRED_PANELS",
    "CandidateUIShell",
    "ConsoleActionAdmission",
    "ConsolePanelState",
    "OperatorConsoleState",
    "build_operator_console_state",
    "validate_console_action",
]

REQUIRED_PANELS = (
    "TASK_GRAPH",
    "WORKFLOW_LIBRARY",
    "TOOL_REGISTRY",
    "ASSET_BROWSER",
    "QUEUE",
    "APPROVAL_INBOX",
    "EVIDENCE_LEDGER",
    "REPLAY_VIEWER",
    "RISK_PANEL",
    "FAILURE_PANEL",
    "NEXT_ACTION_PANEL",
    "SUBSTRATE_CANDIDATE_PANEL",
    "SYSTEM_HEALTH",
)

ALLOWED_UI_ACTION_TYPES = (
    "task_intent",
    "command_id",
    "approval_decision",
    "risk_acknowledgement",
    "replay_request",
    "asset_query",
    "workflow_selection",
)

FORBIDDEN_UI_ACTION_FIELDS = frozenset(
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
        "direct_tool_launch",
        "launch_tool",
        "file_write",
        "file_write_path",
        "network",
        "browser",
        "provider",
        "provider_api",
        "credential",
        "secret",
    )
)

DANGEROUS_ACTION_TYPES = frozenset(("command_id",))


@dataclass(frozen=True)
class ConsolePanelState:
    panel_id: str
    enabled: bool
    read_only: bool
    data_contract: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateUIShell:
    candidate_id: str
    name: str
    role: str
    direct_dependency_allowed_now: bool
    runtime_integration_allowed_now: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OperatorConsoleState:
    model_version: str
    panels: tuple[ConsolePanelState, ...]
    allowed_action_types: tuple[str, ...]
    forbidden_action_fields: tuple[str, ...]
    candidate_ui_shells: tuple[CandidateUIShell, ...]
    production_autonomy_allowed: bool
    ui_runtime_present: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "model_version": self.model_version,
            "panels": [panel.as_dict() for panel in self.panels],
            "allowed_action_types": list(self.allowed_action_types),
            "forbidden_action_fields": list(self.forbidden_action_fields),
            "candidate_ui_shells": [shell.as_dict() for shell in self.candidate_ui_shells],
            "production_autonomy_allowed": self.production_autonomy_allowed,
            "ui_runtime_present": self.ui_runtime_present,
        }


@dataclass(frozen=True)
class ConsoleActionAdmission:
    accepted: bool
    action_type: str | None
    approval_required: bool
    failures: tuple[str, ...]


def build_operator_console_state() -> OperatorConsoleState:
    panels = tuple(
        ConsolePanelState(
            panel_id=panel_id,
            enabled=True,
            read_only=panel_id
            not in {"APPROVAL_INBOX", "NEXT_ACTION_PANEL", "RISK_PANEL"},
            data_contract=f"{panel_id.lower()}_state_v1",
        )
        for panel_id in REQUIRED_PANELS
    )
    return OperatorConsoleState(
        model_version="operator_console_state_model_v1",
        panels=panels,
        allowed_action_types=ALLOWED_UI_ACTION_TYPES,
        forbidden_action_fields=tuple(sorted(FORBIDDEN_UI_ACTION_FIELDS)),
        candidate_ui_shells=(
            CandidateUIShell(
                candidate_id="tauri",
                name="Tauri",
                role="candidate_future_desktop_shell",
                direct_dependency_allowed_now=False,
                runtime_integration_allowed_now=False,
            ),
        ),
        production_autonomy_allowed=False,
        ui_runtime_present=False,
    )


def validate_console_action(action: Mapping[str, object]) -> ConsoleActionAdmission:
    if not isinstance(action, Mapping):
        return ConsoleActionAdmission(False, None, False, ("action_must_be_mapping",))
    action_type = action.get("action_type")
    failures: list[str] = []
    if not isinstance(action_type, str) or action_type not in ALLOWED_UI_ACTION_TYPES:
        failures.append("action_type_not_allowed")
        action_type = None
    forbidden = _forbidden_fields(action)
    failures.extend(f"{field}_forbidden" for field in forbidden)
    approval_required = action_type in DANGEROUS_ACTION_TYPES
    if approval_required and action.get("approval_decision") != "APPROVED":
        failures.append("approval_required_for_dangerous_action")
    return ConsoleActionAdmission(
        accepted=not failures,
        action_type=action_type,
        approval_required=approval_required,
        failures=tuple(failures),
    )


def _forbidden_fields(payload: Mapping[str, object]) -> tuple[str, ...]:
    found: set[str] = set()
    for key, value in payload.items():
        normalized = str(key).lower()
        if normalized in FORBIDDEN_UI_ACTION_FIELDS:
            found.add(normalized)
        if isinstance(value, Mapping):
            found.update(_forbidden_fields(value))
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, Mapping):
                    found.update(_forbidden_fields(item))
    return tuple(sorted(found))
