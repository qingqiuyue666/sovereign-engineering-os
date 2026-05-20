"""Mocked fail-closed tests for the DaVinci Resolve HFX handoff socket."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
import tempfile
import unittest

from kernel.vfx.render_artifact_ledger import ExrFileChecksum, RenderArtifactRecord
from workbenches.interfaces import davinci_handoff_socket as davinci


class _ResolveModule:
    def __init__(self, resolve: Any) -> None:
        self._resolve = resolve

    def scriptapp(self, app_name: str) -> Any:
        if app_name != "Resolve":
            raise AssertionError(f"unexpected Resolve app name: {app_name}")
        return self._resolve


class _ResolveModuleConnectionRefused:
    def scriptapp(self, app_name: str) -> Any:
        if app_name != "Resolve":
            raise AssertionError(f"unexpected Resolve app name: {app_name}")
        return None


class _ProjectManager:
    def __init__(self, project: Any) -> None:
        self._project = project

    def GetCurrentProject(self) -> Any:
        return self._project


class _Resolve:
    def __init__(self, project: Any) -> None:
        self._project = project

    def GetProjectManager(self) -> _ProjectManager:
        return _ProjectManager(self._project)


class _Project:
    def __init__(self, media_pool: Any) -> None:
        self._media_pool = media_pool

    def GetName(self) -> str:
        return "Unit Test Project"

    def GetMediaPool(self) -> Any:
        return self._media_pool


class _Folder:
    def __init__(self, name: str, children: tuple[_Folder, ...] = ()) -> None:
        self._name = name
        self._children = children

    def GetName(self) -> str:
        return self._name

    def GetSubFolderList(self) -> tuple[_Folder, ...]:
        return self._children


class _MediaPoolCannotCreateBin:
    def __init__(self) -> None:
        self.root_folder = _Folder("Root")

    def GetRootFolder(self) -> _Folder:
        return self.root_folder

    def AddSubFolder(self, _root_folder: _Folder, _bin_name: str) -> None:
        return None


def _record_for_directory(exr_directory: Path) -> RenderArtifactRecord:
    return RenderArtifactRecord(
        ledger_version="hfx-render-artifact-ledger-v1",
        record_id="record-1",
        created_at="2026-05-20T00:00:00+00:00",
        exr_directory=exr_directory,
        sequence_glob="shot.*.exr",
        frame_pattern="shot.%04d.exr",
        directory_sha256="abc123",
        files=(
            ExrFileChecksum(
                relative_path="shot.0001.exr",
                frame_number=1,
                size_bytes=40,
                sha256="sha256-1",
            ),
            ExrFileChecksum(
                relative_path="shot.0002.exr",
                frame_number=2,
                size_bytes=40,
                sha256="sha256-2",
            ),
        ),
        metadata={"stage": "unit-test"},
        ledger_path=None,
    )


class DavinciHandoffSocketTests(unittest.TestCase):
    def test_resolve_connection_refusal_returns_handoff_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            record = _record_for_directory(Path(temp_dir_name))
            with (
                patch.object(davinci, "load_latest_render_artifact", return_value=record),
                patch.object(
                    davinci,
                    "hash_exr_directory",
                    return_value=SimpleNamespace(directory_sha256=record.directory_sha256),
                ),
                patch.object(
                    davinci,
                    "_load_resolve_script_module",
                    return_value=_ResolveModuleConnectionRefused(),
                ),
            ):
                with self.assertRaisesRegex(
                    davinci.DavinciHandoffError,
                    "scripting app is unavailable",
                ):
                    davinci.import_latest_hfx_render(davinci.DavinciHandoffRequest())

    def test_missing_media_pool_bin_creation_failure_returns_handoff_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            record = _record_for_directory(Path(temp_dir_name))
            project = _Project(_MediaPoolCannotCreateBin())
            resolve_module = _ResolveModule(_Resolve(project))
            with (
                patch.object(davinci, "load_latest_render_artifact", return_value=record),
                patch.object(
                    davinci,
                    "hash_exr_directory",
                    return_value=SimpleNamespace(directory_sha256=record.directory_sha256),
                ),
                patch.object(davinci, "_load_resolve_script_module", return_value=resolve_module),
            ):
                with self.assertRaisesRegex(
                    davinci.DavinciHandoffError,
                    "could not create Media Pool bin",
                ):
                    davinci.import_latest_hfx_render(
                        davinci.DavinciHandoffRequest(media_pool_bin_name="Missing Bin")
                    )

    def test_missing_media_pool_returns_handoff_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            record = _record_for_directory(Path(temp_dir_name))
            project = _Project(media_pool=None)
            resolve_module = _ResolveModule(_Resolve(project))
            with (
                patch.object(davinci, "load_latest_render_artifact", return_value=record),
                patch.object(
                    davinci,
                    "hash_exr_directory",
                    return_value=SimpleNamespace(directory_sha256=record.directory_sha256),
                ),
                patch.object(davinci, "_load_resolve_script_module", return_value=resolve_module),
            ):
                with self.assertRaisesRegex(
                    davinci.DavinciHandoffError,
                    "has no Media Pool",
                ):
                    davinci.import_latest_hfx_render(davinci.DavinciHandoffRequest())


if __name__ == "__main__":
    unittest.main()
