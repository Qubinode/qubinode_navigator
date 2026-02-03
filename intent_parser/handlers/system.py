"""
System status and info handlers.

Delegates to existing functions from airflow/scripts/mcp_server_fastmcp.py.
"""

import logging
from typing import Dict

from ..router import register
from ..models import IntentCategory

logger = logging.getLogger("intent-parser.handlers.system")

_backend_available = False
try:
    import sys
    import os

    _scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "airflow", "scripts")
    _scripts_dir = os.path.normpath(_scripts_dir)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)

    from mcp_server_fastmcp import (
        get_airflow_status as _get_airflow_status_tool,
        get_system_info as _get_system_info_tool,
    )

    def _unwrap(t):
        if callable(t):
            return t
        fn = getattr(t, "fn", None)
        if fn and callable(fn):
            return fn
        raise TypeError(f"Cannot unwrap {type(t)}")

    _get_airflow_status = _unwrap(_get_airflow_status_tool)
    _get_system_info = _unwrap(_get_system_info_tool)

    _backend_available = True
    logger.info("System backend functions loaded")
except ImportError as e:
    logger.warning(f"System backend not available: {e}")


def _unavailable_msg(operation: str) -> str:
    return f"Error: System {operation} is not available. The Airflow MCP backend could not be loaded."


async def handle_system_status(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("status")
    return await _get_airflow_status()


async def handle_system_info(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("info")
    return await _get_system_info()


register(IntentCategory.SYSTEM_STATUS, handle_system_status)
register(IntentCategory.SYSTEM_INFO, handle_system_info)
