"""Context Packs page for read-only packet planning."""

from __future__ import annotations

from apps.ui import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from apps.ui.i18n import UiText
from apps.ui.read_models import RuntimeSnapshot

CONTEXT_PACKET_OPTIONS: tuple[str, ...] = (
    "Gemini packet",
    "Codex task packet",
    "Claude review packet",
    "HFX-only packet",
    "desktop-only packet",
    "tests-only packet",
    "branch diff packet",
)

_PACKET_KEYS: dict[str, str] = {
    "Gemini packet": "context.gemini",
    "Codex task packet": "context.codex",
    "Claude review packet": "context.claude",
    "HFX-only packet": "context.hfx_only",
    "desktop-only packet": "context.desktop_only",
    "tests-only packet": "context.tests_only",
    "branch diff packet": "context.branch_diff",
}


class ContextPacksPage(QWidget):
    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        self.title = QLabel(self.text.tr("page.context_packs"), self)
        self.title.setObjectName("ContextPacksTitle")
        layout.addWidget(self.title)

        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self._packet_labels: dict[str, QLabel] = {}
        for index, option in enumerate(CONTEXT_PACKET_OPTIONS):
            label = QLabel(self.text.tr(_PACKET_KEYS[option]), self)
            label.setWordWrap(True)
            self._packet_labels[option] = label
            self.grid.addWidget(_panel(option, label), index // 3, index % 3)
        layout.addLayout(self.grid)

        self.token_budget = QLabel("Token / Size Budget: 24k target | local metadata only", self)
        self.token_budget.setObjectName("ContextPackBudget")
        self.generated_placeholder = QLabel("Generated packet artifact placeholder: none selected", self)
        self.generated_placeholder.setObjectName("GeneratedPacketPlaceholder")
        self.assembly_placeholder = QLabel("Packet assembly placeholder: idle", self)
        self.assembly_placeholder.setObjectName("PacketAssemblyPlaceholder")
        for label in (self.token_budget, self.generated_placeholder, self.assembly_placeholder):
            label.setWordWrap(True)
            layout.addWidget(label)

        self.copy_button = QPushButton("Copy Packet", self)
        self.open_button = QPushButton("Open Packet", self)
        for button in (self.copy_button, self.open_button):
            button.setEnabled(False)
            button.setToolTip(self.text.tr("common.disabled_until_facade"))
            layout.addWidget(button)
        layout.addStretch(1)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        self.token_budget.setText(
            f"Token / Size Budget: 24k target | jobs={len(snapshot.latest_jobs)} artifacts={snapshot.latest_artifacts_count}"
        )

    def packet_options(self) -> tuple[str, ...]:
        return CONTEXT_PACKET_OPTIONS

    def action_controls(self) -> tuple[QPushButton, ...]:
        return (self.copy_button, self.open_button)

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.context_packs"))
        for option, label in self._packet_labels.items():
            label.setText(self.text.tr(_PACKET_KEYS[option]))
        for button in self.action_controls():
            button.setToolTip(self.text.tr("common.disabled_until_facade"))


def _panel(title: str, content: QWidget) -> QFrame:
    panel = QFrame()
    panel.setProperty("role", "metricCard")
    panel.setMinimumHeight(74)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(12, 10, 12, 10)
    label = QLabel(title, panel)
    label.setProperty("role", "eyebrow")
    layout.addWidget(label)
    layout.addWidget(content)
    return panel
