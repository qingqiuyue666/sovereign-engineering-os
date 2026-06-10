#!/usr/bin/env python3
"""Generate metadata-only capability PR scaffold files.

This tool writes inert skeleton text for future capability PRs. It does not
create runners, issue tokens, launch browsers, execute adapters, or access the
network.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from string import Template

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

DEFAULT_OUTPUT_FILE_NAMES = (
    "result_contract.json",
    "output_artifact_manifest.json",
    "artifact_index.json",
    "artifact_index_manifest.json",
    "summary.md",
    "checklist.md",
)

DEFAULT_FORBIDDEN_BOUNDARIES = (
    "live website automation",
    "arbitrary URL execution",
    "general browser automation",
    "account login",
    "credential handling",
    "cookie handling",
    "scraping",
    "CAPTCHA",
    "bypass",
    "stealth",
    "external network",
    "npm install",
    "npx install",
    "candidate repo runtime execution",
    "token issuance",
    "runner creation",
    "adapter execution",
    "Playwright execution",
    "browser opening",
    "production promotion",
    "autonomous execution",
    "daemon/scheduler/worker loop",
)

DETERMINISTIC_REJECTION_REASONS = (
    "metadata_only_boundary_missing",
    "forbidden_boundary_requested",
    "non_contract_output_requested",
    "unsafe_template_mutation_requested",
)

_CAPABILITY_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*[a-z0-9]$")


class ScaffoldCollisionError(FileExistsError):
    """Raised when scaffold output would overwrite existing files."""


@dataclass(frozen=True)
class CapabilityScaffoldConfig:
    capability_id: str
    output_dir: Path
    capability_file_name: str | None = None
    output_file_names: tuple[str, ...] = DEFAULT_OUTPUT_FILE_NAMES
    allow_overwrite: bool = False


@dataclass(frozen=True)
class PlannedScaffoldFile:
    template_name: str
    relative_path: Path
    text: str

    def target_path(self, output_dir: Path) -> Path:
        return output_dir / self.relative_path


def _validate_capability_id(capability_id: str) -> str:
    normalized = capability_id.strip()
    if not _CAPABILITY_ID_RE.fullmatch(normalized):
        raise ValueError(
            "capability_id must be lowercase kebab/snake text beginning with a "
            "letter and ending with a letter or digit"
        )
    return normalized


def _validate_file_name(file_name: str) -> str:
    name = file_name.strip()
    if not name.endswith(".py"):
        raise ValueError("capability_file_name must end with .py")
    if Path(name).name != name:
        raise ValueError("capability_file_name must not include directories")
    if not re.fullmatch(r"[a-z][a-z0-9_]*\.py", name):
        raise ValueError("capability_file_name must be lowercase snake_case .py")
    return name


def _module_slug(capability_id: str) -> str:
    return capability_id.replace("-", "_")


def _class_name(capability_id: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[-_]+", capability_id))


def _render_sequence(items: tuple[str, ...], checkbox: bool = False) -> str:
    marker = "- [ ] " if checkbox else "- "
    return "\n".join(f"{marker}{item}" for item in items)


def _render_python_tuple(items: tuple[str, ...]) -> str:
    rendered = ",\n".join(f"    {item!r}" for item in items)
    return f"(\n{rendered},\n)"


def _context(config: CapabilityScaffoldConfig) -> dict[str, str]:
    capability_id = _validate_capability_id(config.capability_id)
    module_slug = _module_slug(capability_id)
    capability_file_name = _validate_file_name(
        config.capability_file_name or f"{module_slug}_capability.py"
    )
    output_file_names = tuple(name.strip() for name in config.output_file_names if name.strip())
    if not output_file_names:
        raise ValueError("at least one output file name is required")
    if any(Path(name).name != name for name in output_file_names):
        raise ValueError("output file names must not include directories")
    return {
        "capability_id": capability_id,
        "capability_module_name": Path(capability_file_name).stem,
        "capability_class_name": _class_name(capability_id),
        "capability_file_name": capability_file_name,
        "tracer_test_file_name": f"test_{module_slug}.py",
        "decision_file_name": f"{capability_id}_decision.md",
        "output_file_names": _render_sequence(output_file_names),
        "output_file_names_python": _render_python_tuple(output_file_names),
        "forbidden_boundaries": _render_sequence(DEFAULT_FORBIDDEN_BOUNDARIES, checkbox=True),
        "forbidden_boundaries_python": _render_python_tuple(DEFAULT_FORBIDDEN_BOUNDARIES),
        "rejection_reasons": _render_sequence(DETERMINISTIC_REJECTION_REASONS),
        "rejection_reasons_python": _render_python_tuple(DETERMINISTIC_REJECTION_REASONS),
    }


def _render_template(template_name: str, context: dict[str, str]) -> str:
    template_path = TEMPLATE_DIR / template_name
    template = Template(template_path.read_text(encoding="utf-8"))
    return template.substitute(context)


def plan_scaffold(config: CapabilityScaffoldConfig) -> tuple[PlannedScaffoldFile, ...]:
    context = _context(config)
    files = (
        ("capability_module.py.tmpl", Path("capability") / context["capability_file_name"]),
        ("tracer_test.py.tmpl", Path("tests/tracer_bullet") / context["tracer_test_file_name"]),
        ("decision_doc.md.tmpl", Path("docs/decisions") / context["decision_file_name"]),
        ("result_contract.md.tmpl", Path("contracts/result_contract.md")),
        ("output_manifest_contract.md.tmpl", Path("contracts/output_artifact_manifest_contract.md")),
        ("artifact_index_contract.md.tmpl", Path("contracts/artifact_index_contract.md")),
        (
            "artifact_index_manifest_contract.md.tmpl",
            Path("contracts/artifact_index_manifest_contract.md"),
        ),
        ("summary.md.tmpl", Path("reports/summary.md")),
        ("boundary_checklist.md.tmpl", Path("checklists/forbidden_boundary_checklist.md")),
        ("pr_report.md.tmpl", Path("reports/pr_report_template.md")),
        ("validation_checklist.md.tmpl", Path("validation/validation_checklist.md")),
    )
    return tuple(
        PlannedScaffoldFile(
            template_name=template_name,
            relative_path=relative_path,
            text=_render_template(template_name, context),
        )
        for template_name, relative_path in files
    )


def generate_scaffold(config: CapabilityScaffoldConfig) -> tuple[Path, ...]:
    output_dir = Path(config.output_dir)
    planned = plan_scaffold(config)
    collisions = [
        planned_file.relative_path.as_posix()
        for planned_file in planned
        if planned_file.target_path(output_dir).exists()
    ]
    if collisions and not config.allow_overwrite:
        joined = ", ".join(sorted(collisions))
        raise ScaffoldCollisionError(f"output_collision: {joined}")

    written: list[Path] = []
    for planned_file in planned:
        target = planned_file.target_path(output_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(planned_file.text, encoding="utf-8")
        written.append(target)
    return tuple(written)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an inert metadata-only capability PR scaffold.",
    )
    parser.add_argument("--capability-id", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--capability-file-name")
    parser.add_argument(
        "--output-file",
        action="append",
        dest="output_files",
        help="Expected output file name. May be repeated.",
    )
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Explicit safe flag allowing existing scaffold files to be replaced.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    config = CapabilityScaffoldConfig(
        capability_id=args.capability_id,
        output_dir=args.output_dir,
        capability_file_name=args.capability_file_name,
        output_file_names=tuple(args.output_files or DEFAULT_OUTPUT_FILE_NAMES),
        allow_overwrite=args.allow_overwrite,
    )
    written = generate_scaffold(config)
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
