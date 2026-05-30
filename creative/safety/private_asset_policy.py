"""Private asset policy checks."""

from __future__ import annotations

PRIVATE_EXTENSIONS = {".blend", ".hip", ".ztl", ".fbx", ".obj", ".vdb", ".exr", ".rar", ".zip", ".7z"}

def is_private_asset_path(path_text: str) -> bool:
    return any(path_text.lower().endswith(ext) for ext in PRIVATE_EXTENSIONS)
