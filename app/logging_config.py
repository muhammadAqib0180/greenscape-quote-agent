"""
app/logging_config.py — Structured logging and request correlation middleware.

Extracted from app/main.py so that the logging setup is reusable and testable
in isolation. Import JsonFormatter and CorrelationIdMiddleware from this module.
"""

import json
import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

__all__ = ["JsonFormatter", "CorrelationIdMiddleware", "configure_root_logger"]

logger = logging.getLogger(__name__)


class JsonFormatter(logging.Formatter):
    """Structured JSON formatter for production and cloud environments.

    Emits every log record as a single-line JSON object so log aggregators
    (Datadog, Cloud Logging, Loki) can index fields natively without regex
    parsing.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_record: dict = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "path"):
            log_record["path"] = record.path
        if hasattr(record, "method"):
            log_record["method"] = record.method
        if hasattr(record, "status_code"):
            log_record["status_code"] = record.status_code
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware attaching a unique request_id to every HTTP request.

    - Reads the X-Request-ID header if present (supports distributed tracing).
    - Falls back to a freshly generated UUID4 for requests without a prior ID.
    - Echoes the ID back in the response X-Request-ID header.
    - Emits a structured INFO log on every completed request.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "HTTP request completed",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
            },
        )
        return response


def configure_root_logger() -> None:
    """Wire the root logger to emit structured JSON to stdout.

    Call this once at application startup (in app/main.py) before any
    other loggers are created.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger.handlers = [handler]
