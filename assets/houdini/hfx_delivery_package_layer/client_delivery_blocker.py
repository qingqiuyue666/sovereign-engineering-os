#!/usr/bin/env python3
"""
Fail-closed client delivery blocker for hfx_delivery_package_layer.
"""

import json


SYSTEM_STATE = 'HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS'


def validate(payload=None, context=None):
    payload = payload or {}
    context = context or {}
    return {
        "ok": False,
        "status": "CLIENT_DELIVERY_BLOCKED",
        "system_state": SYSTEM_STATE,
        "reason": "Client/public delivery is blocked in the no-final-pixels scaffold state.",
        "final_pixels_authorized": False,
        "client_delivery_allowed": False,
        "public_delivery_allowed": False,
        "payload_keys": sorted(payload.keys()),
        "context_keys": sorted(context.keys()),
    }


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
