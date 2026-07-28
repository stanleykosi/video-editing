"""Structured logging configuration used by the API, CLI, and workers."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload["context"] = context
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def configure_logging(level: str = "INFO", *, json_output: bool = False) -> None:
    handler = logging.StreamHandler()
    if json_output:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
