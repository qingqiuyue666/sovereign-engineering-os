"""Safe motion and sync-state primitives for the native console."""

from __future__ import annotations

from enum import Enum

from apps.ui.read_models import RuntimeSnapshot, SYNC_STALE_AFTER_MS


class MotionIntensity(str, Enum):
    MINIMAL = "Minimal"
    STANDARD = "Standard"
    HIGH_ENERGY = "High Energy"


class VisualSeverity(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    FATAL = "fatal"


class SyncState(str, Enum):
    HEALTHY = "Healthy"
    DEGRADED = "Degraded"
    LOST = "Lost"


def normalize_motion_intensity(value: str | MotionIntensity | None) -> MotionIntensity:
    if isinstance(value, MotionIntensity):
        return value
    normalized = str(value or "").strip().lower().replace("_", " ")
    mapping = {
        "minimal": MotionIntensity.MINIMAL,
        "standard": MotionIntensity.STANDARD,
        "high energy": MotionIntensity.HIGH_ENERGY,
        "high": MotionIntensity.HIGH_ENERGY,
    }
    return mapping.get(normalized, MotionIntensity.STANDARD)


def resolve_sync_state(
    snapshot: RuntimeSnapshot,
    *,
    now_ms: int | None = None,
    stale_after_ms: int = SYNC_STALE_AFTER_MS,
    had_healthy_projection: bool = False,
) -> SyncState:
    if not snapshot.runtime_available or not snapshot.database_available:
        return SyncState.LOST if had_healthy_projection else SyncState.DEGRADED
    if snapshot.age_ms(now_ms=now_ms) > stale_after_ms:
        return SyncState.LOST if had_healthy_projection else SyncState.DEGRADED
    if snapshot.sync_stale:
        return SyncState.LOST if had_healthy_projection else SyncState.DEGRADED
    return SyncState.HEALTHY


def classify_memory_pressure(memory_pressure: str) -> VisualSeverity:
    text = str(memory_pressure).strip().lower()
    if text.startswith("high") or "fatal" in text:
        return VisualSeverity.FATAL
    if text.startswith("elevated") or "warning" in text:
        return VisualSeverity.WARNING
    return VisualSeverity.NORMAL


def classify_wal_status(wal_status: str) -> VisualSeverity:
    text = str(wal_status).strip().lower()
    if text in {"wal", "ok", "normal"}:
        return VisualSeverity.NORMAL
    if text in {"unknown", "missing", "disabled"}:
        return VisualSeverity.WARNING
    if "error" in text or "fatal" in text:
        return VisualSeverity.FATAL
    return VisualSeverity.WARNING


def effective_motion_intensity(
    requested: str | MotionIntensity | None,
    *,
    memory_pressure: str = "Nominal",
    sync_state: str | SyncState = SyncState.HEALTHY,
) -> MotionIntensity:
    normalized = normalize_motion_intensity(requested)
    resolved_sync = SyncState(sync_state) if not isinstance(sync_state, SyncState) else sync_state
    if resolved_sync is SyncState.LOST:
        return MotionIntensity.MINIMAL
    if classify_memory_pressure(memory_pressure) is VisualSeverity.FATAL:
        return MotionIntensity.MINIMAL
    return normalized


def risky_actions_locked(sync_state: str | SyncState) -> bool:
    resolved = SyncState(sync_state) if not isinstance(sync_state, SyncState) else sync_state
    return resolved in {SyncState.DEGRADED, SyncState.LOST}
