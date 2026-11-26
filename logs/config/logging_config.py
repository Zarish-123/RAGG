
import logging
import os

from collections import deque
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler


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


class InMemoryLogHandler(logging.Handler):

    def __init__(self, max_records=5000):

        super().__init__(logging.DEBUG)

        self.records = deque(maxlen=max_records)

    def emit(self, record):

        try:

            log_entry = {
                "level": record.levelname,
                "message": self.format(record),
                "created": record.created
            }

            self.acquire()

            try:
                self.records.append(log_entry)

            finally:
                self.release()

        except Exception:
            self.handleError(record)

    def get_records(self, level="ALL", limit=200):

        self.acquire()

        try:
            records = list(self.records)

        finally:
            self.release()

        if level != "ALL":

            records = [
                record
                for record in records
                if record["level"] == level
            ]

        return [
            record["message"]
            for record in records[-limit:]
        ]


memory_handler = InMemoryLogHandler(
    max_records=5000
)


def get_recent_logs(level="ALL", limit=200):

    return memory_handler.get_records(
        level=level,
        limit=limit
    )


def setup_logging():

    project_root = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )

    logs_dir = os.path.join(
        project_root,
        "logs"
    )

    os.makedirs(
        logs_dir,
        exist_ok=True
    )

    log_file = os.path.join(
        logs_dir,
        "app.log"
    )

    log_format = (
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    )

    formatter = PakistanTimeFormatter(
        fmt=log_format,
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    root_logger = logging.getLogger()

    root_logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers during reload.
    if getattr(
        root_logger,
        "_rag_logging_configured",
        False
    ):
        return

    # Console handler: INFO and above.
    console_handler = logging.StreamHandler()

    console_handler.setLevel(logging.INFO)

    console_handler.setFormatter(formatter)

    # Rotating file handler: DEBUG and above.
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )

    file_handler.setLevel(logging.DEBUG)

    file_handler.setFormatter(formatter)

    # In-memory handler: DEBUG and above.
    memory_handler.setLevel(logging.DEBUG)

    memory_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)

    root_logger.addHandler(file_handler)

    root_logger.addHandler(memory_handler)

    root_logger._rag_logging_configured = True

    root_logger.info(
        "Logging system initialized."
    )

    root_logger.info(
        "Log file: %s",
        log_file
    )
