"""Logging configuration for the application."""

import logging
import logging.config
from pythonjsonlogger import jsonlogger

from .settings import settings


def setup_logging():
    """Setup structured logging configuration."""
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": jsonlogger.JsonFormatter,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            },
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            }
        },
        "handlers": {
            "default": {
                "level": settings.log_level,
                "formatter": "json",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": settings.log_level,
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["default"],
                "level": settings.log_level,
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)
    return logging.getLogger(__name__)
