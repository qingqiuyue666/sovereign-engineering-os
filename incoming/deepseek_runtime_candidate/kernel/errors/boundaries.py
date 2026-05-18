"""Exception boundaries: context managers for catching and translating errors."""

from __future__ import annotations

from collections.abc import Callable
import functools
from typing import TypeVar

from kernel.errors.hierarchy import SovereignError
from kernel.audit.trail import audit

__all__ = ["error_boundary", "ErrorBoundary"]

F = TypeVar("F", bound=Callable)


class ErrorBoundary:
    """Context manager that catches exceptions and translates them into SovereignError subtypes.

    Usage:
        with ErrorBoundary(component="task_validator"):
            validate_task(payload)
    """

    def __init__(self, component: str, reraise: type[SovereignError] | None = None) -> None:
        self.component = component
        self.reraise = reraise
        self.caught: BaseException | None = None

    def __enter__(self) -> ErrorBoundary:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None,
                 exc_tb: object) -> bool:
        if exc_val is None:
            return False  # no exception — normal exit

        audit("error_boundary.caught", component=self.component,
              error=exc_val.__class__.__name__, message=str(exc_val))

        # If reraise type specified and the caught exception IS that type, let it pass through
        if self.reraise and isinstance(exc_val, self.reraise):
            self.caught = exc_val
            return False  # don't suppress — propagate

        # If reraise type specified but exception is different, translate it
        if self.reraise and not isinstance(exc_val, self.reraise):
            self.caught = self.reraise(str(exc_val))
            raise self.caught from exc_val

        # No reraise type — suppress everything
        if isinstance(exc_val, SovereignError):
            self.caught = exc_val
        else:
            self.caught = SovereignError(
                f"boundary_catch:{self.component} {exc_type.__name__ if exc_type else 'unknown'}:{exc_val}"
            )
        return True  # suppress


def error_boundary(component: str) -> Callable[[F], F]:
    """Decorator: wrap a function in an ErrorBoundary."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> object:
            with ErrorBoundary(component=component):
                return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
