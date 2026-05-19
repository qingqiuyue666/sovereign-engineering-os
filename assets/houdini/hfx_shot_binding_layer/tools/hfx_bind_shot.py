#!/usr/bin/env python3
"""CLI for creating deterministic HFX shot-binding packages."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from hfx_shot_binding_lib import HFXShotBindingError, bind_shot


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind HFX Factory Core 12 assets into a shot package.")
    parser.add_argument("--request", required=True, help="Path to a ShotBindingRequest JSON file.")
    args = parser.parse_args()

    try:
        result = bind_shot(Path(args.request))
    except HFXShotBindingError as exc:
        print(f"HFX_BIND_SHOT_FAIL: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
