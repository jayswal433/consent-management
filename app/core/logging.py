import logging


class _ShortNameFormatter(logging.Formatter):
    """Abbreviate logger names to the last two segments for readability."""

    def format(self, record: logging.LogRecord) -> str:
        parts = record.name.split(".")
        record.shortname = ".".join(parts[-2:]) if len(parts) > 1 else record.name
        return super().format(record)


def setup_logging(level: str = "INFO") -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = _ShortNameFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(shortname)-35s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)
    else:
        for h in root.handlers:
            h.setFormatter(formatter)
    root.setLevel(log_level)

    # Give uvicorn loggers their own handlers (propagate=False avoids duplicates).
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        if not uv_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            uv_logger.addHandler(handler)
        else:
            for h in uv_logger.handlers:
                h.setFormatter(formatter)
        uv_logger.setLevel(log_level)
        uv_logger.propagate = False

    # Suppress noisy SQLAlchemy pool chatter unless DEBUG.
    sa_level = logging.DEBUG if log_level == logging.DEBUG else logging.WARNING
    logging.getLogger("sqlalchemy.engine").setLevel(sa_level)
    logging.getLogger("sqlalchemy.pool").setLevel(sa_level)
    logging.getLogger("aiomysql").setLevel(logging.WARNING)
