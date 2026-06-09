"""Project, asset, and shot runtime."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from creative.common import load_json, write_json
from execution_plane.permits.builder import stable_id
from execution_plane.runner.result_envelope import sha256_file, utc_now
from execution_plane.workflows.runner import run_workflow

PRODUCTION_RUNTIME_SCHEMA_VERSION = "seos.production_runtime.v1"


class ProductionRuntime:
    def __init__(self, root: str | Path = "work/production_runtime") -> None:
        self.root = Path(root)
        self.state_path = self.root / "production_state.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def create_project(self, name: str) -> dict[str, Any]:
        project_id = stable_id("PROJ", name, utc_now())
        project_dir = self.root / "projects" / project_id
        record = {
            "schema_version": "seos.project.v1",
            "project_id": project_id,
            "name": name,
            "created_at": utc_now(),
            "asset_scan_ids": [],
            "shot_ids": [],
            "status": "ACTIVE",
        }
        write_json(project_dir / "project.json", record)
        state = self._read_state()
        state["projects"][project_id] = record
        self._write_state(state)
        return {"ok": True, "project": record, "project_path": (project_dir / "project.json").as_posix()}

    def scan_assets(self, scan_root: str | Path, *, project_id: str | None = None) -> dict[str, Any]:
        root = Path(scan_root)
        if not root.exists():
            raise FileNotFoundError(f"asset_root_missing:{root}")
        records = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            relative_path = path.relative_to(root).as_posix()
            digest = sha256_file(path)
            records.append(
                {
                    "schema_version": "seos.asset.v1",
                    "asset_id": stable_id("ASSET", root.as_posix(), relative_path, digest),
                    "relative_path": relative_path,
                    "source_root": root.as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": digest,
                    "media_type": _media_type(relative_path),
                }
            )
        scan_id = stable_id("ASSETSCAN", root.as_posix(), len(records), utc_now())
        scan_dir = self.root / "asset_scans" / scan_id
        registry = {
            "schema_version": "seos.asset_registry.v1",
            "scan_id": scan_id,
            "project_id": project_id,
            "scan_root": root.as_posix(),
            "created_at": utc_now(),
            "asset_count": len(records),
            "assets": records,
        }
        write_json(scan_dir / "asset_registry.json", registry)
        state = self._read_state()
        state["asset_scans"][scan_id] = registry
        state["latest_asset_scan_id"] = scan_id
        if project_id and project_id in state["projects"]:
            project = dict(state["projects"][project_id])
            project["asset_scan_ids"] = [*project.get("asset_scan_ids", []), scan_id]
            state["projects"][project_id] = project
            write_json(self.root / "projects" / project_id / "project.json", project)
        self._write_state(state)
        return {"ok": True, "scan": registry, "registry_path": (scan_dir / "asset_registry.json").as_posix()}

    def create_shot(self, project_id: str, shot_name: str) -> dict[str, Any]:
        state = self._read_state()
        if project_id not in state["projects"]:
            raise KeyError(f"project_not_found:{project_id}")
        shot_id = stable_id("SHOT", project_id, shot_name, utc_now())
        latest_scan = state.get("latest_asset_scan_id")
        asset_refs = []
        if latest_scan and latest_scan in state["asset_scans"]:
            asset_refs = [
                {"asset_id": asset["asset_id"], "relative_path": asset["relative_path"]}
                for asset in state["asset_scans"][latest_scan].get("assets", [])
            ]
        record = {
            "schema_version": "seos.shot.v1",
            "shot_id": shot_id,
            "project_id": project_id,
            "shot_name": shot_name,
            "created_at": utc_now(),
            "asset_scan_id": latest_scan,
            "asset_refs": asset_refs,
            "workflow": None,
            "runs": [],
            "versions": [],
            "status": "READY",
        }
        shot_dir = self.root / "shots" / shot_id
        write_json(shot_dir / "shot.json", record)
        state["shots"][shot_id] = record
        project = dict(state["projects"][project_id])
        project["shot_ids"] = [*project.get("shot_ids", []), shot_id]
        state["projects"][project_id] = project
        write_json(self.root / "projects" / project_id / "project.json", project)
        self._write_state(state)
        return {"ok": True, "shot": record, "shot_path": (shot_dir / "shot.json").as_posix()}

    def attach_workflow(self, shot_id: str, workflow_ref: str) -> dict[str, Any]:
        state = self._read_state()
        if shot_id not in state["shots"]:
            raise KeyError(f"shot_not_found:{shot_id}")
        workflow_path = _resolve_workflow_path(workflow_ref)
        workflow_payload = load_json(workflow_path)
        workflow = {
            "workflow_id": str(workflow_payload.get("workflow_id") or Path(workflow_ref).stem),
            "workflow_path": workflow_path.as_posix(),
            "attached_at": utc_now(),
        }
        shot = dict(state["shots"][shot_id])
        shot["workflow"] = workflow
        state["shots"][shot_id] = shot
        write_json(self.root / "shots" / shot_id / "shot.json", shot)
        self._write_state(state)
        return {"ok": True, "shot_id": shot_id, "workflow": workflow}

    def run_shot(self, shot_id: str) -> dict[str, Any]:
        state = self._read_state()
        if shot_id not in state["shots"]:
            raise KeyError(f"shot_not_found:{shot_id}")
        shot = dict(state["shots"][shot_id])
        workflow = shot.get("workflow") if isinstance(shot.get("workflow"), Mapping) else None
        if workflow is None:
            raise ValueError(f"shot_workflow_not_attached:{shot_id}")
        run_id = stable_id("SHOTRUN", shot_id, workflow["workflow_id"], utc_now())
        run_dir = self.root / "shots" / shot_id / "runs" / run_id
        workflow_receipt = run_workflow(
            {
                "workflow_path": workflow["workflow_path"],
                "output_root": (run_dir / "workflow").as_posix(),
                "runtime_token": _default_runtime_token(shot_id),
            }
        )
        receipt = {
            "schema_version": "seos.shot_run_receipt.v1",
            "run_id": run_id,
            "project_id": shot["project_id"],
            "shot_id": shot_id,
            "workflow_id": workflow["workflow_id"],
            "created_at": utc_now(),
            "terminal_status": workflow_receipt["terminal_status"],
            "workflow_receipt_path": (run_dir / "workflow" / "workflow_receipt.json").as_posix(),
            "artifact_refs": workflow_receipt.get("artifact_refs", []),
            "workflow_receipt": workflow_receipt,
        }
        write_json(run_dir / "shot_run_receipt.json", receipt)
        write_json(run_dir / "artifact_manifest.json", {"schema_version": "seos.shot_artifact_manifest.v1", "artifact_refs": receipt["artifact_refs"]})
        shot_runs = [*shot.get("runs", []), {"run_id": run_id, "terminal_status": receipt["terminal_status"], "receipt_path": (run_dir / "shot_run_receipt.json").as_posix()}]
        shot["runs"] = shot_runs
        shot["versions"] = [
            *shot.get("versions", []),
            {
                "version_id": stable_id("SHOTVER", shot_id, run_id),
                "run_id": run_id,
                "terminal_status": receipt["terminal_status"],
                "created_at": utc_now(),
            },
        ]
        state["shots"][shot_id] = shot
        write_json(self.root / "shots" / shot_id / "shot.json", shot)
        self._write_state(state)
        return {"ok": True, "run": receipt, "run_path": (run_dir / "shot_run_receipt.json").as_posix()}

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {
                "schema_version": PRODUCTION_RUNTIME_SCHEMA_VERSION,
                "projects": {},
                "asset_scans": {},
                "shots": {},
                "latest_asset_scan_id": None,
            }
        state = load_json(self.state_path)
        for key in ("projects", "asset_scans", "shots"):
            if not isinstance(state.get(key), dict):
                state[key] = {}
        return state

    def _write_state(self, state: Mapping[str, Any]) -> None:
        write_json(self.state_path, state)


def _resolve_workflow_path(workflow_ref: str) -> Path:
    direct = Path(workflow_ref)
    if direct.exists():
        return direct
    candidate = Path("examples/workflows") / f"{workflow_ref}.json"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"workflow_not_found:{workflow_ref}")


def _default_runtime_token(shot_id: str) -> dict[str, Any]:
    return {
        "task_id": f"TASK_SHOT_RUN_{shot_id}",
        "operator_approval_id": f"RCPT_SHOT_RUN_{shot_id}",
        "expires_at": "2099-01-01T00:00:00Z",
        "max_runtime_seconds": 60,
        "max_output_bytes": 104_857_600,
        "max_files": 200,
        "auto_provision": {
            "enabled": True,
            "allowed_adapters": ["comfyui_local", "davinci_resolve"],
            "max_wait_seconds": 1,
            "heartbeat_interval_seconds": 1,
        },
        "concurrency": {
            "max_global_jobs": 2,
            "max_per_adapter_jobs": {
                "fake_dcc": 1,
                "houdini_hython": 1,
                "comfyui_local": 1,
                "davinci_resolve": 1,
            },
        },
        "retry": {"enabled": True, "max_attempts": 2, "backoff_seconds": 1},
        "patch_repair": {
            "enabled": True,
            "mode": "generate_patch_then_test",
            "allowed_tools": ["cline", "aider"],
            "auto_apply": False,
        },
    }


def _media_type(path: str) -> str:
    suffix = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return {
        "txt": "text/plain",
        "json": "application/json",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "exr": "image/aces",
        "bgeo": "application/x-bgeo",
        "abc": "model/vnd.alembic",
    }.get(suffix, "application/octet-stream")
