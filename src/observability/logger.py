"""
Structured JSON Logger

Provides a configured logger that emits structured JSON records.
Replaces all print() calls throughout the ingestion pipeline.

Usage:
    from src.observability.logger import get_logger
    logger = get_logger(__name__)
    logger.info("stage_complete", extra={"task_id": task_id, "stage": "parsing", "count": 10})
"""

import logging
import json
import traceback
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    """
    Formats every log record as a single-line JSON object.
    Supports arbitrary `extra` keyword fields automatically.
    """

    # Fields that the logging.LogRecord always has — we skip them in `extra`
    _RESERVED = frozenset({
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "message",
        "taskName",
    })

    def format(self, record: logging.LogRecord) -> str:
        # Build core fields
        doc: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach extra fields (task_id, stage, duration_ms, etc.)
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                doc[key] = value

        # Attach exception traceback if present
        if record.exc_info is not None:
            doc["exception"] = self.formatException(record.exc_info)

        return json.dumps(doc, default=str)


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger configured with the JSON formatter.

    Multiple calls with the same name return the same logger instance
    (standard Python logging behaviour).
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)

    # Respect LOG_LEVEL env var; default to INFO
    import os
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))

    # Prevent propagation to root logger (avoids duplicate lines)
    logger.propagate = False

    return logger
