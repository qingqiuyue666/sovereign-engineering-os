"""Conservative asset classification for local asset runtime v1."""

from pathlib import Path
import json

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".aiff"}
DCC_EXTENSIONS = {".hip", ".hiplc", ".blend", ".uproject", ".aep", ".drp"}
COLOR_LOOKDEV_EXTENSIONS = {".cube", ".ocio", ".hdr", ".hdri", ".mtlx"}
FX_CACHE_EXTENSIONS = {".vdb", ".abc", ".usd", ".usda", ".usdc"}
SCRIPT_EXTENSIONS = {".py", ".sh", ".jsx"}

MAX_JSON_CLASSIFICATION_BYTES = 2 * 1024 * 1024

__all__ = [
    "classify_local_asset",
]


def classify_local_asset(path: Path) -> str:
    asset_path = Path(path)
    extension = asset_path.suffix.lower()
    if extension in VIDEO_EXTENSIONS:
        return "video"
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in AUDIO_EXTENSIONS:
        return "audio"
    if extension in DCC_EXTENSIONS:
        return "dcc"
    if extension == ".json" and _is_conservative_comfyui_workflow(asset_path):
        return "comfyui_workflow"
    if extension in COLOR_LOOKDEV_EXTENSIONS:
        return "color/lookdev"
    if extension in FX_CACHE_EXTENSIONS:
        return "fx/cache"
    if extension in SCRIPT_EXTENSIONS:
        return "script"
    return "unknown"


def _is_conservative_comfyui_workflow(asset_path: Path) -> bool:
    try:
        if asset_path.stat().st_size > MAX_JSON_CLASSIFICATION_BYTES:
            return False
        payload = json.loads(asset_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False

    if not isinstance(payload, dict):
        return False

    return _looks_like_comfyui_ui_workflow(payload) or _looks_like_comfyui_api_prompt(
        payload
    )


def _looks_like_comfyui_ui_workflow(payload: dict) -> bool:
    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return False
    has_workflow_markers = (
        isinstance(payload.get("links"), list)
        or "last_node_id" in payload
        or "last_link_id" in payload
    )
    if not has_workflow_markers:
        return False
    return any(
        isinstance(node, dict)
        and isinstance(node.get("type"), str)
        and ("inputs" in node or "widgets_values" in node)
        for node in nodes
    )


def _looks_like_comfyui_api_prompt(payload: dict) -> bool:
    if not payload:
        return False
    node_count = 0
    for key, value in payload.items():
        if not isinstance(key, str) or not key.isdigit():
            return False
        if not isinstance(value, dict):
            return False
        if not isinstance(value.get("class_type"), str):
            return False
        if not isinstance(value.get("inputs"), dict):
            return False
        node_count += 1
    return node_count > 0
