from __future__ import annotations

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Final

from app.config import get_settings

_logger_configured = False

def configure_logging() -> None:
    """Idempotent logging setup (call early in bootstrap)."""
    global _logger_configured
    if _logger_configured:
        return
    cfg = get_settings()
    log_dir = Path(cfg.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    _logger_configured = True

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

        return json.dumps(data, ensure_ascii=False).replace('\\"', '"').replace('\\\\', '\\')


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
    logger.setLevel(logging.DEBUG if cfg.DEBUG else logging.INFO)

    # File handler — one per logger.
    log_path = os.path.join(cfg.LOG_DIR, f"{name}.log")
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    if not any(
        isinstance(h, RotatingFileHandler) and h.baseFilename == log_path
        for h in logger.handlers
    ):
        handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
        handler.setLevel(logger.level)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger
