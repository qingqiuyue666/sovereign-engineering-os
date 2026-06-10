"""Collect execution results and creative materialization evidence."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from creative.common import write_json
from execution_plane.evidence.materialization import build_materialization_record


def collect_execution_evidence(
    *,
    permit: Mapping[str, Any],
    result: Mapping[str, Any],
    evidence_root: str | Path,
    materialization_root: str | Path,
    materialization_kind: str | None = None,
) -> dict[str, Any]:
    evidence_dir = Path(evidence_root) / str(result["run_id"])
    materialization_dir = Path(materialization_root)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    materialization_dir.mkdir(parents=True, exist_ok=True)

    result_path = evidence_dir / "execution_result.json"
    write_json(result_path, dict(result))

    kind = materialization_kind or _kind_for_adapter(str(result["adapter"]))
    materialization_paths: list[str] = []
    for output in result.get("outputs", []):
        if not isinstance(output, Mapping):
            continue
        relative_path = str(output.get("relative_path", ""))
        if relative_path == "manifest.json":
            continue
        record = build_materialization_record(
            permit=permit,
            result=result,
            output=output,
            kind=kind,
        )
        path = materialization_dir / f"{record['asset_id']}.json"
        write_json(path, record)
        materialization_paths.append(path.as_posix())

    return {
        "execution_result_path": result_path.as_posix(),
        "materialization_paths": materialization_paths,
    }


def _kind_for_adapter(adapter: str) -> str:
    if adapter == "houdini_hython":
        return "houdini_geometry"
    return "fake_dcc_output"

