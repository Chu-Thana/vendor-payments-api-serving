from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from config import LOG_LEVEL


class JsonFormatter(logging.Formatter):
    """
    JSON log formatter.

    Output fields:
    - ts (UTC ISO8601)
    - level
    - logger
    - message
    - module, func, line
    - extras (from logger.*(..., extra={...}))
    - exception info if present
    """

    _reserved = {
        # core record
        "name", "msg", "args", "levelname", "levelno",
        "pathname", "filename", "module", "exc_info", "exc_text",
        "stack_info", "lineno", "funcName", "created", "msecs",
        "relativeCreated", "thread", "threadName", "processName",
        "process", "message",
        # formatter fields
        "asctime",
    }

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()

        # Use record.created for stable timestamp
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

        payload: Dict[str, Any] = {
            "ts": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }

        # Attach extras (anything not reserved)
        for k, v in record.__dict__.items():
            if k in self._reserved:
                continue
            # Avoid overwriting base fields
            if k not in payload:
                payload[k] = v

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging() -> logging.Logger:
    """
    Configure structured JSON logging.

    - One StreamHandler (stdout)
    - No duplicate handlers if called multiple times
    - Returns application logger "api"
    """
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    logger = logging.getLogger("api")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    logger.propagate = False
    return logger