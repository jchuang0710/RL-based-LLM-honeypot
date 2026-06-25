"""Application logging configuration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.shared.paths import LOGS_DIR, ensure_runtime_directories


DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(
    *,
    level: int | str = logging.INFO,
    log_file: str | Path = "application.log",
) -> None:
    """Configure console and rotating-file logging once per process."""
    ensure_runtime_directories()
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if any(getattr(handler, "_honeypot_handler", False) for handler in root_logger.handlers):
        return

    formatter = logging.Formatter(DEFAULT_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler._honeypot_handler = True

    file_path = Path(log_file)
    if not file_path.is_absolute():
        file_path = LOGS_DIR / file_path
    file_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler._honeypot_handler = True

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
