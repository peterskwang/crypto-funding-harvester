"""Central logging configuration for the strategy."""
import logging
from typing import Optional


_LOGGER_NAME = "crypto_funding_harvester"


def configure_logging(level: int = logging.INFO, handler: Optional[logging.Handler] = None) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    handler = handler or logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
