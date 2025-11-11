import logging
import sys
from datetime import datetime

class AppLogger:
    _logger = None  # Singleton pattern

    @staticmethod
    def get_logger(name: str = "App"):
        if AppLogger._logger:
            return AppLogger._logger

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)  # luôn ở chế độ debug

        # Handler xuất ra console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        # Format log có màu sắc
        formatter = logging.Formatter(
            "\033[94m[%(asctime)s]\033[0m "
            "\033[92m[%(levelname)s]\033[0m "
            "\033[96m[%(name)s]\033[0m: "
            "%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        logger.propagate = False
        AppLogger._logger = logger
        return logger
