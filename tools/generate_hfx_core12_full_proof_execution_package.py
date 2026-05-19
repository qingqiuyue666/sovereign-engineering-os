"""Generate the HFX Core12 full proof execution package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kernel.runtime._production_workbench_validation import OBSERVED_AT_NOT_PROVIDED, compute_content_hash
from kernel.runtime.hfx_core12_completion_ledger import (
    build_hfx_core12_completion_ledger,
    render_hfx_core12_completion_ledger_markdown,
)
from kernel.runtime.hfx_core12_proof_execution import (
    build_hfx_core12_proof_execution,
    render_hfx_core12_proof_execution_markdown,
)

REPOSITORY_URL = "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os"
PROOF_RUN_ID = "HFX_CORE12_FULL_PROOF_RUN_001"
POLICY_VERSION = "hfx-core12-proof-execution-v1"
CODE_VERSION = "0.1.0"
HFX_ROOT = ROOT / "assets/houdini/hfx_factory_core12"
HFX_ROOT_LABEL = "assets/houdini/hfx_factory_core12"
INDEX_ROOT = HFX_ROOT / "00_INDEX_资产索引"
PROOF_ROOT = HFX_ROOT / "600_PROOF_EXECUTION" / PROOF_RUN_ID
PROOF_ROOT_LABEL = f"{HFX_ROOT_LABEL}/600_PROOF_EXECUTION/{PROOF_RUN_ID}"
LEDGER_JSON = INDEX_ROOT / "HFX_CORE12_COMPLETION_LEDGER.json"
LEDGER_MD = INDEX_ROOT / "HFX_CORE12_COMPLETION_LEDGER.md"
PLAN_MD = INDEX_ROOT / "HFX_100_PERCENT_COMPLETION_PLAN.md"
ROUTE_PATH = f"{HFX_ROOT_LABEL}/00_INDEX_资产索引/HFX_CORE12_ROLLBACK_QUARANTINE_ROUTES.json"
SHOT_RENDER_PROOF_PLAN_PATH = f"{HFX_ROOT_LABEL}/00_INDEX_资产索引/HFX_CORE12_SHOT_RENDER_PROOF_PLAN.json"
PROMOTION_MATRIX_PATH = f"{HFX_ROOT_LABEL}/00_INDEX_资产索引/HFX_CORE12_PROMOTION_MATRIX.json"
PROOF_EXECUTION_MATRIX_PATH = f"{PROOF_ROOT_LABEL}/HFX_CORE12_PROOF_EXECUTION_MATRIX.json"

ASSETS: tuple[dict[str, str], ...] = (
    {
        "asset_id": "HFX_008",
        "asset_name": "Energy Shockwave",
        "proof_dir": "HFX_008_ENERGY_SHOCKWAVE",
        "promotion_dir": "HFX_008_ENERGY_SHOCKWAVE",
        "promotion_status": "gold_complete",
    },
    {
        "asset_id": "HFX_015",
        "asset_name": "Portal Ring",
        "proof_dir": "HFX_015_PORTAL_RING",
        "promotion_dir": "HFX_015_PORTAL_RING",
        "promotion_status": "production_complete_pending_shot_proof",
    },
    {
        "asset_id": "HFX_016",
        "asset_name": "Heat Distortion",
        "proof_dir": "HFX_016_HEAT_DISTORTION",
        "promotion_dir": "HFX_016_HEAT_DISTORTION",
        "promotion_status": "production_complete_pending_shot_proof",
    },
    {
        "asset_id": "HFX_021",
        "asset_name": "Pyro Explosion",
        "proof_dir": "HFX_021_PYRO_EXPLOSION",
        "promotion_dir": "HFX_021_PYRO_EXPLOSION",
        "promotion_status": "production_complete_pending_shot_proof",
    },
    {
        "asset_id": "HFX_025",
        "asset_name": "Character Energy Field",
        "proof_dir": "HFX_025_CHARACTER_ENERGY_FIELD",
        "promotion_dir": "HFX_025_CHARACTER_ENERGY_FIELD",
        "promotion_status": "production_complete_pending_shot_proof",
    },
    {
        "asset_id": "HFX_027",
        "asset_name": "Summoning Portal Gate",
        "proof_dir": "HFX_027_SUMMONING_PORTAL_GATE",
        "promotion_dir": "HFX_027_SUMMONING_PORTAL_GATE",
        "promotion_status": "production_complete_pending_shot_proof",
    },
    {
        "asset_id": "HFX_028",
        "asset_name": "Space Rift Tear",
        "proof_dir": "HFX_028_SPACE_RIFT_TEAR",
        "promotion_dir": "HFX_028_SPACE_RIFT_TEAR",
        "promotion_status": "production_complete_pending_shot_proof",
    },
    {
        "asset_id": "HFX_029",
        "asset_name": "Black Hole Accretion Disk",
        "proof_dir": "HFX_029_BLACK_HOLE_ACCRETION_DISK",
        "promotion_dir": "HFX_029_BLACK_HOLE_ACCRETION_DISK",
        "promotion_status": "production_complete_pending_shot_proof",
    },
    {
        "asset_id": "HFX_033",
        "asset_name": "Glow Emission Pass",
        "proof_dir": "HFX_033_GLOW_EMISSION_PASS",
        "promotion_dir": "HFX_033_GLOW_EMISSION_PASS",
        "promotion_status": "production_complete_pending_shot_proof",
    },
    {
        "asset_id": "HFX_036",
        "asset_name": "Alpha Holdout Matte",
        "proof_dir": "HFX_036_ALPHA_HOLDOUT_MATTE",
        "promotion_dir": "HFX_036_ALPHA_HOLDOUT_MATTE",
        "promotion_status": "production_complete_pending_shot_proof",
    },
    {
        "asset_id": "HFX_037",
        "asset_name": "Lightwrap Rim Interaction",
        "proof_dir": "HFX_037_LIGHTWRAP_RIM_INTERACTION",
        "promotion_dir": "HFX_037_LIGHTWRAP_RIM_INTERACTION",
        "promotion_status": "production_complete_pending_shot_proof",
    },
    {
        "asset_id": "HFX_038",
        "asset_name": "Contact Shadow Ground Integration",
        "proof_dir": "HFX_038_CONTACT_SHADOW_GROUND_INTEGRATION",
        "promotion_dir": "HFX_038_CONTACT_SHADOW_GROUND_INTEGRATION",
        "promotion_status": "production_complete_pending_shot_proof",
    },
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-commit", required=True)
    args = parser.parse_args()

    PROOF_ROOT.mkdir(parents=True, exist_ok=True)
    per_asset_packages = [_proof_package_material(asset) for asset in ASSETS]
    root_material = _root_proof_material(args.main_commit, per_asset_packages)
    proof_execution = build_hfx_core12_proof_execution(root_material)

    _write_text(PROOF_ROOT / "README.md", _root_readme(args.main_commit, proof_execution.as_dict()))
    _write_json(PROOF_ROOT / f"{PROOF_RUN_ID}.json", proof_execution.as_dict())
    _write_text(PROOF_ROOT / f"{PROOF_RUN_ID}.md", render_hfx_core12_proof_execution_markdown(proof_execution))

    for asset, package in zip(ASSETS, per_asset_packages):
        _write_asset_package(asset, package)

    matrix_payload = _with_hash(_matrix_payload(args.main_commit, per_asset_packages))
    _write_json(PROOF_ROOT / "HFX_CORE12_PROOF_EXECUTION_MATRIX.json", matrix_payload)
    _write_text(PROOF_ROOT / "HFX_CORE12_PROOF_EXECUTION_MATRIX.md", _render_matrix_markdown(matrix_payload))

    ledger = build_hfx_core12_completion_ledger(_ledger_material(args.main_commit, per_asset_packages))
    _write_json(LEDGER_JSON, ledger.as_dict())
    _write_text(LEDGER_MD, render_hfx_core12_completion_ledger_markdown(ledger))
    _write_text(PLAN_MD, _completion_plan_markdown(args.main_commit, per_asset_packages))
    return 0


def _root_proof_material(main_commit: str, per_asset_packages: list[dict[str, object]]) -> dict[str, object]:
    return {
        "proof_run_id": PROOF_RUN_ID,
        "repository_url": REPOSITORY_URL,
        "main_commit": main_commit,
        "core12_assets": [
            {
                "asset_id": asset["asset_id"],
                "asset_name": asset["asset_name"],
                "proof_package_path": _proof_package_path(asset),
            }
            for asset in ASSETS
        ],
        "per_asset_proof_package": per_asset_packages,
        "shot_proof_status": "package_created",
        "render_proof_status": "package_created",
        "comp_proof_status": "package_created",
        "review_status": "package_created",
        "acceptance_decision": "pending_execution",
        "rejection_reasons": [],
        "quarantine_decision": "not_triggered_pending_execution",
        "rollback_decision": "not_triggered_pending_execution",
        "final_claim_allowed": False,
        "remaining_gates": [
            "actual_shot_execution_for_all_12_assets",
            "actual_render_execution_for_all_12_assets",
            "actual_comp_execution_for_all_12_assets",
            "reviewed_acceptance_for_all_12_assets",
        ],
        "policy_version": POLICY_VERSION,
        "code_version": CODE_VERSION,
    }


def _proof_package_material(asset: dict[str, str]) -> dict[str, object]:
    return {
        "asset_id": asset["asset_id"],
        "asset_name": asset["asset_name"],
        "proof_package_path": _proof_package_path(asset),
        "proof_package_markdown_path": _proof_package_md_path(asset),
        "proof_package_status": "package_created",
        "promotion_status": asset["promotion_status"],
        "promotion_closure_path": _promotion_closure_path(asset),
        "rollback_quarantine_route_path": ROUTE_PATH,
        "shot_render_proof_plan_path": SHOT_RENDER_PROOF_PLAN_PATH,
        "shot_proof_status": "package_created",
        "render_proof_status": "package_created",
        "comp_proof_status": "package_created",
        "review_status": "package_created",
        "acceptance_decision": "pending_execution",
        "expected_artifacts": [
            f"{asset['asset_id']} shot binding receipt with asset version, camera, frame range, and scale notes.",
            f"{asset['asset_id']} render proof manifest with artifact paths, pass list, and deterministic hashes.",
            f"{asset['asset_id']} comp review record with integration notes and reviewer acceptance decision.",
        ],
        "missing_proof_artifacts": [
            "actual shot execution receipt",
            "actual render artifact manifest",
            "actual comp review artifact",
            "reviewed acceptance receipt",
        ],
        "minimum_shot_proof_checklist": [
            "Bind the promoted asset version to a named proof shot.",
            "Record camera, frame range, plate or synthetic-plate label, and scale assumptions.",
            "Record the source HIP/HDA closure path without mutating the source asset.",
            "Seal the shot receipt with deterministic artifact names and hashes.",
        ],
        "minimum_render_proof_checklist": [
            "Execute the render proof in the Houdini/render environment.",
            "Record render settings, pass list, frame range, artifact names, and hashes.",
            "Keep failed, missing, or partial renders in a blocked proof state.",
            "Do not promote render status from package_created until real artifacts exist.",
        ],
        "minimum_comp_review_checklist": [
            "Review alpha, holdout, lightwrap, contact, distortion, glow, and integration behavior where applicable.",
            "Record reviewer, decision, rejection reasons, and acceptance notes.",
            "Block acceptance when render or comp artifacts are missing.",
            "Keep final_claim_allowed false until shot, render, and comp proof are accepted.",
        ],
        "acceptance_criteria": [
            "Shot proof is executed and reviewed for the exact promoted asset.",
            "Render proof artifact manifest exists and hashes match recorded artifacts.",
            "Comp review confirms integration behavior and records an explicit acceptance decision.",
            "Rollback and quarantine route remain active for proof mismatch or unsafe claim.",
            "No unlicensed external asset dependency is required for acceptance.",
        ],
        "rejection_criteria": [
            "Missing shot execution receipt.",
            "Missing render artifact manifest.",
            "Missing comp review artifact.",
            "Hash mismatch, manifest disagreement, unsafe completion claim, or unlicensed dependency.",
        ],
        "quarantine_trigger": (
            "Unlicensed external asset dependency, unsafe proof claim, corrupted artifact record, "
            "or missing required proof artifact."
        ),
        "rollback_trigger": (
            "Proof artifact mismatch, failed review, missing accepted render/comp evidence, "
            "or promotion state disagreement."
        ),
        "remaining_gate": "actual shot/render/comp execution and reviewed acceptance are pending",
        "next_required_action": "Execute this proof package in the Houdini/render/comp environment and record reviewed artifacts.",
        "final_claim_allowed": False,
        "actual_proof_artifacts": [],
        "external_asset_dependency_status": {
            "status": "internal_only_external_friend_assets_deferred",
            "declaration": "External friend asset decision remains deferred; no external dependency is enabled by this proof package.",
            "unlicensed_external_dependency": False,
        },
    }


def _write_asset_package(asset: dict[str, str], package: dict[str, object]) -> None:
    asset_root = PROOF_ROOT / asset["proof_dir"]
    asset_root.mkdir(parents=True, exist_ok=True)
    sealed_package = _with_hash(package)
    _write_json(asset_root / "proof_package.json", sealed_package)
    _write_text(asset_root / "proof_package.md", _render_asset_package_markdown(sealed_package))
    _write_text(asset_root / "shot_proof_checklist.md", _render_checklist("Shot Proof Checklist", package, "minimum_shot_proof_checklist"))
    _write_text(
        asset_root / "render_comp_proof_checklist.md",
        _render_render_comp_checklist(package),
    )
    _write_text(asset_root / "acceptance_review.md", _render_acceptance_review(package))
    _write_text(asset_root / "rejection_quarantine_report.md", _render_rejection_quarantine_report(package))


def _matrix_payload(main_commit: str, per_asset_packages: list[dict[str, object]]) -> dict[str, object]:
    rows = []
    for asset, package in zip(ASSETS, per_asset_packages):
        rows.append(
            {
                "asset_id": asset["asset_id"],
                "asset_name": asset["asset_name"],
                "promotion_status": asset["promotion_status"],
                "proof_package_status": package["proof_package_status"],
                "shot_proof_status": package["shot_proof_status"],
                "render_proof_status": package["render_proof_status"],
                "comp_proof_status": package["comp_proof_status"],
                "acceptance_decision": package["acceptance_decision"],
                "final_claim_allowed": package["final_claim_allowed"],
                "remaining_gate": package["remaining_gate"],
                "next_required_action": package["next_required_action"],
            }
        )
    return {
        "matrix_id": "hfx-core12-proof-execution-matrix-v1",
        "proof_run_id": PROOF_RUN_ID,
        "repository_url": REPOSITORY_URL,
        "main_commit": main_commit,
        "policy_version": POLICY_VERSION,
        "code_version": CODE_VERSION,
        "assets": rows,
    }


def _ledger_material(main_commit: str, per_asset_packages: list[dict[str, object]]) -> dict[str, object]:
    return {
        "ledger_id": "hfx-core12-completion-ledger-v1",
        "repository_url": REPOSITORY_URL,
        "main_commit": main_commit,
        "core12_assets": [
            {
                "asset_id": asset["asset_id"],
                "asset_name": asset["asset_name"],
                "completion_status": asset["promotion_status"],
                "validated_evidence": True,
                "closure_path": _promotion_closure_path(asset),
                "rollback_quarantine_route_status": "recorded",
                "shot_render_proof_plan_status": "recorded_pending_execution",
                "promotion_matrix_status": "recorded",
                "missing_gates": list(package["missing_proof_artifacts"]),
                "exact_remaining_gates": [
                    "actual_shot_execution",
                    "actual_render_execution",
                    "actual_comp_execution",
                    "reviewed_acceptance",
                ],
                "next_required_action": package["next_required_action"],
                "final_claim_allowed": False,
            }
            for asset, package in zip(ASSETS, per_asset_packages)
        ],
        "gold_assets": ["HFX_008"],
        "production_candidates": [],
        "partial_candidates": [],
        "shell_only_assets": [],
        "blocked_assets": [],
        "external_asset_policy": (
            "Deferred; no GitHub storage decision made; external friend assets are out of scope, "
            "no external raw assets are committed, and future review defaults to local-first until license review."
        ),
        "next_required_actions": [
            "Execute the full proof package in the Houdini/render/comp environment.",
            "Attach real shot, render, comp, manifest, and review artifacts before acceptance.",
            "Keep final_claim_allowed false until all 12 assets have accepted proof.",
            "Keep external friend asset decision deferred until internal proof and license review are complete.",
        ],
        "completion_decision": "proof_package_complete_pending_execution",
        "policy_version": "hfx-core12-completion-ledger-v1",
        "code_version": CODE_VERSION,
        "full_promotion_closure_run_id": "hfx-core12-full-promotion-closure-v1",
        "full_proof_run_id": PROOF_RUN_ID,
        "per_asset_closure_paths": [_promotion_closure_path(asset) for asset in ASSETS],
        "per_asset_proof_package_paths": [_proof_package_path(asset) for asset in ASSETS],
        "rollback_quarantine_route_path": ROUTE_PATH,
        "shot_render_proof_plan_path": SHOT_RENDER_PROOF_PLAN_PATH,
        "promotion_matrix_path": PROMOTION_MATRIX_PATH,
        "proof_package_root_path": PROOF_ROOT_LABEL,
        "proof_execution_matrix_path": PROOF_EXECUTION_MATRIX_PATH,
        "proof_execution_status": "package_created_pending_actual_execution",
        "final_remaining_gate": "actual shot/render/comp proof execution and reviewed acceptance for all 12 assets",
        "final_claim_allowed_summary": "false_for_all_12_assets_without_real_accepted_proof",
        "rollback_quarantine_route_status": "recorded_for_all_12_assets",
        "shot_render_proof_plan_status": "recorded_for_all_12_assets_pending_execution",
        "exact_remaining_gates": [
            "actual_shot_execution_for_all_12_assets",
            "actual_render_execution_for_all_12_assets",
            "actual_comp_execution_for_all_12_assets",
            "reviewed_acceptance_for_all_12_assets",
            "external_asset_license_and_storage_policy_decision_deferred",
        ],
        "external_asset_decision": "Deferred; no GitHub storage decision made; no external raw assets committed by this branch.",
    }


def _completion_plan_markdown(main_commit: str, per_asset_packages: list[dict[str, object]]) -> str:
    proof_paths = "\n".join(f"- `{package['proof_package_path']}`" for package in per_asset_packages)
    return (
        "# HFX 100 Percent Completion Plan\n"
        "\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        "| plan_id | hfx-100-percent-completion-plan-v3 |\n"
        f"| proof_run_id | {PROOF_RUN_ID} |\n"
        f"| repository_url | {REPOSITORY_URL} |\n"
        f"| main_commit | {main_commit} |\n"
        "| current_completion_decision | proof_package_complete_pending_execution |\n"
        f"| proof_package_root | {PROOF_ROOT_LABEL} |\n"
        f"| proof_execution_matrix | {PROOF_EXECUTION_MATRIX_PATH} |\n"
        "\n"
        "## Current State\n"
        "- Core12 promotion closure is complete.\n"
        "- Full proof execution package exists for all 12 Core12 assets.\n"
        "- True remaining HFX 100% gate is actual shot/render/comp proof execution and review.\n"
        "- Real remaining work is final shot/render/comp proof execution, not a completion claim.\n"
        "- External asset decision remains deferred.\n"
        "- External friend asset decision remains deferred until license and storage review.\n"
        "- No external raw assets are committed by this proof package branch.\n"
        "- No fake film-grade claims are permitted.\n"
        "- No final Hollywood/film-grade claim is allowed yet, and no final pixel status is asserted.\n"
        "- Next operational step is to execute the proof package in the Houdini/render/comp environment.\n"
        "\n"
        "## Per-Asset Proof Packages\n"
        f"{proof_paths}\n"
        "\n"
        "## Claim Boundary\n"
        "This plan does not claim current 100%. The proof package is complete, but actual proof execution and reviewed acceptance remain pending.\n"
    )


def _root_readme(main_commit: str, proof_payload: dict[str, object]) -> str:
    return (
        "# HFX Core12 Full Proof Run 001\n"
        "\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        f"| proof_run_id | {PROOF_RUN_ID} |\n"
        f"| repository_url | {REPOSITORY_URL} |\n"
        f"| main_commit | {main_commit} |\n"
        f"| acceptance_decision | {proof_payload['acceptance_decision']} |\n"
        f"| final_claim_allowed | {str(proof_payload['final_claim_allowed']).lower()} |\n"
        f"| content_hash | {proof_payload['content_hash']} |\n"
        "\n"
        "## Scope\n"
        "This package covers all 12 HFX Core12 assets in one proof execution run. It records deterministic package, checklist, acceptance, rejection, quarantine, rollback, and matrix artifacts.\n"
        "\n"
        "## Execution Boundary\n"
        "No render, image, video, or comp artifact is created by this package. Actual shot/render/comp execution and reviewed acceptance remain pending.\n"
    )


def _render_asset_package_markdown(package: dict[str, object]) -> str:
    lines = _metadata_lines(f"{package['asset_id']} Proof Package", package, "asset_id")
    sections = (
        ("Linked Evidence", [
            f"promotion_closure_path: {package['promotion_closure_path']}",
            f"rollback_quarantine_route_path: {package['rollback_quarantine_route_path']}",
            f"shot_render_proof_plan_path: {package['shot_render_proof_plan_path']}",
        ]),
        ("Minimum Shot Proof Checklist", package["minimum_shot_proof_checklist"]),
        ("Minimum Render Proof Checklist", package["minimum_render_proof_checklist"]),
        ("Minimum Comp Review Checklist", package["minimum_comp_review_checklist"]),
        ("Expected Artifacts", package["expected_artifacts"]),
        ("Missing Proof Artifacts", package["missing_proof_artifacts"]),
        ("Acceptance Criteria", package["acceptance_criteria"]),
        ("Rejection Criteria", package["rejection_criteria"]),
        ("Quarantine Trigger", package["quarantine_trigger"]),
        ("Rollback Trigger", package["rollback_trigger"]),
        ("Current Acceptance Decision", package["acceptance_decision"]),
    )
    for title, value in sections:
        lines.append(f"## {title}")
        if isinstance(value, list):
            lines.extend(f"- {item}" for item in value)
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_checklist(title: str, package: dict[str, object], field: str) -> str:
    lines = _metadata_lines(f"{package['asset_id']} {title}", package, "asset_id")
    lines.append("## Checklist")
    lines.extend(f"- [ ] {item}" for item in package[field])
    lines.extend(
        [
            "",
            "## Status",
            f"- shot_proof_status: {package['shot_proof_status']}",
            f"- acceptance_decision: {package['acceptance_decision']}",
            "- actual execution remains pending.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_render_comp_checklist(package: dict[str, object]) -> str:
    lines = _metadata_lines(f"{package['asset_id']} Render Comp Proof Checklist", package, "asset_id")
    lines.append("## Render Checklist")
    lines.extend(f"- [ ] {item}" for item in package["minimum_render_proof_checklist"])
    lines.extend(["", "## Comp Review Checklist"])
    lines.extend(f"- [ ] {item}" for item in package["minimum_comp_review_checklist"])
    lines.extend(
        [
            "",
            "## Status",
            f"- render_proof_status: {package['render_proof_status']}",
            f"- comp_proof_status: {package['comp_proof_status']}",
            f"- review_status: {package['review_status']}",
            "- actual execution remains pending.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_acceptance_review(package: dict[str, object]) -> str:
    lines = _metadata_lines(f"{package['asset_id']} Acceptance Review", package, "asset_id")
    lines.extend(
        [
            "## Current Decision",
            f"- acceptance_decision: {package['acceptance_decision']}",
            f"- final_claim_allowed: {str(package['final_claim_allowed']).lower()}",
            "",
            "## Acceptance Criteria",
        ]
    )
    lines.extend(f"- [ ] {item}" for item in package["acceptance_criteria"])
    lines.extend(
        [
            "",
            "## Missing Proof Artifacts",
        ]
    )
    lines.extend(f"- {item}" for item in package["missing_proof_artifacts"])
    return "\n".join(lines).rstrip() + "\n"


def _render_rejection_quarantine_report(package: dict[str, object]) -> str:
    lines = _metadata_lines(f"{package['asset_id']} Rejection Quarantine Report", package, "asset_id")
    lines.extend(
        [
            "## Rejection Criteria",
        ]
    )
    lines.extend(f"- {item}" for item in package["rejection_criteria"])
    lines.extend(
        [
            "",
            "## Quarantine Trigger",
            f"- {package['quarantine_trigger']}",
            "",
            "## Rollback Trigger",
            f"- {package['rollback_trigger']}",
            "",
            "## Current Route Decision",
            "- quarantine_decision: not_triggered_pending_execution",
            "- rollback_decision: not_triggered_pending_execution",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_matrix_markdown(payload: dict[str, object]) -> str:
    lines = _metadata_lines("HFX Core12 Proof Execution Matrix", payload, "matrix_id")
    columns = (
        "asset_id",
        "asset_name",
        "promotion_status",
        "proof_package_status",
        "shot_proof_status",
        "render_proof_status",
        "comp_proof_status",
        "acceptance_decision",
        "final_claim_allowed",
        "remaining_gate",
        "next_required_action",
    )
    lines.extend(["## Matrix", "| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"])
    for asset in payload["assets"]:
        lines.append("| " + " | ".join(_cell(asset[column]) for column in columns) + " |")
    return "\n".join(lines).rstrip() + "\n"


def _metadata_lines(title: str, payload: dict[str, object], id_field: str) -> list[str]:
    lines = [
        f"# {title}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| {id_field} | {_cell(payload[id_field])} |",
    ]
    for field in (
        "asset_name",
        "proof_run_id",
        "repository_url",
        "main_commit",
        "proof_package_status",
        "shot_proof_status",
        "render_proof_status",
        "comp_proof_status",
        "review_status",
        "acceptance_decision",
        "final_claim_allowed",
        "policy_version",
        "code_version",
        "content_hash",
        "observed_at",
    ):
        if field in payload:
            lines.append(f"| {field} | {_cell(payload[field])} |")
    lines.append("")
    return lines


def _promotion_closure_path(asset: dict[str, str]) -> str:
    return (
        f"{HFX_ROOT_LABEL}/300_PRODUCTION_UPGRADE/{asset['promotion_dir']}/"
        f"{asset['asset_id']}_PROMOTION_CLOSURE.json"
    )


def _proof_package_path(asset: dict[str, str]) -> str:
    return f"{PROOF_ROOT_LABEL}/{asset['proof_dir']}/proof_package.json"


def _proof_package_md_path(asset: dict[str, str]) -> str:
    return f"{PROOF_ROOT_LABEL}/{asset['proof_dir']}/proof_package.md"


def _with_hash(payload: dict[str, object]) -> dict[str, object]:
    sealed = dict(payload)
    sealed["content_hash"] = compute_content_hash(payload)
    sealed["observed_at"] = OBSERVED_AT_NOT_PROVIDED
    return sealed


def _cell(value: object) -> str:
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, list):
        text = ", ".join(str(item) for item in value) if value else "none"
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
