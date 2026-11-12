
import logging
import os

from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler


# Pakistan Standard Time (UTC+5)
PKT = timezone(timedelta(hours=5))


class PakistanTimeFormatter(logging.Formatter):

    def formatTime(self, record, datefmt=None):
        timestamp = datetime.fromtimestamp(
            record.created,
            tz=PKT
        )

        if datefmt:
            return timestamp.strftime(datefmt)

        return timestamp.isoformat()


def setup_logging():

    # Find project root directory
    project_root = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )

    # Create logs directory
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Log file
    log_file = os.path.join(logs_dir, "app.log")

    # Log format
    log_format = (
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    )

    formatter = PakistanTimeFormatter(
        fmt=log_format,
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Prevent duplicate handlers on repeated setup
    if getattr(root_logger, "_rag_logging_configured", False):
        return

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Rotating file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )

    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    root_logger._rag_logging_configured = True

    root_logger.info("Logging system initialized.")
    root_logger.info("Log file: %s", log_file)
