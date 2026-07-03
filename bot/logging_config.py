"""
Centralized logging configuration for the trading bot.

Logs go to both the console (human-friendly, INFO+) and a rotating
log file (detailed, DEBUG+) so every API request/response/error is
captured for audit purposes without flooding the terminal.
"""

import logging
import logging.handlers
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure and return the application's root logger.

    - Console handler: INFO and above (or DEBUG if verbose=True), concise.
    - File handler: DEBUG and above, rotating (1MB x 5 backups), full detail.

    Safe to call multiple times (won't duplicate handlers).
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if setup_logging() is called more than once
    if logger.handlers:
        return logger

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger
