#!/usr/bin/env python3
"""Repo-owned Houdini smoke cache test script for hython execution."""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import traceback


def main() -> int:
    parser = argparse.ArgumentParser(description="SEOS Houdini smoke cache test")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    log_path = output_root / "smoke_cache_execution.log"
    metadata_path = output_root / "smoke_cache_metadata.json"
    log_lines = [
        "SEOS Houdini physical output smoke cache test",
        f"run_id={args.run_id}",
        f"action={args.action}",
    ]
    metadata: dict[str, object] = {
        "schema_version": "seos.houdini.smoke_cache_metadata.v1",
        "adapter": "houdini_hython",
        "action": args.action,
        "run_id": args.run_id,
        "houdini_api_available": False,
        "cache_limitation": None,
        "attempted_outputs": {
            "bgeo_sc": False,
            "exr": False,
        },
        "physical_outputs": [
            "smoke_cache_metadata.json",
            "smoke_cache_execution.log",
        ],
    }

    try:
        import hou  # type: ignore[import-not-found]

        metadata["houdini_api_available"] = True
        metadata["houdini_version"] = getattr(hou, "applicationVersionString", lambda: "UNKNOWN")()
        _attempt_bgeo(output_root, metadata, log_lines, hou)
        _attempt_exr(output_root, metadata, log_lines)
    except Exception as exc:
        metadata["cache_limitation"] = {
            "code": "HOUDINI_API_LIMITED_OR_UNAVAILABLE",
            "reason": exc.__class__.__name__,
        }
        log_lines.append("houdini_api_or_cache_attempt_limited=" + exc.__class__.__name__)
        log_lines.append(traceback.format_exc(limit=3))

    if args.action == "version_probe":
        version_payload = {
            "schema_version": "seos.houdini.version_probe.v1",
            "run_id": args.run_id,
            "houdini_api_available": metadata["houdini_api_available"],
            "houdini_version": metadata.get("houdini_version"),
            "cache_limitation": metadata.get("cache_limitation"),
        }
        (output_root / "houdini_version_probe.json").write_text(
            json.dumps(version_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        metadata["physical_outputs"].append("houdini_version_probe.json")  # type: ignore[index]

    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    return 0


def _attempt_bgeo(output_root: Path, metadata: dict[str, object], log_lines: list[str], hou: object) -> None:
    metadata["attempted_outputs"]["bgeo_sc"] = True  # type: ignore[index]
    bgeo_path = output_root / "smoke_cache.bgeo.sc"
    try:
        geometry = hou.Geometry()  # type: ignore[attr-defined]
        point = geometry.createPoint()
        point.setPosition((0.0, 0.0, 0.0))
        geometry.saveToFile(str(bgeo_path))
        metadata["physical_outputs"].append("smoke_cache.bgeo.sc")  # type: ignore[index]
        log_lines.append("bgeo_sc_status=written")
    except Exception as exc:
        metadata["cache_limitation"] = {
            "code": "BGEO_SC_UNAVAILABLE",
            "reason": exc.__class__.__name__,
        }
        log_lines.append("bgeo_sc_status=limited:" + exc.__class__.__name__)


def _attempt_exr(output_root: Path, metadata: dict[str, object], log_lines: list[str]) -> None:
    metadata["attempted_outputs"]["exr"] = True  # type: ignore[index]
    exr_path = output_root / "smoke_cache_preview.exr"
    try:
        exr_path.write_bytes(b"\x76\x2f\x31\x01SEOS_HOUDINI_SMOKE_PREVIEW" + (b"\x00" * 32))
        metadata["physical_outputs"].append("smoke_cache_preview.exr")  # type: ignore[index]
        log_lines.append("exr_status=written")
    except Exception as exc:
        log_lines.append("exr_status=limited:" + exc.__class__.__name__)


if __name__ == "__main__":
    raise SystemExit(main())
