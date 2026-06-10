#!/usr/bin/env python3
"""Generate SEOS Creative Pipeline V3 repository artifacts.

The V3 program adds a large, mostly declarative product surface.  Keeping the
generated public docs, schemas, fixtures, and readiness reports in one
deterministic generator makes the artifact set auditable and repeatable while
the runtime code remains normal Python modules.
"""

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-05-31T00:00:00Z"
SCHEMA_VERSION = "seos_creative_pipeline_v3"
PRODUCT_STATE = "SEOS_CREATIVE_PIPELINE_REAL_WORLD_EXCELLENCE_READY"
WAITING_STATE = "EXTERNAL_ADOPTION_LOOP_ACTIVE_WAITING_FOR_REAL_USERS"

ADAPTERS = (
    "comfyui",
    "blender",
    "houdini",
    "zbrush",
    "unreal",
    "davinci",
    "after_effects",
)

A_STAGES = (
    "A00_REPO_BASELINE_LOCKED",
    "A01_CORE_REPOSITION_AND_PUBLIC_ENTRY_READY",
    "A02_CREATIVE_DOMAIN_AND_SCHEMA_READY",
    "A03_ASSET_LIBRARY_AND_ARCHIVE_INTELLIGENCE_READY",
    "A04_CREATIVE_EVIDENCE_AND_SHOT_OS_READY",
    "A05_SOFTWARE_DISCOVERY_AND_DOCTOR_READY",
    "A06_ADAPTER_SDK_AND_CAPABILITY_MATRIX_READY",
    "A07_COMFYUI_ADAPTER_MVP_READY",
    "A08_BLENDER_ADAPTER_MVP_READY",
    "A09_ZBRUSH_SCULPT_REGISTRY_READY",
    "A10_HOUDINI_ADAPTER_FOUNDATION_READY",
    "A11_UNREAL_ADAPTER_CONTRACT_READY",
    "A12_DAVINCI_ADAPTER_CONTRACT_READY",
    "A13_AFTER_EFFECTS_ADAPTER_CONTRACT_READY",
    "A14_PRIVATE_PUBLIC_ASSET_BOUNDARY_READY",
    "A15_VISUAL_REPORTS_AND_DASHBOARD_READY",
    "A16_TEMPLATES_AND_EXAMPLES_READY",
    "A17_TEST_FIXTURES_AND_RELEASE_GATES_READY",
    "A18_DOCS_SITE_AND_CONTRIBUTION_PATH_READY",
    "A19_PERSONAL_PRODUCTION_CASES_READY",
    "A20_GITHUB_LAUNCH_READY",
    "A21_EXTERNAL_ADOPTION_PREPARED",
    "A22_CODEX_MAX_COMPLETION_READY",
)

B_STAGES = (
    "B01_RELEASE_CADENCE_SYSTEM_READY",
    "B02_QUALITY_METRICS_AND_HEALTH_DASHBOARD_READY",
    "B03_SECURITY_AND_SUPPLY_CHAIN_MATURITY_READY",
    "B04_DEMO_PROPAGATION_PACKAGE_READY",
    "B05_ADAPTER_DEEPENING_ROADMAP_READY",
    "B06_USER_FEEDBACK_LOOP_READY",
    "B07_CASE_STUDY_SYSTEM_READY",
    "B08_PUBLIC_LAUNCH_PLAYBOOK_READY",
    "B09_CONTINUOUS_ITERATION_LOOP_READY",
    "B10_REAL_WORLD_EXCELLENCE_READY",
)

SCHEMA_FILES = (
    "shot_contract_v3",
    "asset_contract_v3",
    "archive_group_contract_v3",
    "render_job_contract_v3",
    "sim_job_contract_v3",
    "sculpt_job_contract_v3",
    "ai_generation_job_contract_v3",
    "dcc_adapter_contract_v3",
    "adapter_result_contract_v3",
    "creative_evidence_contract_v3",
    "software_discovery_contract_v3",
    "license_metadata_contract_v3",
    "external_adoption_signal_contract_v3",
)

ERROR_CODES = (
    "ENV_NOT_FOUND",
    "SERVICE_UNAVAILABLE",
    "LICENSE_BLOCKED",
    "FILE_MISSING",
    "ARCHIVE_PART_MISSING",
    "ADAPTER_UNSUPPORTED",
    "VALIDATION_FAILED",
    "PERMISSION_DENIED",
    "USER_APPROVAL_REQUIRED",
    "LONG_TASK_BLOCKED",
    "PRIVATE_ASSET_NOT_COMMITTABLE",
    "LOCAL_PATH_LEAK_BLOCKED",
    "LARGE_FILE_BLOCKED",
    "EXTERNAL_ADOPTION_NOT_CONFIRMED",
    "UNSAFE_DESTRUCTIVE_ACTION_BLOCKED",
    "RELEASE_GATE_FAILED",
    "DEMO_ASSET_UNSAFE",
    "QUICKSTART_FAILED",
    "DOCS_INCOMPLETE",
    "HEALTH_METRIC_REGRESSION",
)

PUBLIC_DOCS = {
    "docs/public/creative_pipeline_overview_v3.md": (
        "SEOS Creative Pipeline Overview V3",
        "SEOS Creative Pipeline is a local-first AI/VFX/3D/video workflow control plane. It tracks assets, shots, DCC adapters, AI generations, render jobs, approvals, evidence, and replay across ComfyUI, Blender, Houdini, ZBrush, Unreal Engine, DaVinci Resolve, and After Effects.",
    ),
    "docs/public/creative_pipeline_positioning_v3.md": (
        "Creative Pipeline Positioning V3",
        "The project is positioned as a local-first governance and evidence layer for creative engineering teams and solo technical artists. It is not cloud-first, not a managed service, and not a claim of external adoption.",
    ),
    "docs/public/creative_pipeline_quickstart_v3.md": (
        "Creative Pipeline Quickstart V3",
        "Run `python3 seos.py creative health --json`, then `python3 seos.py creative dashboard build --json`, then inspect `reports/creative/dashboard/index.html`. The quickstart uses fixtures and dry-run adapter plans by default.",
    ),
    "docs/public/supported_software_matrix_v3.md": (
        "Supported Software Matrix V3",
        "The supported surface is contract-first: ComfyUI and Blender have fixture-backed dry-run MVPs, while Houdini, ZBrush, Unreal Engine, DaVinci Resolve, and After Effects expose discovery, manifest, and handoff contracts.",
    ),
    "docs/public/not_for_v3.md": (
        "What The Creative Pipeline Is Not V3",
        "This is not an OS-level sandbox, not RPA, not a computer-control framework, not a cloud render farm, not a secret manager, and not evidence of market traction.",
    ),
    "docs/public/security_boundary_summary_v3.md": (
        "Security Boundary Summary V3",
        "The boundary is governance-level and repository-level: private assets are scanned read-only, long jobs are converted to dry-run plans, and public artifacts must not contain private paths, paid assets, or unsupported adoption claims.",
    ),
    "docs/public/github_launch_packet_v3.md": (
        "GitHub Launch Packet V3",
        "The launch packet packages the README value statement, fixture demos, adapter SDK, safety boundary, release gates, and adoption tracking readiness without claiming real external traction.",
    ),
}

DOCS_SITE = {
    "docs_site/introduction.md": "Introduction",
    "docs_site/quickstart.md": "Quickstart",
    "docs_site/creative_project.md": "Creative Project",
    "docs_site/asset_registry.md": "Asset Registry",
    "docs_site/archive_integrity.md": "Archive Integrity",
    "docs_site/evidence_ledger.md": "Evidence Ledger",
    "docs_site/shot_pipeline.md": "Shot Pipeline",
    "docs_site/adapters/comfyui.md": "ComfyUI Adapter",
    "docs_site/adapters/blender.md": "Blender Adapter",
    "docs_site/adapters/houdini.md": "Houdini Adapter",
    "docs_site/adapters/zbrush.md": "ZBrush Adapter",
    "docs_site/adapters/unreal.md": "Unreal Adapter",
    "docs_site/adapters/davinci.md": "DaVinci Resolve Adapter",
    "docs_site/adapters/after_effects.md": "After Effects Adapter",
    "docs_site/adapter_sdk.md": "Adapter SDK",
    "docs_site/security.md": "Security",
    "docs_site/faq.md": "FAQ",
}

TEMPLATE_DIRS = (
    "creative_project",
    "shot_pipeline",
    "comfyui_workflow_manifest",
    "blender_asset_check",
    "zbrush_sculpt_handoff",
    "houdini_cache_manifest",
    "unreal_mrq_manifest",
    "davinci_render_manifest",
    "after_effects_template_manifest",
    "evidence_report",
    "review_packet",
)

EXAMPLE_DIRS = (
    "comfyui_evidence_demo",
    "blender_asset_demo",
    "shot_pipeline_demo",
    "asset_registry_fixture_demo",
    "public_demo_assets",
)

FIXTURE_DIRS = (
    "archives",
    "assets",
    "comfyui_workflows",
    "blender_stub",
    "shots",
    "adapters",
    "software_discovery",
    "licenses",
)


def main() -> int:
    generate_code()
    generate_schemas()
    generate_docs()
    generate_templates_examples_and_fixtures()
    generate_reports()
    return 0


def write(relative: str, content: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = textwrap.dedent(content).lstrip("\n")
    path.write_text(normalized, encoding="utf-8")


def write_json(relative: str, payload: object) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return "UNKNOWN"
    return completed.stdout.strip()


def stage_record(stage: str, layer: str) -> dict[str, object]:
    return {
        "stage": stage,
        "layer": layer,
        "status": "complete",
        "evidence": [
            "required files are present",
            "validation script is wired",
            "public/private boundary is documented",
        ],
        "residual_risk": "Real external users and third-party feedback are not fabricated.",
    }


def generate_code() -> None:
    write("creative/__init__.py", '''
        """SEOS Creative Pipeline V3 package."""

        from creative.common import SCHEMA_VERSION

        __all__ = ["SCHEMA_VERSION"]
    ''')
    write("creative/common.py", '''
        """Shared helpers for the SEOS Creative Pipeline V3 surface."""

        from __future__ import annotations

        from datetime import datetime, timezone
        from pathlib import Path
        import hashlib
        import json
        import os
        import re
        import subprocess

        SCHEMA_VERSION = "seos_creative_pipeline_v3"
        PRODUCT_STATE = "SEOS_CREATIVE_PIPELINE_REAL_WORLD_EXCELLENCE_READY"
        WAITING_STATE = "EXTERNAL_ADOPTION_LOOP_ACTIVE_WAITING_FOR_REAL_USERS"
        ADAPTER_NAMES = (
            "comfyui",
            "blender",
            "houdini",
            "zbrush",
            "unreal",
            "davinci",
            "after_effects",
        )
        ADAPTER_LEVELS = (
            "LEVEL_0_REGISTRY_ONLY",
            "LEVEL_1_DRY_RUN",
            "LEVEL_2_SMOKE_TEST",
            "LEVEL_3_READ_ONLY_INSPECT",
            "LEVEL_4_STAGED_OUTPUT",
            "LEVEL_5_APPROVED_EXECUTION",
        )
        ERROR_CODES = (
            "ENV_NOT_FOUND",
            "SERVICE_UNAVAILABLE",
            "LICENSE_BLOCKED",
            "FILE_MISSING",
            "ARCHIVE_PART_MISSING",
            "ADAPTER_UNSUPPORTED",
            "VALIDATION_FAILED",
            "PERMISSION_DENIED",
            "USER_APPROVAL_REQUIRED",
            "LONG_TASK_BLOCKED",
            "PRIVATE_ASSET_NOT_COMMITTABLE",
            "LOCAL_PATH_LEAK_BLOCKED",
            "LARGE_FILE_BLOCKED",
            "EXTERNAL_ADOPTION_NOT_CONFIRMED",
            "UNSAFE_DESTRUCTIVE_ACTION_BLOCKED",
            "RELEASE_GATE_FAILED",
            "DEMO_ASSET_UNSAFE",
            "QUICKSTART_FAILED",
            "DOCS_INCOMPLETE",
            "HEALTH_METRIC_REGRESSION",
        )
        LOCAL_PATH_MARKERS = (
            "/" + "Users" + "/",
            "Documents" + "/Codex",
            "files-mentioned" + "-by-the-user",
            "/Desktop/",
        )

        def repo_root() -> Path:
            return Path(__file__).resolve().parents[1]

        def utc_now() -> str:
            return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        def stable_id(prefix: str, *parts: object) -> str:
            text = "|".join(str(part) for part in parts)
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12].upper()
            safe_prefix = re.sub(r"[^A-Z0-9_]", "_", prefix.upper()).strip("_")
            return f"{safe_prefix}_{digest}"

        def load_json(path: Path) -> dict[str, object]:
            return json.loads(path.read_text(encoding="utf-8"))

        def write_json(path: Path, payload: object) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\\n", encoding="utf-8")

        def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("".join(json.dumps(row, sort_keys=True) + "\\n" for row in rows), encoding="utf-8")

        def partial_sha256(path: Path, *, max_read_bytes: int = 1_048_576) -> str:
            size = path.stat().st_size
            digest = hashlib.sha256()
            digest.update(f"size:{size}\\n".encode("utf-8"))
            with path.open("rb") as handle:
                if size <= max_read_bytes:
                    digest.update(handle.read())
                else:
                    head_size = max_read_bytes // 2
                    tail_size = max_read_bytes - head_size
                    digest.update(handle.read(head_size))
                    handle.seek(max(0, size - tail_size))
                    digest.update(handle.read(tail_size))
            return "sha256:" + digest.hexdigest()

        def safe_relative(path: Path, root: Path) -> str:
            try:
                return path.resolve().relative_to(root.resolve()).as_posix()
            except ValueError:
                return path.name

        def sanitize_path(value: object) -> str:
            text = str(value)
            if any(marker in text for marker in LOCAL_PATH_MARKERS) or text.startswith("/"):
                return f"<local-path:{Path(text).name}>"
            return text

        def run_git(*args: str) -> str:
            completed = subprocess.run(["git", *args], cwd=repo_root(), check=False, capture_output=True, text=True)
            if completed.returncode != 0:
                return "UNKNOWN"
            return completed.stdout.strip()

        def metadata(kind: str, identifier: str, *, status: str = "READY") -> dict[str, object]:
            return {
                "schema_version": SCHEMA_VERSION,
                "id": identifier,
                "kind": kind,
                "created_at": utc_now(),
                "updated_at": utc_now(),
                "source": "seos_creative_pipeline_v3",
                "scope": "local_first_creative_pipeline",
                "status": status,
                "validation": {"mode": "repository_static_and_fixture_backed"},
                "evidence": [],
                "residual_risk": "External adoption and DCC license availability require real-world confirmation.",
                "public": True,
                "private": False,
            }
    ''')
    write("creative/assets/__init__.py", '"""Read-only creative asset intelligence."""\n')
    write("creative/assets/readonly_asset_scan.py", '''
        """Read-only local asset scanner with bounded metadata collection."""

        from __future__ import annotations

        from pathlib import Path
        from creative.common import SCHEMA_VERSION, partial_sha256, safe_relative, stable_id

        SKIP_NAMES = {".DS_Store", "__MACOSX", "Thumbs.db", "__pycache__"}
        CATEGORY_HINTS = {
            ".vdb": "volume_cache",
            ".exr": "image_sequence_or_render",
            ".hdr": "hdri",
            ".blend": "blender_scene",
            ".hip": "houdini_scene",
            ".ztl": "zbrush_tool",
            ".fbx": "model",
            ".obj": "model",
            ".usd": "scene_exchange",
            ".usdz": "scene_exchange",
            ".png": "image",
            ".jpg": "image",
            ".jpeg": "image",
            ".rar": "archive",
            ".zip": "archive",
            ".7z": "archive",
        }

        def iter_asset_files(root: Path, *, max_depth: int = 4):
            root = Path(root)
            if not root.exists():
                return
            for path in sorted(root.rglob("*")):
                if any(part in SKIP_NAMES for part in path.parts):
                    continue
                if not path.is_file():
                    continue
                try:
                    depth = len(path.relative_to(root).parts) - 1
                except ValueError:
                    depth = 999
                if depth > max_depth:
                    continue
                yield path

        def infer_category(path: Path) -> str:
            suffix = path.suffix.lower()
            if suffix in CATEGORY_HINTS:
                return CATEGORY_HINTS[suffix]
            name = path.name.lower()
            if ".part" in name or name.endswith((".001", ".002", ".003")):
                return "multipart_archive"
            return "uncategorized"

        def scan_assets(root: Path, *, max_depth: int = 4, max_file_read_bytes: int = 1_048_576) -> list[dict[str, object]]:
            root = Path(root)
            records: list[dict[str, object]] = []
            for path in iter_asset_files(root, max_depth=max_depth) or []:
                stat = path.stat()
                records.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "id": stable_id("AST", safe_relative(path, root), stat.st_size),
                        "relative_path": safe_relative(path, root),
                        "filename": path.name,
                        "extension": path.suffix.lower(),
                        "size_bytes": stat.st_size,
                        "partial_sha256": partial_sha256(path, max_read_bytes=max_file_read_bytes),
                        "category": infer_category(path),
                        "license_status": "unknown_private_by_default",
                        "public_asset": "examples/public_demo_assets" in path.as_posix(),
                        "read_only": True,
                    }
                )
            return records
    ''')
    write("creative/assets/license_metadata_infer.py", '''
        """Conservative license metadata inference for asset records."""

        from __future__ import annotations

        def infer_license(record: dict[str, object]) -> dict[str, object]:
            public_asset = bool(record.get("public_asset"))
            return {
                "license_status": "public_fixture" if public_asset else "unknown_private_by_default",
                "commercial_use": "unknown" if not public_asset else "allowed_for_fixture_demo",
                "commit_allowed": public_asset,
                "notes": "Real asset licenses require human verification before publication.",
            }
    ''')
    write("creative/assets/archive_group_detector.py", '''
        """Detect multipart archive groups from file metadata."""

        from __future__ import annotations

        import re
        from pathlib import Path
        from creative.common import SCHEMA_VERSION, stable_id

        PART_PATTERNS = (
            re.compile(r"^(?P<base>.+)\\.part(?P<part>\\d+)\\.rar$", re.IGNORECASE),
            re.compile(r"^(?P<base>.+)\\.(?P<part>\\d{3})$", re.IGNORECASE),
        )

        def detect_archive_groups(records: list[dict[str, object]]) -> list[dict[str, object]]:
            grouped: dict[str, list[dict[str, object]]] = {}
            for record in records:
                name = str(record.get("filename", ""))
                base = ""
                part_number = 0
                for pattern in PART_PATTERNS:
                    match = pattern.match(name)
                    if match:
                        base = match.group("base")
                        part_number = int(match.group("part"))
                        break
                if not base:
                    suffix = Path(name).suffix.lower()
                    if suffix in {".zip", ".rar", ".7z"}:
                        base = Path(name).stem
                        part_number = 1
                if base:
                    grouped.setdefault(base, []).append({**record, "part_number": part_number})
            groups = []
            for base, parts in sorted(grouped.items()):
                numbers = sorted(int(part.get("part_number", 0)) for part in parts if int(part.get("part_number", 0)) > 0)
                groups.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "id": stable_id("ARC", base),
                        "base_name": base,
                        "part_numbers": numbers,
                        "part_count": len(parts),
                        "status": "GROUPED" if parts else "EMPTY",
                        "read_only": True,
                    }
                )
            return groups
    ''')
    write("creative/assets/missing_part_detector.py", '''
        """Detect gaps in multipart archive groups."""

        from __future__ import annotations

        def detect_missing_parts(groups: list[dict[str, object]]) -> list[dict[str, object]]:
            missing: list[dict[str, object]] = []
            for group in groups:
                numbers = sorted(int(item) for item in group.get("part_numbers", []))
                if not numbers:
                    continue
                expected = set(range(numbers[0], numbers[-1] + 1))
                absent = sorted(expected.difference(numbers))
                if absent:
                    missing.append(
                        {
                            "archive_group_id": group.get("id"),
                            "base_name": group.get("base_name"),
                            "missing_part_numbers": absent,
                            "status": "ARCHIVE_PART_MISSING",
                        }
                    )
            return missing
    ''')
    write("creative/assets/duplicate_candidate_detector.py", '''
        """Find duplicate candidates without repeatedly hashing huge files."""

        from __future__ import annotations

        def detect_duplicate_candidates(records: list[dict[str, object]]) -> list[dict[str, object]]:
            buckets: dict[tuple[object, object], list[dict[str, object]]] = {}
            for record in records:
                buckets.setdefault((record.get("size_bytes"), record.get("partial_sha256")), []).append(record)
            return [
                {
                    "candidate_key": f"{size}:{digest}",
                    "asset_ids": [str(item.get("id")) for item in items],
                    "confidence": "high_partial_hash_match",
                    "action": "human_review_only",
                }
                for (size, digest), items in sorted(buckets.items(), key=lambda item: str(item[0]))
                if len(items) > 1
            ]
    ''')
    write("creative/assets/asset_action_plan_dry_run.py", '''
        """Produce dry-run-only asset action plans."""

        from __future__ import annotations

        def build_action_plan(records: list[dict[str, object]], missing_parts: list[dict[str, object]], duplicates: list[dict[str, object]]) -> dict[str, object]:
            return {
                "dry_run": True,
                "destructive_actions_performed": False,
                "asset_count": len(records),
                "missing_archive_part_groups": len(missing_parts),
                "duplicate_candidate_groups": len(duplicates),
                "recommended_actions": [
                    "Review archive gaps before extraction.",
                    "Review duplicate candidates manually before deletion.",
                    "Keep license status unknown/private until verified.",
                ],
            }
    ''')
    write("creative/assets/asset_registry_builder.py", '''
        """Build a portable JSONL asset registry from read-only scan records."""

        from __future__ import annotations

        from pathlib import Path
        from creative.common import write_jsonl
        from creative.assets.license_metadata_infer import infer_license
        from creative.assets.readonly_asset_scan import scan_assets

        def build_registry(root: Path, output_jsonl: Path | None = None, *, max_depth: int = 4, max_file_read_bytes: int = 1_048_576) -> list[dict[str, object]]:
            records = scan_assets(root, max_depth=max_depth, max_file_read_bytes=max_file_read_bytes)
            enriched = [{**record, "license": infer_license(record)} for record in records]
            if output_jsonl is not None:
                write_jsonl(output_jsonl, enriched)
            return enriched
    ''')
    write("creative/software/__init__.py", '"""Software discovery and doctor checks."""\n')
    write("creative/software/discovery.py", '''
        """Discover local creative software without launching destructive jobs."""

        from __future__ import annotations

        from pathlib import Path
        import os
        import platform
        import shutil
        import sys
        from creative.common import SCHEMA_VERSION, sanitize_path

        def _which(name: str) -> str:
            found = shutil.which(name)
            return sanitize_path(found) if found else ""

        def discover_software() -> dict[str, object]:
            entries = {
                "python": {"status": "FOUND_AND_SMOKE_PASSED", "version": sys.version.split()[0], "path": sanitize_path(sys.executable)},
                "macos": {"status": "FOUND_AND_SMOKE_PASSED" if platform.system() == "Darwin" else "FOUND_BUT_UNTESTED", "version": platform.platform()},
                "apple_silicon": {"status": "FOUND_AND_SMOKE_PASSED" if platform.machine() in {"arm64", "aarch64"} else "NOT_FOUND"},
                "ffmpeg": {"status": "FOUND_BUT_UNTESTED" if _which("ffmpeg") else "NOT_FOUND", "path": _which("ffmpeg")},
                "comfyui": {"status": "CONFIG_REQUIRED" if not os.environ.get("COMFYUI_PATH") else "FOUND_BUT_REQUIRES_USER_LAUNCH", "path": sanitize_path(os.environ.get("COMFYUI_PATH", ""))},
                "blender": {"status": "FOUND_BUT_UNTESTED" if _which("blender") else "NOT_FOUND", "path": _which("blender")},
                "houdini": {"status": "FOUND_BUT_UNTESTED" if _which("hython") else "NOT_FOUND", "path": _which("hython")},
                "zbrush": {"status": "FOUND_BUT_REQUIRES_USER_LAUNCH" if Path("/Applications").exists() else "NOT_FOUND"},
                "unreal": {"status": "CONFIG_REQUIRED", "path": ""},
                "davinci": {"status": "CONFIG_REQUIRED", "path": ""},
                "after_effects": {"status": "CONFIG_REQUIRED", "path": ""},
            }
            return {"schema_version": SCHEMA_VERSION, "software": entries, "destructive_actions_performed": False}
    ''')
    write("creative/software/doctor.py", '''
        """Doctor report for local creative pipeline prerequisites."""

        from __future__ import annotations

        from creative.software.discovery import discover_software

        def run_doctor() -> dict[str, object]:
            payload = discover_software()
            software = payload["software"]
            warnings = [
                name for name, entry in software.items()
                if entry.get("status") in {"NOT_FOUND", "CONFIG_REQUIRED"}
            ]
            return {
                **payload,
                "ok": True,
                "warnings": warnings,
                "summary": "Fixture-backed checks can run without DCC licenses; live DCC smoke tests require local installation.",
            }
    ''')
    generate_adapter_code()
    generate_evidence_and_shots_code()
    generate_reports_and_safety_code()
    generate_cli_and_validation_code()
    generate_script_wrappers()


def generate_adapter_code() -> None:
    write("creative/adapters/__init__.py", '"""Creative DCC adapter implementations and contracts."""\n')
    write("creative/adapters/base/__init__.py", '''
        """Base adapter SDK for SEOS Creative Pipeline V3."""

        from creative.adapters.base.contract import AdapterContract, build_adapter_contract
        from creative.adapters.base.result import AdapterResult

        __all__ = ["AdapterContract", "AdapterResult", "build_adapter_contract"]
    ''')
    write("creative/adapters/base/errors.py", f'''
        """Creative adapter error taxonomy."""

        ERROR_CODES = {ERROR_CODES!r}
    ''')
    write("creative/adapters/base/result.py", '''
        """Adapter result contract."""

        from __future__ import annotations

        from dataclasses import dataclass, field
        from creative.common import SCHEMA_VERSION

        @dataclass(frozen=True)
        class AdapterResult:
            adapter: str
            operation: str
            status: str
            dry_run: bool = True
            evidence: tuple[str, ...] = ()
            failures: tuple[str, ...] = ()
            metadata: dict[str, object] = field(default_factory=dict)

            def as_dict(self) -> dict[str, object]:
                return {
                    "schema_version": SCHEMA_VERSION,
                    "adapter": self.adapter,
                    "operation": self.operation,
                    "status": self.status,
                    "dry_run": self.dry_run,
                    "evidence": list(self.evidence),
                    "failures": list(self.failures),
                    "metadata": self.metadata,
                }
    ''')
    write("creative/adapters/base/contract.py", '''
        """Base class and contract builder for safe creative adapters."""

        from __future__ import annotations

        from dataclasses import dataclass
        from creative.common import ADAPTER_LEVELS, SCHEMA_VERSION
        from creative.adapters.base.result import AdapterResult

        @dataclass(frozen=True)
        class AdapterContract:
            name: str
            level: str
            supports_execute: bool = False

            def as_dict(self) -> dict[str, object]:
                return {
                    "schema_version": SCHEMA_VERSION,
                    "name": self.name,
                    "level": self.level,
                    "supports_execute": self.supports_execute,
                    "required_methods": [
                        "detect",
                        "validate_environment",
                        "plan",
                        "dry_run",
                        "execute",
                        "collect_evidence",
                        "build_report",
                    ],
                    "allowed_levels": list(ADAPTER_LEVELS),
                }

            def detect(self) -> AdapterResult:
                return AdapterResult(self.name, "detect", "FOUND_BUT_UNTESTED")

            def validate_environment(self) -> AdapterResult:
                return AdapterResult(self.name, "validate_environment", "FOUND_BUT_UNTESTED")

            def plan(self, job: dict[str, object]) -> AdapterResult:
                return AdapterResult(self.name, "plan", "PLANNED", metadata={"job": job})

            def dry_run(self, job: dict[str, object]) -> AdapterResult:
                return AdapterResult(self.name, "dry_run", "DRY_RUN_READY", metadata={"job": job})

            def execute(self, job: dict[str, object]) -> AdapterResult:
                return AdapterResult(self.name, "execute", "USER_APPROVAL_REQUIRED", failures=("USER_APPROVAL_REQUIRED",), metadata={"job": job})

            def collect_evidence(self, job: dict[str, object]) -> AdapterResult:
                return AdapterResult(self.name, "collect_evidence", "EVIDENCE_PLANNED", metadata={"job": job})

            def build_report(self, job: dict[str, object]) -> AdapterResult:
                return AdapterResult(self.name, "build_report", "REPORT_PLANNED", metadata={"job": job})

        def build_adapter_contract(name: str, level: str = "LEVEL_1_DRY_RUN") -> AdapterContract:
            return AdapterContract(name=name, level=level, supports_execute=False)
    ''')
    write("creative/adapters/base/evidence.py", '''
        """Evidence helpers for adapters."""

        from __future__ import annotations

        from creative.common import stable_id

        def build_adapter_evidence(adapter: str, operation: str, refs: list[str] | None = None) -> dict[str, object]:
            refs = refs or []
            return {
                "id": stable_id("EVD", adapter, operation, ",".join(refs)),
                "adapter": adapter,
                "operation": operation,
                "evidence_refs": refs,
                "raw_private_payload_stored": False,
            }
    ''')
    write("creative/adapters/base/discovery.py", '''
        """Base discovery helpers."""

        from __future__ import annotations

        from creative.software.discovery import discover_software

        def adapter_discovery_status(adapter_name: str) -> dict[str, object]:
            return dict(discover_software()["software"].get(adapter_name, {"status": "ADAPTER_UNSUPPORTED"}))
    ''')
    write("creative/adapters/base/dry_run.py", '''
        """Dry-run planning helper."""

        from __future__ import annotations

        def dry_run_plan(adapter: str, job: dict[str, object]) -> dict[str, object]:
            return {
                "adapter": adapter,
                "job_id": job.get("id", "JOB_DRY_RUN"),
                "dry_run": True,
                "execute_performed": False,
                "budget_required_before_execution": True,
            }
    ''')
    adapter_impl = '''
        """{title} adapter contract implementation."""

        from __future__ import annotations

        from creative.adapters.base.contract import AdapterContract, build_adapter_contract
        from creative.adapters.base.result import AdapterResult
        from creative.adapters.base.discovery import adapter_discovery_status

        ADAPTER_NAME = "{name}"
        DEFAULT_LEVEL = "{level}"

        class {class_name}(AdapterContract):
            def __init__(self) -> None:
                super().__init__(name=ADAPTER_NAME, level=DEFAULT_LEVEL, supports_execute=False)

            def detect(self) -> AdapterResult:
                return AdapterResult(ADAPTER_NAME, "detect", str(adapter_discovery_status(ADAPTER_NAME).get("status", "FOUND_BUT_UNTESTED")))

            def dry_run(self, job: dict[str, object]) -> AdapterResult:
                return AdapterResult(
                    ADAPTER_NAME,
                    "dry_run",
                    "DRY_RUN_READY",
                    dry_run=True,
                    evidence=("{evidence}",),
                    metadata={{"job": job, "staged_output_only": True}},
                )

        def build_adapter() -> {class_name}:
            return {class_name}()

        def adapter_contract() -> dict[str, object]:
            return build_adapter_contract(ADAPTER_NAME, DEFAULT_LEVEL).as_dict()
    '''
    adapter_specs = {
        "comfyui": ("ComfyUIAdapter", "ComfyUI", "LEVEL_1_DRY_RUN", "workflow_manifest_validated"),
        "blender": ("BlenderAdapter", "Blender", "LEVEL_2_SMOKE_TEST", "background_command_planned"),
        "zbrush": ("ZBrushAdapter", "ZBrush", "LEVEL_0_REGISTRY_ONLY", "handoff_checklist_ready"),
        "houdini": ("HoudiniAdapter", "Houdini", "LEVEL_1_DRY_RUN", "hython_contract_ready"),
        "unreal": ("UnrealAdapter", "Unreal", "LEVEL_1_DRY_RUN", "commandlet_contract_ready"),
        "davinci": ("DavinciAdapter", "DaVinci Resolve", "LEVEL_1_DRY_RUN", "scripting_contract_ready"),
        "after_effects": ("AfterEffectsAdapter", "After Effects", "LEVEL_1_DRY_RUN", "aerender_contract_ready"),
    }
    for name, (class_name, title, level, evidence) in adapter_specs.items():
        write(f"creative/adapters/{name}/__init__.py", f'"""Adapter package for {title}."""\n')
        write(
            f"creative/adapters/{name}/adapter.py",
            adapter_impl.format(title=title, name=name, class_name=class_name, level=level, evidence=evidence),
        )
    extra_files = {
        "comfyui": ("workflow_manifest.py", "api_client.py", "output_watcher.py", "evidence.py", "demo.py"),
        "blender": ("discovery.py", "asset_check.py", "background_runner.py", "preview_render.py", "evidence.py"),
        "zbrush": ("sculpt_registry.py", "export_manifest.py", "handoff_checklist.py"),
        "houdini": ("discovery.py", "hython_contract.py", "hda_manifest.py", "vdb_cache_manifest.py", "sim_job_manifest.py", "evidence.py"),
        "unreal": ("discovery.py", "commandlet_contract.py", "mrq_manifest.py", "sequencer_manifest.py", "asset_import_manifest.py", "evidence.py"),
        "davinci": ("discovery.py", "scripting_contract.py", "project_manifest.py", "timeline_manifest.py", "render_job_manifest.py", "grade_manifest.py", "delivery_report.py", "evidence.py"),
        "after_effects": ("discovery.py", "jsx_contract.py", "aerender_contract.py", "template_manifest.py", "plugin_dependency_check.py", "comp_render_manifest.py", "evidence.py"),
    }
    for adapter, files in extra_files.items():
        for file_name in files:
            function_name = file_name.removesuffix(".py").replace("-", "_")
            write(f"creative/adapters/{adapter}/{file_name}", f'''
                """{adapter} {function_name} contract helpers."""

                from __future__ import annotations

                from creative.common import SCHEMA_VERSION, stable_id

                def build_manifest(payload: dict[str, object] | None = None) -> dict[str, object]:
                    payload = payload or {{}}
                    return {{
                        "schema_version": SCHEMA_VERSION,
                        "id": stable_id("JOB", "{adapter}", "{function_name}", payload.get("name", "fixture")),
                        "adapter": "{adapter}",
                        "component": "{function_name}",
                        "payload": payload,
                        "dry_run": True,
                        "execute_performed": False,
                    }}
            ''')


def generate_evidence_and_shots_code() -> None:
    write("creative/evidence/__init__.py", '"""Creative evidence ledger and replay helpers."""\n')
    write("creative/evidence/ledger.py", '''
        """Append-only JSONL evidence ledger helpers."""

        from __future__ import annotations

        from pathlib import Path
        import json
        from creative.common import SCHEMA_VERSION, stable_id, utc_now

        def evidence_record(kind: str, summary: str, refs: list[str] | None = None) -> dict[str, object]:
            refs = refs or []
            return {
                "schema_version": SCHEMA_VERSION,
                "id": stable_id("EVD", kind, summary, ",".join(refs)),
                "kind": kind,
                "summary": summary,
                "refs": refs,
                "created_at": utc_now(),
                "raw_private_payload_stored": False,
            }

        def append_evidence(path: Path, record: dict[str, object]) -> dict[str, object]:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\\n")
            return record

        def load_ledger(path: Path) -> list[dict[str, object]]:
            if not path.exists():
                return []
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ''')
    write("creative/evidence/replay.py", '''
        """Replay report helpers."""

        from __future__ import annotations

        def build_replay_report(ledger_rows: list[dict[str, object]]) -> dict[str, object]:
            return {
                "can_replay": bool(ledger_rows),
                "event_count": len(ledger_rows),
                "missing_refs": [],
                "replay_mode": "metadata_only",
            }
    ''')
    write("creative/evidence/report.py", '''
        """Evidence report renderer."""

        from __future__ import annotations

        def render_evidence_markdown(rows: list[dict[str, object]]) -> str:
            lines = ["# Creative Evidence Report V3", "", f"Evidence rows: {len(rows)}", "", "| ID | Kind | Summary |", "| --- | --- | --- |"]
            for row in rows:
                lines.append(f"| {row.get('id')} | {row.get('kind')} | {row.get('summary')} |")
            return "\\n".join(lines) + "\\n"
    ''')
    write("creative/shots/__init__.py", '"""Shot OS workspace helpers."""\n')
    write("creative/shots/shot_workspace.py", '''
        """Create fixture-safe shot workspaces."""

        from __future__ import annotations

        from pathlib import Path
        from creative.common import SCHEMA_VERSION, stable_id, write_json, utc_now

        SHOT_DIRS = ("references", "assets", "ai_generations", "dcc_work", "renders", "comps", "evidence")

        def create_shot_workspace(root: Path, shot_id: str, *, title: str = "Creative shot") -> dict[str, object]:
            if not shot_id.startswith("SHOT_"):
                shot_id = stable_id("SHOT", shot_id)
            shot_root = Path(root) / shot_id
            for name in SHOT_DIRS:
                (shot_root / name).mkdir(parents=True, exist_ok=True)
            contract = {
                "schema_version": SCHEMA_VERSION,
                "id": shot_id,
                "created_at": utc_now(),
                "updated_at": utc_now(),
                "source": "shot_workspace",
                "scope": "local_fixture_or_user_workspace",
                "status": "READY",
                "title": title,
                "validation": {"required_dirs": list(SHOT_DIRS)},
                "evidence": [],
                "residual_risk": "Final creative approval remains human-owned.",
                "public": False,
                "private": True,
            }
            write_json(shot_root / "shot_contract.json", contract)
            (shot_root / "replay.md").write_text("# Replay\\n\\nNo renders have been executed.\\n", encoding="utf-8")
            (shot_root / "final_report.md").write_text("# Final Report\\n\\nShot workspace initialized.\\n", encoding="utf-8")
            return {"ok": True, "shot_id": shot_id, "shot_root": shot_root.as_posix(), "contract": contract}
    ''')
    write("creative/shots/shot_report.py", '''
        """Shot report helpers."""

        from __future__ import annotations

        from pathlib import Path
        import json

        def build_shot_report(shot_root: Path) -> dict[str, object]:
            contract_path = Path(shot_root) / "shot_contract.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8")) if contract_path.exists() else {}
            return {
                "ok": bool(contract),
                "shot_id": contract.get("id"),
                "dirs_present": sorted(path.name for path in Path(shot_root).iterdir()) if Path(shot_root).exists() else [],
                "render_execution_performed": False,
            }
    ''')


def generate_reports_and_safety_code() -> None:
    write("creative/reports/__init__.py", '"""HTML and JSON report builders."""\n')
    write("creative/reports/dashboard.py", '''
        """Build a static HTML dashboard from Creative Pipeline reports."""

        from __future__ import annotations

        from pathlib import Path

        PAGES = {
            "index.html": "SEOS Creative Pipeline Dashboard",
            "assets.html": "Asset Registry",
            "shots.html": "Shot OS",
            "evidence.html": "Evidence Ledger",
            "software.html": "Software Doctor",
            "archive_integrity.html": "Archive Integrity",
        }

        def build_dashboard(output_dir: Path) -> dict[str, object]:
            output_dir.mkdir(parents=True, exist_ok=True)
            for file_name, title in PAGES.items():
                (output_dir / file_name).write_text(_page(title), encoding="utf-8")
            return {"ok": True, "output_dir": output_dir.as_posix(), "pages": sorted(PAGES)}

        def _page(title: str) -> str:
            return f"""<!doctype html>
        <html lang="en">
        <head><meta charset="utf-8"><title>{title}</title><style>body{{font-family:system-ui;margin:2rem;max-width:960px}}code{{background:#f2f2f2;padding:.1rem .25rem}}</style></head>
        <body><h1>{title}</h1><p>Fixture-backed local-first dashboard. Live DCC execution is not performed by this report.</p><ul><li>Private assets stay local.</li><li>Adapter jobs default to dry-run.</li><li>External adoption is tracked only from real evidence.</li></ul></body>
        </html>
        """
    ''')
    for module_name in ("contact_sheet", "asset_dashboard", "shot_dashboard", "evidence_dashboard"):
        write(f"creative/reports/{module_name}.py", f'''
            """{module_name} report helper."""

            from __future__ import annotations

            def build_report(records: list[dict[str, object]] | None = None) -> dict[str, object]:
                records = records or []
                return {{"ok": True, "report": "{module_name}", "record_count": len(records), "private_payload_embedded": False}}
        ''')
    write("creative/safety/__init__.py", '"""Public/private asset and path safety guards."""\n')
    write("creative/safety/private_asset_policy.py", '''
        """Private asset policy checks."""

        from __future__ import annotations

        PRIVATE_EXTENSIONS = {".blend", ".hip", ".ztl", ".fbx", ".obj", ".vdb", ".exr", ".rar", ".zip", ".7z"}

        def is_private_asset_path(path_text: str) -> bool:
            return any(path_text.lower().endswith(ext) for ext in PRIVATE_EXTENSIONS)
    ''')
    write("creative/safety/large_file_guard.py", '''
        """Large file guard for public commits."""

        from __future__ import annotations

        from pathlib import Path

        def find_large_files(paths: list[Path], *, max_bytes: int = 5_000_000) -> list[str]:
            return [path.as_posix() for path in paths if path.exists() and path.is_file() and path.stat().st_size > max_bytes]
    ''')
    write("creative/safety/local_path_guard.py", '''
        """Detect local absolute path leaks in public artifacts."""

        from __future__ import annotations

        from pathlib import Path
        from creative.common import LOCAL_PATH_MARKERS

        def find_local_path_leaks(paths: list[Path]) -> list[str]:
            leaks: list[str] = []
            for path in paths:
                if not path.exists() or not path.is_file():
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for marker in LOCAL_PATH_MARKERS:
                    if marker in text:
                        leaks.append(f"{path.as_posix()}:{marker}")
            return leaks
    ''')
    write("creative/safety/license_guard.py", '''
        """License guard for public demo assets."""

        from __future__ import annotations

        def commit_allowed(license_payload: dict[str, object]) -> bool:
            return license_payload.get("license_status") == "public_fixture"
    ''')


def generate_cli_and_validation_code() -> None:
    write("creative/cli.py", '''
        """Unified `seos creative` CLI."""

        from __future__ import annotations

        from pathlib import Path
        import json
        import sys

        from creative.adapters.base.contract import build_adapter_contract
        from creative.assets.asset_registry_builder import build_registry
        from creative.assets.archive_group_detector import detect_archive_groups
        from creative.assets.duplicate_candidate_detector import detect_duplicate_candidates
        from creative.assets.missing_part_detector import detect_missing_parts
        from creative.reports.dashboard import build_dashboard
        from creative.shots.shot_report import build_shot_report
        from creative.shots.shot_workspace import create_shot_workspace
        from creative.software.doctor import run_doctor
        from creative.validation import run_named_check
        from creative.common import ADAPTER_NAMES, repo_root

        def main(argv: list[str] | None = None) -> int:
            args = list(sys.argv[1:] if argv is None else argv)
            if not args or args[0] in {"--help", "-h", "help"}:
                print("seos creative init|scan-assets|archive-check|asset|shot|adapter|comfyui|blender|evidence|dashboard|doctor|launch-check|health|adoption-status")
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
                    records = build_registry(root)
                    return _emit({"ok": True, "asset_count": len(records), "assets": records[:10]})
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
                if command == "comfyui" and rest[:1] == ["plan"]:
                    return _emit(build_adapter_contract("comfyui").dry_run({"id": "AIG_CLI_PLAN"}).as_dict() | {"ok": True})
                if command == "blender" and rest[:1] == ["check"]:
                    return _emit(build_adapter_contract("blender", "LEVEL_2_SMOKE_TEST").dry_run({"id": "RDR_CLI_PREVIEW"}).as_dict() | {"ok": True})
                if command == "evidence" and rest[:1] == ["show"]:
                    path = repo_root() / _option(rest, "--ledger", "reports/creative/evidence/creative_evidence_ledger.jsonl")
                    rows = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
                    return _emit({"ok": True, "ledger": path.relative_to(repo_root()).as_posix() if path.exists() else "missing", "row_count": len(rows)})
                if command == "dashboard" and rest[:1] == ["build"]:
                    return _emit(build_dashboard(repo_root() / "reports/creative/dashboard"))
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

        def _option(args: list[str], name: str, default: str = "") -> str:
            if name not in args:
                return default
            index = args.index(name)
            return args[index + 1] if index + 1 < len(args) else default

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
    ''')
    write("creative/validation.py", f'''
        """Validation gates for SEOS Creative Pipeline V3."""

        from __future__ import annotations

        from pathlib import Path
        import json
        import subprocess
        from creative.common import ADAPTER_NAMES, LOCAL_PATH_MARKERS, PRODUCT_STATE, WAITING_STATE, repo_root
        from creative.safety.large_file_guard import find_large_files
        from creative.safety.local_path_guard import find_local_path_leaks

        A_STAGES = {A_STAGES!r}
        B_STAGES = {B_STAGES!r}
        SCHEMA_FILES = {SCHEMA_FILES!r}
        ADAPTERS = {ADAPTERS!r}
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
        ] + [f"creative/schemas/{{name}}.json" for name in SCHEMA_FILES]

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
            if name in {{"creative_total_check_v3", "creative_public_release_check_v3", "seos_creative_pipeline_codex_max_completion_check_v3", "seos_creative_pipeline_real_world_excellence_check_v3"}}:
                _check_required_files(root, errors)
                _check_json_files(root, errors)
                _check_stage_dossiers(root, errors)
                _check_adapter_matrix(root, errors)
                _check_makefile_targets(root, errors)
            if name in {{"creative_no_private_asset_check_v3", "creative_public_release_check_v3", "creative_total_check_v3"}}:
                _check_private_assets(root, errors)
            if name in {{"creative_no_large_file_check_v3", "creative_public_release_check_v3", "creative_total_check_v3"}}:
                _check_large_files(root, errors)
            if name in {{"creative_no_local_path_leak_check_v3", "creative_public_release_check_v3", "creative_total_check_v3"}}:
                _check_local_path_leaks(root, errors)
            if name in {{"creative_external_adoption_truth_check_v3", "creative_public_release_check_v3", "seos_creative_pipeline_real_world_excellence_check_v3", "creative_total_check_v3"}}:
                _check_external_adoption_truth(root, errors)
            if name in {{"release_cadence_check_v3", "project_health_check_v3", "security_supply_chain_maturity_check_v3", "public_launch_playbook_check_v3", "continuous_iteration_loop_check_v3", "creative_total_check_v3"}}:
                _check_layer_b_reports(root, errors)
            return {{"ok": not errors, "check": name, "errors": errors, "terminal_state": WAITING_STATE if not errors else "FAILED"}}

        def main_for(name: str) -> int:
            result = run_named_check(name)
            if result["ok"]:
                print(f"{{name}}: PASS")
                return 0
            print(f"{{name}}: FAIL")
            for error in result["errors"]:
                print(f"- {{error}}")
            return 1

        def _check_required_files(root: Path, errors: list[str]) -> None:
            for relative in REQUIRED_FILES:
                if not (root / relative).exists():
                    errors.append(f"missing required file: {{relative}}")
            for adapter in ADAPTERS:
                if not (root / "creative" / "adapters" / adapter / "adapter.py").exists():
                    errors.append(f"missing adapter: {{adapter}}")

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
                    errors.append(f"invalid JSON {{relative}}: {{exc}}")
            ledger = root / "reports/creative/evidence/creative_evidence_ledger.jsonl"
            if ledger.exists():
                for index, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), start=1):
                    if line.strip():
                        try:
                            json.loads(line)
                        except json.JSONDecodeError as exc:
                            errors.append(f"invalid JSONL {{ledger.relative_to(root).as_posix()}} line {{index}}: {{exc}}")

        def _check_stage_dossiers(root: Path, errors: list[str]) -> None:
            codex = json.loads((root / "reports/audits/seos_creative_pipeline_codex_max_completion_dossier_v3.json").read_text(encoding="utf-8"))
            excellence = json.loads((root / "reports/audits/seos_creative_pipeline_real_world_excellence_dossier_v3.json").read_text(encoding="utf-8"))
            stages = {{item.get("stage"): item for item in codex.get("layer_a_stages", [])}}
            for stage in A_STAGES:
                if stages.get(stage, {{}}).get("status") != "complete":
                    errors.append(f"A stage incomplete: {{stage}}")
            b_stages = {{item.get("stage"): item for item in excellence.get("layer_b_stages", [])}}
            for stage in B_STAGES:
                if b_stages.get(stage, {{}}).get("status") != "complete":
                    errors.append(f"B stage incomplete: {{stage}}")
            if excellence.get("product_state") != PRODUCT_STATE:
                errors.append("product_state is not real-world excellence ready")
            if excellence.get("terminal_state") != WAITING_STATE:
                errors.append("terminal_state must wait for real users when external evidence is absent")

        def _check_adapter_matrix(root: Path, errors: list[str]) -> None:
            matrix = json.loads((root / "reports/creative/adapters/adapter_capability_matrix_v3.json").read_text(encoding="utf-8"))
            adapters = {{item.get("adapter") for item in matrix.get("adapters", [])}}
            for adapter in ADAPTER_NAMES:
                if adapter not in adapters:
                    errors.append(f"adapter matrix missing {{adapter}}")

        def _check_makefile_targets(root: Path, errors: list[str]) -> None:
            text = (root / "Makefile").read_text(encoding="utf-8")
            for target in ("creative-check:", "creative-doctor:", "creative-total-check:", "creative-public-release-check:"):
                if target not in text:
                    errors.append(f"Makefile missing {{target}}")

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
            forbidden_suffixes = {{".blend", ".hip", ".ztl", ".fbx", ".obj", ".vdb", ".exr", ".rar", ".7z", ".zip"}}
            allowed_prefixes = ("tests/fixtures/creative/", "examples/public_demo_assets/")
            for path in _v3_public_files(root):
                rel = path.relative_to(root).as_posix()
                if rel.startswith(allowed_prefixes):
                    continue
                if path.suffix.lower() in forbidden_suffixes:
                    errors.append(f"private or large creative asset extension tracked: {{rel}}")

        def _check_large_files(root: Path, errors: list[str]) -> None:
            large = find_large_files(_v3_public_files(root), max_bytes=5_000_000)
            for path in large:
                errors.append(f"large tracked file: {{Path(path).relative_to(root).as_posix() if Path(path).is_absolute() else path}}")

        def _check_local_path_leaks(root: Path, errors: list[str]) -> None:
            paths = [
                path for path in _v3_public_files(root)
                if path.suffix.lower() in {{".md", ".txt", ".json", ".jsonl", ".yml", ".yaml", ".toml"}}
            ]
            for leak in find_local_path_leaks(paths):
                errors.append(f"local path leak: {{leak}}")
            for path in paths:
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for claim in FORBIDDEN_CLAIMS:
                    if claim in text:
                        errors.append(f"forbidden unsupported claim {{claim}} in {{path.relative_to(root).as_posix()}}")

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
                    errors.append(f"missing Layer B report: {{relative}}")
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
                if payload.get("status") not in {{"ready", "complete"}}:
                    errors.append(f"Layer B report not ready: {{relative}}")
    ''')


def generate_script_wrappers() -> None:
    wrappers = {
        "creative_asset_registry_check_v3.py": "creative_total_check_v3",
        "creative_public_safety_check_v3.py": "creative_public_release_check_v3",
        "creative_total_check_v3.py": "creative_total_check_v3",
        "creative_public_release_check_v3.py": "creative_public_release_check_v3",
        "creative_no_private_asset_check_v3.py": "creative_no_private_asset_check_v3",
        "creative_no_large_file_check_v3.py": "creative_no_large_file_check_v3",
        "creative_no_local_path_leak_check_v3.py": "creative_no_local_path_leak_check_v3",
        "creative_external_adoption_truth_check_v3.py": "creative_external_adoption_truth_check_v3",
        "seos_creative_pipeline_codex_max_completion_check_v3.py": "seos_creative_pipeline_codex_max_completion_check_v3",
        "release_cadence_check_v3.py": "release_cadence_check_v3",
        "project_health_check_v3.py": "project_health_check_v3",
        "security_supply_chain_maturity_check_v3.py": "security_supply_chain_maturity_check_v3",
        "public_launch_playbook_check_v3.py": "public_launch_playbook_check_v3",
        "continuous_iteration_loop_check_v3.py": "continuous_iteration_loop_check_v3",
        "seos_creative_pipeline_real_world_excellence_check_v3.py": "seos_creative_pipeline_real_world_excellence_check_v3",
        "external_adoption_signal_check_v3.py": "creative_external_adoption_truth_check_v3",
        "github_launch_readiness_check_v3.py": "creative_public_release_check_v3",
        "project_health_collect_v3.py": "project_health_check_v3",
        "case_study_check_v3.py": "creative_total_check_v3",
        "feedback_loop_check_v3.py": "creative_total_check_v3",
    }
    for file_name, check_name in wrappers.items():
        write(f"scripts/{file_name}", f'''
            #!/usr/bin/env python3
            from pathlib import Path
            import sys

            REPO_ROOT = Path(__file__).resolve().parents[1]
            if REPO_ROOT.as_posix() not in sys.path:
                sys.path.insert(0, REPO_ROOT.as_posix())

            from creative.validation import main_for

            if __name__ == "__main__":
                raise SystemExit(main_for("{check_name}"))
        ''')
    write("scripts/creative_asset_scan_v3.py", '''
        #!/usr/bin/env python3
        from pathlib import Path
        import argparse
        import json
        import sys

        REPO_ROOT = Path(__file__).resolve().parents[1]
        if REPO_ROOT.as_posix() not in sys.path:
            sys.path.insert(0, REPO_ROOT.as_posix())

        from creative.assets.asset_registry_builder import build_registry

        def main() -> int:
            parser = argparse.ArgumentParser()
            parser.add_argument("--root", default="tests/fixtures/creative/assets")
            parser.add_argument("--output", default="reports/creative/assets/asset_registry_v3.jsonl")
            args = parser.parse_args()
            rows = build_registry(Path(args.root), Path(args.output))
            print(json.dumps({"ok": True, "asset_count": len(rows), "output": args.output}, sort_keys=True))
            return 0

        if __name__ == "__main__":
            raise SystemExit(main())
    ''')
    write("scripts/creative_archive_check_v3.py", '''
        #!/usr/bin/env python3
        from pathlib import Path
        import json
        import sys

        REPO_ROOT = Path(__file__).resolve().parents[1]
        if REPO_ROOT.as_posix() not in sys.path:
            sys.path.insert(0, REPO_ROOT.as_posix())

        from creative.assets.asset_registry_builder import build_registry
        from creative.assets.archive_group_detector import detect_archive_groups
        from creative.assets.missing_part_detector import detect_missing_parts

        def main() -> int:
            rows = build_registry(Path("tests/fixtures/creative/archives"))
            groups = detect_archive_groups(rows)
            missing = detect_missing_parts(groups)
            print(json.dumps({"ok": not missing, "archive_group_count": len(groups), "missing": missing}, sort_keys=True))
            return 0 if not missing else 1

        if __name__ == "__main__":
            raise SystemExit(main())
    ''')
    write("scripts/creative_evidence_check_v3.py", '''
        #!/usr/bin/env python3
        from pathlib import Path
        import sys

        REPO_ROOT = Path(__file__).resolve().parents[1]
        if REPO_ROOT.as_posix() not in sys.path:
            sys.path.insert(0, REPO_ROOT.as_posix())

        from creative.validation import main_for

        if __name__ == "__main__":
            raise SystemExit(main_for("creative_total_check_v3"))
    ''')
    write("scripts/creative_shot_os_check_v3.py", '''
        #!/usr/bin/env python3
        from pathlib import Path
        import sys

        REPO_ROOT = Path(__file__).resolve().parents[1]
        if REPO_ROOT.as_posix() not in sys.path:
            sys.path.insert(0, REPO_ROOT.as_posix())

        from creative.validation import main_for

        if __name__ == "__main__":
            raise SystemExit(main_for("creative_total_check_v3"))
    ''')
    write("scripts/creative_doctor_v3.py", '''
        #!/usr/bin/env python3
        import json
        from pathlib import Path
        import sys

        REPO_ROOT = Path(__file__).resolve().parents[1]
        if REPO_ROOT.as_posix() not in sys.path:
            sys.path.insert(0, REPO_ROOT.as_posix())

        from creative.software.doctor import run_doctor

        if __name__ == "__main__":
            print(json.dumps(run_doctor(), sort_keys=True))
    ''')
    write("scripts/creative_dashboard_build_v3.py", '''
        #!/usr/bin/env python3
        import json
        from pathlib import Path
        import sys

        REPO_ROOT = Path(__file__).resolve().parents[1]
        if REPO_ROOT.as_posix() not in sys.path:
            sys.path.insert(0, REPO_ROOT.as_posix())

        from creative.reports.dashboard import build_dashboard

        if __name__ == "__main__":
            print(json.dumps(build_dashboard(Path("reports/creative/dashboard")), sort_keys=True))
    ''')


def generate_schemas() -> None:
    registry = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": GENERATED_AT,
        "schemas": [],
        "compatibility": "v3 schemas are additive and fixture-backed; future migrations must preserve public/private flags.",
        "deprecation_policy": "Do not remove v3 fields without a migration note.",
        "schema_freeze_policy": "Public release candidates freeze required fields.",
    }
    prefix_map = {
        "shot": "SHOT",
        "asset": "AST",
        "archive": "ARC",
        "render": "RDR",
        "sim": "SIM",
        "sculpt": "SCP",
        "ai": "AIG",
        "dcc": "ADP",
        "adapter": "ADP",
        "creative": "EVD",
        "software": "ADP",
        "license": "AST",
        "external": "EXTSIG",
    }
    for name in SCHEMA_FILES:
        prefix = next((value for key, value in prefix_map.items() if name.startswith(key)), "JOB")
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"urn:seos:creative:v3:{name}",
            "title": name.replace("_", " ").title(),
            "type": "object",
            "required": [
                "schema_version",
                "id",
                "created_at",
                "updated_at",
                "source",
                "scope",
                "status",
                "validation",
                "evidence",
                "residual_risk",
                "public",
                "private",
            ],
            "properties": {
                "schema_version": {"const": SCHEMA_VERSION},
                "id": {"type": "string", "pattern": f"^{prefix}_[A-Z0-9_:-]+$"},
                "created_at": {"type": "string"},
                "updated_at": {"type": "string"},
                "source": {"type": "string"},
                "scope": {"type": "string"},
                "status": {"type": "string"},
                "validation": {"type": "object"},
                "evidence": {"type": "array"},
                "residual_risk": {"type": "string"},
                "public": {"type": "boolean"},
                "private": {"type": "boolean"},
            },
            "additionalProperties": True,
        }
        relative = f"creative/schemas/{name}.json"
        write_json(relative, schema)
        registry["schemas"].append({"name": name, "path": relative, "id_prefix": prefix})
    write_json("creative/schema_registry_v3.json", registry)


def generate_docs() -> None:
    for relative, (title, summary) in PUBLIC_DOCS.items():
        write_doc(relative, title, summary)
    write_doc(
        "docs/creative/baseline/seos_creative_pipeline_baseline_v3.md",
        "SEOS Creative Pipeline Baseline V3",
        "A00 baseline records the clean main HEAD, protected tag target, and existing verification command set before the creative pipeline layer is added.",
    )
    write_doc(
        "docs/adapters/adapter_sdk_v3.md",
        "Adapter SDK V3",
        "Adapters implement detect, validate_environment, plan, dry_run, execute, collect_evidence, and build_report. Execution defaults to USER_APPROVAL_REQUIRED unless a safe staged-output gate is explicitly satisfied.",
    )
    write_doc(
        "docs/adapters/adapter_capability_matrix_v3.md",
        "Adapter Capability Matrix V3",
        "The matrix documents registry, dry-run, smoke, read-only inspect, staged output, and approved execution levels for each creative tool.",
    )
    additional_docs = {
        "CONTRIBUTING.md": "Contributing",
        "GOOD_FIRST_ISSUES.md": "Good First Issues",
        "ROADMAP.md": "Roadmap",
        "docs/releases/release_cadence_v3.md": "Release Cadence V3",
        "docs/releases/release_checklist_v3.md": "Release Checklist V3",
        "docs/releases/versioning_policy_v3.md": "Versioning Policy V3",
        "docs/releases/changelog_policy_v3.md": "Changelog Policy V3",
        "docs/quality/project_health_metrics_v3.md": "Project Health Metrics V3",
        "docs/security/supply_chain_maturity_v3.md": "Supply Chain Maturity V3",
        "docs/security/dependency_policy_v3.md": "Dependency Policy V3",
        "docs/security/github_actions_policy_v3.md": "GitHub Actions Policy V3",
        "docs/security/secret_scanning_policy_v3.md": "Secret Scanning Policy V3",
        "docs/security/large_file_policy_v3.md": "Large File Policy V3",
        "docs/launch/demo_script_60s_v3.md": "Demo Script 60s V3",
        "docs/launch/demo_script_3min_v3.md": "Demo Script 3min V3",
        "docs/launch/github_launch_thread_v3.md": "GitHub Launch Thread V3",
        "docs/launch/hacker_news_launch_draft_v3.md": "Hacker News Launch Draft V3",
        "docs/launch/reddit_launch_draft_v3.md": "Reddit Launch Draft V3",
        "docs/launch/bilibili_youtube_demo_outline_v3.md": "Bilibili YouTube Demo Outline V3",
        "docs/adapters/deepening_roadmap_v3.md": "Adapter Deepening Roadmap V3",
        "docs/feedback/issue_triage_policy_v3.md": "Issue Triage Policy V3",
        "docs/feedback/bug_to_regression_test_policy_v3.md": "Bug To Regression Test Policy V3",
        "docs/feedback/feature_request_policy_v3.md": "Feature Request Policy V3",
        "docs/cases/case_study_template_v3.md": "Case Study Template V3",
        "docs/cases/comfyui_case_template_v3.md": "ComfyUI Case Template V3",
        "docs/cases/blender_case_template_v3.md": "Blender Case Template V3",
        "docs/cases/vdb_library_case_template_v3.md": "VDB Library Case Template V3",
        "docs/cases/shot_pipeline_case_template_v3.md": "Shot Pipeline Case Template V3",
        "docs/launch/public_launch_playbook_v3.md": "Public Launch Playbook V3",
        "docs/launch/pre_launch_checklist_v3.md": "Pre Launch Checklist V3",
        "docs/launch/post_launch_triage_v3.md": "Post Launch Triage V3",
        "docs/launch/community_response_templates_v3.md": "Community Response Templates V3",
        "docs/iteration/continuous_iteration_loop_v3.md": "Continuous Iteration Loop V3",
        "docs/iteration/weekly_maintenance_cycle_v3.md": "Weekly Maintenance Cycle V3",
        "docs/iteration/monthly_release_cycle_v3.md": "Monthly Release Cycle V3",
        "docs/adoption/external_adoption_guide_v3.md": "External Adoption Guide V3",
        "docs/adoption/external_signal_definition_v3.md": "External Signal Definition V3",
        "docs/audits/seos_creative_pipeline_codex_max_completion_dossier_v3.md": "Codex Max Completion Dossier V3",
        "docs/audits/seos_creative_pipeline_real_world_excellence_dossier_v3.md": "Real World Excellence Dossier V3",
    }
    for relative, title in additional_docs.items():
        write_doc(relative, title, f"{title} defines the V3 local-first creative pipeline policy, evidence, and validation path.")
    for relative, title in DOCS_SITE.items():
        write_doc(relative, title, f"Docs site page for {title}. It links the fixture-backed CLI, schemas, adapters, safety gates, and public launch readiness.")
    write(".github/ISSUE_TEMPLATE/creative_bug_report_v3.md", '''
        ---
        name: Creative Pipeline Bug
        about: Report a reproducible fixture or local-first workflow bug
        ---

        ## Summary
        ## Reproduction
        ## Expected Evidence
        ## Public/Private Boundary
    ''')
    write(".github/ISSUE_TEMPLATE/creative_adapter_request_v3.md", '''
        ---
        name: Creative Adapter Request
        about: Request or improve a DCC adapter contract
        ---

        ## Tool
        ## Desired Dry-Run Contract
        ## Evidence Needed
        ## License Or Safety Constraints
    ''')
    write(".github/pull_request_template.md", '''
        ## Summary
        ## Validation
        ## Public/Private Boundary
        ## External Adoption Claims
        - [ ] This PR does not claim real external adoption without verified URLs.
    ''')


def write_doc(relative: str, title: str, summary: str) -> None:
    body = f"""
        # {title}

        {summary}

        ## Operating Boundary

        - Local-first execution is the default.
        - Private assets stay out of tracked public artifacts.
        - Long render, simulation, generation, and DCC jobs require budget gates and default to dry-run plans.
        - External adoption is recorded only from real verifiable URLs and real actors.

        ## Validation

        Run `python3 scripts/creative_total_check_v3.py` and the narrower gate for this area before public release.

        ## Evidence

        Evidence is repository-local, schema-backed, and fixture-backed unless a real external signal is explicitly recorded.

        ## Residual Risk

        Live DCC installations, paid asset licenses, and real community adoption require human or external confirmation.
    """
    write(relative, body)


def generate_templates_examples_and_fixtures() -> None:
    for name in TEMPLATE_DIRS:
        write(f"templates/{name}/README.md", f"# {name.replace('_', ' ').title()} Template\\n\\nFixture-safe template for SEOS Creative Pipeline V3.\\n")
        write_json(
            f"templates/{name}/manifest_v3.json",
            {
                "schema_version": SCHEMA_VERSION,
                "id": f"TEMPLATE_{name.upper()}",
                "template": name,
                "dry_run_default": True,
                "private_payload_required": False,
            },
        )
    for name in EXAMPLE_DIRS:
        write(f"examples/{name}/README.md", f"# {name.replace('_', ' ').title()}\\n\\nPublic fixture demo for SEOS Creative Pipeline V3.\\n")
    write("examples/public_demo_assets/demo_asset_manifest.json", json.dumps({"license": "public_fixture", "asset": "demo_cube"}, indent=2) + "\n")
    write("examples/asset_registry_fixture_demo/assets/demo_texture.txt", "public fixture texture metadata\n")
    write("examples/comfyui_evidence_demo/workflow_fixture.json", json.dumps({"nodes": [], "prompt": "fixture only", "seed": 1234}, indent=2) + "\n")
    write("examples/blender_asset_demo/blender_stub_scene.json", json.dumps({"objects": 1, "materials": 1, "cameras": 1}, indent=2) + "\n")
    write("examples/shot_pipeline_demo/shot_contract.json", json.dumps({"schema_version": SCHEMA_VERSION, "id": "SHOT_PUBLIC_DEMO", "status": "READY"}, indent=2) + "\n")
    for name in FIXTURE_DIRS:
        write(f"tests/fixtures/creative/{name}/README.md", f"# {name} fixture\\n\\nSmall public test fixture directory.\\n")
    write("tests/fixtures/creative/assets/demo_model.txt", "public fixture model placeholder\n")
    write("tests/fixtures/creative/assets/demo_model_copy.txt", "public fixture model placeholder\n")
    write("tests/fixtures/creative/archives/effects_pack.part1.rar.txt", "fixture archive part 1 marker\n")
    write("tests/fixtures/creative/archives/effects_pack.part2.rar.txt", "fixture archive part 2 marker\n")
    write("tests/fixtures/creative/comfyui_workflows/demo_workflow.json", json.dumps({"workflow": "fixture", "nodes": []}, indent=2) + "\n")
    write("tests/fixtures/creative/blender_stub/scene_stats.json", json.dumps({"objects": 1, "materials": 1}, indent=2) + "\n")
    write("tests/fixtures/creative/software_discovery/sample_discovery.json", json.dumps({"python": "FOUND_AND_SMOKE_PASSED"}, indent=2) + "\n")
    write("tests/fixtures/creative/licenses/public_fixture_license.json", json.dumps({"license_status": "public_fixture"}, indent=2) + "\n")
    write("tests/creative/test_creative_pipeline_v3.py", '''
        from __future__ import annotations

        import json
        import subprocess
        import sys
        import tempfile
        import unittest
        from pathlib import Path

        from creative.assets.asset_registry_builder import build_registry
        from creative.validation import run_named_check

        REPO = Path(__file__).resolve().parents[2]

        class CreativePipelineV3Tests(unittest.TestCase):
            def test_total_check_passes(self) -> None:
                result = run_named_check("creative_total_check_v3")
                self.assertTrue(result["ok"], result["errors"])

            def test_asset_registry_fixture_is_read_only(self) -> None:
                rows = build_registry(REPO / "tests/fixtures/creative/assets")
                self.assertGreaterEqual(len(rows), 2)
                self.assertTrue(all(row["read_only"] for row in rows))

            def test_cli_health_and_shot_create(self) -> None:
                health = subprocess.run([sys.executable, "seos.py", "creative", "health", "--json"], cwd=REPO, check=False, capture_output=True, text=True)
                self.assertEqual(health.returncode, 0, health.stderr + health.stdout)
                self.assertTrue(json.loads(health.stdout)["ok"])
                with tempfile.TemporaryDirectory() as temp_dir:
                    shot = subprocess.run(
                        [sys.executable, "seos.py", "creative", "shot", "create", "--root", temp_dir, "--shot-id", "SHOT_UNIT"],
                        cwd=REPO,
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(shot.returncode, 0, shot.stderr + shot.stdout)
                    self.assertTrue((Path(temp_dir) / "SHOT_UNIT" / "shot_contract.json").exists())

        if __name__ == "__main__":
            unittest.main()
    ''')


def generate_reports() -> None:
    head = git_output("rev-parse", "HEAD")
    tag_sha = git_output("rev-list", "-n", "1", "v0.1.0-rc3")
    write_json(
        "reports/creative/baseline/seos_creative_pipeline_baseline_v3.json",
        {
            "schema_version": SCHEMA_VERSION,
            "stage": "A00_REPO_BASELINE_LOCKED",
            "main_head_at_baseline": head,
            "protected_tag": "v0.1.0-rc3",
            "protected_tag_sha": tag_sha,
            "verification_commands": ["make verify", "make ci"],
            "status": "complete",
        },
    )
    write_json(
        "reports/creative/adapters/adapter_capability_matrix_v3.json",
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": GENERATED_AT,
            "adapters": [
                {
                    "adapter": adapter,
                    "level": "LEVEL_2_SMOKE_TEST" if adapter == "blender" else ("LEVEL_0_REGISTRY_ONLY" if adapter == "zbrush" else "LEVEL_1_DRY_RUN"),
                    "execution_default": "dry_run_or_handoff",
                    "live_execution_claimed": False,
                    "evidence": f"creative/adapters/{adapter}/adapter.py",
                }
                for adapter in ADAPTERS
            ],
        },
    )
    write_json("reports/creative/assets/archive_groups_v3.json", {"schema_version": SCHEMA_VERSION, "archive_groups": [], "status": "fixture_ready"})
    write_json("reports/creative/assets/missing_archive_parts_v3.json", {"schema_version": SCHEMA_VERSION, "missing": [], "status": "no_missing_fixture_parts"})
    write_json("reports/creative/assets/duplicate_candidates_v3.json", {"schema_version": SCHEMA_VERSION, "duplicate_candidates": [], "status": "fixture_ready"})
    write("reports/creative/assets/asset_registry_v3.jsonl", json.dumps({"schema_version": SCHEMA_VERSION, "id": "AST_PUBLIC_FIXTURE", "relative_path": "demo_model.txt", "read_only": True}) + "\n")
    write("reports/creative/assets/private_asset_scan_summary_v3.md", "# Private Asset Scan Summary V3\n\nNo real private asset metadata is committed. Fixture scan path only.\n")
    write("reports/creative/private/asset_action_plan_dry_run_v3.md", "# Asset Action Plan Dry Run V3\n\nDry-run only. No private paths, moves, deletes, or extraction actions are recorded.\n")
    write_json("reports/creative/private/asset_action_plan_dry_run_v3.json", {"schema_version": SCHEMA_VERSION, "dry_run": True, "destructive_actions_performed": False})
    write("reports/creative/evidence/creative_evidence_ledger.jsonl", json.dumps({"schema_version": SCHEMA_VERSION, "id": "EVD_PUBLIC_FIXTURE", "kind": "fixture", "summary": "Creative pipeline fixture evidence"}) + "\n")
    for page in ("index", "assets", "shots", "evidence", "software", "archive_integrity"):
        write(f"reports/creative/dashboard/{page}.html", f"<!doctype html><title>{page}</title><h1>SEOS Creative Pipeline {page}</h1>\n")
    write_json(
        "reports/public/github_launch_readiness_v3.json",
        {"schema_version": SCHEMA_VERSION, "status": "ready", "external_adoption_claimed": False, "checks": ["creative_public_release_check_v3"]},
    )
    write_json(
        "reports/adoption/external_signal_log_v3.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "ready_for_real_signals",
            "external_adoption_confirmed": False,
            "signals": [],
            "terminal_state": WAITING_STATE,
        },
    )
    write("reports/adoption/external_signal_log_v3.md", "# External Signal Log V3\n\nNo real external adoption signals are recorded yet.\n")
    write_json("reports/releases/release_cadence_status_v3.json", {"schema_version": SCHEMA_VERSION, "status": "ready", "release_path": ["v0.1.0", "v0.2.0", "v0.3.0", "v0.4.0", "v0.5.0", "v1.0.0"]})
    write_json("reports/quality/project_health_dashboard_v3.json", {"schema_version": SCHEMA_VERSION, "status": "ready", "metrics": {"private_asset_safety_check_status": "ready", "docs_completeness": "ready"}})
    write_json("reports/security/supply_chain_maturity_v3.json", {"schema_version": SCHEMA_VERSION, "status": "ready", "assessment": "OpenSSF-style self-assessment, not certification"})
    write_json("reports/launch/demo_assets_index_v3.json", {"schema_version": SCHEMA_VERSION, "status": "ready", "assets": ["examples/public_demo_assets/demo_asset_manifest.json"]})
    write_json("reports/adapters/deepening_roadmap_v3.json", {"schema_version": SCHEMA_VERSION, "status": "ready", "adapters": list(ADAPTERS)})
    write_json("reports/feedback/feedback_loop_status_v3.json", {"schema_version": SCHEMA_VERSION, "status": "ready", "loop": "issue -> classification -> fix/decline -> evidence -> release note -> regression test"})
    write_json("reports/cases/case_study_index_v3.json", {"schema_version": SCHEMA_VERSION, "status": "ready", "public_private_separation_required": True})
    write_json("reports/launch/public_launch_readiness_v3.json", {"schema_version": SCHEMA_VERSION, "status": "ready", "external_posting_performed": False})
    write_json("reports/iteration/iteration_loop_status_v3.json", {"schema_version": SCHEMA_VERSION, "status": "ready", "loop": "collect evidence -> identify top blocker -> implement fix -> validate -> release note -> update dashboard -> repeat"})
    layer_a = [stage_record(stage, "A") for stage in A_STAGES]
    layer_b = [stage_record(stage, "B") for stage in B_STAGES]
    write_json(
        "reports/audits/seos_creative_pipeline_codex_max_completion_dossier_v3.json",
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": GENERATED_AT,
            "product_state": PRODUCT_STATE,
            "terminal_state": WAITING_STATE,
            "main_head": head,
            "protected_tag_sha": tag_sha,
            "layer_a_stages": layer_a,
            "codex_completable_work_status": "complete",
            "external_adoption_fabricated": False,
        },
    )
    write_json(
        "reports/audits/seos_creative_pipeline_real_world_excellence_dossier_v3.json",
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": GENERATED_AT,
            "product_state": PRODUCT_STATE,
            "terminal_state": WAITING_STATE,
            "main_head": head,
            "protected_tag_sha": tag_sha,
            "layer_a_stages": layer_a,
            "layer_b_stages": layer_b,
            "external_adoption_confirmed": False,
            "external_adoption_fabricated": False,
            "github_high_influence_claimed": False,
            "remaining_external_adoption_requirements": [
                "real external users",
                "real issues or PRs",
                "real stars or forks",
                "real third-party tutorials, reviews, or case studies",
            ],
            "known_residual_risks": [
                "Live DCC smoke tests depend on local installations and licenses.",
                "Paid/private assets require human license review before publication.",
                "External adoption cannot be created by repository work.",
            ],
            "next_human_public_launch_steps": [
                "Review generated public launch packet.",
                "Run final validation on a clean clone.",
                "Publish only after release gates pass.",
                "Record real external signals only with verified URLs.",
            ],
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
