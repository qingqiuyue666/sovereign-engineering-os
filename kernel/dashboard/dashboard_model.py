"""Dashboard data model only. No UI runtime is started."""

from __future__ import annotations

from typing import Mapping

from .run_summary_model import validate_run_summary_model
from .security_status_model import validate_security_status_model

__all__ = ["build_dashboard_model", "validate_dashboard_model"]


def build_dashboard_model(*, cards: list[dict[str, object]], run_summary: dict[str, object], security_status: dict[str, object]) -> dict[str, object]:
    return {
        "model_type": "v12_dashboard_model",
        "cards": cards,
        "run_summary": run_summary,
        "security_status": security_status,
        "web_server_started": False,
        "frontend_build_performed": False,
        "network_accessed": False,
    }


def validate_dashboard_model(model: Mapping[str, object]) -> tuple[str, ...]:
    if not isinstance(model, Mapping):
        return ("dashboard_model_must_be_mapping",)
    failures: list[str] = []
    if model.get("model_type") != "v12_dashboard_model":
        failures.append("model_type_invalid")
    if not isinstance(model.get("cards"), list):
        failures.append("cards_required")
    elif not all(isinstance(card, Mapping) and card.get("card_id") and card.get("title") for card in model["cards"]):  # type: ignore[index]
        failures.append("dashboard_cards_invalid")
    if isinstance(model.get("run_summary"), Mapping):
        failures.extend(validate_run_summary_model(model["run_summary"]))  # type: ignore[arg-type]
    else:
        failures.append("run_summary_required")
    if isinstance(model.get("security_status"), Mapping):
        failures.extend(validate_security_status_model(model["security_status"]))  # type: ignore[arg-type]
    else:
        failures.append("security_status_required")
    for flag in ("web_server_started", "frontend_build_performed", "network_accessed"):
        if model.get(flag) is not False:
            failures.append(f"{flag}_must_be_false")
    return tuple(sorted(set(failures)))
