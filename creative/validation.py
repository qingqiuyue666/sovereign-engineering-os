"""Validation gates for SEOS Creative Pipeline V3."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
from creative.common import ADAPTER_NAMES, LOCAL_PATH_MARKERS, PRODUCT_STATE, WAITING_STATE, repo_root
from creative.safety.large_file_guard import find_large_files
from creative.safety.local_path_guard import find_local_path_leaks

A_STAGES = ('A00_REPO_BASELINE_LOCKED', 'A01_CORE_REPOSITION_AND_PUBLIC_ENTRY_READY', 'A02_CREATIVE_DOMAIN_AND_SCHEMA_READY', 'A03_ASSET_LIBRARY_AND_ARCHIVE_INTELLIGENCE_READY', 'A04_CREATIVE_EVIDENCE_AND_SHOT_OS_READY', 'A05_SOFTWARE_DISCOVERY_AND_DOCTOR_READY', 'A06_ADAPTER_SDK_AND_CAPABILITY_MATRIX_READY', 'A07_COMFYUI_ADAPTER_MVP_READY', 'A08_BLENDER_ADAPTER_MVP_READY', 'A09_ZBRUSH_SCULPT_REGISTRY_READY', 'A10_HOUDINI_ADAPTER_FOUNDATION_READY', 'A11_UNREAL_ADAPTER_CONTRACT_READY', 'A12_DAVINCI_ADAPTER_CONTRACT_READY', 'A13_AFTER_EFFECTS_ADAPTER_CONTRACT_READY', 'A14_PRIVATE_PUBLIC_ASSET_BOUNDARY_READY', 'A15_VISUAL_REPORTS_AND_DASHBOARD_READY', 'A16_TEMPLATES_AND_EXAMPLES_READY', 'A17_TEST_FIXTURES_AND_RELEASE_GATES_READY', 'A18_DOCS_SITE_AND_CONTRIBUTION_PATH_READY', 'A19_PERSONAL_PRODUCTION_CASES_READY', 'A20_GITHUB_LAUNCH_READY', 'A21_EXTERNAL_ADOPTION_PREPARED', 'A22_CODEX_MAX_COMPLETION_READY')
B_STAGES = ('B01_RELEASE_CADENCE_SYSTEM_READY', 'B02_QUALITY_METRICS_AND_HEALTH_DASHBOARD_READY', 'B03_SECURITY_AND_SUPPLY_CHAIN_MATURITY_READY', 'B04_DEMO_PROPAGATION_PACKAGE_READY', 'B05_ADAPTER_DEEPENING_ROADMAP_READY', 'B06_USER_FEEDBACK_LOOP_READY', 'B07_CASE_STUDY_SYSTEM_READY', 'B08_PUBLIC_LAUNCH_PLAYBOOK_READY', 'B09_CONTINUOUS_ITERATION_LOOP_READY', 'B10_REAL_WORLD_EXCELLENCE_READY')
SCHEMA_FILES = ('shot_contract_v3', 'asset_contract_v3', 'archive_group_contract_v3', 'render_job_contract_v3', 'sim_job_contract_v3', 'sculpt_job_contract_v3', 'ai_generation_job_contract_v3', 'dcc_adapter_contract_v3', 'adapter_result_contract_v3', 'creative_evidence_contract_v3', 'software_discovery_contract_v3', 'license_metadata_contract_v3', 'external_adoption_signal_contract_v3')
ADAPTERS = ('comfyui', 'blender', 'houdini', 'zbrush', 'unreal', 'davinci', 'after_effects')
PUBLIC_V3_PREFIXES = (
    ".github/ISSUE_TEMPLATE/",
    ".github/pull_request_template.md",
    "CONTRIBUTING.md",
    "GOOD_FIRST_ISSUES.md",
    "ROADMAP.md",
    "creative/",
    "docs/adapters/",
    "docs/adoption/",
    "docs/audits/seos_creative_pipeline_",
    "docs/cases/",
    "docs/creative/",
    "docs/feedback/",
    "docs/iteration/",
    "docs/launch/",
    "docs/public/",
    "docs/quality/",
    "docs/releases/",
    "docs/security/dependency_policy_v3.md",
    "docs/security/github_actions_policy_v3.md",
    "docs/security/large_file_policy_v3.md",
    "docs/security/secret_scanning_policy_v3.md",
    "docs/security/supply_chain_maturity_v3.md",
    "docs_site/",
    "examples/asset_registry_fixture_demo/",
    "examples/blender_asset_demo/",
    "examples/comfyui_evidence_demo/",
    "examples/public_demo_assets/",
    "examples/shot_pipeline_demo/",
    "reports/adapters/",
    "reports/adoption/",
    "reports/audits/seos_creative_pipeline_",
    "reports/cases/",
    "reports/creative/",
    "reports/feedback/",
    "reports/iteration/",
    "reports/launch/",
    "reports/public/",
    "reports/quality/",
    "reports/releases/",
    "reports/security/",
    "scripts/creative_",
    "scripts/external_adoption_signal_check_v3.py",
    "scripts/github_launch_readiness_check_v3.py",
    "scripts/project_health_",
    "scripts/public_launch_playbook_check_v3.py",
    "scripts/release_cadence_check_v3.py",
    "scripts/security_supply_chain_maturity_check_v3.py",
    "scripts/seos_creative_pipeline_",
    "scripts/case_study_check_v3.py",
    "scripts/continuous_iteration_loop_check_v3.py",
    "scripts/feedback_loop_check_v3.py",
    "templates/",
    "tests/creative/",
    "tests/fixtures/creative/",
)
REQUIRED_FILES = [
    "creative/schema_registry_v3.json",
    "reports/audits/seos_creative_pipeline_codex_max_completion_dossier_v3.json",
    "reports/audits/seos_creative_pipeline_real_world_excellence_dossier_v3.json",
    "reports/adoption/external_signal_log_v3.json",
    "docs/public/creative_pipeline_overview_v3.md",
    "docs/public/github_launch_packet_v3.md",
    "docs/adapters/adapter_sdk_v3.md",
    "docs/adapters/adapter_capability_matrix_v3.md",
    "reports/creative/adapters/adapter_capability_matrix_v3.json",
] + [f"creative/schemas/{name}.json" for name in SCHEMA_FILES]

FORBIDDEN_CLAIMS = (
    "GLOBAL_RECOGNITION_CONFIRMED",
    "global top project",
    "industry standard",
    "product-market fit confirmed",
    "external adoption confirmed",
    "high GitHub influence confirmed",
)

def run_named_check(name: str) -> dict[str, object]:
    root = repo_root()
    errors: list[str] = []
    if name in {"creative_total_check_v3", "creative_public_release_check_v3", "seos_creative_pipeline_codex_max_completion_check_v3", "seos_creative_pipeline_real_world_excellence_check_v3"}:
        _check_required_files(root, errors)
        _check_json_files(root, errors)
        _check_stage_dossiers(root, errors)
        _check_adapter_matrix(root, errors)
        _check_makefile_targets(root, errors)
    if name in {"creative_no_private_asset_check_v3", "creative_public_release_check_v3", "creative_total_check_v3"}:
        _check_private_assets(root, errors)
    if name in {"creative_no_large_file_check_v3", "creative_public_release_check_v3", "creative_total_check_v3"}:
        _check_large_files(root, errors)
    if name in {"creative_no_local_path_leak_check_v3", "creative_public_release_check_v3", "creative_total_check_v3"}:
        _check_local_path_leaks(root, errors)
    if name in {"creative_external_adoption_truth_check_v3", "creative_public_release_check_v3", "seos_creative_pipeline_real_world_excellence_check_v3", "creative_total_check_v3"}:
        _check_external_adoption_truth(root, errors)
    if name in {"release_cadence_check_v3", "project_health_check_v3", "security_supply_chain_maturity_check_v3", "public_launch_playbook_check_v3", "continuous_iteration_loop_check_v3", "creative_total_check_v3"}:
        _check_layer_b_reports(root, errors)
    return {"ok": not errors, "check": name, "errors": errors, "terminal_state": WAITING_STATE if not errors else "FAILED"}

def main_for(name: str) -> int:
    result = run_named_check(name)
    if result["ok"]:
        print(f"{name}: PASS")
        return 0
    print(f"{name}: FAIL")
    for error in result["errors"]:
        print(f"- {error}")
    return 1

def _check_required_files(root: Path, errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        if not (root / relative).exists():
            errors.append(f"missing required file: {relative}")
    for adapter in ADAPTERS:
        if not (root / "creative" / "adapters" / adapter / "adapter.py").exists():
            errors.append(f"missing adapter: {adapter}")

def _check_json_files(root: Path, errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        if not relative.endswith(".json"):
            continue
        path = root / relative
        if not path.exists():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON {relative}: {exc}")
    ledger = root / "reports/creative/evidence/creative_evidence_ledger.jsonl"
    if ledger.exists():
        for index, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip():
                try:
                    json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"invalid JSONL {ledger.relative_to(root).as_posix()} line {index}: {exc}")

def _check_stage_dossiers(root: Path, errors: list[str]) -> None:
    codex = json.loads((root / "reports/audits/seos_creative_pipeline_codex_max_completion_dossier_v3.json").read_text(encoding="utf-8"))
    excellence = json.loads((root / "reports/audits/seos_creative_pipeline_real_world_excellence_dossier_v3.json").read_text(encoding="utf-8"))
    stages = {item.get("stage"): item for item in codex.get("layer_a_stages", [])}
    for stage in A_STAGES:
        if stages.get(stage, {}).get("status") != "complete":
            errors.append(f"A stage incomplete: {stage}")
    b_stages = {item.get("stage"): item for item in excellence.get("layer_b_stages", [])}
    for stage in B_STAGES:
        if b_stages.get(stage, {}).get("status") != "complete":
            errors.append(f"B stage incomplete: {stage}")
    if excellence.get("product_state") != PRODUCT_STATE:
        errors.append("product_state is not real-world excellence ready")
    if excellence.get("terminal_state") != WAITING_STATE:
        errors.append("terminal_state must wait for real users when external evidence is absent")

def _check_adapter_matrix(root: Path, errors: list[str]) -> None:
    matrix = json.loads((root / "reports/creative/adapters/adapter_capability_matrix_v3.json").read_text(encoding="utf-8"))
    adapters = {item.get("adapter") for item in matrix.get("adapters", [])}
    for adapter in ADAPTER_NAMES:
        if adapter not in adapters:
            errors.append(f"adapter matrix missing {adapter}")

def _check_makefile_targets(root: Path, errors: list[str]) -> None:
    text = (root / "Makefile").read_text(encoding="utf-8")
    for target in ("creative-check:", "creative-doctor:", "creative-total-check:", "creative-public-release-check:"):
        if target not in text:
            errors.append(f"Makefile missing {target}")

def _tracked_files(root: Path) -> list[Path]:
    completed = subprocess.run(["git", "ls-files"], cwd=root, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        return [path for path in root.rglob("*") if path.is_file() and ".git" not in path.parts]
    tracked = [root / line for line in completed.stdout.splitlines() if line]
    others = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, check=False, capture_output=True, text=True)
    if others.returncode == 0:
        tracked.extend(root / line for line in others.stdout.splitlines() if line and (root / line).is_file())
    return sorted(set(tracked))

def _v3_public_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in _tracked_files(root):
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if rel == "scripts/generate_creative_v3_artifacts.py" or rel.startswith(PUBLIC_V3_PREFIXES):
            files.append(path)
    return files

def _check_private_assets(root: Path, errors: list[str]) -> None:
    forbidden_suffixes = {".blend", ".hip", ".ztl", ".fbx", ".obj", ".vdb", ".exr", ".rar", ".7z", ".zip"}
    allowed_prefixes = ("tests/fixtures/creative/", "examples/public_demo_assets/")
    for path in _v3_public_files(root):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(allowed_prefixes):
            continue
        if path.suffix.lower() in forbidden_suffixes:
            errors.append(f"private or large creative asset extension tracked: {rel}")

def _check_large_files(root: Path, errors: list[str]) -> None:
    large = find_large_files(_v3_public_files(root), max_bytes=5_000_000)
    for path in large:
        errors.append(f"large tracked file: {Path(path).relative_to(root).as_posix() if Path(path).is_absolute() else path}")

def _check_local_path_leaks(root: Path, errors: list[str]) -> None:
    paths = [
        path for path in _v3_public_files(root)
        if path.suffix.lower() in {".md", ".txt", ".json", ".jsonl", ".yml", ".yaml", ".toml"}
    ]
    for leak in find_local_path_leaks(paths):
        errors.append(f"local path leak: {leak}")
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for claim in FORBIDDEN_CLAIMS:
            if claim in text:
                errors.append(f"forbidden unsupported claim {claim} in {path.relative_to(root).as_posix()}")

def _check_external_adoption_truth(root: Path, errors: list[str]) -> None:
    log = json.loads((root / "reports/adoption/external_signal_log_v3.json").read_text(encoding="utf-8"))
    signals = log.get("signals", [])
    if log.get("external_adoption_confirmed") is True and not signals:
        errors.append("external adoption confirmed without signals")
    for signal in signals:
        if not signal.get("url") or signal.get("verification_status") != "verified":
            errors.append("external adoption signal missing verified URL evidence")

def _check_layer_b_reports(root: Path, errors: list[str]) -> None:
    required = (
        "reports/releases/release_cadence_status_v3.json",
        "reports/quality/project_health_dashboard_v3.json",
        "reports/security/supply_chain_maturity_v3.json",
        "reports/launch/public_launch_readiness_v3.json",
        "reports/iteration/iteration_loop_status_v3.json",
    )
    for relative in required:
        path = root / relative
        if not path.exists():
            errors.append(f"missing Layer B report: {relative}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") not in {"ready", "complete"}:
            errors.append(f"Layer B report not ready: {relative}")
