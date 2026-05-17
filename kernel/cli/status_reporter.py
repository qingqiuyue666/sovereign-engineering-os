"""CLI status adapter."""

from __future__ import annotations

from kernel.status.status_reporter import v12_status_report

__all__ = ["cli_status_report"]


def cli_status_report() -> dict[str, object]:
    report = v12_status_report()
    return {
        "ok": True,
        "status": "V12 foundation status",
        "implemented_count": report["implemented_count"],
        "missing_count": report["missing_count"],
        "forbidden_surfaces_absent": report["forbidden_surfaces_absent"],
    }
