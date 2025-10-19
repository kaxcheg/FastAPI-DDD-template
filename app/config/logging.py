from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from logging import StreamHandler
from pathlib import Path
from typing import Any, Final

from app.config import get_settings

class JsonFormatter(logging.Formatter):
    """Format log record as JSON string and mask sensitive fields."""

    SENSITIVE_KEYS: Final[set[str]] = {
        "username",
        "password",
        "token",
        "secret_key",
        "email",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Return JSON-formatted record."""
        data: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
        }

        raw_msg = record.msg if isinstance(record.msg, dict) else record.getMessage()
        if isinstance(raw_msg, dict):
            data["message"] = {
                k: "[FILTERED]" if k.lower() in self.SENSITIVE_KEYS else v
                for k, v in raw_msg.items()
            }
        else:
            data["message"] = str(raw_msg)

        if record.exc_info:
            data["trace"] = super().formatException(record.exc_info)

        return (
            json.dumps(data, ensure_ascii=False)
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )


class LevelFilter(logging.Filter):
    def __init__(self, min_level: int | None = None, max_level: int | None = None):
        super().__init__()
        self.min_level = min_level
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        if self.min_level is not None and record.levelno < self.min_level:
            return False
        if self.max_level is not None and record.levelno > self.max_level:
            return False
        return True


def get_logger(name: str) -> logging.Logger:
    """Return configured logger.

    Args:
        name: Logger name.

    Returns:
        logging.Logger: Ready-to-use logger.
    """
    logger = logging.getLogger(name)
    logger.propagate = False
    cfg = get_settings()
    logger.setLevel(logging.DEBUG if cfg.FASTAPI_DDD_TEMPLATE_DEBUG else logging.INFO)

    # Stdout handler: INFO and below
    if not any(
        isinstance(h, logging.StreamHandler)
        and getattr(h, "stream", None) is sys.stdout
        for h in logger.handlers
    ):
        sh_out = logging.StreamHandler(sys.stdout)
        sh_out.setLevel(logging.DEBUG)
        sh_out.addFilter(LevelFilter(max_level=logging.INFO))
        sh_out.setFormatter(JsonFormatter())
        logger.addHandler(sh_out)

    # Stderr handler: WARNING and above
    if not any(
        isinstance(h, logging.StreamHandler)
        and getattr(h, "stream", None) is sys.stderr
        for h in logger.handlers
    ):
        sh_err = logging.StreamHandler(sys.stderr)
        sh_err.setLevel(logging.WARNING)
        sh_err.addFilter(LevelFilter(min_level=logging.WARNING))
        sh_err.setFormatter(JsonFormatter())
        logger.addHandler(sh_err)

    return logger
