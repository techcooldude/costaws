import json
import logging
import os
from logging import Logger

from app.config import settings


def setup_logging():
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(level=level)


def get_logger(name: str) -> Logger:
    return logging.getLogger(name)
