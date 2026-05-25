"""Langfuse observability helpers — compatible with langfuse 3.x SDK."""

from __future__ import annotations

import logging
import os
from contextvars import ContextVar
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)

_enabled = bool(os.getenv("LANGFUSE_SECRET_KEY"))
_lf: Any = None

if _enabled:
    try:
        from langfuse import Langfuse as _Langfuse

        from shared.config import get_settings as _get_settings

        _s = _get_settings()
        _lf = _Langfuse(
            secret_key=_s.langfuse_secret_key,
            public_key=_s.langfuse_public_key,
            host=_s.langfuse_base_url,
        )
        logger.info("Langfuse tracing enabled (host=%s)", _s.langfuse_base_url)
    except ImportError as exc:
        logger.warning("langfuse not installed — tracing disabled: %s", exc)
        _enabled = False
    except Exception as exc:
        logger.warning("langfuse init failed — tracing disabled: %s", exc)
        _enabled = False

# ContextVars for cross-thread trace propagation.
# Python 3.7+ ThreadPoolExecutor copies ContextVars into spawned threads,
# so these propagate reliably into LangGraph's parallel node threads.
_active_trace_id: ContextVar[str | None] = ContextVar("_argus_trace_id", default=None)
_active_observation: ContextVar[Any] = ContextVar("_argus_observation", default=None)


def create_trace(name: str, **kwargs: Any) -> Any:
    """Create a root Langfuse trace, store its ID for thread propagation."""
    if not _enabled or _lf is None:
        return None
    try:
        trace = _lf.trace(name=name, **kwargs)
        _active_trace_id.set(trace.id)
        return trace
    except Exception as exc:
        logger.debug("Langfuse trace creation failed (non-fatal): %s", exc)
        return None


def observe(name: str = "", as_type: str = "", **_: Any):
    """Decorator that wraps a function in a Langfuse span or generation.

    When a root trace has been created via create_trace(), child observations
    are attached to it explicitly using the trace_id — this works across
    LangGraph's parallel threads.  Without a root trace the decorator falls
    back to start_as_current_span/generation (creates its own root).
    """

    def decorator(fn):
        if not _enabled or _lf is None:
            return fn

        @wraps(fn)
        def wrapper(*args, **kwargs):
            span_name = name or fn.__name__
            trace_id = _active_trace_id.get()

            if not trace_id:
                # No active trace — use context manager (creates new root trace).
                try:
                    if as_type == "generation":
                        cm = _lf.start_as_current_generation(name=span_name)
                    else:
                        cm = _lf.start_as_current_span(name=span_name)
                    with cm:
                        return fn(*args, **kwargs)
                except Exception as exc:
                    logger.debug("Langfuse span error (non-fatal): %s", exc)
                    return fn(*args, **kwargs)

            # Create an explicit child observation under the active trace.
            obs = None
            try:
                if as_type == "generation":
                    obs = _lf.generation(trace_id=trace_id, name=span_name)
                else:
                    obs = _lf.span(trace_id=trace_id, name=span_name)
            except Exception as exc:
                logger.debug("Langfuse observation creation failed (non-fatal): %s", exc)
                return fn(*args, **kwargs)

            token = _active_observation.set(obs)
            try:
                return fn(*args, **kwargs)
            finally:
                _active_observation.reset(token)
                try:
                    obs.end()
                except Exception as exc:
                    logger.debug("Langfuse obs.end() failed (non-fatal): %s", exc)

        return wrapper

    return decorator


class _ContextProxy:
    """Mimics the langfuse_context interface used across agent files."""

    def __bool__(self) -> bool:
        return _enabled and _lf is not None

    def update_current_trace(self, **kwargs: Any) -> None:
        if _lf is None:
            return
        try:
            _lf.update_current_trace(**kwargs)
        except Exception as exc:
            logger.debug("update_current_trace failed (non-fatal): %s", exc)

    def update_current_observation(self, **kwargs: Any) -> None:
        obs = _active_observation.get()
        if obs is not None:
            try:
                obs.update(**kwargs)
                return
            except Exception as exc:
                logger.debug("obs.update failed (non-fatal): %s", exc)
        # Fall back to Langfuse context API (used when no explicit observation exists).
        if _lf is None:
            return
        try:
            _lf.update_current_generation(**kwargs)
        except Exception:
            try:
                _lf.update_current_span(**kwargs)
            except Exception as exc:
                logger.debug("update_current_observation failed (non-fatal): %s", exc)


langfuse_context = _ContextProxy()


def flush() -> None:
    """Flush all pending Langfuse events to the server."""
    if _enabled and _lf is not None:
        try:
            _lf.flush()
        except Exception as exc:
            logger.debug("Langfuse flush failed (non-fatal): %s", exc)


def get_callback_handler() -> Any | None:
    """Return a Langfuse LangGraph callback handler, or None if unavailable."""
    if not _enabled or _lf is None:
        return None
    try:
        from langfuse.langchain import CallbackHandler

        return CallbackHandler()
    except Exception:
        return None
