import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import LOG_DIR, LOG_FILE


os.makedirs(LOG_DIR, exist_ok=True)
logger = logging.getLogger("repo_summarizer")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(file_handler)
