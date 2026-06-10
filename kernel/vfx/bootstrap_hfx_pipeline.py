"""Bootstrap the bureaucratic skeleton for the HFX Houdini pipeline.

This script creates contract directories, JSON schemas, Markdown contracts, and
empty validator templates for a 12-layer Houdini/VFX pipeline scaffold. It is
deliberately limited to small text artifacts and never loads real production
assets such as PBR textures, VDB volumes, HDRIs, EXRs, HIP files, or comp media.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypeAlias
import json
import os


MASTER_SEAL_STATUS: Final[str] = "HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS"
BOOTSTRAP_SCHEMA_VERSION: Final[str] = "hfx-pipeline-bootstrap-v1"
MASTER_SEAL_SCHEMA_VERSION: Final[str] = "hfx-master-pipeline-global-seal-v1"
ASSETS_HOUDINI_RELATIVE_ROOT: Final[Path] = Path("assets") / "houdini"
SCRIPT_RELATIVE_PATH: Final[str] = "kernel/vfx/bootstrap_hfx_pipeline.py"

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class SchemaSpec:
    """One JSON schema emitted into a layer directory."""

    filename: str
    title: str
    description: str
    schema_version: str
    required_fields: tuple[str, ...]
    properties: Mapping[str, JsonObject]


@dataclass(frozen=True, slots=True)
class LayerSpec:
    """One HFX pipeline layer and the files needed to govern it."""

    directory: str
    title: str
    purpose: str
    schemas: tuple[SchemaSpec, ...]
    gates: tuple[str, ...]
    validator_filename: str
    contract_filename: str = "HFX_LAYER_CONTRACT.md"


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    """Summary of directories and files touched by the bootstrap run."""

    houdini_root: Path
    layer_directories: tuple[Path, ...]
    written_files: tuple[Path, ...]


def string_property(
    description: str,
    *,
    min_length: int = 1,
    pattern: str | None = None,
    enum: Sequence[str] | None = None,
    const: str | None = None,
) -> JsonObject:
    payload: JsonObject = {
        "description": description,
        "type": "string",
    }
    if min_length:
        payload["minLength"] = min_length
    if pattern is not None:
        payload["pattern"] = pattern
    if enum is not None:
        payload["enum"] = list(enum)
    if const is not None:
        payload["const"] = const
    return payload


def boolean_property(
    description: str,
    *,
    const: bool | None = None,
    default: bool | None = None,
) -> JsonObject:
    payload: JsonObject = {
        "description": description,
        "type": "boolean",
    }
    if const is not None:
        payload["const"] = const
    if default is not None:
        payload["default"] = default
    return payload


def integer_property(
    description: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
    default: int | None = None,
) -> JsonObject:
    payload: JsonObject = {
        "description": description,
        "type": "integer",
    }
    if minimum is not None:
        payload["minimum"] = minimum
    if maximum is not None:
        payload["maximum"] = maximum
    if default is not None:
        payload["default"] = default
    return payload


def number_property(
    description: str,
    *,
    minimum: float | None = None,
    exclusive_minimum: float | None = None,
) -> JsonObject:
    payload: JsonObject = {
        "description": description,
        "type": "number",
    }
    if minimum is not None:
        payload["minimum"] = minimum
    if exclusive_minimum is not None:
        payload["exclusiveMinimum"] = exclusive_minimum
    return payload


def string_array_property(description: str) -> JsonObject:
    return {
        "description": description,
        "items": {"minLength": 1, "type": "string"},
        "type": "array",
        "uniqueItems": True,
    }


def ref_array_property(description: str) -> JsonObject:
    return {
        "description": description,
        "items": {
            "additionalProperties": False,
            "required": ("name", "ref"),
            "properties": {
                "name": string_property("Human-readable slot or artifact name."),
                "ref": string_property("Logical reference to a contract artifact."),
                "required": boolean_property(
                    "Whether the referenced artifact is required.",
                    default=True,
                ),
            },
            "type": "object",
        },
        "type": "array",
    }


def frame_range_property(description: str) -> JsonObject:
    return {
        "description": description,
        "additionalProperties": False,
        "required": ("start", "end", "step"),
        "properties": {
            "start": integer_property("First frame in the governed range.", minimum=1),
            "end": integer_property("Last frame in the governed range.", minimum=1),
            "step": integer_property("Frame increment.", minimum=1, default=1),
        },
        "type": "object",
    }


def layer_schema_document(layer: LayerSpec, schema: SchemaSpec) -> JsonObject:
    common_properties: dict[str, JsonObject] = {
        "schema_version": string_property(
            "Exact schema version for this contract payload.",
            const=schema.schema_version,
        ),
        "contract_layer": string_property(
            "Owning HFX contract layer.",
            const=layer.directory,
        ),
        "contract_status": string_property(
            "Lifecycle state for the contract payload.",
            enum=("draft", "ready_for_review", "approved", "blocked"),
        ),
        "final_pixel_claim": boolean_property(
            "Must remain false while this scaffold is not producing final pixels.",
            const=False,
        ),
        "notes": string_array_property("Optional governance notes."),
    }
    properties: dict[str, JsonObject] = {
        **common_properties,
        **dict(schema.properties),
    }
    required: tuple[str, ...] = unique_tuple(
        (
            "schema_version",
            "contract_layer",
            "contract_status",
            "final_pixel_claim",
            *schema.required_fields,
        )
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": (
            "sovereign-engineering-os://assets/houdini/"
            f"{layer.directory}/{schema.filename}"
        ),
        "title": schema.title,
        "description": schema.description,
        "type": "object",
        "additionalProperties": False,
        "required": list(required),
        "properties": properties,
    }


def unique_tuple(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return tuple(ordered)


def build_contract_markdown(layer: LayerSpec) -> str:
    schema_lines = "\n".join(
        f"- `{schema.filename}`: {schema.description}" for schema in layer.schemas
    )
    gate_lines = "\n".join(f"- {gate}" for gate in layer.gates)
    return f"""# {layer.title}

## Purpose
{layer.purpose}

## Status
This is a bureaucratic skeleton contract. It defines governance surfaces only and
does not authorize final-pixel production, renderer execution, compositing, or
loading of large production assets.

## Schemas
{schema_lines}

## Required Gates
{gate_lines}

## Hard Prohibitions
- Do not load PBR texture payloads, VDB caches, HDRIs, EXR sequences, HIP files,
  comp timelines, or delivery media from this layer.
- Do not claim final pixels from this layer.
- Do not bypass the layer validator when one is later implemented.

## Validator
The generated validator template is `{layer.validator_filename}`. It is empty by
design and must be filled with fail-closed checks before the layer can govern real
production work.
"""


def build_validator_template(layer: LayerSpec) -> str:
    schema_filenames = ", ".join(f'"{schema.filename}"' for schema in layer.schemas)
    return f'''"""Empty validator template for {layer.title}.

This template intentionally contains no production validation logic yet. It is a
typed placeholder for future fail-closed checks over the layer's JSON contracts.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final


LAYER_DIRECTORY: Final[str] = "{layer.directory}"
SCHEMA_FILENAMES: Final[tuple[str, ...]] = ({schema_filenames},)


def validate_contract(payload: Mapping[str, object]) -> tuple[str, ...]:
    """Return validation failures for one layer contract payload.

    TODO: implement layer-specific validation gates.
    """
    _ = payload
    return ()
'''


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_directory(path: Path) -> None:
    os.makedirs(path, exist_ok=True)


def write_json_file(path: Path, payload: Mapping[str, JsonValue]) -> None:
    ensure_directory(path.parent)
    encoded = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
    path.write_text(f"{encoded}\n", encoding="utf-8")


def write_text_file(path: Path, payload: str) -> None:
    ensure_directory(path.parent)
    path.write_text(payload, encoding="utf-8")


def write_layer(layer_root: Path, layer: LayerSpec) -> tuple[Path, ...]:
    layer_directory = layer_root / layer.directory
    ensure_directory(layer_directory)
    written: list[Path] = []

    contract_path = layer_directory / layer.contract_filename
    write_text_file(contract_path, build_contract_markdown(layer))
    written.append(contract_path)

    validator_path = layer_directory / layer.validator_filename
    write_text_file(validator_path, build_validator_template(layer))
    written.append(validator_path)

    for schema in layer.schemas:
        schema_path = layer_directory / schema.filename
        write_json_file(schema_path, layer_schema_document(layer, schema))
        written.append(schema_path)

    return tuple(written)


def build_global_seal_payload(layers: Sequence[LayerSpec]) -> JsonObject:
    return {
        "schema_version": MASTER_SEAL_SCHEMA_VERSION,
        "contract_layer": "hfx_master_pipeline_seal",
        "contract_status": "approved",
        "final_pixel_claim": False,
        "status": MASTER_SEAL_STATUS,
        "locked": True,
        "final_pixel_execution": "BLOCKED",
        "real_asset_loading": "DISABLED",
        "large_file_loading": "DISABLED",
        "generated_by": SCRIPT_RELATIVE_PATH,
        "governed_root": ASSETS_HOUDINI_RELATIVE_ROOT.as_posix(),
        "layer_count": len(layers),
        "layers": [layer.directory for layer in layers],
        "notes": [
            "Generated by the HFX bootstrapper.",
            "No final-pixel production is authorized by this seal.",
        ],
        "non_goals": [
            "No EXR rendering",
            "No compositing execution",
            "No PBR texture loading",
            "No VDB loading",
            "No HDRI loading",
            "No final-pixel claims",
        ],
        "change_control": {
            "bootstrap_schema_version": BOOTSTRAP_SCHEMA_VERSION,
            "status_const": MASTER_SEAL_STATUS,
            "requires_code_review": True,
            "requires_validator_implementation_before_production": True,
        },
    }


def bootstrap_hfx_pipeline() -> BootstrapResult:
    repo_root = repository_root()
    houdini_root = repo_root / ASSETS_HOUDINI_RELATIVE_ROOT
    ensure_directory(houdini_root)

    layer_directories: list[Path] = []
    written_files: list[Path] = []
    for layer in HFX_LAYERS:
        layer_directory = houdini_root / layer.directory
        layer_directories.append(layer_directory)
        written_files.extend(write_layer(houdini_root, layer))

    seal_directory = houdini_root / "hfx_master_pipeline_seal"
    seal_path = seal_directory / "HFX_MASTER_PIPELINE_GLOBAL_SEAL.json"
    write_json_file(seal_path, build_global_seal_payload(HFX_LAYERS))
    if seal_path not in written_files:
        written_files.append(seal_path)

    return BootstrapResult(
        houdini_root=houdini_root,
        layer_directories=tuple(layer_directories),
        written_files=tuple(written_files),
    )


HFX_LAYERS: Final[tuple[LayerSpec, ...]] = (
    LayerSpec(
        directory="hfx_assetization_layer",
        title="HFX Assetization Layer",
        purpose=(
            "Defines publish manifests and HDA readiness surfaces for Houdini "
            "assets before any renderer or large asset payload is touched."
        ),
        validator_filename="validate_hfx_assetization_layer.py",
        gates=(
            "Every publish manifest declares asset identity, version, ownership, and blocked claims.",
            "HDA readiness must be explicit before an asset can be routed downstream.",
            "The layer may only reference logical artifacts, not binary production payloads.",
        ),
        schemas=(
            SchemaSpec(
                filename="hfx_publish_manifest.schema.json",
                title="HFX Publish Manifest Schema",
                description="Default schema for a lightweight Houdini publish manifest.",
                schema_version="hfx-publish-manifest-v1",
                required_fields=(
                    "asset_id",
                    "asset_type",
                    "publish_version",
                    "owner",
                    "readiness_status",
                ),
                properties={
                    "asset_id": string_property("Stable asset identifier."),
                    "asset_type": string_property(
                        "Governed Houdini asset category.",
                        enum=("hda", "scene", "shot_asset", "fx_element", "utility"),
                    ),
                    "source_scene_ref": string_property(
                        "Logical reference to the source scene or work order."
                    ),
                    "publish_version": string_property(
                        "Semantic publish version.",
                        pattern=r"^v[0-9]{3,}$",
                    ),
                    "owner": string_property("Responsible artist or automation owner."),
                    "dependencies": string_array_property(
                        "Logical dependency references needed by the publish."
                    ),
                    "blocked_claims": string_array_property(
                        "Claims this publish explicitly cannot make."
                    ),
                    "readiness_status": string_property(
                        "Assetization readiness state.",
                        enum=("draft", "ready_for_hda_review", "approved", "blocked"),
                    ),
                },
            ),
            SchemaSpec(
                filename="hfx_hda_readiness.schema.json",
                title="HFX HDA Readiness Schema",
                description="Default schema for declaring HDA interface readiness.",
                schema_version="hfx-hda-readiness-v1",
                required_fields=(
                    "hda_name",
                    "interface_locked",
                    "parameter_contract_version",
                    "required_inputs",
                    "required_outputs",
                ),
                properties={
                    "hda_name": string_property("Name of the Houdini Digital Asset."),
                    "interface_locked": boolean_property(
                        "Whether the HDA interface is frozen for downstream contracts."
                    ),
                    "parameter_contract_version": string_property(
                        "Version of the public parameter contract.",
                        pattern=r"^v[0-9]+$",
                    ),
                    "required_inputs": string_array_property(
                        "Named HDA inputs required by the interface contract."
                    ),
                    "required_outputs": string_array_property(
                        "Named outputs promised by the HDA contract."
                    ),
                    "unsafe_external_file_refs": string_array_property(
                        "External references that must be resolved or banned."
                    ),
                },
            ),
        ),
    ),
    LayerSpec(
        directory="hfx_aov_pass_contract_layer",
        title="HFX AOV Pass Contract Layer",
        purpose="Defines the global AOV matrix required by render and comp layers.",
        validator_filename="validate_hfx_aov_pass_contract_layer.py",
        gates=(
            "Every AOV must declare channel type, bit depth, color role, and ownership.",
            "AOV additions require contract review before render automation can reference them.",
            "The matrix describes intent only and does not inspect rendered frames.",
        ),
        schemas=(
            SchemaSpec(
                filename="hfx_global_aov_matrix.schema.json",
                title="HFX Global AOV Matrix Schema",
                description="Default schema for the global render pass and AOV contract.",
                schema_version="hfx-global-aov-matrix-v1",
                required_fields=("show_id", "render_layer_name", "aovs"),
                properties={
                    "show_id": string_property("Show or project identifier."),
                    "render_layer_name": string_property("Governed render layer name."),
                    "aovs": {
                        "description": "AOV declarations required by this render layer.",
                        "items": {
                            "additionalProperties": False,
                            "required": (
                                "name",
                                "channel_type",
                                "bit_depth",
                                "color_space_role",
                                "owner",
                                "approval_status",
                            ),
                            "properties": {
                                "name": string_property("AOV name."),
                                "channel_type": string_property(
                                    "Channel data class.",
                                    enum=("color", "scalar", "vector", "id", "utility"),
                                ),
                                "bit_depth": string_property(
                                    "Intended storage precision.",
                                    enum=("half", "float", "uint16", "uint32"),
                                ),
                                "color_space_role": string_property(
                                    "Color-management role for the AOV."
                                ),
                                "required_for_final": boolean_property(
                                    "Whether this AOV would be required after final-pixel gates open.",
                                    default=False,
                                ),
                                "owner": string_property("Owner responsible for the AOV."),
                                "approval_status": string_property(
                                    "Review state for this AOV.",
                                    enum=("draft", "approved", "blocked"),
                                ),
                            },
                            "type": "object",
                        },
                        "minItems": 1,
                        "type": "array",
                    },
                },
            ),
        ),
    ),
    LayerSpec(
        directory="hfx_resource_library_layer",
        title="HFX Resource Library Layer",
        purpose=(
            "Defines a desktop inbox scanner manifest for cataloging candidate "
            "resources without loading or decoding large files."
        ),
        validator_filename="validate_hfx_resource_library_layer.py",
        gates=(
            "Scanner manifests must declare roots as logical references.",
            "Scanner policies must forbid binary payload reads during skeleton validation.",
            "Quarantine rules must exist before any resource is promoted.",
        ),
        schemas=(
            SchemaSpec(
                filename="hfx_desktop_inbox_scanner_manifest.schema.json",
                title="HFX Desktop Inbox Scanner Manifest Schema",
                description="Default schema for lightweight resource inbox scanning.",
                schema_version="hfx-desktop-inbox-scanner-manifest-v1",
                required_fields=(
                    "scanner_id",
                    "inbox_roots",
                    "resource_classes",
                    "no_large_file_loading",
                ),
                properties={
                    "scanner_id": string_property("Stable scanner manifest identifier."),
                    "inbox_roots": string_array_property(
                        "Logical inbox roots to inventory without payload reads."
                    ),
                    "resource_classes": string_array_property(
                        "Allowed resource classes such as texture_ref, cache_ref, or hdri_ref."
                    ),
                    "no_large_file_loading": boolean_property(
                        "Must remain true for this skeleton scanner.",
                        const=True,
                    ),
                    "max_metadata_probe_bytes": integer_property(
                        "Maximum bytes allowed for metadata-only probing.",
                        minimum=0,
                        default=0,
                    ),
                    "quarantine_rules": string_array_property(
                        "Named rules that send unknown resources to quarantine."
                    ),
                },
            ),
        ),
    ),
    LayerSpec(
        directory="hfx_lookdev_shader_contract_layer",
        title="HFX Lookdev Shader Contract Layer",
        purpose="Defines material binding and shader parameter contracts for lookdev handoff.",
        validator_filename="validate_hfx_lookdev_shader_contract_layer.py",
        gates=(
            "Material bindings must target logical geometry queries, not loaded geometry.",
            "Texture slots may reference only catalog IDs or logical resource refs.",
            "Shader parameter contracts must declare defaults and review ownership.",
        ),
        schemas=(
            SchemaSpec(
                filename="hfx_material_binding.schema.json",
                title="HFX Material Binding Schema",
                description="Default schema for logical material-to-geometry binding.",
                schema_version="hfx-material-binding-v1",
                required_fields=("material_id", "geometry_binding_query", "shader_family"),
                properties={
                    "material_id": string_property("Stable material identifier."),
                    "geometry_binding_query": string_property(
                        "Logical query for the intended geometry binding."
                    ),
                    "shader_family": string_property(
                        "Approved shader family.",
                        enum=("principled", "karma_materialx", "usd_preview", "custom_contract"),
                    ),
                    "texture_slots": ref_array_property(
                        "Texture slot references without binary texture payloads."
                    ),
                    "approval_owner": string_property("Lookdev owner for this binding."),
                },
            ),
            SchemaSpec(
                filename="hfx_shader_parameter_contract.schema.json",
                title="HFX Shader Parameter Contract Schema",
                description="Default schema for shader parameter declarations.",
                schema_version="hfx-shader-parameter-contract-v1",
                required_fields=("shader_id", "parameters"),
                properties={
                    "shader_id": string_property("Stable shader contract identifier."),
                    "parameters": {
                        "description": "Public shader parameters and defaults.",
                        "items": {
                            "additionalProperties": False,
                            "required": ("name", "value_type", "default_policy"),
                            "properties": {
                                "name": string_property("Parameter name."),
                                "value_type": string_property(
                                    "Contracted value type.",
                                    enum=("float", "integer", "boolean", "string", "color", "vector"),
                                ),
                                "default_policy": string_property(
                                    "How a default is supplied or blocked."
                                ),
                                "artist_editable": boolean_property(
                                    "Whether artists may edit this parameter.",
                                    default=True,
                                ),
                            },
                            "type": "object",
                        },
                        "type": "array",
                    },
                },
            ),
        ),
    ),
    LayerSpec(
        directory="hfx_plate_camera_integration_layer",
        title="HFX Plate Camera Integration Layer",
        purpose="Defines tracking, lens, and camera metadata contracts for shot integration.",
        validator_filename="validate_hfx_plate_camera_integration_layer.py",
        gates=(
            "Plate, track, and lens references must be logical metadata refs.",
            "Frame ranges and coordinate systems must be explicit.",
            "No image sequence, solve cache, or lens grid payload may be loaded here.",
        ),
        schemas=(
            SchemaSpec(
                filename="hfx_tracking_contract.schema.json",
                title="HFX Tracking Contract Schema",
                description="Default schema for a tracking and camera solution contract.",
                schema_version="hfx-tracking-contract-v1",
                required_fields=(
                    "shot_id",
                    "plate_ref",
                    "frame_range",
                    "tracking_solution_ref",
                    "coordinate_system",
                ),
                properties={
                    "shot_id": string_property("Shot identifier."),
                    "plate_ref": string_property("Logical plate reference."),
                    "frame_range": frame_range_property("Governed shot frame range."),
                    "tracking_solution_ref": string_property(
                        "Logical reference to the camera tracking solution."
                    ),
                    "undistortion_model": string_property(
                        "Declared undistortion model.",
                        enum=("none", "brown_conrady", "stmap_ref", "custom_contract"),
                    ),
                    "coordinate_system": string_property("World and unit coordinate declaration."),
                    "validation_status": string_property(
                        "Tracking validation state.",
                        enum=("draft", "artist_review", "approved", "blocked"),
                    ),
                },
            ),
            SchemaSpec(
                filename="hfx_lens_metadata.schema.json",
                title="HFX Lens Metadata Schema",
                description="Default schema for lens and calibration metadata.",
                schema_version="hfx-lens-metadata-v1",
                required_fields=("lens_id", "focal_length_mm", "sensor_width_mm", "distortion_model"),
                properties={
                    "lens_id": string_property("Stable lens identifier."),
                    "focal_length_mm": number_property(
                        "Focal length in millimeters.",
                        exclusive_minimum=0.0,
                    ),
                    "sensor_width_mm": number_property(
                        "Sensor width in millimeters.",
                        exclusive_minimum=0.0,
                    ),
                    "distortion_model": string_property(
                        "Lens distortion model.",
                        enum=("none", "brown_conrady", "anamorphic", "stmap_ref", "custom_contract"),
                    ),
                    "calibration_ref": string_property(
                        "Logical reference to lens calibration metadata."
                    ),
                    "units": string_property("Unit convention for lens metadata.", const="millimeters"),
                },
            ),
        ),
    ),
    LayerSpec(
        directory="hfx_render_automation_layer",
        title="HFX Render Automation Layer",
        purpose="Defines render job and retry contracts without executing renders.",
        validator_filename="validate_hfx_render_automation_layer.py",
        gates=(
            "Render jobs must remain dry-run contracts until final-pixel gates are opened.",
            "Retry policies must be explicit before farm orchestration is connected.",
            "The layer must not invoke Houdini, hython, renderers, or file probes.",
        ),
        schemas=(
            SchemaSpec(
                filename="hfx_render_job.schema.json",
                title="HFX Render Job Schema",
                description="Default schema for render automation job declarations.",
                schema_version="hfx-render-job-v1",
                required_fields=(
                    "job_id",
                    "shot_id",
                    "hip_manifest_ref",
                    "renderer",
                    "frame_range",
                    "dry_run_only",
                ),
                properties={
                    "job_id": string_property("Stable render job identifier."),
                    "shot_id": string_property("Shot identifier."),
                    "hip_manifest_ref": string_property("Logical HIP or scene manifest reference."),
                    "renderer": string_property(
                        "Renderer family intended by the contract.",
                        enum=("karma", "mantra", "opengl", "custom_contract"),
                    ),
                    "frame_range": frame_range_property("Frames the job would cover."),
                    "output_intent": string_property("Declared output intent for downstream review."),
                    "aov_matrix_ref": string_property("Logical reference to the approved AOV matrix."),
                    "max_retries": integer_property("Maximum retries allowed by job policy.", minimum=0),
                    "dry_run_only": boolean_property(
                        "Must remain true in the no-final-pixels scaffold.",
                        const=True,
                    ),
                },
            ),
            SchemaSpec(
                filename="hfx_render_retry_policy.schema.json",
                title="HFX Render Retry Policy Schema",
                description="Default schema for render retry and escalation policy.",
                schema_version="hfx-render-retry-policy-v1",
                required_fields=("policy_id", "max_attempts", "retryable_failures", "escalation_owner"),
                properties={
                    "policy_id": string_property("Stable retry policy identifier."),
                    "retryable_failures": string_array_property(
                        "Failure classes that can be retried by automation."
                    ),
                    "max_attempts": integer_property("Maximum attempts including the first try.", minimum=1),
                    "backoff_seconds": {
                        "description": "Retry backoff intervals in seconds.",
                        "items": {"minimum": 0, "type": "integer"},
                        "type": "array",
                    },
                    "escalation_owner": string_property("Owner paged when retries are exhausted."),
                },
            ),
        ),
    ),
    LayerSpec(
        directory="hfx_comp_automation_layer",
        title="HFX Comp Automation Layer",
        purpose="Defines Nuke and Resolve comp template schemas without running comp applications.",
        validator_filename="validate_hfx_comp_automation_layer.py",
        gates=(
            "Comp templates may reference render intents but not actual frame sequences.",
            "Color-management refs must be explicit before a template is admitted.",
            "The layer must not launch Nuke, Resolve, or media transcode jobs.",
        ),
        schemas=(
            SchemaSpec(
                filename="hfx_nuke_comp_template.schema.json",
                title="HFX Nuke Comp Template Schema",
                description="Default schema for Nuke comp template contracts.",
                schema_version="hfx-nuke-comp-template-v1",
                required_fields=("template_id", "shot_id", "script_template_ref", "input_layers"),
                properties={
                    "template_id": string_property("Stable Nuke template identifier."),
                    "shot_id": string_property("Shot identifier."),
                    "script_template_ref": string_property("Logical Nuke script template reference."),
                    "input_layers": ref_array_property("Logical render layer references."),
                    "output_nodes": string_array_property("Named output node contracts."),
                    "color_management_ref": string_property("OCIO or ACES contract reference."),
                },
            ),
            SchemaSpec(
                filename="hfx_resolve_comp_template.schema.json",
                title="HFX Resolve Comp Template Schema",
                description="Default schema for Resolve/Fusion comp template contracts.",
                schema_version="hfx-resolve-comp-template-v1",
                required_fields=("template_id", "timeline_template_ref", "input_clips"),
                properties={
                    "template_id": string_property("Stable Resolve template identifier."),
                    "timeline_template_ref": string_property("Logical timeline template reference."),
                    "input_clips": ref_array_property("Logical input clip references."),
                    "output_presets": string_array_property("Named output preset contracts."),
                    "color_management_ref": string_property("OCIO or ACES contract reference."),
                },
            ),
        ),
    ),
    LayerSpec(
        directory="hfx_color_management_layer",
        title="HFX Color Management Layer",
        purpose="Defines OCIO and ACES governance contracts for the pipeline.",
        validator_filename="validate_hfx_color_management_layer.py",
        gates=(
            "Color contracts must reference configs and transforms logically.",
            "Roles, display views, and interchange spaces must be declared before render or comp use.",
            "The layer must not load LUT payloads or OCIO config files during scaffold validation.",
        ),
        schemas=(
            SchemaSpec(
                filename="hfx_ocio_contract.schema.json",
                title="HFX OCIO Contract Schema",
                description="Default schema for OpenColorIO contract declarations.",
                schema_version="hfx-ocio-contract-v1",
                required_fields=("config_ref", "config_version", "roles", "display_views", "no_lut_payload"),
                properties={
                    "config_ref": string_property("Logical OCIO config reference."),
                    "config_version": string_property("Declared OCIO config version."),
                    "roles": {
                        "description": "Named OCIO roles mapped to logical color spaces.",
                        "additionalProperties": {"type": "string"},
                        "type": "object",
                    },
                    "display_views": string_array_property("Allowed display/view combinations."),
                    "no_lut_payload": boolean_property(
                        "Must remain true so LUT payloads are not embedded.",
                        const=True,
                    ),
                },
            ),
            SchemaSpec(
                filename="hfx_aces_contract.schema.json",
                title="HFX ACES Contract Schema",
                description="Default schema for ACES color pipeline declarations.",
                schema_version="hfx-aces-contract-v1",
                required_fields=("aces_version", "working_space", "interchange_space"),
                properties={
                    "aces_version": string_property("ACES version declaration."),
                    "working_space": string_property("Working color space."),
                    "interchange_space": string_property("Interchange color space."),
                    "required_transforms": string_array_property(
                        "Named transforms required by downstream contracts."
                    ),
                    "approval_status": string_property(
                        "Color contract approval state.",
                        enum=("draft", "approved", "blocked"),
                    ),
                },
            ),
        ),
    ),
    LayerSpec(
        directory="hfx_review_dailies_layer",
        title="HFX Review Dailies Layer",
        purpose="Defines dailies manifests and QC checklist schemas for review gates.",
        validator_filename="validate_hfx_review_dailies_layer.py",
        gates=(
            "Dailies manifests must reference media logically and cannot inspect encoded media.",
            "QC checklist items must declare severity, required status, and waiver state.",
            "Review approval does not imply final-pixel acceptance while the master seal blocks it.",
        ),
        schemas=(
            SchemaSpec(
                filename="hfx_dailies_manifest.schema.json",
                title="HFX Dailies Manifest Schema",
                description="Default schema for daily review submission manifests.",
                schema_version="hfx-dailies-manifest-v1",
                required_fields=("review_id", "shot_id", "submitted_by", "media_ref", "qc_checklist_ref"),
                properties={
                    "review_id": string_property("Stable dailies review identifier."),
                    "shot_id": string_property("Shot identifier."),
                    "submitted_by": string_property("Submitting artist or automation."),
                    "media_ref": string_property("Logical review media reference."),
                    "frame_range": frame_range_property("Submitted frame range."),
                    "color_pipeline_ref": string_property("Color-management contract reference."),
                    "qc_checklist_ref": string_property("QC checklist contract reference."),
                },
            ),
            SchemaSpec(
                filename="hfx_qc_checklist.schema.json",
                title="HFX QC Checklist Schema",
                description="Default schema for review and dailies QC checklists.",
                schema_version="hfx-qc-checklist-v1",
                required_fields=("checklist_id", "checks"),
                properties={
                    "checklist_id": string_property("Stable QC checklist identifier."),
                    "checks": {
                        "description": "QC checks required for the review gate.",
                        "items": {
                            "additionalProperties": False,
                            "required": ("id", "label", "severity", "required", "status"),
                            "properties": {
                                "id": string_property("Stable check identifier."),
                                "label": string_property("Human-readable check label."),
                                "severity": string_property(
                                    "Severity of failure.",
                                    enum=("info", "warning", "error", "blocker"),
                                ),
                                "required": boolean_property(
                                    "Whether this check blocks approval when failed."
                                ),
                                "status": string_property(
                                    "Current check status.",
                                    enum=("pending", "pass", "fail", "waived"),
                                ),
                            },
                            "type": "object",
                        },
                        "type": "array",
                    },
                },
            ),
        ),
    ),
    LayerSpec(
        directory="hfx_final_pixel_gate_layer",
        title="HFX Final Pixel Gate Layer",
        purpose="Defines the blocked claim registry that prevents premature final-pixel assertions.",
        validator_filename="validate_hfx_final_pixel_gate_layer.py",
        gates=(
            "Final-pixel claims must be registered as blocked unless explicitly cleared later.",
            "Blocked claims must include owner, reason, and the gate that can unblock them.",
            "The registry is a governance artifact and does not inspect final images.",
        ),
        schemas=(
            SchemaSpec(
                filename="hfx_blocked_claim_registry.schema.json",
                title="HFX Blocked Claim Registry Schema",
                description="Default schema for final-pixel blocked claim governance.",
                schema_version="hfx-blocked-claim-registry-v1",
                required_fields=("registry_id", "global_block_enabled", "blocked_claims"),
                properties={
                    "registry_id": string_property("Stable blocked claim registry identifier."),
                    "global_block_enabled": boolean_property(
                        "Must remain true while the master seal blocks final pixels.",
                        const=True,
                    ),
                    "blocked_claims": {
                        "description": "Claims that cannot be made by this pipeline yet.",
                        "items": {
                            "additionalProperties": False,
                            "required": (
                                "claim_id",
                                "claim_text",
                                "reason",
                                "blocked_until_gate",
                                "owner",
                                "status",
                            ),
                            "properties": {
                                "claim_id": string_property("Stable claim identifier."),
                                "claim_text": string_property("Claim currently blocked."),
                                "reason": string_property("Reason the claim is blocked."),
                                "blocked_until_gate": string_property(
                                    "Gate that must pass before the claim can be considered."
                                ),
                                "owner": string_property("Owner responsible for clearing the claim."),
                                "status": string_property(
                                    "Blocked claim lifecycle status.",
                                    enum=("active", "resolved", "superseded"),
                                ),
                            },
                            "type": "object",
                        },
                        "minItems": 1,
                        "type": "array",
                    },
                },
            ),
        ),
    ),
    LayerSpec(
        directory="hfx_delivery_package_layer",
        title="HFX Delivery Package Layer",
        purpose="Defines delivery manifest contracts without packaging final media.",
        validator_filename="validate_hfx_delivery_package_layer.py",
        gates=(
            "Delivery manifests must enumerate intended deliverables and approvals.",
            "Checksum manifests must be referenced logically until real packaging is authorized.",
            "Delivery readiness cannot override the master no-final-pixels seal.",
        ),
        schemas=(
            SchemaSpec(
                filename="hfx_delivery_manifest.schema.json",
                title="HFX Delivery Manifest Schema",
                description="Default schema for delivery package governance.",
                schema_version="hfx-delivery-manifest-v1",
                required_fields=("delivery_id", "package_version", "shots", "deliverables", "approvals"),
                properties={
                    "delivery_id": string_property("Stable delivery package identifier."),
                    "package_version": string_property(
                        "Delivery package version.",
                        pattern=r"^v[0-9]{3,}$",
                    ),
                    "shots": string_array_property("Shot identifiers included in the package."),
                    "deliverables": ref_array_property("Logical deliverable references."),
                    "checksums_manifest_ref": string_property(
                        "Logical checksum manifest reference."
                    ),
                    "color_contract_ref": string_property("Color-management contract reference."),
                    "approvals": string_array_property("Named approvals required for delivery."),
                },
            ),
        ),
    ),
    LayerSpec(
        directory="hfx_master_pipeline_seal",
        title="HFX Master Pipeline Seal",
        purpose=(
            "Defines the locked global seal proving the scaffold is ready as a "
            "contract system while still forbidding final-pixel production."
        ),
        validator_filename="validate_hfx_master_pipeline_seal.py",
        gates=(
            f"`HFX_MASTER_PIPELINE_GLOBAL_SEAL.json` status must equal `{MASTER_SEAL_STATUS}`.",
            "The seal must list all 12 governed HFX layers.",
            "The seal must keep final-pixel execution and large asset loading blocked.",
        ),
        schemas=(
            SchemaSpec(
                filename="hfx_master_pipeline_global_seal.schema.json",
                title="HFX Master Pipeline Global Seal Schema",
                description="Default schema for the locked global no-final-pixels seal.",
                schema_version=MASTER_SEAL_SCHEMA_VERSION,
                required_fields=(
                    "status",
                    "locked",
                    "final_pixel_execution",
                    "real_asset_loading",
                    "large_file_loading",
                    "generated_by",
                    "governed_root",
                    "layer_count",
                    "layers",
                    "change_control",
                ),
                properties={
                    "status": string_property(
                        "Permanently locked master pipeline status.",
                        const=MASTER_SEAL_STATUS,
                    ),
                    "locked": boolean_property("Seal lock flag.", const=True),
                    "final_pixel_execution": string_property(
                        "Final-pixel execution state.",
                        const="BLOCKED",
                    ),
                    "real_asset_loading": string_property(
                        "Real asset loading state.",
                        const="DISABLED",
                    ),
                    "large_file_loading": string_property(
                        "Large file loading state.",
                        const="DISABLED",
                    ),
                    "generated_by": string_property(
                        "Bootstrapper responsible for generating the seal.",
                        const=SCRIPT_RELATIVE_PATH,
                    ),
                    "governed_root": string_property(
                        "Governed Houdini asset root.",
                        const=ASSETS_HOUDINI_RELATIVE_ROOT.as_posix(),
                    ),
                    "layer_count": {
                        "description": "Number of governed HFX layers.",
                        "const": 12,
                        "type": "integer",
                    },
                    "layers": string_array_property("All governed HFX layer directories."),
                    "non_goals": string_array_property(
                        "Production actions explicitly outside this scaffold."
                    ),
                    "change_control": {
                        "description": "Immutable change-control facts for the seal.",
                        "additionalProperties": False,
                        "required": (
                            "bootstrap_schema_version",
                            "status_const",
                            "requires_code_review",
                            "requires_validator_implementation_before_production",
                        ),
                        "properties": {
                            "bootstrap_schema_version": string_property(
                                "Bootstrapper schema version.",
                                const=BOOTSTRAP_SCHEMA_VERSION,
                            ),
                            "status_const": string_property(
                                "Exact status constant required by the seal.",
                                const=MASTER_SEAL_STATUS,
                            ),
                            "requires_code_review": boolean_property(
                                "Whether changes to the seal require review.",
                                const=True,
                            ),
                            "requires_validator_implementation_before_production": (
                                boolean_property(
                                    "Whether validators must exist before production use.",
                                    const=True,
                                )
                            ),
                        },
                        "type": "object",
                    },
                },
            ),
        ),
    ),
)


def main() -> int:
    result = bootstrap_hfx_pipeline()
    print(
        "HFX pipeline scaffold bootstrapped: "
        f"{len(result.layer_directories)} layer directories, "
        f"{len(result.written_files)} files under {result.houdini_root}"
    )
    print(f"Master seal status: {MASTER_SEAL_STATUS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
