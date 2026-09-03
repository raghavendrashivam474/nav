"""NAV logging foundation.

Provides centralized logging configuration for all NAV components.
Uses Python standard library logging module exclusively.
"""

import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a configured logger for a NAV component.

    Args:
        name: Logger name, typically `__name__` of the calling module.
        level: Logging level (default: `logging.INFO`).

    Returns:
        Configured `logging.Logger` instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level)
    return logger
