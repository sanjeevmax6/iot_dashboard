import logging

from app.core.config import settings

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(levelname)s %(name)s %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
