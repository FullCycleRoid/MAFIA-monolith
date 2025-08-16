import logging
import os

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    if not logger.handlers:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
