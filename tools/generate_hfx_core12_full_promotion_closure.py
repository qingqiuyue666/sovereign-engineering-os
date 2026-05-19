"""Generate HFX Core12 full promotion closure artifacts."""

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
from kernel.runtime.hfx_core12_promotion_closure import (
    build_hfx_core12_promotion_closure,
    render_hfx_core12_promotion_closure_markdown,
)

REPOSITORY_URL = "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os"
RUN_ID = "hfx-core12-full-promotion-closure-v1"
POLICY_VERSION = "hfx-core12-promotion-closure-v1"
CODE_VERSION = "0.1.0"
HFX_ROOT = ROOT / "assets/houdini/hfx_factory_core12"
HFX_ROOT_LABEL = "assets/houdini/hfx_factory_core12"
INDEX_ROOT = HFX_ROOT / "00_INDEX_资产索引"
PRODUCTION_ROOT = HFX_ROOT / "300_PRODUCTION_UPGRADE"

ROUTE_JSON = INDEX_ROOT / "HFX_CORE12_ROLLBACK_QUARANTINE_ROUTES.json"
ROUTE_MD = INDEX_ROOT / "HFX_CORE12_ROLLBACK_QUARANTINE_ROUTES.md"
PROOF_JSON = INDEX_ROOT / "HFX_CORE12_SHOT_RENDER_PROOF_PLAN.json"
PROOF_MD = INDEX_ROOT / "HFX_CORE12_SHOT_RENDER_PROOF_PLAN.md"
MATRIX_JSON = INDEX_ROOT / "HFX_CORE12_PROMOTION_MATRIX.json"
MATRIX_MD = INDEX_ROOT / "HFX_CORE12_PROMOTION_MATRIX.md"
LEDGER_JSON = INDEX_ROOT / "HFX_CORE12_COMPLETION_LEDGER.json"
LEDGER_MD = INDEX_ROOT / "HFX_CORE12_COMPLETION_LEDGER.md"
PLAN_MD = INDEX_ROOT / "HFX_100_PERCENT_COMPLETION_PLAN.md"

ASSETS: tuple[dict[str, str], ...] = (
    {
        "asset_id": "HFX_008",
        "asset_name": "Energy Shockwave",
        "output_dir": "HFX_008_ENERGY_SHOCKWAVE",
        "evidence_dir": "HFX_008_ENERGY_SHOCKWAVE",
        "factory_dir": "",
    },
    {
        "asset_id": "HFX_015",
        "asset_name": "Portal Ring",
        "output_dir": "HFX_015_PORTAL_RING",
        "evidence_dir": "HFX_015_PORTAL_RING",
        "factory_dir": "HFX_015_BATCH_FINALIZE_V007_TO_V014",
    },
    {
        "asset_id": "HFX_016",
        "asset_name": "Heat Distortion",
        "output_dir": "HFX_016_HEAT_DISTORTION",
        "evidence_dir": "HFX_016_HEAT_DISTORTION",
        "factory_dir": "HFX_016_BATCH_FINALIZE_V015_TO_V022",
    },
    {
        "asset_id": "HFX_021",
        "asset_name": "Pyro Explosion",
        "output_dir": "HFX_021_PYRO_EXPLOSION",
        "evidence_dir": "HFX_021_ADVANCED_PYRO_EXPLOSION",
        "factory_dir": "HFX_021_BATCH_FINALIZE_V023_TO_V030",
    },
    {
        "asset_id": "HFX_025",
        "asset_name": "Character Energy Field",
        "output_dir": "HFX_025_CHARACTER_ENERGY_FIELD",
        "evidence_dir": "HFX_025_CHARACTER_ENERGY_FIELD",
        "factory_dir": "HFX_025_BATCH_FINALIZE_V031_TO_V038",
    },
    {
        "asset_id": "HFX_027",
        "asset_name": "Summoning Portal Gate",
        "output_dir": "HFX_027_SUMMONING_PORTAL_GATE",
        "evidence_dir": "HFX_027_SUMMONING_PORTAL_GATE",
        "factory_dir": "HFX_027_BATCH_FINALIZE_V079_TO_V086",
    },
    {
        "asset_id": "HFX_028",
        "asset_name": "Space Rift Tear",
        "output_dir": "HFX_028_SPACE_RIFT_TEAR",
        "evidence_dir": "HFX_028_SPACE_RIFT_TEAR",
        "factory_dir": "HFX_028_BATCH_FINALIZE_V039_TO_V046",
    },
    {
        "asset_id": "HFX_029",
        "asset_name": "Black Hole Accretion Disk",
        "output_dir": "HFX_029_BLACK_HOLE_ACCRETION_DISK",
        "evidence_dir": "HFX_029_BLACK_HOLE_ACCRETION_DISK",
        "factory_dir": "HFX_029_BATCH_FINALIZE_V087_TO_V094",
    },
    {
        "asset_id": "HFX_033",
        "asset_name": "Glow Emission Pass",
        "output_dir": "HFX_033_GLOW_EMISSION_PASS",
        "evidence_dir": "HFX_033_GLOW_EMISSION_PASS",
        "factory_dir": "HFX_033_BATCH_FINALIZE_V047_TO_V054",
    },
    {
        "asset_id": "HFX_036",
        "asset_name": "Alpha Holdout Matte",
        "output_dir": "HFX_036_ALPHA_HOLDOUT_MATTE",
        "evidence_dir": "HFX_036_ALPHA_HOLDOUT_MATTE",
        "factory_dir": "HFX_036_BATCH_FINALIZE_V055_TO_V062",
    },
    {
        "asset_id": "HFX_037",
        "asset_name": "Lightwrap Rim Interaction",
        "output_dir": "HFX_037_LIGHTWRAP_RIM_INTERACTION",
        "evidence_dir": "HFX_037_LIGHTWRAP_RIM_INTERACTION",
        "factory_dir": "HFX_037_BATCH_FINALIZE_V063_TO_V070",
    },
    {
        "asset_id": "HFX_038",
        "asset_name": "Contact Shadow Ground Integration",
        "output_dir": "HFX_038_CONTACT_SHADOW_GROUND_INTEGRATION",
        "evidence_dir": "HFX_038_CONTACTSHADOW_GROUND_INTEGRATION",
        "factory_dir": "HFX_038_BATCH_FINALIZE_V071_TO_V078",
    },
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-commit", required=True)
    args = parser.parse_args()

    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    closure_payloads = []
    for asset in ASSETS:
        closure = build_hfx_core12_promotion_closure(_closure_material(asset, args.main_commit))
        closure_payloads.append(closure.as_dict())
        output_root = PRODUCTION_ROOT / asset["output_dir"]
        output_root.mkdir(parents=True, exist_ok=True)
        prefix = asset["asset_id"]
        _write_json(output_root / f"{prefix}_PROMOTION_CLOSURE.json", closure.as_dict())
        _write_text(output_root / f"{prefix}_PROMOTION_CLOSURE.md", render_hfx_core12_promotion_closure_markdown(closure))

    route_payload = _with_hash(_route_payload(args.main_commit))
    proof_payload = _with_hash(_proof_payload(args.main_commit))
    matrix_payload = _with_hash(_matrix_payload(args.main_commit, closure_payloads))
    _write_json(ROUTE_JSON, route_payload)
    _write_text(ROUTE_MD, _render_routes_markdown(route_payload))
    _write_json(PROOF_JSON, proof_payload)
    _write_text(PROOF_MD, _render_proof_plan_markdown(proof_payload))
    _write_json(MATRIX_JSON, matrix_payload)
    _write_text(MATRIX_MD, _render_matrix_markdown(matrix_payload))

    ledger = build_hfx_core12_completion_ledger(_ledger_material(args.main_commit, closure_payloads))
    _write_json(LEDGER_JSON, ledger.as_dict())
    _write_text(LEDGER_MD, render_hfx_core12_completion_ledger_markdown(ledger))
    _write_text(PLAN_MD, _completion_plan_markdown(args.main_commit))
    return 0


def _closure_material(asset: dict[str, str], main_commit: str) -> dict[str, object]:
    asset_id = asset["asset_id"]
    decision = "gold_complete" if asset_id == "HFX_008" else "production_complete_pending_shot_proof"
    current_status = "gold_complete" if asset_id == "HFX_008" else "production_candidate"
    render_present = asset_id == "HFX_008"
    missing_gates = [] if render_present else ["final_shot_render_comp_proof_execution", "reviewed_final_composite_acceptance"]
    return {
        "asset_id": asset_id,
        "asset_name": asset["asset_name"],
        "current_reality_status": current_status,
        "target_promotion_status": decision,
        "hip_or_hda_evidence": _hip_evidence(asset),
        "preview_evidence": _preview_evidence(asset),
        "validation_evidence": _validation_evidence(asset),
        "checksum_evidence": _checksum_evidence(asset),
        "manifest_evidence": _manifest_evidence(asset),
        "shot_binding_evidence": _shot_evidence(asset),
        "render_or_comp_evidence": _render_evidence(asset, present=render_present),
        "rollback_route": _closure_route(asset, kind="rollback"),
        "quarantine_route": _closure_route(asset, kind="quarantine"),
        "external_asset_dependency_status": {
            "status": "internal_only_external_friend_assets_deferred",
            "declaration": (
                "No external raw asset dependency is required or added by this promotion closure; "
                "external friend asset review remains deferred."
            ),
            "unlicensed_external_dependency": False,
        },
        "missing_gates": missing_gates,
        "next_required_actions": _next_actions(asset, render_present=render_present),
        "promotion_decision": decision,
        "policy_version": POLICY_VERSION,
        "code_version": CODE_VERSION,
    }


def _hip_evidence(asset: dict[str, str]) -> dict[str, object]:
    asset_id = asset["asset_id"]
    if asset_id == "HFX_008":
        paths = [
            f"{HFX_ROOT_LABEL}/300_PRODUCTION_UPGRADE/{asset['evidence_dir']}/00_source/qqy_hfx_energy_shockwave_v009C.hda",
            f"{HFX_ROOT_LABEL}/300_PRODUCTION_UPGRADE/{asset['evidence_dir']}/10_release/release_package/hip/HFX_008_ENERGY_SHOCKWAVE_FINAL_TIER_v007.hip",
        ]
    else:
        final_name = _final_candidate_name(asset)
        paths = [
            f"{HFX_ROOT_LABEL}/300_PRODUCTION_UPGRADE/{asset['evidence_dir']}/03_final/hip/{final_name}.hip",
            f"{HFX_ROOT_LABEL}/300_PRODUCTION_UPGRADE/{asset['evidence_dir']}/10_release/release_package/hip/{final_name}.hip",
        ]
    return {
        "present": True,
        "summary": "Reusable internal HIP/HDA evidence is present; this branch does not mutate HIP/HDA files.",
        "paths": paths,
    }


def _preview_evidence(asset: dict[str, str]) -> dict[str, object]:
    return {
        "present": True,
        "summary": "Preview-tier or preview-policy evidence exists in repository records; this branch creates no image or video preview.",
        "paths": [
            f"{HFX_ROOT_LABEL}/300_PRODUCTION_UPGRADE/{asset['evidence_dir']}/01_preview/hip",
            f"{HFX_ROOT_LABEL}/00_INDEX_资产索引/{asset['asset_id']}_BATCH_FINALIZE_REPORT.md",
        ],
    }


def _validation_evidence(asset: dict[str, str]) -> dict[str, object]:
    paths = [f"{HFX_ROOT_LABEL}/00_INDEX_资产索引/{asset['asset_id']}_BATCH_FINALIZE_REPORT.md"]
    if asset["factory_dir"]:
        paths.append(f"{HFX_ROOT_LABEL}/500_HFX_FACTORY/{asset['factory_dir']}/02_validation")
    else:
        paths.append(f"{HFX_ROOT_LABEL}/300_PRODUCTION_UPGRADE/{asset['evidence_dir']}/07_validation")
    return {
        "present": True,
        "summary": "Validation evidence is present and is referenced without launching Houdini or executing a render.",
        "paths": paths,
    }


def _checksum_evidence(asset: dict[str, str]) -> dict[str, object]:
    if asset["factory_dir"]:
        path = f"{HFX_ROOT_LABEL}/500_HFX_FACTORY/{asset['factory_dir']}/03_manifests/{asset['factory_dir']}_SHA256SUMS.txt"
    else:
        path = f"{HFX_ROOT_LABEL}/300_PRODUCTION_UPGRADE/{asset['evidence_dir']}/08_manifests/HFX_008_V002_SHA256SUMS.txt"
    return {
        "present": True,
        "summary": "Checksum evidence is present in existing manifests; observed_at is not part of any content hash.",
        "paths": [path],
    }


def _manifest_evidence(asset: dict[str, str]) -> dict[str, object]:
    if asset["factory_dir"]:
        path = f"{HFX_ROOT_LABEL}/500_HFX_FACTORY/{asset['factory_dir']}/03_manifests/{asset['factory_dir']}_MANIFEST.json"
    else:
        path = f"{HFX_ROOT_LABEL}/300_PRODUCTION_UPGRADE/{asset['evidence_dir']}/08_manifests/HFX_PRODUCTION_UPGRADE_V002_HFX008_SOURCE_RESOLUTION_MANIFEST.json"
    return {
        "present": True,
        "summary": "Manifest evidence is present for the reusable internal asset closure.",
        "paths": [path],
    }


def _shot_evidence(asset: dict[str, str]) -> dict[str, object]:
    return {
        "present": True,
        "summary": "Shot binding or shot-bound contract evidence exists; final proof execution remains governed by the proof plan.",
        "paths": [
            f"{HFX_ROOT_LABEL}/00_INDEX_资产索引/SHOT_001_TEST_REAL_FX_BINDING_HERO_HIP_ASSET_INDEX_v007.json",
            f"{HFX_ROOT_LABEL}/00_INDEX_资产索引/HFX_CORE12_SHOT_RENDER_PROOF_PLAN.json",
        ],
    }


def _render_evidence(asset: dict[str, str], *, present: bool) -> dict[str, object]:
    if present:
        summary = (
            "Internal render/comp package evidence exists for the reusable HFX_008 closure; "
            "it is not a final public film-grade status claim."
        )
        paths = [
            f"{HFX_ROOT_LABEL}/300_PRODUCTION_UPGRADE/{asset['evidence_dir']}/06_comp/HFX_008_FINAL_COMP_HANDOFF_v007.json",
            f"{HFX_ROOT_LABEL}/00_INDEX_资产索引/SHOT_BOUND_HFX008_FINAL_PIXEL_RENDER_V011_FINAL_ASSET_SYSTEM_SEAL_REPORT.md",
        ]
    else:
        summary = "Final shot/render/comp proof is planned but not executed in this branch."
        paths = [f"{HFX_ROOT_LABEL}/00_INDEX_资产索引/HFX_CORE12_SHOT_RENDER_PROOF_PLAN.json"]
    return {"present": present, "summary": summary, "paths": paths}


def _closure_route(asset: dict[str, str], *, kind: str) -> dict[str, object]:
    return {
        "present": True,
        "route_id": f"{asset['asset_id']}_{kind}_route_v1",
        "trigger": f"{asset['asset_id']} evidence mismatch, unsafe claim, missing final proof, or manifest/checksum disagreement.",
        "action": (
            "Return promotion state to production_candidate, preserve existing evidence and manifest records, "
            "and require manual review before promotion reentry."
        )
        if kind == "rollback"
        else (
            "Mark the closure blocked for promotion, isolate the disputed evidence reference, preserve original records, "
            "and require manual review before reentry."
        ),
        "safe_state": "Audit-only closure state with no HIP/HDA mutation, no external raw asset enablement, and no generated media.",
    }


def _next_actions(asset: dict[str, str], *, render_present: bool) -> list[str]:
    actions = [
        "Keep rollback and quarantine route active for every promotion reentry.",
        "Keep external friend asset decision deferred until internal closure and license review.",
        "Do not assert final film-grade or Hollywood-grade status until reviewed shot/render/comp proof exists.",
    ]
    if not render_present:
        actions.insert(0, "Execute and review the final shot/render/comp proof plan before complete final-claim status.")
    return actions


def _route_payload(main_commit: str) -> dict[str, object]:
    return {
        "route_id": "hfx-core12-rollback-quarantine-routes-v1",
        "repository_url": REPOSITORY_URL,
        "main_commit": main_commit,
        "run_id": RUN_ID,
        "policy_version": POLICY_VERSION,
        "code_version": CODE_VERSION,
        "assets": [
            {
                "asset_id": asset["asset_id"],
                "asset_name": asset["asset_name"],
                "rollback_trigger": "Evidence mismatch, missing final proof, unsafe claim, checksum drift, or manifest disagreement.",
                "quarantine_trigger": "Unlicensed external raw dependency, empty critical evidence, unsafe final-status language, or corrupted record.",
                "rollback_action": "Revert promotion state to production_candidate and keep all existing evidence records intact.",
                "quarantine_action": "Block promotion reentry, isolate the disputed reference, and retain original manifests and checksums.",
                "safe_state": "Audit-only candidate state; no generated media, no external raw assets, and no mutable Houdini asset changes.",
                "forbidden_recovery_actions": [
                    "enable_external_raw_assets",
                    "claim_final_film_grade_status",
                    "mutate_hip_hda_or_otl",
                    "launch_houdini_or_hython",
                    "run_render_or_comp_output",
                ],
                "review_required": "Manual HFX steward review is required before promotion reentry.",
                "promotion_reentry_gate": "All closure evidence, route evidence, proof-plan evidence, checksum evidence, and missing-gate records must pass.",
            }
            for asset in ASSETS
        ],
        "global_boundary": [
            "Rollback cannot enable external raw assets.",
            "Rollback cannot assert final film-grade or Hollywood-grade status.",
            "Rollback cannot mutate HIP/HDA/OTL files in this branch.",
            "Rollback cannot launch Houdini, hython, render, or comp tools.",
            "Quarantine must preserve original evidence and manifest records.",
        ],
    }


def _proof_payload(main_commit: str) -> dict[str, object]:
    return {
        "plan_id": "hfx-core12-shot-render-proof-plan-v1",
        "repository_url": REPOSITORY_URL,
        "main_commit": main_commit,
        "run_id": RUN_ID,
        "policy_version": POLICY_VERSION,
        "code_version": CODE_VERSION,
        "proof_execution_status": "planned_not_executed",
        "assets": [
            {
                "asset_id": asset["asset_id"],
                "asset_name": asset["asset_name"],
                "minimum_shot_proof": f"{asset['asset_id']} bound to a named shot manifest with camera, scale, frame range, and expected integration notes.",
                "minimum_preview_proof": "Non-final preview artifact or preview validation record tied to the exact asset version.",
                "minimum_render_comp_proof": "Reviewed render/comp package with artifact names, hashes, pass list, and acceptance notes.",
                "allowed_synthetic_proof": "Synthetic plate/camera proof is allowed only when labeled synthetic and not used as final-status evidence.",
                "required_final_proof": "Executed shot/render/comp proof reviewed against the asset-specific acceptance gate.",
                "proof_artifact_naming": f"{asset['asset_id']}_SHOT_RENDER_COMP_PROOF_v###",
                "review_gate": "Manual HFX steward review plus checksum and manifest match.",
                "rejection_conditions": [
                    "Missing shot binding",
                    "Missing render/comp proof artifact",
                    "Unlabeled synthetic proof",
                    "Unsafe final-status language",
                    "Unlicensed external raw dependency",
                ],
                "no_fake_final_pixel_claim_boundary": "Proof remains planned in this branch; no final-pixel status is asserted.",
            }
            for asset in ASSETS
        ],
    }


def _matrix_payload(main_commit: str, closure_payloads: list[dict[str, object]]) -> dict[str, object]:
    closure_by_id = {str(payload["asset_id"]): payload for payload in closure_payloads}
    rows = []
    for asset in ASSETS:
        closure = closure_by_id[asset["asset_id"]]
        render_present = bool(closure["render_or_comp_evidence"]["present"])
        rows.append(
            {
                "asset_id": asset["asset_id"],
                "asset_name": asset["asset_name"],
                "previous_reality_status": closure["current_reality_status"],
                "new_promotion_status": closure["promotion_decision"],
                "rollback_route": "recorded",
                "quarantine_route": "recorded",
                "shot_proof_status": "planned_not_executed",
                "render_comp_proof_status": "internal_record_present_final_claim_blocked"
                if render_present
                else "planned_not_executed",
                "external_asset_dependency_status": "internal_only_external_friend_assets_deferred",
                "missing_gates": list(closure["missing_gates"]),
                "next_required_action": "Execute reviewed shot/render/comp proof before any final-status claim.",
                "final_claim_allowed": False,
            }
        )
    return {
        "matrix_id": "hfx-core12-promotion-matrix-v1",
        "repository_url": REPOSITORY_URL,
        "main_commit": main_commit,
        "run_id": RUN_ID,
        "policy_version": POLICY_VERSION,
        "code_version": CODE_VERSION,
        "assets": rows,
    }


def _ledger_material(main_commit: str, closure_payloads: list[dict[str, object]]) -> dict[str, object]:
    closure_paths = [_closure_path_for(asset) for asset in ASSETS]
    core12_assets = []
    gold_assets = []
    for asset, closure in zip(ASSETS, closure_payloads):
        status = str(closure["promotion_decision"])
        if status == "gold_complete":
            gold_assets.append(asset["asset_id"])
        core12_assets.append(
            {
                "asset_id": asset["asset_id"],
                "asset_name": asset["asset_name"],
                "completion_status": status,
                "validated_evidence": True,
                "closure_path": _closure_path_for(asset),
                "rollback_quarantine_route_status": "recorded",
                "shot_render_proof_plan_status": "planned_not_executed",
                "promotion_matrix_status": "recorded",
                "missing_gates": list(closure["missing_gates"]),
                "exact_remaining_gates": _remaining_gates_for(asset),
                "next_required_action": "Execute reviewed shot/render/comp proof before any final-status claim.",
                "final_claim_allowed": False,
            }
        )
    return {
        "ledger_id": "hfx-core12-completion-ledger-v1",
        "repository_url": REPOSITORY_URL,
        "main_commit": main_commit,
        "core12_assets": core12_assets,
        "gold_assets": gold_assets,
        "production_candidates": [],
        "partial_candidates": [],
        "shell_only_assets": [],
        "blocked_assets": [],
        "external_asset_policy": (
            "Deferred; no GitHub storage decision made; external friend assets are out of scope, "
            "no external raw assets are committed, and future review defaults to local-first until license review."
        ),
        "next_required_actions": [
            "Execute reviewed shot/render/comp proof for every Core12 asset before any final-status claim.",
            "Keep rollback/quarantine routes recorded and active for all 12 assets.",
            "Keep external friend asset decision deferred until internal closure and license review.",
            "Do not claim current 100% while final proof execution remains incomplete.",
        ],
        "completion_decision": "promotion_closure_complete_pending_shot_proof",
        "policy_version": "hfx-core12-completion-ledger-v1",
        "code_version": CODE_VERSION,
        "full_promotion_closure_run_id": RUN_ID,
        "per_asset_closure_paths": closure_paths,
        "rollback_quarantine_route_path": _label(ROUTE_JSON),
        "shot_render_proof_plan_path": _label(PROOF_JSON),
        "promotion_matrix_path": _label(MATRIX_JSON),
        "rollback_quarantine_route_status": "recorded_for_all_12_assets",
        "shot_render_proof_plan_status": "planned_not_executed_for_all_12_assets",
        "exact_remaining_gates": [
            "final_shot_render_comp_proof_execution_for_all_12_assets",
            "reviewed_final_composite_acceptance_for_all_12_assets",
            "external_asset_license_and_storage_policy_decision_deferred",
        ],
        "external_asset_decision": "Deferred; no GitHub storage decision made; no external raw assets committed by this branch.",
    }


def _completion_plan_markdown(main_commit: str) -> str:
    closure_paths = "\n".join(f"- `{_closure_path_for(asset)}`" for asset in ASSETS)
    return (
        "# HFX 100 Percent Completion Plan\n"
        "\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        f"| plan_id | hfx-100-percent-completion-plan-v2 |\n"
        f"| run_id | {RUN_ID} |\n"
        f"| repository_url | {REPOSITORY_URL} |\n"
        f"| main_commit | {main_commit} |\n"
        "| current_completion_decision | promotion_closure_complete_pending_shot_proof |\n"
        "\n"
        "## Current Branch Closure\n"
        "- All 12 Core12 assets have a deterministic promotion closure record.\n"
        "- All 12 Core12 assets have rollback and quarantine routes.\n"
        "- All 12 Core12 assets have a shot/render proof plan.\n"
        "- The Core12 promotion matrix exists and records final_claim_allowed as false for every asset.\n"
        "- The Core12 completion ledger is updated with the full promotion closure run id.\n"
        "- External friend asset decision remains deferred until internal closure and license review.\n"
        "- No external raw assets are committed by this branch.\n"
        "\n"
        "## Per-Asset Closure Records\n"
        f"{closure_paths}\n"
        "\n"
        "## Real Path To 100 Percent\n"
        "- Execute reviewed final shot/render/comp proof for every Core12 asset.\n"
        "- Attach artifact names, hashes, manifests, and review outcomes to each asset closure.\n"
        "- Recompute the promotion matrix with final_claim_allowed true only where final proof exists.\n"
        "- Update the completion ledger to complete only if every final evidence gate is true.\n"
        "- Resolve external asset license and storage policy only after internal closure is complete.\n"
        "\n"
        "## Claim Boundary\n"
        "This plan does not claim current 100%. No fake film-grade claims are permitted, and no final film-grade or Hollywood-grade status is asserted until reviewed shot/render/comp proof exists.\n"
    )


def _render_routes_markdown(payload: dict[str, object]) -> str:
    lines = _metadata_lines("HFX Core12 Rollback Quarantine Routes", payload, "route_id")
    lines.extend(
        [
            "## Asset Routes",
            "| asset_id | asset_name | rollback_trigger | quarantine_trigger | rollback_action | quarantine_action | safe_state | review_required | promotion_reentry_gate |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for asset in payload["assets"]:
        lines.append(
            "| "
            + " | ".join(
                _cell(asset[field])
                for field in (
                    "asset_id",
                    "asset_name",
                    "rollback_trigger",
                    "quarantine_trigger",
                    "rollback_action",
                    "quarantine_action",
                    "safe_state",
                    "review_required",
                    "promotion_reentry_gate",
                )
            )
            + " |"
        )
    lines.extend(["", "## Forbidden Recovery Actions"])
    for action in payload["assets"][0]["forbidden_recovery_actions"]:
        lines.append(f"- `{action}`")
    lines.extend(["", "## Global Boundary"])
    lines.extend(f"- {item}" for item in payload["global_boundary"])
    return "\n".join(lines).rstrip() + "\n"


def _render_proof_plan_markdown(payload: dict[str, object]) -> str:
    lines = _metadata_lines("HFX Core12 Shot Render Proof Plan", payload, "plan_id")
    lines.extend(
        [
            "## Proof Plan Matrix",
            "| asset_id | asset_name | minimum_shot_proof | minimum_preview_proof | minimum_render_comp_proof | allowed_synthetic_proof | required_final_proof | proof_artifact_naming | review_gate | proof_status |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for asset in payload["assets"]:
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    asset["asset_id"],
                    asset["asset_name"],
                    asset["minimum_shot_proof"],
                    asset["minimum_preview_proof"],
                    asset["minimum_render_comp_proof"],
                    asset["allowed_synthetic_proof"],
                    asset["required_final_proof"],
                    asset["proof_artifact_naming"],
                    asset["review_gate"],
                    payload["proof_execution_status"],
                )
            )
            + " |"
        )
    lines.extend(["", "## Planned Only Boundary", "Proof is planned, not executed. No EXR, image, video, or render output is created by this branch."])
    return "\n".join(lines).rstrip() + "\n"


def _render_matrix_markdown(payload: dict[str, object]) -> str:
    lines = _metadata_lines("HFX Core12 Promotion Matrix", payload, "matrix_id")
    columns = (
        "asset_id",
        "asset_name",
        "previous_reality_status",
        "new_promotion_status",
        "rollback_route",
        "quarantine_route",
        "shot_proof_status",
        "render_comp_proof_status",
        "external_asset_dependency_status",
        "missing_gates",
        "next_required_action",
        "final_claim_allowed",
    )
    lines.extend(["## Matrix", "| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"])
    for asset in payload["assets"]:
        lines.append("| " + " | ".join(_cell(asset[column]) for column in columns) + " |")
    return "\n".join(lines).rstrip() + "\n"


def _metadata_lines(title: str, payload: dict[str, object], id_field: str) -> list[str]:
    return [
        f"# {title}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| {id_field} | {_cell(payload[id_field])} |",
        f"| repository_url | {_cell(payload['repository_url'])} |",
        f"| main_commit | {_cell(payload['main_commit'])} |",
        f"| run_id | {_cell(payload['run_id'])} |",
        f"| policy_version | {_cell(payload['policy_version'])} |",
        f"| code_version | {_cell(payload['code_version'])} |",
        f"| content_hash | {_cell(payload['content_hash'])} |",
        f"| observed_at | {_cell(payload['observed_at'])} |",
        "",
    ]


def _with_hash(payload: dict[str, object]) -> dict[str, object]:
    sealed = dict(payload)
    sealed["content_hash"] = compute_content_hash(payload)
    sealed["observed_at"] = OBSERVED_AT_NOT_PROVIDED
    return sealed


def _final_candidate_name(asset: dict[str, str]) -> str:
    versions = {
        "HFX_015": "v014",
        "HFX_016": "v022",
        "HFX_021": "v030",
        "HFX_025": "v038",
        "HFX_027": "v086",
        "HFX_028": "v046",
        "HFX_029": "v094",
        "HFX_033": "v054",
        "HFX_036": "v062",
        "HFX_037": "v070",
        "HFX_038": "v078",
    }
    return f"{asset['evidence_dir']}_FINAL_CANDIDATE_{versions[asset['asset_id']]}"


def _closure_path_for(asset: dict[str, str]) -> str:
    return f"{HFX_ROOT_LABEL}/300_PRODUCTION_UPGRADE/{asset['output_dir']}/{asset['asset_id']}_PROMOTION_CLOSURE.json"


def _remaining_gates_for(asset: dict[str, str]) -> list[str]:
    gates = ["final_shot_render_comp_proof_execution", "reviewed_final_composite_acceptance"]
    if asset["asset_id"] == "HFX_008":
        return ["final_public_claim_review_gate"]
    return gates


def _label(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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
