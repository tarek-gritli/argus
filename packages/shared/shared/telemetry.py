"""Langfuse observability helpers — all no-ops when LANGFUSE_SECRET_KEY is not set."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_enabled = bool(os.getenv("LANGFUSE_SECRET_KEY"))

if _enabled:
    try:
        from langfuse.decorators import langfuse_context, observe

        # CallbackHandler moved from langfuse.callback (v2) to langfuse.langchain (v3)
        try:
            from langfuse.langchain import CallbackHandler
        except ImportError:
            from langfuse.callback import CallbackHandler  # type: ignore[no-redef]

    except ImportError as exc:
        logger.warning("langfuse import failed — tracing disabled: %s", exc)
        _enabled = False

if not _enabled:

    def observe(name: str = "", as_type: str = "", **kwargs: Any):  # type: ignore[misc]
        return lambda fn: fn

    langfuse_context: Any = None
    CallbackHandler: Any = None


def get_callback_handler() -> Any | None:
    """Return a LangfuseCallbackHandler that inherits the current trace, or None."""
    if not _enabled or CallbackHandler is None:
        return None
    try:
        return CallbackHandler()
    except Exception as exc:
        logger.warning("Langfuse CallbackHandler init failed — skipping: %s", exc)
        return None
