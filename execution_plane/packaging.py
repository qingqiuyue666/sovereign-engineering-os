"""Portable run and shot package writer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from creative.common import load_json, write_json
from execution_plane.runner.result_envelope import sha256_file, utc_now


def package_run(
    run_id: str,
    *,
    runtime_root: str | Path = "work/production_runtime",
    package_root: str | Path = "work/packages",
) -> dict[str, Any]:
    run_dir = _find_run_dir(runtime_root, run_id)
    receipt_path = run_dir / "shot_run_receipt.json"
    receipt = load_json(receipt_path)
    package_dir = Path(package_root) / "runs" / run_id
    package_dir.mkdir(parents=True, exist_ok=True)
    workflow_receipt_path = Path(str(receipt.get("workflow_receipt_path", "")))
    manifest = {
        "schema_version": "seos.run_package_manifest.v1",
        "package_kind": "run",
        "run_id": run_id,
        "shot_id": receipt.get("shot_id"),
        "project_id": receipt.get("project_id"),
        "created_at": utc_now(),
        "terminal_status": receipt.get("terminal_status"),
        "copy_policy": "artifact_refs_only",
        "receipts": [
            _receipt_ref(receipt_path, runtime_root),
            _receipt_ref(workflow_receipt_path, runtime_root) if workflow_receipt_path.exists() else None,
        ],
        "artifact_refs": receipt.get("artifact_refs", []),
    }
    manifest["receipts"] = [item for item in manifest["receipts"] if item is not None]
    write_json(package_dir / "manifest.json", manifest)
    write_json(package_dir / "shot_run_receipt.json", receipt)
    if workflow_receipt_path.exists():
        write_json(package_dir / "workflow_receipt.json", load_json(workflow_receipt_path))
    write_json(package_dir / "artifact_refs.json", {"schema_version": "seos.package_artifact_refs.v1", "artifact_refs": receipt.get("artifact_refs", [])})
    return {"ok": True, "package_path": (package_dir / "manifest.json").as_posix(), "manifest": manifest}


def package_shot(
    shot_id: str,
    *,
    runtime_root: str | Path = "work/production_runtime",
    package_root: str | Path = "work/packages",
) -> dict[str, Any]:
    shot_dir = Path(runtime_root) / "shots" / shot_id
    shot_path = shot_dir / "shot.json"
    if not shot_path.exists():
        raise FileNotFoundError(f"shot_not_found:{shot_id}")
    shot = load_json(shot_path)
    run_manifests = []
    artifact_refs = []
    for run in shot.get("runs", []):
        run_id = str(run.get("run_id"))
        packaged = package_run(run_id, runtime_root=runtime_root, package_root=package_root)
        run_manifests.append(packaged["manifest"])
        artifact_refs.extend(packaged["manifest"].get("artifact_refs", []))
    package_dir = Path(package_root) / "shots" / shot_id
    package_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "seos.shot_package_manifest.v1",
        "package_kind": "shot",
        "shot_id": shot_id,
        "project_id": shot.get("project_id"),
        "created_at": utc_now(),
        "copy_policy": "artifact_refs_only",
        "asset_refs": shot.get("asset_refs", []),
        "run_count": len(run_manifests),
        "runs": run_manifests,
        "artifact_refs": artifact_refs,
    }
    write_json(package_dir / "manifest.json", manifest)
    write_json(package_dir / "shot.json", shot)
    write_json(package_dir / "artifact_refs.json", {"schema_version": "seos.package_artifact_refs.v1", "artifact_refs": artifact_refs})
    return {"ok": True, "package_path": (package_dir / "manifest.json").as_posix(), "manifest": manifest}


def _find_run_dir(runtime_root: str | Path, run_id: str) -> Path:
    root = Path(runtime_root)
    for path in root.glob(f"shots/*/runs/{run_id}"):
        if (path / "shot_run_receipt.json").exists():
            return path
    raise FileNotFoundError(f"run_not_found:{run_id}")


def _receipt_ref(path: Path, runtime_root: str | Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "relative_path": path.relative_to(Path(runtime_root)).as_posix() if path.is_relative_to(Path(runtime_root)) else path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }
