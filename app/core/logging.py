import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_dir: str = "logs") -> None:
    Path(log_dir).mkdir(exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = RotatingFileHandler(Path(log_dir) / "app.log", maxBytes=5_000_000, backupCount=5)
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)

    # Avoid duplicate handlers
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
