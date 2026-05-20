"""Read-only dashboard page for Sovereign Console Phase 1."""

from __future__ import annotations

from apps.ui import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget
from apps.ui.read_models import RuntimeSnapshot


class DashboardPage(QWidget):
    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Dashboard", self)
        title.setObjectName("DashboardTitle")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(10)
        self._cards: dict[str, QLabel] = {}
        metrics = (
            ("runtime_status", "OS Runtime"),
            ("wal_status", "SQLite WAL"),
            ("queue_depth", "Queue Depth"),
            ("active_jobs", "Active Jobs"),
            ("failed_jobs", "Failed Jobs"),
            ("quarantined_jobs", "Quarantined Jobs"),
            ("latest_artifacts_count", "Latest Artifacts"),
            ("hfx_008_landing_summary", "HFX_008 Landing"),
            ("desktop_smoke_summary", "Desktop Smoke"),
            ("resource_warning_status", "ResourceWarning"),
            ("memory_pressure", "Memory Pressure"),
            ("next_required_action", "Next Required Action"),
        )
        for index, (key, label) in enumerate(metrics):
            card, value = _metric_card(label)
            self._cards[key] = value
            grid.addWidget(card, index // 3, index % 3)
        layout.addLayout(grid)
        layout.addStretch(1)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        values = {
            "runtime_status": snapshot.runtime_status,
            "wal_status": snapshot.wal_status,
            "queue_depth": snapshot.queue_depth,
            "active_jobs": snapshot.active_jobs,
            "failed_jobs": snapshot.failed_jobs,
            "quarantined_jobs": snapshot.quarantined_jobs,
            "latest_artifacts_count": snapshot.latest_artifacts_count,
            "hfx_008_landing_summary": snapshot.hfx_008_landing_summary,
            "desktop_smoke_summary": snapshot.desktop_smoke_summary,
            "resource_warning_status": snapshot.resource_warning_status,
            "memory_pressure": snapshot.memory_pressure,
            "next_required_action": snapshot.next_required_action,
        }
        for key, value in values.items():
            self._cards[key].setText(str(value))

    def rendered_values(self) -> dict[str, str]:
        return {key: value.text() for key, value in self._cards.items()}


def _metric_card(title: str) -> tuple[QFrame, QLabel]:
    card = QFrame()
    card.setProperty("role", "metricCard")
    card.setMinimumHeight(82)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(5)
    label = QLabel(title.upper(), card)
    label.setProperty("role", "eyebrow")
    value = QLabel("--", card)
    value.setWordWrap(True)
    layout.addWidget(label)
    layout.addWidget(value)
    layout.addStretch(1)
    return card, value
