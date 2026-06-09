"""Production dogfood fixture runner."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from creative.common import load_json, write_json, write_jsonl
from execution_plane.packaging import package_run, package_shot
from execution_plane.permits.builder import stable_id
from execution_plane.production_runtime import ProductionRuntime
from execution_plane.review_artifacts import create_review_artifact
from execution_plane.runner.result_envelope import sha256_file, utc_now

DOGFOOD_FIXTURE_SCHEMA_VERSION = "seos.production_dogfood_fixture.v1"
DOGFOOD_RUN_SCHEMA_VERSION = "seos.production_dogfood_run.v1"


def run_production_dogfood_fixture(
    fixture_path: str | Path,
    *,
    runtime_root: str | Path = "work/production_dogfood/runtime",
    package_root: str | Path = "work/production_dogfood/packages",
    output_root: str | Path = "work/production_dogfood/runs",
    review_root: str | Path = "work/production_dogfood/review_artifacts",
) -> dict[str, Any]:
    """Run a complete local production-style project/shot/package fixture."""

    started_at = utc_now()
    fixture_path = Path(fixture_path)
    output_root = Path(output_root)
    run_id = stable_id("DOGFOOD", fixture_path.as_posix(), started_at)
    run_dir = output_root / run_id
    ledger: list[dict[str, Any]] = []
    paths = _dogfood_paths(run_dir)
    command = _callable_command(fixture_path, runtime_root, package_root, output_root, review_root)
    try:
        fixture = _load_fixture(fixture_path)
        ledger.append(_ledger("fixture_loaded", fixture_id=fixture["fixture_id"], fixture_path=fixture_path.as_posix()))
        asset_root = _resolve_fixture_path(fixture_path, str(fixture["asset_root"]))
        workflow_path = _resolve_fixture_path(fixture_path, str(fixture["workflow_path"]))
        if not asset_root.exists():
            raise FileNotFoundError(f"asset_root_missing:{asset_root}")
        if not workflow_path.exists():
            raise FileNotFoundError(f"workflow_missing:{workflow_path}")
        ledger.append(_ledger("fixture_paths_validated", asset_root=asset_root.as_posix(), workflow_path=workflow_path.as_posix()))

        runtime = ProductionRuntime(runtime_root)
        project_result = runtime.create_project(str(fixture["project_name"]))
        project = project_result["project"]
        ledger.append(_ledger("project_created", project_id=project["project_id"], project_path=project_result["project_path"]))

        scan_result = runtime.scan_assets(asset_root, project_id=project["project_id"])
        scan = scan_result["scan"]
        ledger.append(
            _ledger(
                "asset_scan_created",
                scan_id=scan["scan_id"],
                asset_count=scan["asset_count"],
                registry_path=scan_result["registry_path"],
            )
        )

        shot_result = runtime.create_shot(project["project_id"], str(fixture["shot_name"]))
        shot = shot_result["shot"]
        ledger.append(_ledger("shot_created", shot_id=shot["shot_id"], shot_path=shot_result["shot_path"]))

        attach_result = runtime.attach_workflow(shot["shot_id"], workflow_path.as_posix())
        ledger.append(_ledger("workflow_attached", shot_id=shot["shot_id"], workflow_id=attach_result["workflow"]["workflow_id"]))

        run_result = runtime.run_shot(shot["shot_id"])
        shot_run = run_result["run"]
        ledger.append(_ledger("shot_run_completed", run_id=shot_run["run_id"], terminal_status=shot_run["terminal_status"], run_path=run_result["run_path"]))
        if shot_run["terminal_status"] != "TERMINAL_SUCCEEDED":
            return _finish_failure(
                run_dir=run_dir,
                run_id=run_id,
                started_at=started_at,
                command=command,
                fixture=fixture,
                ledger=ledger,
                failure_code="WORKFLOW_TERMINAL_FAILED",
                failure_summary=str(shot_run.get("failure_summary") or "shot workflow failed"),
                workflow_receipt_path=str(shot_run.get("workflow_receipt_path", "")),
            )

        run_package = package_run(shot_run["run_id"], runtime_root=runtime.root, package_root=package_root)
        ledger.append(_ledger("run_packaged", run_id=shot_run["run_id"], package_path=run_package["package_path"]))

        shot_package = package_shot(shot["shot_id"], runtime_root=runtime.root, package_root=package_root)
        ledger.append(_ledger("shot_packaged", shot_id=shot["shot_id"], package_path=shot_package["package_path"]))

        review = create_review_artifact(shot["shot_id"], runtime_root=runtime.root, package_root=package_root, output_root=review_root)
        ledger.append(_ledger("review_artifact_created", review_path=review["review_path"], packet_path=review["packet_path"]))

        manifest = {
            "schema_version": "seos.production_dogfood_manifest.v1",
            "dogfood_run_id": run_id,
            "fixture_id": fixture["fixture_id"],
            "fixture_path": fixture_path.as_posix(),
            "created_at": utc_now(),
            "project_id": project["project_id"],
            "asset_scan_id": scan["scan_id"],
            "asset_registry_path": scan_result["registry_path"],
            "shot_id": shot["shot_id"],
            "shot_run_id": shot_run["run_id"],
            "terminal_status": shot_run["terminal_status"],
            "workflow_receipt_path": shot_run["workflow_receipt_path"],
            "shot_run_receipt_path": run_result["run_path"],
            "run_package_manifest_path": run_package["package_path"],
            "shot_package_manifest_path": shot_package["package_path"],
            "review_artifact_path": review["review_path"],
            "review_packet_path": review["packet_path"],
            "copy_policy": "artifact_refs_only",
            "artifact_refs": shot_run.get("artifact_refs", []),
            "commands": [command],
            "state_ledger_path": paths["ledger_path"].as_posix(),
        }
        write_json(paths["manifest_path"], manifest)
        ledger.append(_ledger("dogfood_manifest_written", manifest_path=paths["manifest_path"].as_posix()))
        write_jsonl(paths["ledger_path"], ledger)
        artifact_manifest = _dogfood_artifact_manifest(manifest)
        write_json(paths["artifact_manifest_path"], artifact_manifest)
        receipt = {
            "schema_version": DOGFOOD_RUN_SCHEMA_VERSION,
            "dogfood_run_id": run_id,
            "fixture_id": fixture["fixture_id"],
            "started_at": started_at,
            "ended_at": utc_now(),
            "terminal_status": "TERMINAL_SUCCEEDED",
            "real_callable_command": command,
            "mocked_ci_path": {
                "adapter": "fake_dcc",
                "workflow_path": workflow_path.as_posix(),
                "terminal_status": shot_run["terminal_status"],
            },
            "state_ledger_path": paths["ledger_path"].as_posix(),
            "manifest_path": paths["manifest_path"].as_posix(),
            "artifact_manifest_path": paths["artifact_manifest_path"].as_posix(),
            "failure_bundle_path": None,
            "artifact_refs": shot_run.get("artifact_refs", []),
            "package_refs": {
                "run_package_manifest_path": run_package["package_path"],
                "shot_package_manifest_path": shot_package["package_path"],
            },
            "review_artifact_path": review["review_path"],
        }
        write_json(paths["receipt_path"], receipt)
        return {"ok": True, "receipt_path": paths["receipt_path"].as_posix(), "manifest_path": paths["manifest_path"].as_posix(), "receipt": receipt}
    except Exception as exc:
        return _finish_failure(
            run_dir=run_dir,
            run_id=run_id,
            started_at=started_at,
            command=command,
            fixture={"fixture_id": fixture_path.stem},
            ledger=ledger,
            failure_code=exc.__class__.__name__,
            failure_summary=str(exc),
            workflow_receipt_path=None,
        )


def _load_fixture(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if payload.get("schema_version") != DOGFOOD_FIXTURE_SCHEMA_VERSION:
        raise ValueError(f"fixture_schema_mismatch:{payload.get('schema_version')}")
    required = ("fixture_id", "project_name", "shot_name", "asset_root", "workflow_path")
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise ValueError(f"fixture_missing_required_fields:{','.join(missing)}")
    return dict(payload)


def _resolve_fixture_path(fixture_path: Path, value: str) -> Path:
    direct = Path(value)
    if direct.exists():
        return direct
    relative = fixture_path.parent / value
    if relative.exists():
        return relative
    return direct


def _dogfood_paths(run_dir: Path) -> dict[str, Path]:
    return {
        "receipt_path": run_dir / "dogfood_receipt.json",
        "manifest_path": run_dir / "dogfood_manifest.json",
        "artifact_manifest_path": run_dir / "artifact_manifest.json",
        "ledger_path": run_dir / "dogfood_state_ledger.jsonl",
        "failure_bundle_path": run_dir / "failure_bundle.json",
    }


def _finish_failure(
    *,
    run_dir: Path,
    run_id: str,
    started_at: str,
    command: str,
    fixture: Mapping[str, Any],
    ledger: list[dict[str, Any]],
    failure_code: str,
    failure_summary: str,
    workflow_receipt_path: str | None,
) -> dict[str, Any]:
    paths = _dogfood_paths(run_dir)
    ledger.append(_ledger("dogfood_failed", failure_code=failure_code, failure_summary=failure_summary))
    write_jsonl(paths["ledger_path"], ledger)
    failure_bundle = {
        "schema_version": "seos.production_dogfood_failure_bundle.v1",
        "dogfood_run_id": run_id,
        "fixture_id": fixture.get("fixture_id"),
        "terminal_status": "TERMINAL_FAILED",
        "failure_code": failure_code,
        "failure_summary": failure_summary,
        "real_callable_command": command,
        "workflow_receipt_path": workflow_receipt_path,
        "state_ledger_path": paths["ledger_path"].as_posix(),
    }
    write_json(paths["failure_bundle_path"], failure_bundle)
    receipt = {
        "schema_version": DOGFOOD_RUN_SCHEMA_VERSION,
        "dogfood_run_id": run_id,
        "fixture_id": fixture.get("fixture_id"),
        "started_at": started_at,
        "ended_at": utc_now(),
        "terminal_status": "TERMINAL_FAILED",
        "real_callable_command": command,
        "state_ledger_path": paths["ledger_path"].as_posix(),
        "manifest_path": None,
        "artifact_manifest_path": None,
        "failure_bundle_path": paths["failure_bundle_path"].as_posix(),
        "artifact_refs": [],
    }
    write_json(paths["receipt_path"], receipt)
    return {
        "ok": False,
        "receipt_path": paths["receipt_path"].as_posix(),
        "failure_bundle_path": paths["failure_bundle_path"].as_posix(),
        "receipt": receipt,
        "failure_bundle": failure_bundle,
    }


def _dogfood_artifact_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    files = [
        str(manifest.get("asset_registry_path", "")),
        str(manifest.get("shot_run_receipt_path", "")),
        str(manifest.get("workflow_receipt_path", "")),
        str(manifest.get("run_package_manifest_path", "")),
        str(manifest.get("shot_package_manifest_path", "")),
        str(manifest.get("review_artifact_path", "")),
    ]
    refs = []
    for value in files:
        path = Path(value)
        if path.exists() and path.is_file():
            refs.append({"path": path.as_posix(), "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    return {
        "schema_version": "seos.production_dogfood_artifact_manifest.v1",
        "dogfood_run_id": manifest.get("dogfood_run_id"),
        "fixture_id": manifest.get("fixture_id"),
        "copy_policy": manifest.get("copy_policy"),
        "artifact_refs": list(manifest.get("artifact_refs", [])),
        "receipt_refs": refs,
    }


def _ledger(step: str, **details: Any) -> dict[str, Any]:
    return {"schema_version": "seos.production_dogfood_ledger_event.v1", "at": utc_now(), "step": step, "details": details}


def _callable_command(
    fixture_path: Path,
    runtime_root: str | Path,
    package_root: str | Path,
    output_root: str | Path,
    review_root: str | Path,
) -> str:
    return (
        f"python3 seos.py dogfood run {fixture_path.as_posix()} "
        f"--runtime-root {Path(runtime_root).as_posix()} "
        f"--package-root {Path(package_root).as_posix()} "
        f"--output-root {Path(output_root).as_posix()} "
        f"--review-root {Path(review_root).as_posix()}"
    )
