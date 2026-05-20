"""System Health page for bounded runtime projection diagnostics."""

from __future__ import annotations

from apps.ui import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget
from apps.ui.energy_widgets import SystemPulseBoiler
from apps.ui.i18n import UiText
from apps.ui.motion import resolve_sync_state
from apps.ui.read_models import RuntimeSnapshot

SYSTEM_HEALTH_FIELDS: tuple[str, ...] = (
    "memory usage",
    "worker count",
    "active process count",
    "DB connection state",
    "SQLite WAL state",
    "artifact store size",
    "last smoke result",
    "last CI result",
    "warning list",
    "next maintenance task",
    "sync health",
)


class SystemHealthPage(QWidget):
    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        self.title = QLabel(self.text.tr("page.system_health"), self)
        self.title.setObjectName("SystemHealthTitle")
        layout.addWidget(self.title)

        self.boiler = SystemPulseBoiler(self)
        layout.addWidget(self.boiler)

        grid = QGridLayout()
        grid.setSpacing(10)
        self._values: dict[str, QLabel] = {}
        for index, field in enumerate(SYSTEM_HEALTH_FIELDS):
            card, value = _health_card(field)
            self._values[field] = value
            grid.addWidget(card, index // 3, index % 3)
        layout.addLayout(grid)
        layout.addStretch(1)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        sync_state = resolve_sync_state(snapshot)
        values = {
            "memory usage": snapshot.memory_pressure,
            "worker count": snapshot.workers,
            "active process count": snapshot.active_jobs,
            "DB connection state": "Available" if snapshot.database_available else "Unavailable",
            "SQLite WAL state": snapshot.wal_status,
            "artifact store size": snapshot.latest_artifacts_count,
            "last smoke result": snapshot.desktop_smoke_summary,
            "last CI result": "Not projected by desktop UI",
            "warning list": snapshot.warning_count,
            "next maintenance task": snapshot.next_required_action,
            "sync health": sync_state.value,
        }
        self.boiler.render(memory_pressure=snapshot.memory_pressure, wal_status=snapshot.wal_status)
        for key, value in values.items():
            self._values[key].setText(str(value))

    def rendered_values(self) -> dict[str, str]:
        return {key: label.text() for key, label in self._values.items()}

    def required_fields(self) -> tuple[str, ...]:
        return SYSTEM_HEALTH_FIELDS

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.system_health"))


def _health_card(title: str) -> tuple[QFrame, QLabel]:
    card = QFrame()
    card.setProperty("role", "metricCard")
    card.setMinimumHeight(78)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    label = QLabel(title, card)
    label.setProperty("role", "eyebrow")
    value = QLabel("--", card)
    value.setWordWrap(True)
    layout.addWidget(label)
    layout.addWidget(value)
    return card, value
