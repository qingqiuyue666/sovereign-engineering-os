"""Fail-closed exception boundaries.

Boundaries audit exception types only. Raw exception messages are not persisted
into the audit trail.
"""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import TypeVar
import functools

from .hierarchy import SovereignError

__all__ = ["ErrorBoundary", "error_boundary"]

F = TypeVar("F", bound=Callable[..., object])


class ErrorBoundary:
    """Translate unexpected exceptions into bounded SovereignError failures."""

    def __init__(
        self,
        component: str,
        *,
        translate_to: type[SovereignError] | None = SovereignError,
        suppress: bool = False,
    ) -> None:
        if not isinstance(component, str) or not component:
            raise SovereignError("error_boundary_component_required")
        if suppress and translate_to is not None:
            raise SovereignError("suppress_requires_translate_to_none")
        self.component = component
        self.translate_to = translate_to
        self.suppress = suppress
        self.caught_type: str | None = None

    def __enter__(self) -> ErrorBoundary:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        if exc_val is None:
            return False
        self.caught_type = exc_val.__class__.__name__
        from kernel.audit.trail import audit

        audit(
            "error_boundary.caught",
            component=self.component,
            error_type=self.caught_type,
            translated_to=self.translate_to.__name__ if self.translate_to else None,
        )
        if self.suppress:
            return True
        if self.translate_to is None:
            return False
        if isinstance(exc_val, self.translate_to):
            return False
        reason = f"boundary_failure:{self.component}:{self.caught_type}"
        raise self.translate_to(reason) from exc_val


def error_boundary(
    component: str,
    *,
    translate_to: type[SovereignError] | None = SovereignError,
) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> object:
            with ErrorBoundary(component, translate_to=translate_to):
                return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
