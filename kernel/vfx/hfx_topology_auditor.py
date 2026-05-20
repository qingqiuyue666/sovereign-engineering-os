"""Fail-closed Houdini HIP topology auditor for physical HFX verification.

Run this file with ``hython``. It loads one HIP file, finds an admissible final
render node, audits display/render flags, cooks geometry for point/primitive
counts, and emits one strict JSON object. Any missing ROP/OUT node or effective
geometry point count below the configured threshold classifies the file as a
placeholder guide.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final
import argparse
import json
import re
import traceback


AUDIT_SCHEMA_VERSION: Final[str] = "hfx-topology-auditor-v1"
DEFAULT_MINIMUM_REAL_ASSET_POINTS: Final[int] = 1_000
DEFAULT_OUTPUT_PARAMETER_CANDIDATES: Final[tuple[str, ...]] = (
    "picture",
    "vm_picture",
    "lopoutput",
    "outputimage",
    "output",
    "filename",
)
DEFAULT_RENDERER_TYPE_TOKENS: Final[tuple[str, ...]] = (
    "opengl",
    "ogl",
    "karma",
    "usdrender",
    "usd_render",
    "mantra",
    "ifd",
)
FINAL_NAME_TOKENS: Final[tuple[str, ...]] = (
    "final",
    "render",
    "beauty",
    "master",
    "main",
    "output",
    "karma",
    "mantra",
    "opengl",
    "ogl",
)
GEOMETRY_CATEGORY_NAMES: Final[frozenset[str]] = frozenset(
    {
        "Object",
        "Sop",
        "Lop",
    }
)
_SAFE_NODE_PATH_RE: Final[re.Pattern[str]] = re.compile(r"\A/[A-Za-z0-9_./-]{1,512}\Z")


class HfxTopologyAuditError(RuntimeError):
    """Raised when the auditor cannot produce a trustworthy report."""


@dataclass(frozen=True, slots=True)
class RenderNodeCandidate:
    """One possible final render node found in the HIP topology."""

    path: str
    name: str
    type_name: str
    category_name: str
    is_bypassed: bool
    valid_renderer: bool
    final_name_score: int
    output_parameter: str | None
    output_path: str | None
    display_flag: bool | None
    render_flag: bool | None

    @property
    def score(self) -> tuple[int, int, int]:
        out_bonus = 1 if self.path.startswith("/out/") or self.path == "/out" else 0
        active_bonus = 0 if self.is_bypassed else 1
        return (out_bonus, active_bonus, self.final_name_score)

    def as_dict(self) -> dict[str, object]:
        return {
            "category_name": self.category_name,
            "display_flag": self.display_flag,
            "final_name_score": self.final_name_score,
            "is_bypassed": self.is_bypassed,
            "name": self.name,
            "output_parameter": self.output_parameter,
            "output_path": self.output_path,
            "path": self.path,
            "render_flag": self.render_flag,
            "type_name": self.type_name,
            "valid_renderer": self.valid_renderer,
        }


@dataclass(frozen=True, slots=True)
class GeometrySample:
    """Cooked geometry count for one Houdini node."""

    path: str
    name: str
    type_name: str
    category_name: str
    point_count: int
    primitive_count: int
    display_flag: bool | None
    render_flag: bool | None
    is_bypassed: bool
    is_counted_for_effective_total: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "category_name": self.category_name,
            "display_flag": self.display_flag,
            "is_bypassed": self.is_bypassed,
            "is_counted_for_effective_total": self.is_counted_for_effective_total,
            "name": self.name,
            "path": self.path,
            "point_count": self.point_count,
            "primitive_count": self.primitive_count,
            "render_flag": self.render_flag,
            "type_name": self.type_name,
        }


@dataclass(frozen=True, slots=True)
class FlagAudit:
    """Display/render flag summary for the whole HIP topology."""

    display_flagged_nodes: tuple[str, ...]
    render_flagged_nodes: tuple[str, ...]
    display_without_render: tuple[str, ...]
    render_without_display: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "display_flagged_nodes": list(self.display_flagged_nodes),
            "display_without_render": list(self.display_without_render),
            "render_flagged_nodes": list(self.render_flagged_nodes),
            "render_without_display": list(self.render_without_display),
        }


@dataclass(frozen=True, slots=True)
class TopologyAuditReport:
    """Strict JSON report for one HIP audit."""

    schema_version: str
    checked_at: str
    hip_file: str
    status: str
    classification: str
    minimum_real_asset_points: int
    selected_render_node: RenderNodeCandidate | None
    render_node_candidates: tuple[RenderNodeCandidate, ...]
    geometry_samples: tuple[GeometrySample, ...]
    effective_point_count: int
    effective_primitive_count: int
    max_single_node_point_count: int
    max_single_node_path: str | None
    flag_audit: FlagAudit
    failures: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == "PASS" and self.classification == "Real Asset"

    def as_dict(self) -> dict[str, object]:
        return {
            "checked_at": self.checked_at,
            "classification": self.classification,
            "effective_point_count": self.effective_point_count,
            "effective_primitive_count": self.effective_primitive_count,
            "failures": list(self.failures),
            "flag_audit": self.flag_audit.as_dict(),
            "geometry": {
                "counted_nodes": [
                    sample.as_dict()
                    for sample in self.geometry_samples
                    if sample.is_counted_for_effective_total
                ],
                "effective_point_count": self.effective_point_count,
                "effective_primitive_count": self.effective_primitive_count,
                "max_single_node_path": self.max_single_node_path,
                "max_single_node_point_count": self.max_single_node_point_count,
                "sample_count": len(self.geometry_samples),
                "samples": [sample.as_dict() for sample in self.geometry_samples],
            },
            "hip_file": self.hip_file,
            "minimum_real_asset_points": self.minimum_real_asset_points,
            "render_node_candidates": [
                candidate.as_dict() for candidate in self.render_node_candidates
            ],
            "schema_version": self.schema_version,
            "selected_render_node": (
                self.selected_render_node.as_dict()
                if self.selected_render_node is not None
                else None
            ),
            "status": self.status,
            "warnings": list(self.warnings),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.as_dict(),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )


def audit_hip_file(
    hip_file: Path | str,
    *,
    minimum_real_asset_points: int = DEFAULT_MINIMUM_REAL_ASSET_POINTS,
    preferred_render_node_path: str | None = None,
    renderer_type_tokens: Sequence[str] = DEFAULT_RENDERER_TYPE_TOKENS,
    output_parameter_candidates: Sequence[str] = DEFAULT_OUTPUT_PARAMETER_CANDIDATES,
) -> TopologyAuditReport:
    """Load a HIP file in hython and return a fail-closed topology report."""

    admitted_hip = _admit_hip_file(hip_file)
    if minimum_real_asset_points < 1:
        raise HfxTopologyAuditError("minimum_real_asset_points must be >= 1")
    admitted_preferred_path = _admit_optional_node_path(preferred_render_node_path)

    hou = _import_hou()
    hou.hipFile.load(admitted_hip.as_posix(), suppress_save_prompt=True)
    nodes = _all_nodes(hou)
    candidates = _find_render_node_candidates(
        nodes,
        renderer_type_tokens=renderer_type_tokens,
        output_parameter_candidates=output_parameter_candidates,
    )
    selected_render_node = _select_render_node(candidates, admitted_preferred_path)
    flag_audit = _audit_flags(nodes)
    geometry_samples = _audit_geometry(nodes)
    counted_samples = _select_effective_geometry_samples(geometry_samples)
    effective_point_count = sum(sample.point_count for sample in counted_samples)
    effective_primitive_count = sum(sample.primitive_count for sample in counted_samples)
    max_sample = max(geometry_samples, key=lambda sample: sample.point_count, default=None)

    failures: list[str] = []
    warnings: list[str] = []
    if selected_render_node is None:
        failures.append("no_valid_rop_or_out_render_node")
    if not geometry_samples:
        failures.append("no_cookable_geometry_nodes")
    if effective_point_count < minimum_real_asset_points:
        failures.append("geometry_point_count_below_real_asset_threshold")
    if not flag_audit.display_flagged_nodes:
        warnings.append("no_display_flagged_nodes_found")
    if not flag_audit.render_flagged_nodes:
        warnings.append("no_render_flagged_nodes_found")
    if flag_audit.display_without_render:
        warnings.append("display_flags_without_matching_render_flags")
    if flag_audit.render_without_display:
        warnings.append("render_flags_without_matching_display_flags")

    status = "FAIL" if failures else "PASS"
    classification = "Real Asset" if status == "PASS" else "Placeholder Guide"
    return TopologyAuditReport(
        schema_version=AUDIT_SCHEMA_VERSION,
        checked_at=datetime.now(UTC).isoformat(timespec="seconds"),
        hip_file=admitted_hip.as_posix(),
        status=status,
        classification=classification,
        minimum_real_asset_points=minimum_real_asset_points,
        selected_render_node=selected_render_node,
        render_node_candidates=candidates,
        geometry_samples=tuple(
            GeometrySample(
                path=sample.path,
                name=sample.name,
                type_name=sample.type_name,
                category_name=sample.category_name,
                point_count=sample.point_count,
                primitive_count=sample.primitive_count,
                display_flag=sample.display_flag,
                render_flag=sample.render_flag,
                is_bypassed=sample.is_bypassed,
                is_counted_for_effective_total=sample.path
                in {counted.path for counted in counted_samples},
            )
            for sample in geometry_samples
        ),
        effective_point_count=effective_point_count,
        effective_primitive_count=effective_primitive_count,
        max_single_node_point_count=max_sample.point_count if max_sample else 0,
        max_single_node_path=max_sample.path if max_sample else None,
        flag_audit=flag_audit,
        failures=tuple(failures),
        warnings=tuple(warnings),
    )


def _import_hou() -> Any:
    try:
        import hou  # type: ignore[import-not-found]
    except ImportError as exc:
        raise HfxTopologyAuditError("hfx_topology_auditor must be run with hython") from exc
    return hou


def _admit_hip_file(hip_file: Path | str) -> Path:
    path = Path(hip_file).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise HfxTopologyAuditError(f"HIP file is missing: {path}")
    if path.suffix.lower() not in {".hip", ".hiplc", ".hipnc"}:
        raise HfxTopologyAuditError("HIP file must use .hip, .hiplc, or .hipnc")
    return path


def _admit_optional_node_path(path: str | None) -> str | None:
    if path is None:
        return None
    if not _SAFE_NODE_PATH_RE.fullmatch(path):
        raise HfxTopologyAuditError("preferred render node path is not a safe absolute path")
    return path


def _all_nodes(hou: Any) -> tuple[Any, ...]:
    root = hou.node("/")
    if root is None:
        raise HfxTopologyAuditError("Houdini root node is unavailable")
    result: list[Any] = [root]
    result.extend(root.allSubChildren())
    return tuple(result)


def _find_render_node_candidates(
    nodes: Iterable[Any],
    *,
    renderer_type_tokens: Sequence[str],
    output_parameter_candidates: Sequence[str],
) -> tuple[RenderNodeCandidate, ...]:
    normalized_renderer_tokens = tuple(token.lower().strip() for token in renderer_type_tokens)
    candidates: list[RenderNodeCandidate] = []
    for node in nodes:
        category_name = _node_category_name(node)
        type_name = _node_type_name(node)
        path = _node_path(node)
        is_driver_category = category_name.lower() in {"driver", "rop"}
        is_out_path = path.startswith("/out/")
        renderer_type_match = any(token in type_name.lower() for token in normalized_renderer_tokens)
        if not (is_driver_category or is_out_path or renderer_type_match):
            continue
        output_parameter, output_path = _first_string_parameter(
            node,
            output_parameter_candidates,
        )
        has_render_method = callable(getattr(node, "render", None))
        valid_renderer = (
            renderer_type_match
            and not _node_bypassed(node)
            and (is_driver_category or is_out_path)
            and has_render_method
            and output_parameter is not None
        )
        candidate = RenderNodeCandidate(
            path=path,
            name=_node_name(node),
            type_name=type_name,
            category_name=category_name,
            is_bypassed=_node_bypassed(node),
            valid_renderer=valid_renderer,
            final_name_score=_final_name_score(path, _node_name(node), type_name),
            output_parameter=output_parameter,
            output_path=output_path,
            display_flag=_safe_bool_method(node, "isDisplayFlagSet"),
            render_flag=_safe_bool_method(node, "isRenderFlagSet"),
        )
        candidates.append(candidate)
    return tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                1 if candidate.valid_renderer else 0,
                *candidate.score,
                candidate.path,
            ),
            reverse=True,
        )
    )


def _select_render_node(
    candidates: Sequence[RenderNodeCandidate],
    preferred_render_node_path: str | None,
) -> RenderNodeCandidate | None:
    valid_candidates = [candidate for candidate in candidates if candidate.valid_renderer]
    if preferred_render_node_path is not None:
        for candidate in valid_candidates:
            if candidate.path == preferred_render_node_path:
                return candidate
        return None
    if not valid_candidates:
        return None
    return valid_candidates[0]


def _audit_flags(nodes: Iterable[Any]) -> FlagAudit:
    display_flagged: list[str] = []
    render_flagged: list[str] = []
    display_without_render: list[str] = []
    render_without_display: list[str] = []
    for node in nodes:
        display_flag = _safe_bool_method(node, "isDisplayFlagSet")
        render_flag = _safe_bool_method(node, "isRenderFlagSet")
        path = _node_path(node)
        if display_flag is True:
            display_flagged.append(path)
        if render_flag is True:
            render_flagged.append(path)
        if display_flag is True and render_flag is False:
            display_without_render.append(path)
        if render_flag is True and display_flag is False:
            render_without_display.append(path)
    return FlagAudit(
        display_flagged_nodes=tuple(sorted(display_flagged)),
        render_flagged_nodes=tuple(sorted(render_flagged)),
        display_without_render=tuple(sorted(display_without_render)),
        render_without_display=tuple(sorted(render_without_display)),
    )


def _audit_geometry(nodes: Iterable[Any]) -> tuple[GeometrySample, ...]:
    samples: list[GeometrySample] = []
    for node in nodes:
        if _node_bypassed(node):
            continue
        if not _looks_like_geometry_node(node):
            continue
        counts = _geometry_counts(node)
        if counts is None:
            continue
        point_count, primitive_count = counts
        if point_count == 0 and primitive_count == 0:
            continue
        samples.append(
            GeometrySample(
                path=_node_path(node),
                name=_node_name(node),
                type_name=_node_type_name(node),
                category_name=_node_category_name(node),
                point_count=point_count,
                primitive_count=primitive_count,
                display_flag=_safe_bool_method(node, "isDisplayFlagSet"),
                render_flag=_safe_bool_method(node, "isRenderFlagSet"),
                is_bypassed=False,
                is_counted_for_effective_total=False,
            )
        )
    return tuple(sorted(samples, key=lambda sample: (sample.path, sample.point_count)))


def _select_effective_geometry_samples(
    samples: Sequence[GeometrySample],
) -> tuple[GeometrySample, ...]:
    render_flagged = tuple(sample for sample in samples if sample.render_flag is True)
    if render_flagged:
        return _dedupe_geometry_samples(render_flagged)
    display_flagged = tuple(sample for sample in samples if sample.display_flag is True)
    if display_flagged:
        return _dedupe_geometry_samples(display_flagged)
    if not samples:
        return ()
    max_points = max(sample.point_count for sample in samples)
    return tuple(sample for sample in samples if sample.point_count == max_points)


def _dedupe_geometry_samples(samples: Sequence[GeometrySample]) -> tuple[GeometrySample, ...]:
    selected: dict[str, GeometrySample] = {}
    for sample in samples:
        selected[sample.path] = sample
    return tuple(selected[path] for path in sorted(selected))


def _looks_like_geometry_node(node: Any) -> bool:
    if not hasattr(node, "geometry"):
        return False
    category_name = _node_category_name(node)
    return category_name in GEOMETRY_CATEGORY_NAMES or category_name.lower() == "sop"


def _geometry_counts(node: Any) -> tuple[int, int] | None:
    try:
        geometry = node.geometry()
    except Exception:
        return None
    if geometry is None:
        return None
    point_count = _geometry_collection_length(geometry, "points", "intrinsicValue", "pointcount")
    primitive_count = _geometry_collection_length(
        geometry,
        "prims",
        "intrinsicValue",
        "primitivecount",
    )
    return (point_count, primitive_count)


def _geometry_collection_length(
    geometry: Any,
    collection_method_name: str,
    intrinsic_method_name: str,
    intrinsic_name: str,
) -> int:
    intrinsic_method = getattr(geometry, intrinsic_method_name, None)
    if callable(intrinsic_method):
        try:
            value = intrinsic_method(intrinsic_name)
            if isinstance(value, int):
                return value
        except Exception:
            pass
    collection_method = getattr(geometry, collection_method_name, None)
    if not callable(collection_method):
        return 0
    try:
        return len(collection_method())
    except Exception:
        return 0


def _first_string_parameter(
    node: Any,
    parameter_names: Sequence[str],
) -> tuple[str | None, str | None]:
    for name in parameter_names:
        parm_method = getattr(node, "parm", None)
        if not callable(parm_method):
            return (None, None)
        try:
            parm = parm_method(name)
        except Exception:
            continue
        if parm is None:
            continue
        value = _parameter_string(parm)
        return (name, value)
    return (None, None)


def _parameter_string(parm: Any) -> str | None:
    for method_name in ("unexpandedString", "evalAsString"):
        method = getattr(parm, method_name, None)
        if not callable(method):
            continue
        try:
            value = method()
        except Exception:
            continue
        if isinstance(value, str):
            return value
    return None


def _final_name_score(path: str, name: str, type_name: str) -> int:
    haystack = f"{path} {name} {type_name}".lower()
    return sum(1 for token in FINAL_NAME_TOKENS if token in haystack)


def _node_path(node: Any) -> str:
    try:
        return str(node.path())
    except Exception:
        return "<unknown>"


def _node_name(node: Any) -> str:
    try:
        return str(node.name())
    except Exception:
        return "<unknown>"


def _node_type_name(node: Any) -> str:
    try:
        return str(node.type().name())
    except Exception:
        return "<unknown>"


def _node_category_name(node: Any) -> str:
    try:
        return str(node.type().category().name())
    except Exception:
        return "<unknown>"


def _node_bypassed(node: Any) -> bool:
    return _safe_bool_method(node, "isBypassed") is True


def _safe_bool_method(node: Any, method_name: str) -> bool | None:
    method = getattr(node, method_name, None)
    if not callable(method):
        return None
    try:
        value = method()
    except Exception:
        return None
    if isinstance(value, bool):
        return value
    return bool(value)


def _failure_report(hip_file: Path | str, error: str) -> dict[str, object]:
    return {
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "classification": "Placeholder Guide",
        "effective_point_count": 0,
        "effective_primitive_count": 0,
        "failures": [error],
        "flag_audit": {
            "display_flagged_nodes": [],
            "display_without_render": [],
            "render_flagged_nodes": [],
            "render_without_display": [],
        },
        "geometry": {
            "counted_nodes": [],
            "effective_point_count": 0,
            "effective_primitive_count": 0,
            "max_single_node_path": None,
            "max_single_node_point_count": 0,
            "sample_count": 0,
            "samples": [],
        },
        "hip_file": str(hip_file),
        "minimum_real_asset_points": DEFAULT_MINIMUM_REAL_ASSET_POINTS,
        "render_node_candidates": [],
        "schema_version": AUDIT_SCHEMA_VERSION,
        "selected_render_node": None,
        "status": "FAIL",
        "warnings": [],
    }


def _write_json_output(path: Path | str | None, payload: Mapping[str, object]) -> None:
    if path is None:
        return
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit one Houdini HIP topology via hython.")
    parser.add_argument("--hip-file", required=True)
    parser.add_argument("--json-output", default=None)
    parser.add_argument("--minimum-real-asset-points", type=int, default=DEFAULT_MINIMUM_REAL_ASSET_POINTS)
    parser.add_argument("--preferred-render-node-path", default=None)
    parser.add_argument(
        "--renderer-type-token",
        action="append",
        default=None,
        help="Allowed renderer type token. May be repeated.",
    )
    parser.add_argument("--include-traceback", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    renderer_type_tokens = (
        tuple(args.renderer_type_token)
        if args.renderer_type_token
        else DEFAULT_RENDERER_TYPE_TOKENS
    )
    try:
        report = audit_hip_file(
            args.hip_file,
            minimum_real_asset_points=args.minimum_real_asset_points,
            preferred_render_node_path=args.preferred_render_node_path,
            renderer_type_tokens=renderer_type_tokens,
        )
        payload = report.as_dict()
        exit_code = 0 if report.passed else 2
    except Exception as exc:
        payload = _failure_report(args.hip_file, f"audit_exception:{exc}")
        if args.include_traceback:
            payload["traceback"] = traceback.format_exc()
        exit_code = 2
    _write_json_output(args.json_output, payload)
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
