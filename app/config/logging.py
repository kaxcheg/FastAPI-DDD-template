import logging
import os
import json
from typing import Any
from logging.handlers import RotatingFileHandler
from app.config.config import settings

LOG_DIR = settings.LOG_DIR
os.makedirs(LOG_DIR, exist_ok=True)

class JsonFormatter(logging.Formatter):
    # Keys that must not appear in logs
    SENSITIVE_KEYS = {"username", "password", "token", "secret_key", "email"}

    def format(self, record: logging.LogRecord) -> str:
        # Build base log dict
        record_dict: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
        }

        # Process message: dict or string
        raw_msg = record.msg if isinstance(record.msg, dict) else record.getMessage()
        if isinstance(raw_msg, dict):
            filtered = {
                k: "[FILTERED]" if k.lower() in self.SENSITIVE_KEYS else v for k, v in raw_msg.items()
            }
            record_dict["message"] = filtered
        else:
            text = str(raw_msg)
            record_dict["message"] = text.splitlines() if "\n" in text else text

        # Exception trace, always as list of lines
        if record.exc_info:
            trace_str = super().formatException(record.exc_info)
            record_dict["trace"] = trace_str.splitlines()

        # Serialize to JSON and remove escaped quotes and slashes in values
        json_str = json.dumps(record_dict, indent=2, ensure_ascii=False)
        # Remove escaped quotes and backslashes
        json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
        return json_str


def setup_logger(name: str):
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # File handler: rotate and JSON format only
    log_path = os.path.join(LOG_DIR, f"{name}.log")
    if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == log_path for h in logger.handlers):
        file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
        file_handler.setLevel(logger.level)
        file_handler.setFormatter(JsonFormatter())
        logger.addHandler(file_handler)

    return logger
