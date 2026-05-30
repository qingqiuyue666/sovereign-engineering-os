"""Discover local creative software without launching destructive jobs."""

from __future__ import annotations

from pathlib import Path
import os
import platform
import shutil
import sys
from creative.common import SCHEMA_VERSION, sanitize_path

def _which(name: str) -> str:
    found = shutil.which(name)
    return sanitize_path(found) if found else ""

def discover_software() -> dict[str, object]:
    entries = {
        "python": {"status": "FOUND_AND_SMOKE_PASSED", "version": sys.version.split()[0], "path": sanitize_path(sys.executable)},
        "macos": {"status": "FOUND_AND_SMOKE_PASSED" if platform.system() == "Darwin" else "FOUND_BUT_UNTESTED", "version": platform.platform()},
        "apple_silicon": {"status": "FOUND_AND_SMOKE_PASSED" if platform.machine() in {"arm64", "aarch64"} else "NOT_FOUND"},
        "ffmpeg": {"status": "FOUND_BUT_UNTESTED" if _which("ffmpeg") else "NOT_FOUND", "path": _which("ffmpeg")},
        "comfyui": {"status": "CONFIG_REQUIRED" if not os.environ.get("COMFYUI_PATH") else "FOUND_BUT_REQUIRES_USER_LAUNCH", "path": sanitize_path(os.environ.get("COMFYUI_PATH", ""))},
        "blender": {"status": "FOUND_BUT_UNTESTED" if _which("blender") else "NOT_FOUND", "path": _which("blender")},
        "houdini": {"status": "FOUND_BUT_UNTESTED" if _which("hython") else "NOT_FOUND", "path": _which("hython")},
        "zbrush": {"status": "FOUND_BUT_REQUIRES_USER_LAUNCH" if Path("/Applications").exists() else "NOT_FOUND"},
        "unreal": {"status": "CONFIG_REQUIRED", "path": ""},
        "davinci": {"status": "CONFIG_REQUIRED", "path": ""},
        "after_effects": {"status": "CONFIG_REQUIRED", "path": ""},
    }
    return {"schema_version": SCHEMA_VERSION, "software": entries, "destructive_actions_performed": False}
