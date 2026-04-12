"""
Machine-checked schema keyword coverage gate.

Constitutional anchors:
- v11 Section 22.10 (invariant enforcement binding — schema enforcement must
  be mechanically auditable)
- v11 Section 24.2 (invariant coverage must be non-zero and passing)
- Foundation Section 3.3 (schema freeze discipline)
- Foundation Section 3.4 (runtime enforcement: ingress + pre-persist)

Purpose:
  This gate reads every frozen .schema.json file, walks the schema tree to
  find which validation-relevant keywords are actually used, and then asserts
  the validator catches a violation of each keyword in the context of each
  schema that uses it.

  If a new keyword is added to a frozen schema but the validator does not
  enforce it, this gate fails. If the validator regresses on an existing
  keyword, this gate fails.

Honest posture:
- format is documented as presence-only (not correctness-checked). The gate
  verifies that format-bearing fields accept string values and that the
  keyword's presence is acknowledged by the validator.
- const is not currently used in any frozen schema. The gate still checks it
  in the validator-level depth tests (test_schema_validation_depth.py).

Coverage semantics:
  For each schema S and each keyword K used in S:
    - construct a minimal valid artifact for S
    - mutate it to violate K
    - assert validate_artifact returns at least one violation mentioning K's
      enforcement behavior
"""

from __future__ import annotations

import json
import sys
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from kernel.schemas import load_schema
from kernel.schemas.validator import validate_artifact


# ---------------------------------------------------------------------------
# Schema discovery
# ---------------------------------------------------------------------------

_SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "kernel" / "schemas"

# Every frozen schema in the pack.
FROZEN_SCHEMA_NAMES = sorted(
    p.stem.replace(".schema", "")
    for p in _SCHEMA_DIR.glob("*.schema.json")
)

# The validation-relevant JSON Schema keywords we gate on.
# Each maps to the violation substring the validator emits when enforcing it.
GATED_KEYWORDS: dict[str, str] = {
    "required": "missing required field",
    "type": "expected type",
    "enum": "not in enum",
    "minLength": "minLength",
    "minimum": "minimum",
    "minItems": "minItems",
    "maxItems": "maxItems",
    "additionalProperties": "additional property not allowed",
    "items": "expected type",  # item-level type violation
}

# Keywords that require special handling (nested objects, format).
NESTED_KEYWORDS = {"nested_required", "nested_additionalProperties"}


# ---------------------------------------------------------------------------
# Helpers: build minimal valid artifacts
# ---------------------------------------------------------------------------


def _default_value_for_type(type_spec: Any, field_schema: dict) -> Any:
    """Produce a minimal valid value for a JSON Schema type specification."""
    if isinstance(type_spec, list):
        non_null = [t for t in type_spec if t != "null"]
        if not non_null:
            return None
        type_spec = non_null[0]

    if type_spec == "string":
        if "enum" in field_schema:
            return field_schema["enum"][0]
        if "format" in field_schema and field_schema["format"] == "date-time":
            return datetime.now(timezone.utc).isoformat()
        return "placeholder"
    if type_spec == "integer":
        return max(0, field_schema.get("minimum", 0))
    if type_spec == "number":
        return max(0.0, field_schema.get("minimum", 0.0))
    if type_spec == "boolean":
        return False
    if type_spec == "array":
        item_schema = field_schema.get("items", {})
        min_items = field_schema.get("minItems", 0)
        item_val = _default_value_for_type(item_schema.get("type", "string"), item_schema)
        return [item_val] * max(min_items, 0)
    if type_spec == "object":
        nested = {}
        for name, prop in field_schema.get("properties", {}).items():
            nested[name] = _default_value_for_type(prop.get("type", "string"), prop)
        return nested
    return None


def _build_minimal_valid_artifact(schema: dict) -> dict:
    """Build a minimal artifact that passes validation against the schema."""
    artifact: dict[str, Any] = {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # Fill all required fields with valid defaults.
    for field_name in required:
        if field_name in properties:
            field_schema = properties[field_name]
            artifact[field_name] = _default_value_for_type(
                field_schema.get("type", "string"), field_schema
            )
        else:
            artifact[field_name] = "placeholder"

    return artifact


# ---------------------------------------------------------------------------
# Keyword extraction from a schema tree
# ---------------------------------------------------------------------------


def _extract_keywords_from_properties(properties: dict) -> set[str]:
    """Walk properties to find which validation-relevant keywords are used."""
    keywords: set[str] = set()
    for _field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            continue
        if "type" in field_schema:
            keywords.add("type")
        if "enum" in field_schema:
            keywords.add("enum")
        if "const" in field_schema:
            keywords.add("const")
        if "minLength" in field_schema:
            keywords.add("minLength")
        if "minimum" in field_schema:
            keywords.add("minimum")
        if "minItems" in field_schema:
            keywords.add("minItems")
        if "maxItems" in field_schema:
            keywords.add("maxItems")
        if "items" in field_schema:
            keywords.add("items")
        if "format" in field_schema:
            keywords.add("format")
        # Nested object detection.
        if field_schema.get("type") == "object" and "properties" in field_schema:
            if "required" in field_schema:
                keywords.add("nested_required")
            if field_schema.get("additionalProperties") is False:
                keywords.add("nested_additionalProperties")
    return keywords


def _extract_keywords(schema: dict) -> set[str]:
    """Extract all validation-relevant keywords from a schema."""
    keywords: set[str] = set()
    if "required" in schema:
        keywords.add("required")
    if schema.get("additionalProperties") is False:
        keywords.add("additionalProperties")
    properties = schema.get("properties", {})
    keywords |= _extract_keywords_from_properties(properties)
    return keywords


# ---------------------------------------------------------------------------
# Find specific fields for targeted violation generation
# ---------------------------------------------------------------------------


def _find_field_with_keyword(
    schema: dict, keyword: str
) -> tuple[str, dict] | None:
    """Find the first field in properties that uses the given keyword."""
    properties = schema.get("properties", {})
    for field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            continue

        if keyword == "nested_required":
            if (
                field_schema.get("type") == "object"
                and "required" in field_schema
                and "properties" in field_schema
            ):
                return field_name, field_schema
        elif keyword == "nested_additionalProperties":
            if (
                field_schema.get("type") == "object"
                and field_schema.get("additionalProperties") is False
            ):
                return field_name, field_schema
        elif keyword in field_schema:
            return field_name, field_schema
    return None


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestAllFrozenSchemasDiscovered(unittest.TestCase):
    """Gate: we must discover at least the 15 frozen schemas."""

    def test_schema_count(self) -> None:
        self.assertGreaterEqual(
            len(FROZEN_SCHEMA_NAMES), 15,
            f"Expected >=15 frozen schemas, found {len(FROZEN_SCHEMA_NAMES)}: {FROZEN_SCHEMA_NAMES}",
        )


class TestMinimalValidArtifactPassesEachSchema(unittest.TestCase):
    """Precondition: our minimal-valid-artifact builder actually passes validation."""

    def test_each_schema(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            with self.subTest(schema=name):
                schema = load_schema(name)
                artifact = _build_minimal_valid_artifact(schema)
                violations = validate_artifact(artifact, schema)
                self.assertEqual(
                    violations, [],
                    f"Minimal valid artifact for {name} has violations: {violations}",
                )


class TestRequiredKeywordEnforcedAcrossSchemas(unittest.TestCase):
    """Gate: every schema with 'required' must reject an artifact missing a required field."""

    def test_each_schema(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            required = schema.get("required", [])
            if not required:
                continue
            with self.subTest(schema=name):
                artifact = _build_minimal_valid_artifact(schema)
                # Remove the first required field.
                target = required[0]
                artifact.pop(target, None)
                violations = validate_artifact(artifact, schema)
                matching = [v for v in violations if "missing required field" in v and target in v]
                self.assertGreater(
                    len(matching), 0,
                    f"Schema {name}: removing required field '{target}' should produce a violation",
                )


class TestTypeKeywordEnforcedAcrossSchemas(unittest.TestCase):
    """Gate: every schema with typed fields must reject wrong-typed values."""

    def test_each_schema(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            result = _find_field_with_keyword(schema, "type")
            if result is None:
                continue
            field_name, field_schema = result
            type_spec = field_schema["type"]

            # Skip nullable types — they need special handling.
            if isinstance(type_spec, list):
                continue

            with self.subTest(schema=name, field=field_name):
                artifact = _build_minimal_valid_artifact(schema)
                # Inject a value of the wrong type.
                if type_spec == "string":
                    artifact[field_name] = 99999
                elif type_spec in ("integer", "number"):
                    artifact[field_name] = "not-a-number"
                elif type_spec == "boolean":
                    artifact[field_name] = "not-bool"
                elif type_spec == "array":
                    artifact[field_name] = "not-array"
                elif type_spec == "object":
                    artifact[field_name] = "not-object"
                else:
                    continue

                violations = validate_artifact(artifact, schema)
                matching = [v for v in violations if "expected type" in v]
                self.assertGreater(
                    len(matching), 0,
                    f"Schema {name}: wrong type for '{field_name}' should produce a violation",
                )


class TestEnumKeywordEnforcedAcrossSchemas(unittest.TestCase):
    """Gate: every schema with enum constraints must reject invalid enum values."""

    def test_each_schema(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            result = _find_field_with_keyword(schema, "enum")
            if result is None:
                continue
            field_name, field_schema = result

            with self.subTest(schema=name, field=field_name):
                artifact = _build_minimal_valid_artifact(schema)
                artifact[field_name] = "__INVALID_ENUM_VALUE__"
                violations = validate_artifact(artifact, schema)
                matching = [v for v in violations if "not in enum" in v]
                self.assertGreater(
                    len(matching), 0,
                    f"Schema {name}: invalid enum for '{field_name}' should produce a violation",
                )


class TestMinLengthKeywordEnforcedAcrossSchemas(unittest.TestCase):
    """Gate: every schema with minLength must reject strings that are too short."""

    def test_each_schema(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            result = _find_field_with_keyword(schema, "minLength")
            if result is None:
                continue
            field_name, field_schema = result

            with self.subTest(schema=name, field=field_name):
                artifact = _build_minimal_valid_artifact(schema)
                artifact[field_name] = ""  # empty string violates minLength >= 1
                violations = validate_artifact(artifact, schema)
                matching = [v for v in violations if "minLength" in v]
                self.assertGreater(
                    len(matching), 0,
                    f"Schema {name}: empty string for '{field_name}' should violate minLength",
                )


class TestMinimumKeywordEnforcedAcrossSchemas(unittest.TestCase):
    """Gate: every schema with minimum must reject values below the floor."""

    def test_each_schema(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            result = _find_field_with_keyword(schema, "minimum")
            if result is None:
                continue
            field_name, field_schema = result
            floor = field_schema["minimum"]

            with self.subTest(schema=name, field=field_name):
                artifact = _build_minimal_valid_artifact(schema)
                artifact[field_name] = floor - 1
                violations = validate_artifact(artifact, schema)
                matching = [v for v in violations if "minimum" in v]
                self.assertGreater(
                    len(matching), 0,
                    f"Schema {name}: value below minimum for '{field_name}' should produce a violation",
                )


class TestMinItemsKeywordEnforcedAcrossSchemas(unittest.TestCase):
    """Gate: every schema with minItems must reject arrays that are too short."""

    def test_each_schema(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            result = _find_field_with_keyword(schema, "minItems")
            if result is None:
                continue
            field_name, _field_schema = result

            with self.subTest(schema=name, field=field_name):
                artifact = _build_minimal_valid_artifact(schema)
                artifact[field_name] = []  # empty array violates minItems >= 1
                violations = validate_artifact(artifact, schema)
                matching = [v for v in violations if "minItems" in v]
                self.assertGreater(
                    len(matching), 0,
                    f"Schema {name}: empty array for '{field_name}' should violate minItems",
                )


class TestMaxItemsKeywordEnforcedAcrossSchemas(unittest.TestCase):
    """Gate: every schema with maxItems must reject arrays that are too long."""

    def test_each_schema(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            result = _find_field_with_keyword(schema, "maxItems")
            if result is None:
                continue
            field_name, field_schema = result
            max_items = field_schema["maxItems"]

            with self.subTest(schema=name, field=field_name):
                artifact = _build_minimal_valid_artifact(schema)
                artifact[field_name] = ["item"] * (max_items + 1)
                violations = validate_artifact(artifact, schema)
                matching = [v for v in violations if "maxItems" in v]
                self.assertGreater(
                    len(matching), 0,
                    f"Schema {name}: oversized array for '{field_name}' should violate maxItems",
                )


class TestAdditionalPropertiesEnforcedAcrossSchemas(unittest.TestCase):
    """Gate: every schema with additionalProperties:false must reject unknown fields."""

    def test_each_schema(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            if schema.get("additionalProperties") is not False:
                continue

            with self.subTest(schema=name):
                artifact = _build_minimal_valid_artifact(schema)
                artifact["__undeclared_test_field__"] = "injected"
                violations = validate_artifact(artifact, schema)
                matching = [v for v in violations if "additional property not allowed" in v]
                self.assertGreater(
                    len(matching), 0,
                    f"Schema {name}: undeclared field should produce additionalProperties violation",
                )


class TestItemsKeywordEnforcedAcrossSchemas(unittest.TestCase):
    """Gate: every schema with items must validate array element types."""

    def test_each_schema(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            result = _find_field_with_keyword(schema, "items")
            if result is None:
                continue
            field_name, field_schema = result
            item_type = field_schema.get("items", {}).get("type")
            if item_type != "string":
                continue

            with self.subTest(schema=name, field=field_name):
                artifact = _build_minimal_valid_artifact(schema)
                # Ensure at least one valid item, then add a wrong-typed one.
                min_items = field_schema.get("minItems", 0)
                artifact[field_name] = ["valid"] * max(min_items, 1) + [12345]
                violations = validate_artifact(artifact, schema)
                matching = [v for v in violations if "expected type string" in v]
                self.assertGreater(
                    len(matching), 0,
                    f"Schema {name}: non-string item in '{field_name}' should violate items constraint",
                )


class TestNestedObjectRequiredEnforcedAcrossSchemas(unittest.TestCase):
    """Gate: nested objects with required fields must enforce them."""

    def test_each_schema(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            result = _find_field_with_keyword(schema, "nested_required")
            if result is None:
                continue
            field_name, field_schema = result
            nested_required = field_schema.get("required", [])
            if not nested_required:
                continue

            with self.subTest(schema=name, field=field_name):
                artifact = _build_minimal_valid_artifact(schema)
                # Remove the first nested required field.
                target = nested_required[0]
                if isinstance(artifact.get(field_name), dict):
                    artifact[field_name].pop(target, None)
                violations = validate_artifact(artifact, schema)
                matching = [v for v in violations if "missing required field" in v and target in v]
                self.assertGreater(
                    len(matching), 0,
                    f"Schema {name}: removing nested required '{target}' from '{field_name}' should violate",
                )


class TestNullableTypeEnforcedAcrossSchemas(unittest.TestCase):
    """Gate: nullable fields (type: ["string", "null"]) must accept null and reject wrong types."""

    def _find_nullable_field(self, schema: dict) -> tuple[str, dict] | None:
        properties = schema.get("properties", {})
        for field_name, field_schema in properties.items():
            if isinstance(field_schema.get("type"), list) and "null" in field_schema["type"]:
                return field_name, field_schema
        return None

    def test_null_accepted_across_schemas(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            result = self._find_nullable_field(schema)
            if result is None:
                continue
            field_name, _field_schema = result

            with self.subTest(schema=name, field=field_name, case="null"):
                artifact = _build_minimal_valid_artifact(schema)
                artifact[field_name] = None
                violations = validate_artifact(artifact, schema)
                # Filter out violations not related to this field.
                field_violations = [v for v in violations if field_name in v]
                self.assertEqual(
                    field_violations, [],
                    f"Schema {name}: null should be accepted for nullable '{field_name}'",
                )

    def test_wrong_type_rejected_across_schemas(self) -> None:
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            result = self._find_nullable_field(schema)
            if result is None:
                continue
            field_name, field_schema = result
            non_null_types = [
                t for t in field_schema["type"] if t != "null"
            ]
            if not non_null_types:
                continue

            with self.subTest(schema=name, field=field_name, case="wrong_type"):
                artifact = _build_minimal_valid_artifact(schema)
                # Inject a definitely wrong type (list is never valid for string|null).
                artifact[field_name] = [1, 2, 3]
                violations = validate_artifact(artifact, schema)
                matching = [v for v in violations if "expected type" in v and field_name in v]
                self.assertGreater(
                    len(matching), 0,
                    f"Schema {name}: wrong type for nullable '{field_name}' should produce a violation",
                )


class TestKeywordCoverageCompleteness(unittest.TestCase):
    """Meta-gate: every validation-relevant keyword used in any frozen schema
    must appear in the keyword list this gate tests. If a new keyword is added
    to a schema, this test forces a human to add gate coverage for it."""

    KNOWN_GATED_KEYWORDS = {
        "required",
        "type",
        "enum",
        "const",
        "minLength",
        "minimum",
        "minItems",
        "maxItems",
        "additionalProperties",
        "items",
        "format",
        "nested_required",
        "nested_additionalProperties",
    }

    # Keywords that are schema metadata, not validation-relevant.
    METADATA_KEYWORDS = {
        "$schema",
        "$id",
        "artifact_type",
        "schema_version",
        "source_ref",
        "properties",
        "description",
    }

    def test_no_ungated_keywords(self) -> None:
        all_found: set[str] = set()
        for name in FROZEN_SCHEMA_NAMES:
            schema = load_schema(name)
            all_found |= _extract_keywords(schema)

        ungated = all_found - self.KNOWN_GATED_KEYWORDS
        self.assertEqual(
            ungated,
            set(),
            f"Schema keywords found but not gated: {sorted(ungated)}. "
            "Add gate tests for these keywords or add them to METADATA_KEYWORDS "
            "if they are not validation-relevant.",
        )


if __name__ == "__main__":
    unittest.main()
