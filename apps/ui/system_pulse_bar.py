"""System Pulse Bar for compact runtime status."""

from __future__ import annotations

from apps.ui import QFrame, QHBoxLayout, QLabel, QSizePolicy, Qt
from apps.ui.motion import resolve_sync_state
from apps.ui.read_models import RuntimeSnapshot


class SystemPulseBar(QFrame):
    """Displays immutable runtime snapshots without querying the backend."""

    FIELD_LABELS: tuple[tuple[str, str], ...] = (
        ("runtime_status", "OS Runtime"),
        ("wal_status", "SQLite WAL"),
        ("queue_depth", "Queue Depth"),
        ("workers", "Workers"),
        ("memory_pressure", "Memory"),
        ("warning_count", "Warnings"),
        ("sync_health", "Sync"),
        ("next_required_action", "Next Required Action"),
    )

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PulseBar")
        self.setFixedHeight(36)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(14)
        self._value_labels: dict[str, QLabel] = {}
        for key, title in self.FIELD_LABELS:
            label = QLabel(f"{title}: --", self)
            label.setObjectName(f"Pulse_{key}")
            if key == "next_required_action":
                label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._value_labels[key] = label
            layout.addWidget(label)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        values = {
            "runtime_status": snapshot.runtime_status,
            "wal_status": snapshot.wal_status,
            "queue_depth": snapshot.queue_depth,
            "workers": snapshot.workers,
            "memory_pressure": snapshot.memory_pressure,
            "warning_count": snapshot.warning_count,
            "sync_health": resolve_sync_state(snapshot).value,
            "next_required_action": snapshot.next_required_action,
        }
        for key, value in values.items():
            label = self._value_labels[key]
            title = dict(self.FIELD_LABELS)[key]
            label.setText(f"{title}: {value}")
        self.setProperty("syncLost", snapshot.is_sync_lost())
        self.style().unpolish(self)
        self.style().polish(self)

    def rendered_text(self) -> dict[str, str]:
        return {key: label.text() for key, label in self._value_labels.items()}
