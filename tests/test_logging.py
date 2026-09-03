"""Tests for NAV logging foundation."""

import logging
import unittest

from core.log import get_logger


class TestLoggingFoundation(unittest.TestCase):
    """Verify the basic logging mechanism works."""

    def test_get_logger_returns_logger(self) -> None:
        logger = get_logger("test.component")
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test.component")

    def test_get_logger_default_level(self) -> None:
        logger = get_logger("test.level_default")
        self.assertEqual(logger.level, logging.INFO)

    def test_get_logger_custom_level(self) -> None:
        logger = get_logger("test.level_debug", level=logging.DEBUG)
        self.assertEqual(logger.level, logging.DEBUG)

    def test_get_logger_has_handler(self) -> None:
        logger = get_logger("test.handler_check")
        self.assertGreater(len(logger.handlers), 0)


if __name__ == "__main__":
    unittest.main()
