"""Unified `seos creative` CLI."""

from __future__ import annotations

from pathlib import Path
import json
import sys

from creative.adapters.optional_contracts import build_optional_adapter_contracts
from creative.adapters.base.contract import build_adapter_contract
from creative.assets.asset_registry_builder import build_registry
from creative.assets.archive_group_detector import detect_archive_groups
from creative.assets.asset_search import build_or_load_report, search_asset_library
from creative.assets.duplicate_candidate_detector import detect_duplicate_candidates
from creative.assets.local_asset_library import build_asset_library_scan, write_asset_library_outputs
from creative.assets.missing_part_detector import detect_missing_parts
from creative.reports.dashboard import build_dashboard
from creative.reports.local_production_dashboard import build_local_production_dashboard
from creative.reports.local_tool_health_dashboard import build_local_tool_health_dashboard
from creative.runners.comfyui_local_runner import (
    ComfyUIWorkflowRequest,
    run_comfyui_workflow_smoke,
    write_comfyui_smoke_reports,
)
from creative.runners.houdini_local_runner import (
    HoudiniSmokeRequest,
    run_houdini_hython_smoke,
    write_houdini_smoke_reports,
)
from creative.shots.shot_report import build_shot_report
from creative.shots.shot_workspace import create_shot_workspace
from creative.software.doctor import run_doctor
from creative.validation import run_named_check
from creative.common import ADAPTER_NAMES, repo_root

def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"--help", "-h", "help"}:
        print("seos creative init|scan-assets|search-assets|archive-check|asset|shot|adapter|comfyui|blender|houdini|evidence|dashboard|production-dashboard|tool-health-dashboard|houdini-smoke|comfyui-smoke|optional-adapter-contracts|doctor|launch-check|health|adoption-status")
        return 0
    command = args[0]
    rest = args[1:]
    try:
        if command == "init":
            root = Path(_option(rest, "--workspace", "work/creative_workspace"))
            for name in ("assets", "shots", "staging", "reports"):
                (root / name).mkdir(parents=True, exist_ok=True)
            return _emit({"ok": True, "workspace": root.as_posix(), "dry_run_defaults": True})
        if command == "scan-assets":
            root = Path(_option(rest, "--root", "tests/fixtures/creative/assets"))
            mode = _option(rest, "--mode", "public")
            max_depth = _option_int(rest, "--max-depth", 12)
            scan = build_asset_library_scan(root, mode=mode, max_depth=max_depth)
            outputs = write_asset_library_outputs(
                scan,
                root=root,
                output_json=Path(_option(rest, "--output-json")) if _option(rest, "--output-json") else None,
                output_markdown=Path(_option(rest, "--output-md")) if _option(rest, "--output-md") else None,
            )
            return _emit(
                {
                    "ok": True,
                    "asset_count": scan["summary"]["total_assets"],
                    "summary": scan["summary"],
                    "outputs": outputs,
                    "duplicate_group_count": scan["summary"]["duplicate_group_count"],
                    "archive_warning_count": scan["summary"]["archive_warning_count"],
                    "next_actions": scan["next_actions"],
                    "assets": scan["assets"][:10],
                }
            )
        if command == "search-assets":
            return _search_assets(rest)
        if command == "production-dashboard":
            return _production_dashboard(rest)
        if command == "tool-health-dashboard":
            return _tool_health_dashboard(rest)
        if command == "houdini-smoke":
            return _houdini_smoke(rest)
        if command == "comfyui-smoke":
            return _comfyui_smoke(rest)
        if command == "optional-adapter-contracts":
            return _optional_adapter_contracts(rest)
        if command == "archive-check":
            records = build_registry(Path(_option(rest, "--root", "tests/fixtures/creative/archives")))
            groups = detect_archive_groups(records)
            missing = detect_missing_parts(groups)
            return _emit({"ok": not missing, "archive_groups": groups, "missing_parts": missing})
        if command == "asset" and rest[:1] == ["show"]:
            records = build_registry(Path(_option(rest, "--root", "tests/fixtures/creative/assets")))
            asset_id = _positional(rest[1:]) or (records[0]["id"] if records else "")
            match = next((item for item in records if item.get("id") == asset_id), None)
            return _emit({"ok": bool(match), "asset": match})
        if command == "asset" and rest[:1] == ["search"]:
            return _search_assets(rest[1:])
        if command == "shot" and rest[:1] == ["create"]:
            return _emit(create_shot_workspace(Path(_option(rest, "--root", "work/creative_shots")), _option(rest, "--shot-id", "SHOT_DEMO")))
        if command == "shot" and rest[:1] == ["report"]:
            return _emit(build_shot_report(Path(_option(rest, "--shot-root", "work/creative_shots/SHOT_DEMO"))))
        if command == "adapter" and rest[:1] == ["list"]:
            return _emit({"ok": True, "adapters": list(ADAPTER_NAMES)})
        if command == "adapter" and rest[:1] == ["detect"]:
            return _emit(run_doctor())
        if command == "adapter" and rest[:1] == ["dry-run"]:
            adapter = _option(rest, "--adapter", _positional(rest[1:]) or "comfyui")
            return _emit(build_adapter_contract(adapter).dry_run({"id": "JOB_CLI_DRY_RUN"}).as_dict() | {"ok": True})
        if command == "adapter" and rest[:1] == ["contracts"]:
            return _optional_adapter_contracts(rest[1:])
        if command == "comfyui" and rest[:1] == ["plan"]:
            return _emit(build_adapter_contract("comfyui").dry_run({"id": "AIG_CLI_PLAN"}).as_dict() | {"ok": True})
        if command == "comfyui" and rest[:1] == ["smoke"]:
            return _comfyui_smoke(rest[1:])
        if command == "blender" and rest[:1] == ["check"]:
            return _emit(build_adapter_contract("blender", "LEVEL_2_SMOKE_TEST").dry_run({"id": "RDR_CLI_PREVIEW"}).as_dict() | {"ok": True})
        if command == "houdini" and rest[:1] == ["smoke"]:
            return _houdini_smoke(rest[1:])
        if command == "evidence" and rest[:1] == ["show"]:
            path = repo_root() / _option(rest, "--ledger", "reports/creative/evidence/creative_evidence_ledger.jsonl")
            rows = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
            return _emit({"ok": True, "ledger": path.relative_to(repo_root()).as_posix() if path.exists() else "missing", "row_count": len(rows)})
        if command == "dashboard" and rest[:1] == ["build"]:
            return _emit(build_dashboard(repo_root() / "reports/creative/dashboard"))
        if command == "dashboard" and rest[:1] == ["production"]:
            return _production_dashboard(rest[1:])
        if command == "dashboard" and rest[:1] == ["tool-health"]:
            return _tool_health_dashboard(rest[1:])
        if command == "doctor":
            return _emit(run_doctor())
        if command in {"launch-check", "health"}:
            return _emit(run_named_check("creative_total_check_v3"))
        if command == "adoption-status":
            return _emit(run_named_check("creative_external_adoption_truth_check_v3"))
    except Exception as exc:
        return _emit({"ok": False, "error": exc.__class__.__name__, "message": str(exc)}, code=1)
    return _emit({"ok": False, "error": "unknown_creative_command", "command": command}, code=2)

def _emit(payload: dict[str, object], *, code: int | None = None) -> int:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    if code is not None:
        return code
    return 0 if payload.get("ok") else 1

def _search_assets(rest: list[str]) -> int:
    mode = _option(rest, "--mode", "public")
    registry_value = _option(rest, "--registry-json")
    root_value = _option(rest, "--root")
    report = build_or_load_report(
        registry_json=Path(registry_value) if registry_value else None,
        root=Path(root_value) if root_value else None,
        mode=mode,
        max_depth=_option_int(rest, "--max-depth", 12),
    )
    result = search_asset_library(
        report,
        query=_option(rest, "--query"),
        category=_option(rest, "--category"),
        extension=_option(rest, "--extension"),
        likely_tool=_option(rest, "--likely-tool"),
        min_size=_option_optional_int(rest, "--min-size"),
        max_size=_option_optional_int(rest, "--max-size"),
        duplicate_only="--duplicate-only" in rest,
        texture_status=_option(rest, "--texture-status"),
        archive_status=_option(rest, "--archive-status"),
        empty_directories="--empty-directories" in rest,
        mode=mode,
        limit=_option_int(rest, "--limit", 50),
    )
    return _emit(result)

def _production_dashboard(rest: list[str]) -> int:
    mode = _option(rest, "--mode", "public")
    registry_value = _option(rest, "--registry-json")
    root_value = _option(rest, "--root")
    report = build_or_load_report(
        registry_json=Path(registry_value) if registry_value else None,
        root=Path(root_value) if root_value else None,
        mode=mode,
        max_depth=_option_int(rest, "--max-depth", 12),
    )
    dashboard = build_local_production_dashboard(
        report,
        output_markdown=Path(_option(rest, "--output-md")) if _option(rest, "--output-md") else None,
        output_html=Path(_option(rest, "--output-html")) if _option(rest, "--output-html") else None,
    )
    return _emit(dashboard)

def _tool_health_dashboard(rest: list[str]) -> int:
    doctor_json = _option(rest, "--doctor-json")
    doctor_report = json.loads(Path(doctor_json).read_text(encoding="utf-8")) if doctor_json else None
    dashboard = build_local_tool_health_dashboard(
        doctor_report,
        mode=_option(rest, "--mode", "public"),
        output_json=Path(_option(rest, "--output-json")) if _option(rest, "--output-json") else None,
        output_markdown=Path(_option(rest, "--output-md")) if _option(rest, "--output-md") else None,
        output_html=Path(_option(rest, "--output-html")) if _option(rest, "--output-html") else None,
    )
    return _emit(dashboard)

def _houdini_smoke(rest: list[str]) -> int:
    request = HoudiniSmokeRequest(
        output_root=Path(_option(rest, "--output-root", "work/creative_runs/houdini_smoke")),
        hython_executable=_option(rest, "--hython") or None,
        mode=_option(rest, "--mode", "public"),
        approved="--approve-local-execution" in rest,
        approval_id=_option(rest, "--approval-id", ""),
        timeout_seconds=float(_option(rest, "--timeout-seconds", "30")),
        observed_at=_option(rest, "--observed-at") or None,
    )
    result = run_houdini_hython_smoke(request)
    outputs = write_houdini_smoke_reports(
        result,
        result_json=Path(_option(rest, "--result-json")) if _option(rest, "--result-json") else None,
        materialization_json=Path(_option(rest, "--materialization-json")) if _option(rest, "--materialization-json") else None,
    )
    return _emit(result | {"ok": True, "outputs": outputs})

def _comfyui_smoke(rest: list[str]) -> int:
    request = ComfyUIWorkflowRequest(
        workflow_json=Path(_option(rest, "--workflow-json", "tests/fixtures/creative/comfyui/api_workflow_fixture_v1.json")),
        output_root=Path(_option(rest, "--output-root", "work/creative_runs/comfyui_smoke")),
        endpoint_url=_option(rest, "--endpoint", "http://127.0.0.1:8188"),
        mode=_option(rest, "--mode", "public"),
        approved="--approve-local-execution" in rest,
        approval_id=_option(rest, "--approval-id", ""),
        timeout_seconds=float(_option(rest, "--timeout-seconds", "60")),
        poll_interval_seconds=float(_option(rest, "--poll-interval-seconds", "1")),
        download_outputs="--no-download-outputs" not in rest,
        max_output_artifacts=_option_int(rest, "--max-output-artifacts", 12),
        max_artifact_bytes=_option_int(rest, "--max-artifact-bytes", 26214400),
        observed_at=_option(rest, "--observed-at") or None,
    )
    result = run_comfyui_workflow_smoke(request)
    outputs = write_comfyui_smoke_reports(
        result,
        result_json=Path(_option(rest, "--result-json")) if _option(rest, "--result-json") else None,
        materialization_json=Path(_option(rest, "--materialization-json")) if _option(rest, "--materialization-json") else None,
    )
    return _emit(result | {"ok": True, "outputs": outputs})

def _optional_adapter_contracts(rest: list[str]) -> int:
    doctor_json = _option(rest, "--doctor-json")
    doctor_report = json.loads(Path(doctor_json).read_text(encoding="utf-8")) if doctor_json else None
    report = build_optional_adapter_contracts(
        doctor_report,
        mode=_option(rest, "--mode", "public"),
        output_json=Path(_option(rest, "--output-json")) if _option(rest, "--output-json") else None,
        output_markdown=Path(_option(rest, "--output-md")) if _option(rest, "--output-md") else None,
    )
    return _emit(report)

def _option(args: list[str], name: str, default: str = "") -> str:
    if name not in args:
        return default
    index = args.index(name)
    return args[index + 1] if index + 1 < len(args) else default

def _option_int(args: list[str], name: str, default: int) -> int:
    value = _option(args, name, "")
    if not value:
        return default
    return int(value)

def _option_optional_int(args: list[str], name: str) -> int | None:
    value = _option(args, name, "")
    return int(value) if value else None

def _positional(args: list[str]) -> str:
    skip = False
    for item in args:
        if skip:
            skip = False
            continue
        if item.startswith("--"):
            skip = True
            continue
        return item
    return ""
