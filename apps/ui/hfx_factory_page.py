"""Read-only HFX Factory page for production-chain readiness."""

from __future__ import annotations

from apps.ui import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget
from apps.ui.i18n import UiText
from apps.ui.read_models import RuntimeSnapshot

HFX_FACTORY_FIELDS: tuple[str, ...] = (
    "Core12",
    "HFX_008 summary",
    "topology audit status",
    "proof artifact status",
    "validation status",
    "human review status",
    "resource package status",
    "final_claim_allowed",
    "next action",
    "blocked reason",
)


class HfxFactoryPage(QWidget):
    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        self.title = QLabel(self.text.tr("page.hfx_factory"), self)
        self.title.setObjectName("HfxFactoryTitle")
        layout.addWidget(self.title)

        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self._values: dict[str, QLabel] = {}
        for index, field in enumerate(HFX_FACTORY_FIELDS):
            card, value = _factory_card(field)
            self._values[field] = value
            self.grid.addWidget(card, index // 2, index % 2)
        layout.addLayout(self.grid)
        layout.addStretch(1)
        self.render_values(_default_factory_values())

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        values = _default_factory_values()
        values["HFX_008 summary"] = snapshot.hfx_008_landing_summary
        values["next action"] = snapshot.next_required_action
        if snapshot.quarantined_jobs:
            values["blocked reason"] = "Quarantined job requires review"
        self.render_values(values)

    def render_values(self, values: dict[str, object]) -> None:
        for key, label in self._values.items():
            label.setText(str(values.get(key, "--")))

    def rendered_values(self) -> dict[str, str]:
        return {key: label.text() for key, label in self._values.items()}

    def required_fields(self) -> tuple[str, ...]:
        return HFX_FACTORY_FIELDS

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.hfx_factory"))


def _factory_card(title: str) -> tuple[QFrame, QLabel]:
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


def _default_factory_values() -> dict[str, object]:
    return {
        "Core12": "12 modules tracked",
        "HFX_008 summary": "Landing chain dry-run evidence visible",
        "topology audit status": "Ready for Review",
        "proof artifact status": "Materialization Required",
        "validation status": "Blocked: Human Review Required",
        "human review status": "Requires Human Review",
        "resource package status": "Blocked: Missing Visual Proof",
        "final_claim_allowed": False,
        "next action": "Review landing evidence",
        "blocked reason": "Human review and visual proof required",
    }
