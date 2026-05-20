"""Reduced left navigation rail for the unified workspace product."""

from __future__ import annotations

from apps.ui import QFrame, QLabel, QToolButton, QVBoxLayout, Signal
from apps.ui.i18n import UiText
from apps.ui.read_models import RuntimeSnapshot

PRIMARY_NAVIGATION_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("workspace", "Workspace", "page.workspace"),
    ("runs", "Runs", "page.runs"),
    ("artifacts", "Artifacts", "page.artifacts"),
    ("reviews", "Reviews", "page.reviews"),
    ("settings", "Settings", "page.settings"),
)

NAVIGATION_ITEMS = PRIMARY_NAVIGATION_ITEMS

REMOVED_FIRST_LEVEL_LABELS: tuple[str, ...] = (
    "Dashboard",
    "System Health",
    "Job Queue",
    "HFX Factory",
    "HFX_008 Landing Chain",
    "Context Packs",
    "Human Review",
    "Failure Quarantine",
    "Artifact Store",
    "Asset Library",
    "Settings / Boundaries",
)


class NavigationRail(QFrame):
    page_selected = Signal(str)

    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.setObjectName("NavRail")
        self.setFixedWidth(184)
        self._buttons: dict[str, QToolButton] = {}
        self._badges: dict[str, QLabel] = {}
        self._button_label_keys: dict[str, str] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(6)

        self.product_label = QLabel("Sovereign Console", self)
        self.product_label.setProperty("role", "eyebrow")
        layout.addWidget(self.product_label)

        for page_id, fallback_text, label_key in PRIMARY_NAVIGATION_ITEMS:
            button = QToolButton(self)
            button.setText(self.text.tr(label_key) if label_key else fallback_text)
            button.setCheckable(True)
            button.setObjectName(f"Nav_{page_id}")
            clicked = getattr(button, "clicked", None)
            if hasattr(clicked, "connect"):
                clicked.connect(lambda _checked=False, value=page_id: self.select_page(value))
            self._buttons[page_id] = button
            self._button_label_keys[page_id] = label_key
            layout.addWidget(button)

            badge = QLabel("", self)
            badge.setObjectName(f"NavBadge_{page_id}")
            badge.setProperty("role", "eyebrow")
            self._badges[page_id] = badge
            layout.addWidget(badge)

        layout.addStretch(1)
        self.select_page("workspace", emit=False)

    def select_page(self, page_id: str, *, emit: bool = True) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == page_id)
        if emit:
            self.page_selected.emit(page_id)

    def render_badges(self, snapshot: RuntimeSnapshot) -> None:
        pending_reviews = sum(1 for artifact in snapshot.latest_artifacts if artifact.review_status in {"needs_review", "new"})
        quarantined_artifacts = sum(1 for artifact in snapshot.latest_artifacts if artifact.quarantine_status != "clean")
        values = {
            "workspace": "",
            "runs": str(snapshot.queue_depth) if snapshot.queue_depth else "",
            "artifacts": str(snapshot.latest_artifacts_count) if snapshot.latest_artifacts_count else "",
            "reviews": str(pending_reviews + snapshot.quarantined_jobs + quarantined_artifacts)
            if pending_reviews or snapshot.quarantined_jobs or quarantined_artifacts
            else "",
            "settings": str(snapshot.warning_count) if snapshot.warning_count else "",
        }
        for page_id, value in values.items():
            self._badges[page_id].setText(value)

    def labels(self) -> tuple[str, ...]:
        return tuple(text for _page_id, text, _label_key in PRIMARY_NAVIGATION_ITEMS)

    def visible_labels(self) -> tuple[str, ...]:
        return tuple(button.text() for button in self._buttons.values())

    def page_ids(self) -> tuple[str, ...]:
        return tuple(self._buttons)

    def removed_first_level_labels(self) -> tuple[str, ...]:
        return REMOVED_FIRST_LEVEL_LABELS

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        for page_id, button in self._buttons.items():
            button.setText(self.text.tr(self._button_label_keys[page_id]))
