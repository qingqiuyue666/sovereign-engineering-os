"""DaVinci Resolve handoff bridge for the latest hashed HFX EXR sequence."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
import argparse
import importlib
import json
import os
import sys

_REPO_ROOT = Path(__file__).resolve().parents[2]
if _REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, _REPO_ROOT.as_posix())

from kernel.vfx.render_artifact_ledger import (  # noqa: E402
    ArtifactLedgerError,
    RenderArtifactRecord,
    hash_exr_directory,
    load_latest_render_artifact,
)

__all__ = [
    "DavinciHandoffError",
    "DavinciHandoffRequest",
    "DavinciHandoffResult",
    "import_latest_hfx_render",
]

DEFAULT_BIN_NAME = "HFX Render Automation"


class ResolveScriptModule(Protocol):
    def scriptapp(self, app_name: str) -> Any:
        """Return a Resolve scripting application handle."""


class DavinciHandoffError(RuntimeError):
    """Raised when Resolve cannot import the latest HFX EXR sequence."""


@dataclass(frozen=True, slots=True)
class DavinciHandoffRequest:
    """Resolve import request for the latest private HFX ledger record."""

    media_pool_bin_name: str = DEFAULT_BIN_NAME
    ledger_root: Path | str | None = None
    project_name: str | None = None

    def validated(self) -> DavinciHandoffRequest:
        if not self.media_pool_bin_name.strip():
            raise DavinciHandoffError("media_pool_bin_name is required")
        if len(self.media_pool_bin_name) > 128:
            raise DavinciHandoffError("media_pool_bin_name is too long")
        if self.project_name is not None and not self.project_name.strip():
            raise DavinciHandoffError("project_name may not be blank")
        return self


@dataclass(frozen=True, slots=True)
class DavinciHandoffResult:
    """Result payload returned after importing the EXR sequence into Resolve."""

    record_id: str
    directory_sha256: str
    project_name: str
    media_pool_bin_name: str
    sequence_path: Path
    imported_clip_count: int
    imported_clip_names: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "directory_sha256": self.directory_sha256,
            "imported_clip_count": self.imported_clip_count,
            "imported_clip_names": list(self.imported_clip_names),
            "media_pool_bin_name": self.media_pool_bin_name,
            "project_name": self.project_name,
            "record_id": self.record_id,
            "sequence_path": self.sequence_path.as_posix(),
        }


def import_latest_hfx_render(
    request: DavinciHandoffRequest | None = None,
) -> DavinciHandoffResult:
    """Locate the latest ledgered EXR sequence and import it into a Resolve bin."""

    admitted = (request or DavinciHandoffRequest()).validated()
    record = load_latest_render_artifact(ledger_root=admitted.ledger_root)
    _verify_record_still_matches_disk(record)
    sequence_path = _resolve_sequence_path(record)

    resolve_module = _load_resolve_script_module()
    resolve = resolve_module.scriptapp("Resolve")
    if resolve is None:
        raise DavinciHandoffError("DaVinci Resolve scripting app is unavailable")

    project = _current_project(resolve)
    project_name = _resolve_project_name(project)
    if admitted.project_name is not None and project_name != admitted.project_name:
        raise DavinciHandoffError(
            f"current Resolve project is {project_name!r}, expected {admitted.project_name!r}"
        )

    media_pool = project.GetMediaPool()
    if media_pool is None:
        raise DavinciHandoffError("current Resolve project has no Media Pool")
    target_folder = _find_or_create_bin(media_pool, admitted.media_pool_bin_name)
    if not media_pool.SetCurrentFolder(target_folder):
        raise DavinciHandoffError(f"could not activate Media Pool bin: {admitted.media_pool_bin_name}")

    clip_info = {
        "EndIndex": int(record.last_frame),
        "FilePath": sequence_path.as_posix(),
        "StartIndex": int(record.first_frame),
    }
    imported_items = media_pool.ImportMedia([clip_info])
    if not imported_items:
        imported_items = media_pool.ImportMedia([sequence_path.as_posix()])
    if not imported_items:
        raise DavinciHandoffError(f"Resolve imported no clips from {sequence_path}")

    clip_names = tuple(_clip_name(item) for item in imported_items)
    return DavinciHandoffResult(
        record_id=record.record_id,
        directory_sha256=record.directory_sha256,
        project_name=project_name,
        media_pool_bin_name=admitted.media_pool_bin_name,
        sequence_path=sequence_path,
        imported_clip_count=len(imported_items),
        imported_clip_names=clip_names,
    )


def _verify_record_still_matches_disk(record: RenderArtifactRecord) -> None:
    if record.first_frame is None or record.last_frame is None:
        raise DavinciHandoffError("ledger record has no frame-numbered EXR sequence")
    if record.first_frame != 1:
        raise DavinciHandoffError("ledger record is not a 0001-to-N EXR sequence")
    expected_count = record.last_frame - record.first_frame + 1
    if record.frame_count != expected_count:
        raise DavinciHandoffError("ledger record is not a contiguous 0001-to-N EXR sequence")
    try:
        current_hash = hash_exr_directory(
            record.exr_directory,
            sequence_glob=record.sequence_glob,
        )
    except ArtifactLedgerError as exc:
        raise DavinciHandoffError(str(exc)) from exc
    if current_hash.directory_sha256 != record.directory_sha256:
        raise DavinciHandoffError("EXR directory hash no longer matches latest ledger record")


def _resolve_sequence_path(record: RenderArtifactRecord) -> Path:
    if record.frame_pattern:
        return record.exr_directory / record.frame_pattern
    first_file = min(
        record.files,
        key=lambda checksum: checksum.frame_number if checksum.frame_number is not None else -1,
    )
    if first_file.frame_number is None:
        raise DavinciHandoffError("could not infer Resolve sequence pattern from ledger record")
    frame_token = f"{first_file.frame_number:04d}"
    return record.exr_directory / first_file.relative_path.replace(frame_token, "%04d")


def _load_resolve_script_module() -> ResolveScriptModule:
    try:
        return importlib.import_module("DaVinciResolveScript")
    except ImportError:
        pass

    for module_path in _resolve_module_search_paths():
        if module_path.exists() and module_path.as_posix() not in sys.path:
            sys.path.append(module_path.as_posix())
        try:
            return importlib.import_module("DaVinciResolveScript")
        except ImportError:
            continue
    raise DavinciHandoffError("DaVinciResolveScript module could not be imported")


def _resolve_module_search_paths() -> tuple[Path, ...]:
    paths: list[Path] = []
    api_root = os.environ.get("RESOLVE_SCRIPT_API")
    if api_root:
        root = Path(api_root).expanduser()
        paths.extend([root, root / "Modules"])
    if sys.platform == "darwin":
        paths.append(
            Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")
        )
    elif os.name == "nt":
        program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        paths.append(
            Path(program_data)
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Developer"
            / "Scripting"
            / "Modules"
        )
    else:
        paths.append(
            Path("/opt/resolve/Developer/Scripting/Modules")
        )
    return tuple(paths)


def _current_project(resolve: Any) -> Any:
    project_manager = resolve.GetProjectManager()
    if project_manager is None:
        raise DavinciHandoffError("Resolve project manager is unavailable")
    project = project_manager.GetCurrentProject()
    if project is None:
        raise DavinciHandoffError("no current Resolve project is open")
    return project


def _resolve_project_name(project: Any) -> str:
    name = project.GetName()
    if not isinstance(name, str) or not name:
        raise DavinciHandoffError("current Resolve project has no name")
    return name


def _find_or_create_bin(media_pool: Any, bin_name: str) -> Any:
    root_folder = media_pool.GetRootFolder()
    if root_folder is None:
        raise DavinciHandoffError("Resolve Media Pool root folder is unavailable")
    existing = _find_folder_by_name(root_folder, bin_name)
    if existing is not None:
        return existing
    created = media_pool.AddSubFolder(root_folder, bin_name)
    if created is None:
        raise DavinciHandoffError(f"could not create Media Pool bin: {bin_name}")
    return created


def _find_folder_by_name(folder: Any, bin_name: str) -> Any | None:
    try:
        if folder.GetName() == bin_name:
            return folder
    except AttributeError:
        return None
    for child in folder.GetSubFolderList() or []:
        found = _find_folder_by_name(child, bin_name)
        if found is not None:
            return found
    return None


def _clip_name(media_pool_item: Any) -> str:
    for getter in (
        lambda item: item.GetName(),
        lambda item: item.GetClipProperty("Clip Name"),
    ):
        try:
            value = getter(media_pool_item)
        except Exception:
            continue
        if isinstance(value, str) and value:
            return value
    return "<unnamed>"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import latest ledgered HFX EXR sequence into Resolve.")
    parser.add_argument(
        "--bin-name",
        default=os.environ.get("SEOS_DAVINCI_MEDIA_POOL_BIN", DEFAULT_BIN_NAME),
    )
    parser.add_argument("--ledger-root", default=None)
    parser.add_argument("--project-name", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = import_latest_hfx_render(
            DavinciHandoffRequest(
                media_pool_bin_name=args.bin_name,
                ledger_root=args.ledger_root,
                project_name=args.project_name,
            )
        )
    except (ArtifactLedgerError, DavinciHandoffError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result.as_dict(), ensure_ascii=True, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
