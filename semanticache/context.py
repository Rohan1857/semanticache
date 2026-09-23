from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

_metadata_ctx = contextvars.ContextVar[dict[str, Any] | None]("semanticache_metadata", default=None)

@contextmanager
def context(**kwargs: Any) -> Iterator[None]:
    """Context manager to attach metadata (like tenant_id) to cache lookups."""
    token = _metadata_ctx.set(kwargs)
    try:
        yield
    finally:
        _metadata_ctx.reset(token)

def set_context(**kwargs: Any) -> None:
    """Set context for the current task/thread."""
    _metadata_ctx.set(kwargs)

def clear_context() -> None:
    """Clear the current context."""
    _metadata_ctx.set(None)

def get_context() -> dict[str, Any] | None:
    """Retrieve the current context."""
    return _metadata_ctx.get()
