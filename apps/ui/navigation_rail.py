"""Left navigation rail for the single-window console workspace."""

from __future__ import annotations

from apps.ui import QFrame, QLabel, QToolButton, QVBoxLayout, Signal

NAVIGATION_ITEMS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("Observe", (("dashboard", "Dashboard"), ("system_health", "System Health"))),
    ("Dispatch", (("job_queue", "Job Queue"), ("hfx_factory", "HFX Factory"), ("context_packs", "Context Packs"))),
    (
        "Govern",
        (
            ("human_review", "Human Review"),
            ("failure_quarantine", "Failure Quarantine"),
            ("artifact_store", "Artifact Store"),
            ("asset_library", "Asset Library"),
        ),
    ),
    ("Settings", (("settings", "Settings"),)),
)


class NavigationRail(QFrame):
    page_selected = Signal(str)

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("NavRail")
        self.setFixedWidth(200)
        self._buttons: dict[str, QToolButton] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(6)
        for group, items in NAVIGATION_ITEMS:
            label = QLabel(group.upper(), self)
            label.setProperty("role", "eyebrow")
            layout.addWidget(label)
            for page_id, text in items:
                button = QToolButton(self)
                button.setText(text)
                button.setCheckable(True)
                button.setObjectName(f"Nav_{page_id}")
                button.clicked.connect(lambda _checked=False, value=page_id: self.select_page(value))
                self._buttons[page_id] = button
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
            values.extend(text for _page_id, text in items)
        return tuple(values)
