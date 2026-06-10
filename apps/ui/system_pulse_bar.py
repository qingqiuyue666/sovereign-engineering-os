"""Grouped System Pulse chips for compact runtime status."""

from __future__ import annotations

from apps.ui import QFrame, QHBoxLayout, QLabel, QSizePolicy, Qt, QVBoxLayout
from apps.ui.motion import SyncState, resolve_sync_state
from apps.ui.read_models import RuntimeSnapshot


class SystemPulseBar(QFrame):
    """Displays immutable runtime snapshots as grouped status chips."""

    FIELD_LABELS: tuple[tuple[str, str], ...] = (
        ("runtime_status", "Runtime"),
        ("wal_status", "WAL"),
        ("queue_depth", "Runs"),
        ("workers", "Workers"),
        ("memory_pressure", "Memory"),
        ("warning_count", "Warnings"),
        ("sync_health", "Sync"),
        ("next_required_action", "Next Action"),
    )

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PulseBar")
        self.setFixedHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)
        self._value_labels: dict[str, QLabel] = {}
        self._chips: dict[str, QFrame] = {}
        for key, title in self.FIELD_LABELS:
            chip = QFrame(self)
            chip.setObjectName(f"PulseChip_{key}")
            chip.setProperty("role", "pulseChip")
            chip_layout = QVBoxLayout(chip)
            chip_layout.setContentsMargins(8, 4, 8, 4)
            chip_layout.setSpacing(1)
            title_label = QLabel(title, chip)
            title_label.setProperty("role", "eyebrow")
            value_label = QLabel("--", chip)
            value_label.setObjectName(f"Pulse_{key}")
            value_label.setWordWrap(False)
            if key == "next_required_action":
                chip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            chip_layout.addWidget(title_label)
            chip_layout.addWidget(value_label)
            self._chips[key] = chip
            self._value_labels[key] = value_label
            layout.addWidget(chip)

    def render_snapshot(self, snapshot: RuntimeSnapshot, *, sync_state: SyncState | None = None) -> None:
        resolved_sync = sync_state or resolve_sync_state(snapshot)
        values = {
            "runtime_status": snapshot.runtime_status,
            "wal_status": snapshot.wal_status,
            "queue_depth": snapshot.queue_depth,
            "workers": snapshot.workers,
            "memory_pressure": snapshot.memory_pressure,
            "warning_count": snapshot.warning_count,
            "sync_health": resolved_sync.value,
            "next_required_action": snapshot.next_required_action,
        }
        for key, value in values.items():
            self._value_labels[key].setText(str(value))
        self.setProperty("syncLost", resolved_sync is SyncState.LOST)
        self.setProperty("syncState", resolved_sync.value)
        self.style().unpolish(self)
        self.style().polish(self)

    def rendered_text(self) -> dict[str, str]:
        return {key: label.text() for key, label in self._value_labels.items()}

    def chip_names(self) -> tuple[str, ...]:
        return tuple(title for _key, title in self.FIELD_LABELS)

    def is_grouped_chip_surface(self) -> bool:
        return bool(self._chips)
