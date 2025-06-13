"""Configuration package for weather API service."""

from .settings import settings
from .logging import setup_logging

__all__ = ["settings", "setup_logging"]
