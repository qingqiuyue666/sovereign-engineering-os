"""Truthful optional adapter contracts for non-default creative tools."""

from __future__ import annotations

from pathlib import Path
from typing import Final
import json

from creative.common import SCHEMA_VERSION, sanitize_path, write_json
from creative.software.doctor import run_doctor

OPTIONAL_ADAPTERS: Final[tuple[str, ...]] = (
    "blender",
    "after_effects",
    "davinci",
    "unreal",
    "zbrush",
)

READY_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "FOUND_AND_SMOKE_PASSED",
        "FOUND_BUT_UNTESTED",
        "FOUND_BUT_REQUIRES_USER_LAUNCH",
    }
)

ADAPTER_META: Final[dict[str, dict[str, object]]] = {
    "blender": {
        "label": "Blender",
        "level": "LEVEL_2_SMOKE_TEST",
        "summary": "Background Python smoke and staged preview contracts only.",
        "required_operator_inputs": ["blender executable path", "blend file or generated fixture scene", "output root"],
        "next_local_proof": "fixed blender --background smoke script that writes version and scene summary JSON",
        "risk_notes": ["addon side effects", "GPU/headless instability", "long render runtime"],
        "artifacts": [
            "creative/adapters/blender/adapter.py",
            "creative/adapters/blender/background_runner.py",
            "creative/adapters/blender/preview_render.py",
            "creative/adapters/blender/asset_check.py",
        ],
    },
    "after_effects": {
        "label": "After Effects",
        "level": "LEVEL_1_DRY_RUN",
        "summary": "Aerender and JSX contract planning only.",
        "required_operator_inputs": ["After Effects app path", "approved fixture project", "output root"],
        "next_local_proof": "fixed aerender or app-version smoke with no arbitrary JSX and no project mutation",
        "risk_notes": ["GUI launch side effects", "plugin licensing", "project/plugin compatibility"],
        "artifacts": [
            "creative/adapters/after_effects/adapter.py",
            "creative/adapters/after_effects/aerender_contract.py",
            "creative/adapters/after_effects/jsx_contract.py",
            "creative/adapters/after_effects/plugin_dependency_check.py",
        ],
    },
    "davinci": {
        "label": "DaVinci Resolve",
        "level": "LEVEL_1_DRY_RUN",
        "summary": "Scripting and render-job manifest contracts only.",
        "required_operator_inputs": ["Resolve scripting availability", "project or timeline manifest", "delivery output root"],
        "next_local_proof": "read-only Resolve scripting smoke that reports version and project access without rendering",
        "risk_notes": ["GUI session dependence", "project database mutation", "codec/license availability"],
        "artifacts": [
            "creative/adapters/davinci/adapter.py",
            "creative/adapters/davinci/scripting_contract.py",
            "creative/adapters/davinci/project_manifest.py",
            "creative/adapters/davinci/render_job_manifest.py",
        ],
    },
    "unreal": {
        "label": "Unreal Engine",
        "level": "LEVEL_1_DRY_RUN",
        "summary": "Commandlet, Sequencer, and MRQ manifest contracts only.",
        "required_operator_inputs": ["UnrealEditor path", "uproject path", "map or sequence identifier", "output root"],
        "next_local_proof": "fixed UnrealEditor commandlet help/version smoke with no project save",
        "risk_notes": ["project upgrade prompts", "shader compilation runtime", "plugin/license mismatch"],
        "artifacts": [
            "creative/adapters/unreal/adapter.py",
            "creative/adapters/unreal/commandlet_contract.py",
            "creative/adapters/unreal/mrq_manifest.py",
            "creative/adapters/unreal/sequencer_manifest.py",
        ],
    },
    "zbrush": {
        "label": "ZBrush",
        "level": "LEVEL_0_REGISTRY_ONLY",
        "summary": "Registry, export-manifest, and manual handoff contracts only.",
        "required_operator_inputs": ["sculpt registry entry", "export manifest", "manual handoff checklist"],
        "next_local_proof": "manual export handoff verification; no default automated ZBrush runner",
        "risk_notes": ["limited stable headless automation", "manual save/export risk", "license/UI dependence"],
        "artifacts": [
            "creative/adapters/zbrush/adapter.py",
            "creative/adapters/zbrush/sculpt_registry.py",
            "creative/adapters/zbrush/export_manifest.py",
            "creative/adapters/zbrush/handoff_checklist.py",
        ],
    },
}

ALLOWED_ACTIONS: Final[tuple[str, ...]] = (
    "detect_local_configuration",
    "validate_environment_metadata",
    "build_dry_run_plan",
    "build_manual_handoff_checklist",
    "collect_digest_only_evidence",
    "write_contract_report",
)

DISALLOWED_ACTIONS: Final[tuple[str, ...]] = (
    "launch_dcc_application",
    "submit_render_or_generation_job",
    "mutate_project_file",
    "install_plugins_or_models",
    "checkout_license_by_default",
    "use_external_network",
    "claim_live_execution_without_runner_evidence",
)


def build_optional_adapter_contracts(
    doctor_report: dict[str, object] | None = None,
    *,
    mode: str = "public",
    output_json: Path | None = None,
    output_markdown: Path | None = None,
) -> dict[str, object]:
    if mode not in {"public", "local"}:
        raise ValueError("mode must be public or local")

    report = dict(doctor_report if doctor_report is not None else run_doctor())
    software = dict(report.get("software", {}))
    adapters = [
        _adapter_contract(adapter, dict(software.get(adapter, {})), mode=mode)
        for adapter in OPTIONAL_ADAPTERS
    ]
    summary = _summary(adapters)
    payload = {
        "adapters": adapters,
        "default_ci_requires_proprietary_tools": False,
        "dcc_or_ai_tools_launched": False,
        "destructive_actions_performed": bool(report.get("destructive_actions_performed", False)),
        "kind": "optional_adapter_contracts_v1",
        "mode": mode,
        "next_actions": _next_actions(adapters),
        "ok": True,
        "read_only": True,
        "schema_version": SCHEMA_VERSION,
        "summary": summary,
    }
    outputs: dict[str, str] = {}
    if output_json is not None:
        write_json(output_json, payload)
        outputs["json"] = output_json.as_posix()
    if output_markdown is not None:
        output_markdown.parent.mkdir(parents=True, exist_ok=True)
        output_markdown.write_text(render_optional_adapter_contracts_markdown(payload), encoding="utf-8")
        outputs["markdown"] = output_markdown.as_posix()
    payload["outputs"] = outputs
    return payload


def render_optional_adapter_contracts_markdown(report: dict[str, object]) -> str:
    summary = dict(report.get("summary", {}))
    lines = [
        "# SEOS Optional Adapter Contracts V1",
        "",
        f"- Mode: `{report.get('mode')}`",
        f"- Read-only: `{report.get('read_only')}`",
        f"- DCC or AI tools launched: `{report.get('dcc_or_ai_tools_launched')}`",
        f"- Default CI requires proprietary tools: `{report.get('default_ci_requires_proprietary_tools')}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in (
        "adapter_count",
        "execution_supported_count",
        "ready_for_manual_dry_run_count",
        "config_required_count",
        "env_not_found_count",
        "contract_only_count",
    ):
        lines.append(f"| {key} | {summary.get(key, 0)} |")

    lines.extend(
        [
            "",
            "## Contracts",
            "",
            "| Adapter | Status | Discovery | Execution | Next local proof |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for adapter in report.get("adapters", []):
        item = dict(adapter)
        discovery = dict(item.get("discovery", {}))
        lines.append(
            "| "
            f"{item.get('label')} | "
            f"`{item.get('contract_status')}` | "
            f"`{discovery.get('status')}` | "
            f"`{item.get('execution_support')}` | "
            f"{_markdown_cell(item.get('next_local_proof'))} |"
        )

    lines.extend(["", "## Adapter Details", ""])
    for adapter in report.get("adapters", []):
        item = dict(adapter)
        lines.extend(
            [
                f"### {item.get('label')}",
                "",
                f"- Adapter: `{item.get('adapter')}`",
                f"- Current level: `{item.get('current_level')}`",
                f"- Summary: {item.get('summary')}",
                f"- Supports execute: `{item.get('supports_execute')}`",
                f"- Required operator inputs: {', '.join(str(value) for value in item.get('required_operator_inputs', []))}",
                f"- Existing artifacts: {', '.join(str(artifact.get('path')) for artifact in item.get('existing_artifacts', []))}",
                f"- Risk notes: {', '.join(str(value) for value in item.get('risk_notes', []))}",
                "",
            ]
        )

    lines.extend(
        [
            "## Safety",
            "",
            "- These contracts do not launch DCC applications.",
            "- These contracts do not submit render, generation, import, export, or commandlet jobs.",
            "- These contracts do not install plugins, download models, or use external networks.",
            "- Future runners require separate approval-gated slices and real local evidence.",
            "",
            "## Next Actions",
            "",
        ]
    )
    for action in report.get("next_actions", []):
        lines.append(f"- {action}")
    lines.append("")
    return "\n".join(lines)


def _adapter_contract(adapter: str, discovery: dict[str, object], *, mode: str) -> dict[str, object]:
    meta = dict(ADAPTER_META[adapter])
    status = str(discovery.get("status", "CONFIG_REQUIRED"))
    return {
        "adapter": adapter,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "contract_status": _contract_status(status),
        "current_level": meta["level"],
        "disallowed_actions": list(DISALLOWED_ACTIONS),
        "discovery": {
            "configured_path": _report_path(discovery.get("path", ""), mode=mode),
            "status": status,
            "version": str(discovery.get("version", "")),
        },
        "execution_support": "CONTRACT_ONLY",
        "existing_artifacts": _existing_artifacts(meta.get("artifacts", [])),
        "label": meta["label"],
        "next_local_proof": meta["next_local_proof"],
        "required_operator_inputs": list(meta["required_operator_inputs"]),
        "risk_notes": list(meta["risk_notes"]),
        "summary": meta["summary"],
        "supports_execute": False,
    }


def _contract_status(discovery_status: str) -> str:
    if discovery_status in READY_STATUSES:
        return "READY_FOR_MANUAL_DRY_RUN"
    if discovery_status == "CONFIG_REQUIRED":
        return "CONFIG_REQUIRED"
    if discovery_status in {"NOT_FOUND", "ENV_NOT_FOUND"}:
        return "ENV_NOT_FOUND"
    return "CONTRACT_ONLY"


def _existing_artifacts(paths: object) -> list[dict[str, object]]:
    artifacts: list[dict[str, object]] = []
    for value in list(paths) if isinstance(paths, list) else []:
        path = Path(str(value))
        artifacts.append(
            {
                "exists": path.is_file(),
                "path": path.as_posix(),
                "role": "contract_or_manifest",
            }
        )
    return artifacts


def _summary(adapters: list[dict[str, object]]) -> dict[str, int]:
    statuses = [str(adapter.get("contract_status", "")) for adapter in adapters]
    return {
        "adapter_count": len(adapters),
        "config_required_count": statuses.count("CONFIG_REQUIRED"),
        "contract_only_count": statuses.count("CONTRACT_ONLY"),
        "env_not_found_count": statuses.count("ENV_NOT_FOUND"),
        "execution_supported_count": sum(1 for adapter in adapters if adapter.get("supports_execute")),
        "ready_for_manual_dry_run_count": statuses.count("READY_FOR_MANUAL_DRY_RUN"),
    }


def _next_actions(adapters: list[dict[str, object]]) -> list[str]:
    actions: list[str] = []
    for adapter in adapters:
        status = adapter.get("contract_status")
        label = adapter.get("label")
        if status == "READY_FOR_MANUAL_DRY_RUN":
            actions.append(f"{label}: review contract and run only manual dry-run/handoff steps.")
        elif status == "CONFIG_REQUIRED":
            actions.append(f"{label}: configure local path or scripting settings before any smoke runner.")
        elif status == "ENV_NOT_FOUND":
            actions.append(f"{label}: install or expose the tool before adapter smoke work.")
        else:
            actions.append(f"{label}: keep contract-only until a separate runner slice is proven.")
    return actions


def _report_path(path: object, *, mode: str) -> str:
    if not path:
        return ""
    return str(path) if mode == "local" else sanitize_path(path)


def _markdown_cell(value: object) -> str:
    text = str(value or "")
    if "|" in text:
        text = text.replace("|", "\\|")
    return text
