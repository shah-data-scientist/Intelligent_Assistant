"""Request tracing utilities for distributed logging."""

import logging
import uuid
from contextvars import ContextVar
from typing import Optional

# Context variable to store trace ID across async calls
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)

logger = logging.getLogger(__name__)


class TraceIDFilter(logging.Filter):
    """Add trace ID to log records."""

    def filter(self, record):
        record.trace_id = trace_id_var.get() or "no-trace"
        return True


def get_trace_id() -> str:
    """Get current trace ID or generate new one.

    Returns:
        Trace ID string
    """
    trace_id = trace_id_var.get()
    if not trace_id:
        trace_id = str(uuid.uuid4())
        trace_id_var.set(trace_id)
    return trace_id


def set_trace_id(trace_id: str) -> None:
    """Set trace ID for current context.

    Args:
        trace_id: Trace ID string
    """
    trace_id_var.set(trace_id)


def clear_trace_id() -> None:
    """Clear trace ID from current context."""
    trace_id_var.set(None)


def generate_trace_id() -> str:
    """Generate and set new trace ID.

    Returns:
        New trace ID string
    """
    trace_id = str(uuid.uuid4())
    set_trace_id(trace_id)
    return trace_id


# Configure logging format to include trace ID
TRACE_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(trace_id)s] [%(name)s:%(lineno)d] %(message)s"


def configure_trace_logging():
    """Configure logging to include trace IDs."""
    # Add trace ID filter to root logger
    root_logger = logging.getLogger()
    trace_filter = TraceIDFilter()

    # Add filter to all handlers
    for handler in root_logger.handlers:
        handler.addFilter(trace_filter)
        # Update formatter to include trace_id
        formatter = logging.Formatter(TRACE_LOG_FORMAT)
        handler.setFormatter(formatter)

    logger.info("Configured trace logging")
