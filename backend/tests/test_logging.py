import logging
import logging.handlers
import tempfile
import unittest
from pathlib import Path

from backend.utils import logger as logger_module


class LoggingSetupTests(unittest.TestCase):
    def test_setup_logging_creates_daily_log_handlers_and_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger_module._configured = False
            logger_module._PROJECT_ROOT = str(tmp_path)
            logger_module.LOG_DIR = str(tmp_path / "logs")
            logger_module.APP_LOG_PATH = str(tmp_path / "logs" / "app.log")
            logger_module.ERROR_LOG_PATH = str(tmp_path / "logs" / "error.log")

            root_logger = logging.getLogger()
            for handler in list(root_logger.handlers):
                root_logger.removeHandler(handler)
                handler.close()

            logger_module.setup_logging(console_level=logging.INFO)

            file_handlers = [
                handler
                for handler in root_logger.handlers
                if isinstance(handler, logger_module.DailyFileHandler)
            ]

            self.assertTrue((tmp_path / "logs").exists())
            self.assertGreaterEqual(len(file_handlers), 1)
            self.assertTrue((tmp_path / "logs" / f"{logger_module.datetime.now().strftime('%Y-%m-%d')}.log").exists())

            for handler in list(root_logger.handlers):
                root_logger.removeHandler(handler)
                handler.close()


if __name__ == "__main__":
    unittest.main()
