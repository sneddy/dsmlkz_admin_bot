import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging():
    LOG_DIR = Path(__file__).parent.parent.parent / "logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    level = os.getenv("LOG_LEVEL", "INFO").upper()

    log_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_DIR / "bot.log", maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(log_formatter)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(log_formatter)

    # force=True makes sure Uvicorn/Aiogram reuse our handlers/level.
    logging.basicConfig(
        level=level, handlers=[file_handler, stdout_handler], force=True
    )

    # Align common libraries with our log level for consistent output.
    for noisy_logger in ("uvicorn", "uvicorn.error", "uvicorn.access", "aiogram"):
        logging.getLogger(noisy_logger).setLevel(level)
