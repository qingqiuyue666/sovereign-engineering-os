"""
Zero-dependency runtime schema validator for frozen artifact schemas.

Constitutional anchors:
- v11 Section 22.7 (context completeness)
- v11 Section 22.10 (invariant enforcement binding)
- Foundation Section 3.4 (runtime enforcement: ingress + pre-persist)

This validator deepens the previous required-field-only checks by also
verifying types, enum values, const values, string constraints, integer
constraints, array constraints (including item-level type checks),
nullable-type patterns, additionalProperties rejection, and nested
object recursion found in the frozen JSON Schema files.

Honest posture:
- This is NOT a full JSON Schema draft-2020-12 validator. It does not
  handle $ref, allOf/anyOf/oneOf, patternProperties, or advanced
  composition. Full draft-2020-12 validation remains a hardening-stage
  item gated on admitting an external dependency (e.g. jsonschema).
- What it does check: required fields, type (string/integer/boolean/
  array/object/null), enum, const, minLength, minimum, minItems,
  maxItems, additionalProperties (when false), nested object recursion
  (required + properties), array item schemas, format presence (not
  format correctness), and nullable union types.
- Every validation failure is fail-closed: the caller receives a
  SchemaValidationError with all violations listed, not just the first.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


class SchemaValidationError(Exception):
    """Raised when an artifact fails schema validation.

    The `violations` attribute lists every individual rule violation
    so callers can emit complete diagnostic evidence.
    """

    def __init__(self, artifact_type: str, violations: list[str]) -> None:
        self.artifact_type = artifact_type
        self.violations = violations
        detail = "; ".join(violations[:10])
        if len(violations) > 10:
            detail += f" ... and {len(violations) - 10} more"
        super().__init__(f"{artifact_type} schema validation failed: {detail}")


# JSON Schema type -> Python type(s) mapping.
_TYPE_MAP: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


def _check_type(
    value: Any,
    type_spec: Any,
    field_path: str,
    violations: list[str],
) -> None:
    """Check a value against a JSON Schema type specification."""
    if type_spec is None:
        return

    # Handle nullable union types: {"type": ["string", "null"]}
    if isinstance(type_spec, list):
        if value is None and "null" in type_spec:
            return
        non_null_types = [t for t in type_spec if t != "null"]
        if not non_null_types:
            return
        allowed = tuple(
            t for tn in non_null_types for t in _TYPE_MAP.get(tn, ())
        )
        if allowed and not isinstance(value, allowed):
            violations.append(
                f"{field_path}: expected type {type_spec}, got {type(value).__name__}"
            )
        return

    # Simple type: {"type": "string"}
    if isinstance(type_spec, str):
        if type_spec == "null":
            if value is not None:
                violations.append(
                    f"{field_path}: expected null, got {type(value).__name__}"
                )
            return
        allowed = _TYPE_MAP.get(type_spec, ())
        if allowed and not isinstance(value, allowed):
            violations.append(
                f"{field_path}: expected type {type_spec}, got {type(value).__name__}"
            )


def _check_field(
    value: Any,
    field_schema: Mapping[str, Any],
    field_path: str,
    violations: list[str],
) -> None:
    """Validate a single field value against its schema definition."""
    # Type check.
    type_spec = field_schema.get("type")
    _check_type(value, type_spec, field_path, violations)

    if value is None:
        return

    # Const check.
    if "const" in field_schema and value != field_schema["const"]:
        violations.append(
            f"{field_path}: value {value!r} does not match const {field_schema['const']!r}"
        )

    # Enum check.
    enum_values = field_schema.get("enum")
    if enum_values is not None and value not in enum_values:
        violations.append(
            f"{field_path}: value {value!r} not in enum {enum_values}"
        )

    # String constraints.
    if isinstance(value, str):
        min_length = field_schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            violations.append(
                f"{field_path}: string length {len(value)} < minLength {min_length}"
            )

    # Integer/number constraints.
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = field_schema.get("minimum")
        if minimum is not None and value < minimum:
            violations.append(
                f"{field_path}: value {value} < minimum {minimum}"
            )

    # Array constraints.
    if isinstance(value, list):
        min_items = field_schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            violations.append(
                f"{field_path}: array length {len(value)} < minItems {min_items}"
            )
        max_items = field_schema.get("maxItems")
        if max_items is not None and len(value) > max_items:
            violations.append(
                f"{field_path}: array length {len(value)} > maxItems {max_items}"
            )
        # Item-level validation.
        items_schema = field_schema.get("items")
        if items_schema is not None:
            for idx, item in enumerate(value):
                item_path = f"{field_path}[{idx}]"
                _check_field(item, items_schema, item_path, violations)

    # Nested object recursion: validate required fields and properties
    # within nested objects (e.g., review_artifact.rendering_provenance).
    if isinstance(value, dict) and type_spec == "object":
        nested_properties = field_schema.get("properties", {})
        nested_required = field_schema.get("required", [])
        for req_field in nested_required:
            if req_field not in value:
                violations.append(
                    f"{field_path}: missing required field: {req_field}"
                )
        for nested_name, nested_value in value.items():
            if nested_name in nested_properties:
                _check_field(
                    nested_value,
                    nested_properties[nested_name],
                    f"{field_path}.{nested_name}",
                    violations,
                )
        # additionalProperties enforcement on nested objects.
        if field_schema.get("additionalProperties") is False:
            extra = set(value.keys()) - set(nested_properties.keys())
            for extra_field in sorted(extra):
                violations.append(
                    f"{field_path}: additional property not allowed: {extra_field}"
                )


def validate_artifact(
    artifact: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> list[str]:
    """Validate an artifact against a frozen JSON Schema.

    Returns a list of violation strings (empty = valid).

    This function is deterministic and side-effect-free. Callers decide
    whether to raise SchemaValidationError or handle violations differently.
    """
    violations: list[str] = []
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # Check required fields.
    for field_name in required:
        if field_name not in artifact:
            violations.append(f"missing required field: {field_name}")

    # Check each present field against its property schema.
    for field_name, value in artifact.items():
        if field_name in properties:
            field_schema = properties[field_name]
            _check_field(value, field_schema, field_name, violations)

    # additionalProperties enforcement: reject fields not declared in
    # the schema's properties when additionalProperties is false.
    if schema.get("additionalProperties") is False:
        extra = set(artifact.keys()) - set(properties.keys())
        for extra_field in sorted(extra):
            violations.append(
                f"additional property not allowed: {extra_field}"
            )

    return violations


def validate_artifact_strict(
    artifact: Mapping[str, Any],
    schema: Mapping[str, Any],
    artifact_type_label: str | None = None,
) -> None:
    """Validate and raise SchemaValidationError on any violation.

    This is the function services call at ingress boundaries.
    """
    violations = validate_artifact(artifact, schema)
    if violations:
        label = artifact_type_label or schema.get("properties", {}).get(
            "artifact_type", {}
        ).get("const", "unknown")
        raise SchemaValidationError(label, violations)
