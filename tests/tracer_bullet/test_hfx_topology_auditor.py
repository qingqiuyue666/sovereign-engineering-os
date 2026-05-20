"""Tracer bullet tests for the fail-closed HFX topology auditor.

These tests run in plain CPython. They replace Houdini's ``hou`` module with a
small typed fake and patch ``subprocess.run`` so CI cannot accidentally launch a
GUI tool or a real hython process.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
import io
import json
import sys
import tempfile
import unittest

from kernel.vfx import hfx_topology_auditor as auditor


@dataclass(frozen=True, slots=True)
class _FakeCategory:
    category_name: str

    def name(self) -> str:
        return self.category_name


@dataclass(frozen=True, slots=True)
class _FakeNodeType:
    type_name: str
    category_name: str

    def name(self) -> str:
        return self.type_name

    def category(self) -> _FakeCategory:
        return _FakeCategory(self.category_name)


@dataclass(frozen=True, slots=True)
class _FakeParm:
    value: str

    def unexpandedString(self) -> str:
        return self.value

    def evalAsString(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class _FakeGeometry:
    point_count: int
    primitive_count: int

    def intrinsicValue(self, name: str) -> int:
        if name == "pointcount":
            return self.point_count
        if name == "primitivecount":
            return self.primitive_count
        raise KeyError(name)


class _FakeNode:
    def __init__(
        self,
        *,
        path: str,
        type_name: str,
        category_name: str,
        children: Sequence[_FakeNode] = (),
        parameters: Mapping[str, str] | None = None,
        geometry: _FakeGeometry | None = None,
        display_flag: bool = False,
        render_flag: bool = False,
        bypassed: bool = False,
    ) -> None:
        self._path = path
        self._type_name = type_name
        self._category_name = category_name
        self._children = tuple(children)
        self._parameters = dict(parameters or {})
        self._geometry = geometry
        self._display_flag = display_flag
        self._render_flag = render_flag
        self._bypassed = bypassed

    def path(self) -> str:
        return self._path

    def name(self) -> str:
        return self._path.rsplit("/", 1)[-1] or "/"

    def type(self) -> _FakeNodeType:
        return _FakeNodeType(self._type_name, self._category_name)

    def allSubChildren(self) -> tuple[_FakeNode, ...]:
        descendants: list[_FakeNode] = []
        for child in self._children:
            descendants.append(child)
            descendants.extend(child.allSubChildren())
        return tuple(descendants)

    def parm(self, name: str) -> _FakeParm | None:
        value = self._parameters.get(name)
        if value is None:
            return None
        return _FakeParm(value)

    def geometry(self) -> _FakeGeometry:
        if self._geometry is None:
            raise RuntimeError("node has no cookable geometry")
        return self._geometry

    def isDisplayFlagSet(self) -> bool:
        return self._display_flag

    def isRenderFlagSet(self) -> bool:
        return self._render_flag

    def isBypassed(self) -> bool:
        return self._bypassed

    def render(self, *_args: object, **_kwargs: object) -> None:
        return None


class _FakeHipFile:
    def __init__(self) -> None:
        self.loaded_paths: list[str] = []

    def load(self, path: str, *, suppress_save_prompt: bool) -> None:
        if not suppress_save_prompt:
            raise AssertionError("auditor must suppress Houdini save prompts")
        self.loaded_paths.append(path)


def _fake_hou_module(root: _FakeNode) -> ModuleType:
    fake_hou = ModuleType("hou")
    fake_hip_file = _FakeHipFile()
    fake_hou.hipFile = fake_hip_file  # type: ignore[attr-defined]
    fake_hou.node = lambda path: root if path == "/" else None  # type: ignore[attr-defined]
    return fake_hou


def _valid_rop_node() -> _FakeNode:
    return _FakeNode(
        path="/out/hfx_final_render",
        type_name="opengl",
        category_name="Driver",
        parameters={"picture": "$HIP/render/hfx.$F4.exr"},
    )


def _geometry_node(*, point_count: int, primitive_count: int = 1) -> _FakeNode:
    return _FakeNode(
        path="/obj/hfx_asset/OUT_render",
        type_name="null",
        category_name="Sop",
        geometry=_FakeGeometry(point_count=point_count, primitive_count=primitive_count),
        display_flag=True,
        render_flag=True,
    )


def _hip_file(temp_dir: Path) -> Path:
    hip_file = temp_dir / "asset.hip"
    hip_file.write_text("fake hip placeholder", encoding="utf-8")
    return hip_file


class HfxTopologyAuditorTracerBulletTests(unittest.TestCase):
    def test_placeholder_guide_under_point_threshold_exits_2_without_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            hip_file = _hip_file(temp_dir)
            root = _FakeNode(
                path="/",
                type_name="root",
                category_name="Root",
                children=(_valid_rop_node(), _geometry_node(point_count=999)),
            )
            stdout = io.StringIO()

            with (
                patch.dict(sys.modules, {"hou": _fake_hou_module(root)}),
                patch("subprocess.run") as subprocess_run,
                redirect_stdout(stdout),
            ):
                exit_code = auditor.main(["--hip-file", hip_file.as_posix()])

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 2)
            self.assertEqual(payload["status"], "FAIL")
            self.assertEqual(payload["classification"], "Placeholder Guide")
            self.assertEqual(payload["effective_point_count"], 999)
            self.assertIn(
                "geometry_point_count_below_real_asset_threshold",
                payload["failures"],
            )
            subprocess_run.assert_not_called()

    def test_missing_valid_rop_fails_closed_even_with_real_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            hip_file = _hip_file(temp_dir)
            non_render_output = _FakeNode(
                path="/out/hfx_notes",
                type_name="geometry",
                category_name="Driver",
                parameters={"sopoutput": "$HIP/cache.bgeo.sc"},
            )
            root = _FakeNode(
                path="/",
                type_name="root",
                category_name="Root",
                children=(non_render_output, _geometry_node(point_count=4_096)),
            )

            with patch.dict(sys.modules, {"hou": _fake_hou_module(root)}):
                report = auditor.audit_hip_file(hip_file)

            self.assertFalse(report.passed)
            self.assertEqual(report.classification, "Placeholder Guide")
            self.assertEqual(report.effective_point_count, 4_096)
            self.assertIn("no_valid_rop_or_out_render_node", report.failures)

    def test_real_asset_with_valid_render_node_passes_without_houdini_installed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            hip_file = _hip_file(temp_dir)
            root = _FakeNode(
                path="/",
                type_name="root",
                category_name="Root",
                children=(_valid_rop_node(), _geometry_node(point_count=1_500)),
            )

            with patch.dict(sys.modules, {"hou": _fake_hou_module(root)}):
                report = auditor.audit_hip_file(hip_file)

            self.assertTrue(report.passed)
            self.assertEqual(report.classification, "Real Asset")
            self.assertEqual(report.effective_point_count, 1_500)
            self.assertIsNotNone(report.selected_render_node)
            assert report.selected_render_node is not None
            self.assertEqual(report.selected_render_node.path, "/out/hfx_final_render")


if __name__ == "__main__":
    unittest.main()
