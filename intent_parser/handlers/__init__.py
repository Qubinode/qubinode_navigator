"""
Intent handler registration.

Each handler module registers its functions with the router on import.
"""

import logging

from ..router import register
from ..models import IntentCategory

logger = logging.getLogger("intent-parser.handlers")


def register_all_handlers() -> None:
    """Import all handler modules to trigger registration."""
    from . import vm, dag, rag, system, troubleshoot, lineage  # noqa: F401

    logger.info("All intent handlers registered")
