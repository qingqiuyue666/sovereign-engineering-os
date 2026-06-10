#!/usr/bin/env python3
"""Read-only CLI renderer for operator dashboard model views."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from kernel.dashboard.operator_dashboard_model_v1 import (
    OPERATOR_DASHBOARD_VIEWS,
    build_operator_dashboard_model,
    render_operator_dashboard_view,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a read-only operator dashboard view.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--view", choices=OPERATOR_DASHBOARD_VIEWS, default="summary")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("operator_dashboard_input_must_be_object")
    model = build_operator_dashboard_model(payload)
    print(render_operator_dashboard_view(model, args.view), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
