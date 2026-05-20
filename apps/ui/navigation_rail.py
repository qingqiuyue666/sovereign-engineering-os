"""Left navigation rail for the single-window console workspace."""

from __future__ import annotations

from apps.ui import QFrame, QLabel, QToolButton, QVBoxLayout, Signal
from apps.ui.i18n import UiText

NAVIGATION_ITEMS: tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...] = (
    ("nav.observe", (("dashboard", "Dashboard", "page.dashboard"), ("system_health", "System Health", "page.system_health"))),
    (
        "nav.dispatch",
        (
            ("job_queue", "Job Queue", "page.job_queue"),
            ("hfx_factory", "HFX Factory", "page.hfx_factory"),
            ("hfx_landing_chain", "HFX_008 Landing Chain", "page.hfx_landing_chain"),
            ("context_packs", "Context Packs", "page.context_packs"),
        ),
    ),
    (
        "nav.govern",
        (
            ("human_review", "Human Review", "page.human_review"),
            ("failure_quarantine", "Failure Quarantine", "page.failure_quarantine"),
            ("artifact_store", "Artifact Store", "page.artifact_store"),
        ),
    ),
    ("nav.settings_group", (("settings", "Settings", "page.settings"),)),
)


class NavigationRail(QFrame):
    page_selected = Signal(str)

    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.setObjectName("NavRail")
        self.setFixedWidth(200)
        self._buttons: dict[str, QToolButton] = {}
        self._button_label_keys: dict[str, str] = {}
        self._group_labels: dict[str, QLabel] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(6)
        for group_key, items in NAVIGATION_ITEMS:
            label = QLabel(self.text.tr(group_key).upper(), self)
            label.setProperty("role", "eyebrow")
            self._group_labels[group_key] = label
            layout.addWidget(label)
            for page_id, fallback_text, label_key in items:
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
        layout.addStretch(1)
        self.select_page("dashboard", emit=False)

    def select_page(self, page_id: str, *, emit: bool = True) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == page_id)
        if emit:
            self.page_selected.emit(page_id)

    def labels(self) -> tuple[str, ...]:
        values: list[str] = []
        for _group, items in NAVIGATION_ITEMS:
            values.extend(text for _page_id, text, _label_key in items)
        return tuple(values)

    def visible_labels(self) -> tuple[str, ...]:
        return tuple(button.text() for button in self._buttons.values())

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        for group_key, label in self._group_labels.items():
            label.setText(self.text.tr(group_key).upper())
        for page_id, button in self._buttons.items():
            button.setText(self.text.tr(self._button_label_keys[page_id]))
