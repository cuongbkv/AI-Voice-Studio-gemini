"""
logs.py
=======
Application-wide logging setup.

Provides:
    - `setup_logging()`: configures the root "AI Voice Studio" logger to also
      write to a rotating file under LOG_DIR.
    - `UILogHandler`: a logging.Handler that forwards each record to a
      callback (e.g. a CTkTextbox in the Dashboard page) so the UI can show
      realtime colored logs without polling.

No module should call `print()` for anything user-facing; use
`logging.getLogger("AI Voice Studio")` instead.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Callable, Optional

from config import LOG_DIR, APP_NAME

# Colors used by the Dashboard log panel (CTkTextbox tag foreground colors)
LEVEL_COLORS: dict[str, str] = {
    "DEBUG": "#9E9E9E",
    "INFO": "#4FC3F7",
    "SUCCESS": "#66BB6A",
    "WARNING": "#FFA726",
    "ERROR": "#EF5350",
}

# Custom SUCCESS level, between INFO and WARNING
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


def _success(self: logging.Logger, message: str, *args, **kwargs) -> None:
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, message, args, **kwargs)


logging.Logger.success = _success  # type: ignore[attr-defined]


class UILogHandler(logging.Handler):
    """Forwards log records to a UI callback: callback(level_name, message)."""

    def __init__(self, callback: Callable[[str, str], None]) -> None:
        super().__init__()
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            self._callback(record.levelname, message)
        except Exception:  # noqa: BLE001 - logging handlers must never raise
            self.handleError(record)


def setup_logging(ui_callback: Optional[Callable[[str, str], None]] = None) -> logging.Logger:
    """Configure and return the application logger.

    Args:
        ui_callback: Optional function(level_name, message) to also stream
            log lines into the UI (Dashboard log panel).
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    if ui_callback is not None:
        ui_handler = UILogHandler(ui_callback)
        ui_handler.setFormatter(formatter)
        ui_handler.setLevel(logging.DEBUG)
        logger.addHandler(ui_handler)

    return logger
