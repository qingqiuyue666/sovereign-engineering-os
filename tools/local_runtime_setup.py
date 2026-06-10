#!/usr/bin/env python3
"""Render and operate the safe local runtime setup path."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from kernel.install_config.local_runtime_path import (
    bootstrap_local_runtime,
    default_local_runtime_config,
    render_local_runtime_config,
    render_local_runtime_receipt,
    reset_local_runtime,
    run_local_runtime_smoke,
    stop_local_runtime,
    validate_local_runtime_config,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap, smoke, stop, or reset a safe local runtime path.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    config = subcommands.add_parser("config", help="Render the default local runtime config.")
    config.add_argument("repo_root", type=Path)
    config.add_argument("--runtime-root", default=".seos-runtime")

    validate = subcommands.add_parser("validate", help="Validate local runtime config and layout policy.")
    _add_common_args(validate)

    bootstrap = subcommands.add_parser("bootstrap", help="Create the marked local runtime layout when --apply is set.")
    _add_common_args(bootstrap)
    bootstrap.add_argument("--apply", action="store_true")

    smoke = subcommands.add_parser("smoke", help="Run the local smoke path without network or provider execution.")
    _add_common_args(smoke)
    smoke.add_argument("--apply", action="store_true")

    stop = subcommands.add_parser("stop", help="Record a clean stop receipt for the disabled-daemon runtime.")
    _add_common_args(stop)
    stop.add_argument("--apply", action="store_true")

    reset = subcommands.add_parser("reset", help="Remove the marked local runtime layout when --apply is set.")
    _add_common_args(reset)
    reset.add_argument("--apply", action="store_true")
    return parser.parse_args()


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("repo_root", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--runtime-root", default=".seos-runtime")


def main() -> int:
    args = _parse_args()
    config = _load_or_default_config(args)
    if args.command == "config":
        print(render_local_runtime_config(config), end="")
        return 0
    if args.command == "validate":
        report = validate_local_runtime_config(args.repo_root, config)
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", end="")
        return 0 if report.accepted else 1
    if args.command == "bootstrap":
        receipt = bootstrap_local_runtime(args.repo_root, config, apply=args.apply)
    elif args.command == "smoke":
        receipt = run_local_runtime_smoke(args.repo_root, config, apply=args.apply)
    elif args.command == "stop":
        receipt = stop_local_runtime(args.repo_root, config, apply=args.apply)
    elif args.command == "reset":
        receipt = reset_local_runtime(args.repo_root, config, apply=args.apply)
    else:  # pragma: no cover - argparse owns this path.
        raise ValueError(f"unsupported command: {args.command}")
    print(render_local_runtime_receipt(receipt), end="")
    return 0 if receipt.accepted else 1


def _load_or_default_config(args: argparse.Namespace) -> dict[str, object]:
    if getattr(args, "config", None):
        config_path = _resolve_config_path(args.repo_root, args.config)
        payload: Any = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("config_must_be_json_object")
        return dict(payload)
    return default_local_runtime_config(runtime_root=args.runtime_root)


def _resolve_config_path(repo_root: Path, config_path: Path) -> Path:
    root = repo_root.expanduser().resolve(strict=False)
    raw_path = config_path.expanduser()
    path = raw_path if raw_path.is_absolute() else root / raw_path
    if path.exists() and path.is_symlink():
        raise ValueError("config_path_symlink_rejected")
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ValueError("config_path_must_remain_inside_repo")
    if any(part in {".env", ".env.local", ".envrc"} for part in resolved.parts):
        raise ValueError("config_path_sensitive_material_rejected")
    return resolved


if __name__ == "__main__":
    raise SystemExit(main())
