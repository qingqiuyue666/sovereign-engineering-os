"""Read-only dashboard page for Sovereign Console Phase 1."""

from __future__ import annotations

from apps.ui import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget
from apps.ui.i18n import UiText
from apps.ui.motion import resolve_sync_state
from apps.ui.read_models import RuntimeSnapshot


class DashboardPage(QWidget):
    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        self.title = QLabel(self.text.tr("page.dashboard"), self)
        self.title.setObjectName("DashboardTitle")
        layout.addWidget(self.title)
        self.warning_strip = QLabel("Local-only projection. Command controls remain gated.", self)
        self.warning_strip.setObjectName("DashboardWarningStrip")
        self.warning_strip.setWordWrap(True)
        layout.addWidget(self.warning_strip)

        grid = QGridLayout()
        grid.setSpacing(10)
        self._cards: dict[str, QLabel] = {}
        self._card_titles: dict[str, QLabel] = {}
        metrics = (
            ("runtime_status", "dashboard.runtime_health"),
            ("wal_status", "dashboard.sqlite_wal"),
            ("queue_depth", "dashboard.queue_depth"),
            ("active_jobs", "dashboard.active_jobs"),
            ("failed_jobs", "dashboard.failed_jobs"),
            ("quarantined_jobs", "dashboard.quarantined_jobs"),
            ("latest_artifacts_count", "dashboard.latest_artifacts"),
            ("hfx_008_landing_summary", "dashboard.hfx_008_landing"),
            ("desktop_smoke_summary", "dashboard.desktop_smoke"),
            ("resource_warning_status", "dashboard.resource_warning"),
            ("memory_pressure", "dashboard.memory_pressure"),
            ("next_required_action", "common.next_action"),
            ("sync_health", "common.sync_health"),
            ("local_only_status", "common.local_only"),
        )
        self._metric_labels = dict(metrics)
        for index, (key, label_key) in enumerate(metrics):
            card, title_label, value = _metric_card(self.text.tr(label_key))
            self._card_titles[key] = title_label
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
            "sync_health": resolve_sync_state(snapshot).value,
            "local_only_status": "Enabled",
        }
        for key, value in values.items():
            self._cards[key].setText(str(value))
        self.warning_strip.setText(
            "Warnings require inspection. Local-only projection remains active."
            if snapshot.warning_count
            else "Local-only projection. Command controls remain gated."
        )

    def rendered_values(self) -> dict[str, str]:
        return {key: value.text() for key, value in self._cards.items()}

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.dashboard"))
        for key, label_key in self._metric_labels.items():
            self._card_titles[key].setText(self.text.tr(label_key).upper())


def _metric_card(title: str) -> tuple[QFrame, QLabel, QLabel]:
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
    return card, label, value
