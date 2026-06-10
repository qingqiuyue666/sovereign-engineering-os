"""Discover local creative software without launching destructive jobs."""

from __future__ import annotations

from pathlib import Path
import os
import platform
import shutil
import sys
from creative.common import SCHEMA_VERSION, sanitize_path
from creative.runners.houdini_local_runner import discover_hython

def _which(name: str) -> str:
    found = shutil.which(name)
    return sanitize_path(found) if found else ""

def _macos_app_path(*patterns: str) -> str:
    applications = Path("/Applications")
    if not applications.exists():
        return ""
    for pattern in patterns:
        matches = sorted(applications.glob(pattern))
        if matches:
            return sanitize_path(matches[0])
    return ""

def _status_for_path(path: str, *, app_requires_launch: bool = False) -> str:
    if not path:
        return "NOT_FOUND"
    return "FOUND_BUT_REQUIRES_USER_LAUNCH" if app_requires_launch else "FOUND_BUT_UNTESTED"

def discover_software() -> dict[str, object]:
    git_path = _which("git")
    ffmpeg_path = _which("ffmpeg")
    blender_path = _which("blender") or _macos_app_path("Blender.app")
    blender_requires_launch = bool(blender_path and not _which("blender"))
    houdini = discover_hython()
    houdini_path = houdini.path
    zbrush_path = _macos_app_path("ZBrush*.app", "Maxon ZBrush*.app")
    after_effects_path = _macos_app_path("Adobe After Effects */Adobe After Effects *.app")
    davinci_path = _macos_app_path("DaVinci Resolve.app", "DaVinci Resolve/DaVinci Resolve.app")
    unreal_path = _macos_app_path("Epic Games/UE_*/Engine/Binaries/Mac/UnrealEditor.app")
    entries = {
        "python": {"status": "FOUND_AND_SMOKE_PASSED", "version": sys.version.split()[0], "path": sanitize_path(sys.executable)},
        "macos": {"status": "FOUND_AND_SMOKE_PASSED" if platform.system() == "Darwin" else "FOUND_BUT_UNTESTED", "version": platform.platform()},
        "apple_silicon": {"status": "FOUND_AND_SMOKE_PASSED" if platform.machine() in {"arm64", "aarch64"} else "NOT_FOUND"},
        "git": {"status": _status_for_path(git_path), "path": git_path},
        "ffmpeg": {"status": _status_for_path(ffmpeg_path), "path": ffmpeg_path},
        "comfyui": {"status": "CONFIG_REQUIRED" if not os.environ.get("COMFYUI_PATH") else "FOUND_BUT_REQUIRES_USER_LAUNCH", "path": sanitize_path(os.environ.get("COMFYUI_PATH", ""))},
        "blender": {"status": _status_for_path(blender_path, app_requires_launch=blender_requires_launch), "path": blender_path},
        "houdini": {"status": houdini.status, "path": sanitize_path(houdini_path)},
        "zbrush": {"status": _status_for_path(zbrush_path, app_requires_launch=True), "path": zbrush_path},
        "unreal": {"status": _status_for_path(unreal_path, app_requires_launch=True) if unreal_path else "CONFIG_REQUIRED", "path": unreal_path},
        "davinci": {"status": _status_for_path(davinci_path, app_requires_launch=True) if davinci_path else "CONFIG_REQUIRED", "path": davinci_path},
        "after_effects": {"status": _status_for_path(after_effects_path, app_requires_launch=True) if after_effects_path else "CONFIG_REQUIRED", "path": after_effects_path},
    }
    return {"schema_version": SCHEMA_VERSION, "software": entries, "destructive_actions_performed": False}
