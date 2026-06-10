"""Creative materialization records for execution outputs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from execution_plane.permits.builder import stable_id
from execution_plane.runner.result_envelope import utc_now

CREATIVE_MATERIALIZATION_SCHEMA_VERSION = "seos_creative_materialization_v1"


def build_materialization_record(
    *,
    permit: Mapping[str, Any],
    result: Mapping[str, Any],
    output: Mapping[str, Any],
    kind: str,
) -> dict[str, Any]:
    asset_id = stable_id(
        "AST",
        result["run_id"],
        output["relative_path"],
        output["sha256"],
    )
    return {
        "schema_version": CREATIVE_MATERIALIZATION_SCHEMA_VERSION,
        "asset_id": asset_id,
        "run_id": result["run_id"],
        "permit_id": permit["permit_id"],
        "kind": kind,
        "created_at": utc_now(),
        "relative_path": output["relative_path"],
        "size_bytes": output["size_bytes"],
        "sha256": output["sha256"],
        "lineage": {
            "task_id": permit["task_id"],
            "adapter": permit["allowed_adapter"],
            "source_inputs": [],
        },
    }

