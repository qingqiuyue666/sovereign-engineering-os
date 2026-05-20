"""Settings view absorbing runtime boundaries and system health."""

from __future__ import annotations

from apps.ui import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from apps.ui.i18n import UiText, language_display_options
from apps.ui.motion import MotionIntensity, normalize_motion_intensity
from apps.ui.read_models import RuntimeSnapshot

SETTINGS_SECTIONS: tuple[str, ...] = (
    "Runtime",
    "Language",
    "Motion",
    "Boundaries",
    "Paths",
    "Workers",
    "Publishing",
    "System Health",
)

SYSTEM_HEALTH_SETTINGS_FIELDS: tuple[str, ...] = (
    "memory",
    "WAL state",
    "DB connection state",
    "last smoke result",
    "last CI result",
    "warnings",
)

SETTINGS_BOUNDARY_FIELDS: tuple[str, ...] = (
    "Language: Auto / English / Chinese",
    "Motion Intensity: Minimal / Standard / High Energy",
    "Runtime",
    "Local-only mode",
    "External network disabled",
    "Boundaries",
    "Asset root paths",
    "Artifact root path",
    "Paths",
    "Allowed workers",
    "Workers",
    "Dangerous action gates",
    "Human review gates",
    "Publish policy",
    "GitHub summary-only policy",
    "Publishing",
    "System Health",
    *SYSTEM_HEALTH_SETTINGS_FIELDS,
)


class SettingsPage(QWidget):
    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.language_option = "auto"
        self.motion_intensity = MotionIntensity.STANDARD
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        self.title = QLabel(self.text.tr("page.settings"), self)
        self.title.setObjectName("SettingsBoundariesTitle")
        layout.addWidget(self.title)

        self.section_strip = QGridLayout()
        self.section_strip.setSpacing(8)
        self._section_labels: dict[str, QLabel] = {}
        for index, section in enumerate(SETTINGS_SECTIONS):
            label = QLabel(section, self)
            label.setProperty("role", "eyebrow")
            self._section_labels[section] = label
            self.section_strip.addWidget(_panel(section, label), index // 4, index % 4)
        layout.addLayout(self.section_strip)

        self.language_panel = QFrame(self)
        self.language_panel.setProperty("role", "metricCard")
        language_layout = QVBoxLayout(self.language_panel)
        language_layout.setContentsMargins(12, 10, 12, 10)
        self.language_label = QLabel(self.text.tr("settings.language"), self.language_panel)
        self.language_label.setProperty("role", "eyebrow")
        language_layout.addWidget(self.language_label)
        self.language_buttons: dict[str, QPushButton] = {}
        for option, display in language_display_options(language):
            button = QPushButton(display, self.language_panel)
            button.setCheckable(True)
            clicked = getattr(button, "clicked", None)
            if hasattr(clicked, "connect"):
                clicked.connect(lambda _checked=False, value=option: self.set_language_option(value))
            self.language_buttons[option] = button
            language_layout.addWidget(button)
        layout.addWidget(self.language_panel)

        self.motion_panel = QFrame(self)
        self.motion_panel.setProperty("role", "metricCard")
        motion_layout = QVBoxLayout(self.motion_panel)
        motion_layout.setContentsMargins(12, 10, 12, 10)
        self.motion_label = QLabel(self.text.tr("settings.motion_intensity"), self.motion_panel)
        self.motion_label.setProperty("role", "eyebrow")
        motion_layout.addWidget(self.motion_label)
        self.motion_buttons: dict[MotionIntensity, QPushButton] = {}
        for intensity, key in (
            (MotionIntensity.MINIMAL, "motion.minimal"),
            (MotionIntensity.STANDARD, "motion.standard"),
            (MotionIntensity.HIGH_ENERGY, "motion.high_energy"),
        ):
            button = QPushButton(self.text.tr(key), self.motion_panel)
            button.setCheckable(True)
            clicked = getattr(button, "clicked", None)
            if hasattr(clicked, "connect"):
                clicked.connect(lambda _checked=False, value=intensity: self.set_motion_intensity(value))
            self.motion_buttons[intensity] = button
            motion_layout.addWidget(button)
        layout.addWidget(self.motion_panel)

        grid = QGridLayout()
        grid.setSpacing(10)
        self._boundary_values: dict[str, QLabel] = {}
        for index, (label, value) in enumerate(_default_boundaries().items()):
            value_label = QLabel(value, self)
            value_label.setWordWrap(True)
            self._boundary_values[label] = value_label
            grid.addWidget(_panel(label, value_label), index // 2, index % 2)
        layout.addLayout(grid)

        self.system_health_grid = QGridLayout()
        self.system_health_grid.setSpacing(10)
        self._system_health_values: dict[str, QLabel] = {}
        for index, field in enumerate(SYSTEM_HEALTH_SETTINGS_FIELDS):
            value_label = QLabel("--", self)
            value_label.setWordWrap(True)
            self._system_health_values[field] = value_label
            self.system_health_grid.addWidget(_panel(field, value_label), index // 3, index % 3)
        layout.addLayout(self.system_health_grid)
        layout.addStretch(1)
        self._refresh_buttons()

    def set_language_option(self, option: str) -> None:
        self.language_option = option if option in {"auto", "en", "zh"} else "auto"
        self._refresh_buttons()

    def set_motion_intensity(self, intensity: str | MotionIntensity) -> None:
        self.motion_intensity = normalize_motion_intensity(intensity)
        self._refresh_buttons()

    def language_options(self) -> tuple[str, ...]:
        return ("auto", "en", "zh")

    def motion_options(self) -> tuple[str, ...]:
        return tuple(intensity.value for intensity in MotionIntensity)

    def required_fields(self) -> tuple[str, ...]:
        return SETTINGS_BOUNDARY_FIELDS

    def required_sections(self) -> tuple[str, ...]:
        return SETTINGS_SECTIONS

    def rendered_boundaries(self) -> dict[str, str]:
        return {key: value.text() for key, value in self._boundary_values.items()}

    def rendered_system_health(self) -> dict[str, str]:
        return {key: value.text() for key, value in self._system_health_values.items()}

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        values = {
            "memory": snapshot.memory_pressure,
            "WAL state": snapshot.wal_status,
            "DB connection state": "Available" if snapshot.database_available else "Unavailable",
            "last smoke result": snapshot.desktop_smoke_summary,
            "last CI result": "Not projected by desktop UI",
            "warnings": str(snapshot.warning_count),
        }
        for key, value in values.items():
            self._system_health_values[key].setText(str(value))

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.settings"))
        self.language_label.setText(self.text.tr("settings.language"))
        self.motion_label.setText(self.text.tr("settings.motion_intensity"))
        for option, button in self.language_buttons.items():
            button.setText(dict(language_display_options(language))[option])
        for intensity, key in (
            (MotionIntensity.MINIMAL, "motion.minimal"),
            (MotionIntensity.STANDARD, "motion.standard"),
            (MotionIntensity.HIGH_ENERGY, "motion.high_energy"),
        ):
            self.motion_buttons[intensity].setText(self.text.tr(key))
        section_keys = {
            "Runtime": "settings.runtime",
            "Language": "settings.language",
            "Motion": "settings.motion_intensity",
            "Boundaries": "settings.boundaries",
            "Paths": "settings.paths",
            "Workers": "settings.workers",
            "Publishing": "settings.publishing",
            "System Health": "settings.system_health",
        }
        for section, key in section_keys.items():
            self._section_labels[section].setText(self.text.tr(key))
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        for option, button in self.language_buttons.items():
            button.setChecked(option == self.language_option)
        for intensity, button in self.motion_buttons.items():
            button.setChecked(intensity == self.motion_intensity)


def _panel(title: str, content: QWidget) -> QFrame:
    panel = QFrame()
    panel.setProperty("role", "metricCard")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(12, 10, 12, 10)
    label = QLabel(title, panel)
    label.setProperty("role", "eyebrow")
    layout.addWidget(label)
    layout.addWidget(content)
    return panel


def _default_boundaries() -> dict[str, str]:
    return {
        "Local-only mode": "Enabled",
        "External network disabled": "Enabled for GUI execution surface",
        "Asset root paths": "Read-only projection",
        "Artifact root path": "Read-only projection",
        "Allowed workers": "Worker registry projection only",
        "Dangerous action gates": "Locked unless OS Runtime Facade admits intent",
        "Human review gates": "Required for publish and final-claim surfaces",
        "Publish policy": "Local metadata first; publish requires review",
        "GitHub summary-only policy": "Summary-only by default",
    }
