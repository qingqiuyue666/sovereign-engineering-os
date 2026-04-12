"""
Schema validation depth tests: proving each keyword enforcement path.

Constitutional anchors:
- v11 Section 22.7 (context completeness — schema enforcement is load-bearing)
- v11 Section 22.10 (invariant enforcement binding — validator must be tested)
- Foundation Section 3.4 (runtime enforcement: ingress + pre-persist)

These tests exercise the validator (kernel/schemas/validator.py) against
synthetic schemas that isolate each JSON Schema keyword the validator
claims to enforce. Each test proves a single enforcement path: wrong input
triggers a violation, correct input does not.

Honest posture:
- format is checked for presence only (not correctness). This is the
  documented limitation from the validator docstring.
- const is tested even though no frozen schema currently uses it, because
  the validator claims to enforce it and a regression would be silent.
"""

from __future__ import annotations

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from kernel.schemas.validator import (
    SchemaValidationError,
    validate_artifact,
    validate_artifact_strict,
)


class TestRequiredFieldEnforcement(unittest.TestCase):
    """Prove: missing required fields produce violations."""

    SCHEMA = {
        "type": "object",
        "required": ["id", "name"],
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
        },
    }

    def test_missing_one_required(self) -> None:
        violations = validate_artifact({"id": "a"}, self.SCHEMA)
        self.assertEqual(len(violations), 1)
        self.assertIn("name", violations[0])
        self.assertIn("missing required field", violations[0])

    def test_missing_all_required(self) -> None:
        violations = validate_artifact({}, self.SCHEMA)
        self.assertEqual(len(violations), 2)

    def test_all_present_passes(self) -> None:
        violations = validate_artifact({"id": "a", "name": "b"}, self.SCHEMA)
        self.assertEqual(violations, [])


class TestTypeEnforcement(unittest.TestCase):
    """Prove: wrong types for string/integer/boolean/array/object produce violations."""

    def _schema_for_type(self, type_name: str) -> dict:
        return {
            "type": "object",
            "required": ["field"],
            "properties": {"field": {"type": type_name}},
        }

    def test_string_type_rejects_integer(self) -> None:
        violations = validate_artifact({"field": 42}, self._schema_for_type("string"))
        self.assertEqual(len(violations), 1)
        self.assertIn("expected type string", violations[0])

    def test_integer_type_rejects_string(self) -> None:
        violations = validate_artifact({"field": "nope"}, self._schema_for_type("integer"))
        self.assertEqual(len(violations), 1)
        self.assertIn("expected type integer", violations[0])

    def test_boolean_type_rejects_string(self) -> None:
        violations = validate_artifact({"field": "true"}, self._schema_for_type("boolean"))
        self.assertEqual(len(violations), 1)
        self.assertIn("expected type boolean", violations[0])

    def test_array_type_rejects_string(self) -> None:
        violations = validate_artifact({"field": "not-array"}, self._schema_for_type("array"))
        self.assertEqual(len(violations), 1)
        self.assertIn("expected type array", violations[0])

    def test_object_type_rejects_string(self) -> None:
        violations = validate_artifact({"field": "not-obj"}, self._schema_for_type("object"))
        self.assertEqual(len(violations), 1)
        self.assertIn("expected type object", violations[0])

    def test_correct_types_pass(self) -> None:
        self.assertEqual(validate_artifact({"field": "ok"}, self._schema_for_type("string")), [])
        self.assertEqual(validate_artifact({"field": 1}, self._schema_for_type("integer")), [])
        self.assertEqual(validate_artifact({"field": True}, self._schema_for_type("boolean")), [])
        self.assertEqual(validate_artifact({"field": []}, self._schema_for_type("array")), [])
        self.assertEqual(validate_artifact({"field": {}}, self._schema_for_type("object")), [])


class TestEnumEnforcement(unittest.TestCase):
    """Prove: invalid enum values produce violations."""

    SCHEMA = {
        "type": "object",
        "required": ["state"],
        "properties": {
            "state": {"type": "string", "enum": ["pending", "sealed", "abandoned"]},
        },
    }

    def test_invalid_enum_value(self) -> None:
        violations = validate_artifact({"state": "invalid"}, self.SCHEMA)
        self.assertEqual(len(violations), 1)
        self.assertIn("not in enum", violations[0])

    def test_valid_enum_value(self) -> None:
        for v in ("pending", "sealed", "abandoned"):
            violations = validate_artifact({"state": v}, self.SCHEMA)
            self.assertEqual(violations, [], f"valid enum value {v!r} should pass")


class TestConstEnforcement(unittest.TestCase):
    """Prove: const violations are caught (validator supports const even if no
    frozen schema currently uses it; a regression here would be silent)."""

    SCHEMA = {
        "type": "object",
        "required": ["kind"],
        "properties": {
            "kind": {"type": "string", "const": "AuditRecord"},
        },
    }

    def test_wrong_const_value(self) -> None:
        violations = validate_artifact({"kind": "wrong"}, self.SCHEMA)
        self.assertEqual(len(violations), 1)
        self.assertIn("does not match const", violations[0])

    def test_correct_const_value(self) -> None:
        violations = validate_artifact({"kind": "AuditRecord"}, self.SCHEMA)
        self.assertEqual(violations, [])


class TestMinLengthEnforcement(unittest.TestCase):
    """Prove: strings shorter than minLength produce violations."""

    SCHEMA = {
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"type": "string", "minLength": 1},
        },
    }

    def test_empty_string_violates(self) -> None:
        violations = validate_artifact({"id": ""}, self.SCHEMA)
        self.assertEqual(len(violations), 1)
        self.assertIn("minLength", violations[0])

    def test_nonempty_string_passes(self) -> None:
        violations = validate_artifact({"id": "x"}, self.SCHEMA)
        self.assertEqual(violations, [])


class TestMinimumEnforcement(unittest.TestCase):
    """Prove: integers below minimum produce violations."""

    SCHEMA = {
        "type": "object",
        "required": ["count"],
        "properties": {
            "count": {"type": "integer", "minimum": 0},
        },
    }

    def test_negative_violates(self) -> None:
        violations = validate_artifact({"count": -1}, self.SCHEMA)
        self.assertEqual(len(violations), 1)
        self.assertIn("minimum", violations[0])

    def test_zero_passes(self) -> None:
        violations = validate_artifact({"count": 0}, self.SCHEMA)
        self.assertEqual(violations, [])

    def test_positive_passes(self) -> None:
        violations = validate_artifact({"count": 42}, self.SCHEMA)
        self.assertEqual(violations, [])


class TestMinItemsEnforcement(unittest.TestCase):
    """Prove: arrays shorter than minItems produce violations."""

    SCHEMA = {
        "type": "object",
        "required": ["files"],
        "properties": {
            "files": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        },
    }

    def test_empty_array_violates(self) -> None:
        violations = validate_artifact({"files": []}, self.SCHEMA)
        self.assertEqual(len(violations), 1)
        self.assertIn("minItems", violations[0])

    def test_nonempty_array_passes(self) -> None:
        violations = validate_artifact({"files": ["a.py"]}, self.SCHEMA)
        self.assertEqual(violations, [])


class TestMaxItemsEnforcement(unittest.TestCase):
    """Prove: arrays longer than maxItems produce violations."""

    SCHEMA = {
        "type": "object",
        "required": ["files"],
        "properties": {
            "files": {"type": "array", "items": {"type": "string"}, "maxItems": 1},
        },
    }

    def test_two_items_violates(self) -> None:
        violations = validate_artifact({"files": ["a.py", "b.py"]}, self.SCHEMA)
        self.assertEqual(len(violations), 1)
        self.assertIn("maxItems", violations[0])

    def test_one_item_passes(self) -> None:
        violations = validate_artifact({"files": ["a.py"]}, self.SCHEMA)
        self.assertEqual(violations, [])


class TestAdditionalPropertiesEnforcement(unittest.TestCase):
    """Prove: extra fields rejected when additionalProperties is false."""

    SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "required": ["id"],
        "properties": {
            "id": {"type": "string"},
        },
    }

    def test_extra_field_rejected(self) -> None:
        violations = validate_artifact({"id": "a", "extra": "bad"}, self.SCHEMA)
        self.assertEqual(len(violations), 1)
        self.assertIn("additional property not allowed", violations[0])
        self.assertIn("extra", violations[0])

    def test_no_extra_passes(self) -> None:
        violations = validate_artifact({"id": "a"}, self.SCHEMA)
        self.assertEqual(violations, [])


class TestArrayItemValidation(unittest.TestCase):
    """Prove: array items are validated against item schema."""

    SCHEMA = {
        "type": "object",
        "required": ["tags"],
        "properties": {
            "tags": {"type": "array", "items": {"type": "string"}},
        },
    }

    def test_non_string_item_violates(self) -> None:
        violations = validate_artifact({"tags": ["ok", 42, "fine"]}, self.SCHEMA)
        self.assertEqual(len(violations), 1)
        self.assertIn("tags[1]", violations[0])
        self.assertIn("expected type string", violations[0])

    def test_all_string_items_pass(self) -> None:
        violations = validate_artifact({"tags": ["a", "b"]}, self.SCHEMA)
        self.assertEqual(violations, [])


class TestNestedObjectEnforcement(unittest.TestCase):
    """Prove: nested object required/properties/additionalProperties are checked."""

    SCHEMA = {
        "type": "object",
        "required": ["meta"],
        "properties": {
            "meta": {
                "type": "object",
                "required": ["renderer_id", "version"],
                "properties": {
                    "renderer_id": {"type": "string"},
                    "version": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    }

    def test_missing_nested_required(self) -> None:
        violations = validate_artifact({"meta": {"renderer_id": "r1"}}, self.SCHEMA)
        self.assertEqual(len(violations), 1)
        self.assertIn("version", violations[0])

    def test_nested_additional_property_rejected(self) -> None:
        violations = validate_artifact(
            {"meta": {"renderer_id": "r1", "version": "1", "extra": "x"}},
            self.SCHEMA,
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("additional property not allowed", violations[0])

    def test_nested_wrong_type(self) -> None:
        violations = validate_artifact(
            {"meta": {"renderer_id": 42, "version": "1"}},
            self.SCHEMA,
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("expected type string", violations[0])

    def test_valid_nested_passes(self) -> None:
        violations = validate_artifact(
            {"meta": {"renderer_id": "r1", "version": "1"}},
            self.SCHEMA,
        )
        self.assertEqual(violations, [])


class TestNullableTypeEnforcement(unittest.TestCase):
    """Prove: nullable union types (["string", "null"]) accept null, reject wrong types."""

    SCHEMA = {
        "type": "object",
        "required": ["reason"],
        "properties": {
            "reason": {"type": ["string", "null"]},
        },
    }

    def test_null_accepted(self) -> None:
        violations = validate_artifact({"reason": None}, self.SCHEMA)
        self.assertEqual(violations, [])

    def test_string_accepted(self) -> None:
        violations = validate_artifact({"reason": "budget exceeded"}, self.SCHEMA)
        self.assertEqual(violations, [])

    def test_integer_rejected(self) -> None:
        violations = validate_artifact({"reason": 42}, self.SCHEMA)
        self.assertEqual(len(violations), 1)
        self.assertIn("expected type", violations[0])


class TestValidateArtifactStrictRaises(unittest.TestCase):
    """Prove: validate_artifact_strict raises SchemaValidationError on violations."""

    SCHEMA = {
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"type": "string", "minLength": 1},
        },
    }

    def test_raises_on_missing_required(self) -> None:
        with self.assertRaises(SchemaValidationError) as ctx:
            validate_artifact_strict({}, self.SCHEMA, artifact_type_label="TestArtifact")
        self.assertEqual(ctx.exception.artifact_type, "TestArtifact")
        self.assertGreater(len(ctx.exception.violations), 0)

    def test_raises_on_minlength_violation(self) -> None:
        with self.assertRaises(SchemaValidationError):
            validate_artifact_strict({"id": ""}, self.SCHEMA)

    def test_no_raise_on_valid(self) -> None:
        validate_artifact_strict({"id": "ok"}, self.SCHEMA)


class TestMultipleViolationsAggregated(unittest.TestCase):
    """Prove: the validator collects ALL violations, not just the first."""

    SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "required": ["a", "b", "c"],
        "properties": {
            "a": {"type": "string", "minLength": 1},
            "b": {"type": "integer", "minimum": 0},
            "c": {"type": "string", "enum": ["x", "y"]},
        },
    }

    def test_all_violations_collected(self) -> None:
        # Missing 'a', wrong type for 'b', invalid enum for 'c', extra field 'd'.
        violations = validate_artifact(
            {"b": "wrong", "c": "invalid", "d": "extra"}, self.SCHEMA
        )
        # Expected: missing 'a', wrong type 'b', invalid enum 'c', additional 'd'.
        self.assertGreaterEqual(len(violations), 4)


if __name__ == "__main__":
    unittest.main()
