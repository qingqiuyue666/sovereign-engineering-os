#!/usr/bin/env python3
"""
Scaffold-only desktop inbox scanner for hfx_resource_library_layer.
"""

import json
import pathlib


SYSTEM_STATE = 'HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS'
DEFAULT_INBOX = pathlib.Path("/Users/qqy/Desktop/HFX_RESOURCE_INBOX/")


def scan(inbox_path=None):
    inbox = pathlib.Path(inbox_path) if inbox_path else DEFAULT_INBOX
    exists = inbox.exists()
    files = []
    if exists:
        files = [str(path) for path in sorted(inbox.iterdir()) if path.is_file()]
    return {
        "ok": True,
        "status": "NO_RESOURCES_FOUND_SCAFFOLD_REPORT" if not files else "RESOURCE_CANDIDATES_FOUND_SCAFFOLD_REPORT",
        "system_state": SYSTEM_STATE,
        "inbox_path": str(inbox),
        "inbox_exists": exists,
        "resource_count": len(files),
        "resources_complete": False,
        "final_pixels_authorized": False,
        "client_delivery_allowed": False,
        "resources": files,
        "reason": "Missing or empty inbox is valid for scaffold validation and does not certify resource completion.",
    }


def validate(payload=None, context=None):
    payload = payload or {}
    return scan(payload.get("inbox_path"))


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
