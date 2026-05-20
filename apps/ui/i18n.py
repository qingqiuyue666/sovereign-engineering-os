"""Localization foundation for Sovereign Console UI labels."""

from __future__ import annotations

import locale
from collections.abc import Mapping
from dataclasses import replace
from enum import Enum

from apps.ui.read_models import RuntimeSnapshot
from apps.ui.translations import LANGUAGE_AUTO, LANGUAGE_CHINESE, LANGUAGE_ENGLISH, LANGUAGE_OPTIONS, TRANSLATIONS


class Language(str, Enum):
    AUTO = LANGUAGE_AUTO
    ENGLISH = LANGUAGE_ENGLISH
    CHINESE = LANGUAGE_CHINESE


def detect_system_language() -> str:
    """Return a supported display language without raising on host locale oddities."""

    try:
        language_code = (locale.getlocale()[0] or "").lower()
    except (TypeError, ValueError):
        language_code = ""
    if language_code.startswith("zh"):
        return LANGUAGE_CHINESE
    return LANGUAGE_ENGLISH


def resolve_language(language: str | Language | None) -> str:
    requested = _language_value(language)
    if requested == LANGUAGE_AUTO:
        return detect_system_language()
    if requested in LANGUAGE_OPTIONS:
        return requested
    return LANGUAGE_ENGLISH


def translate(key: str, language: str | Language | None = LANGUAGE_AUTO) -> str:
    resolved = resolve_language(language)
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return f"[[{key}]]"
    return entry.get(resolved) or entry.get(LANGUAGE_ENGLISH) or f"[[{key}]]"


def localize_status(canonical_status: str, language: str | Language | None = LANGUAGE_AUTO) -> str:
    """Display a canonical status without changing the canonical value."""

    return translate(f"status.{canonical_status}", language)


def language_display_options(language: str | Language | None = LANGUAGE_AUTO) -> tuple[tuple[str, str], ...]:
    return (
        (LANGUAGE_AUTO, translate("language.auto", language)),
        (LANGUAGE_ENGLISH, translate("language.en", language)),
        (LANGUAGE_CHINESE, translate("language.zh", language)),
    )


def snapshot_with_display_language(snapshot: RuntimeSnapshot, _language: str | Language | None) -> RuntimeSnapshot:
    """Return an equal immutable snapshot to make no-mutation tests explicit."""

    return replace(snapshot)


def translated_labels(keys: tuple[str, ...], language: str | Language | None = LANGUAGE_AUTO) -> dict[str, str]:
    return {key: translate(key, language) for key in keys}


class UiText:
    """Small state holder for widgets that need runtime language switching."""

    def __init__(self, language: str | Language | None = LANGUAGE_AUTO) -> None:
        self.language = _language_value(language)

    def set_language(self, language: str | Language | None) -> None:
        self.language = _language_value(language)

    def tr(self, key: str) -> str:
        return translate(key, self.language)

    def status(self, canonical_status: str) -> str:
        return localize_status(canonical_status, self.language)

    def display_options(self) -> Mapping[str, str]:
        return dict(language_display_options(self.language))


def _language_value(language: str | Language | None) -> str:
    if isinstance(language, Language):
        return language.value
    if language in LANGUAGE_OPTIONS:
        return str(language)
    return LANGUAGE_AUTO
