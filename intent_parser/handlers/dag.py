"""
DAG operation handlers.

Delegates to existing functions from airflow/scripts/mcp_server_fastmcp.py.
"""

import logging
from typing import Dict

from ..router import register
from ..models import IntentCategory

logger = logging.getLogger("intent-parser.handlers.dag")

_backend_available = False
try:
    import sys
    import os

    _scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "airflow", "scripts")
    _scripts_dir = os.path.normpath(_scripts_dir)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)

    from mcp_server_fastmcp import (
        list_dags as _list_dags,
        get_dag_info as _get_dag_info,
        trigger_dag as _trigger_dag,
    )

    _backend_available = True
    logger.info("DAG backend functions loaded")
except ImportError as e:
    logger.warning(f"DAG backend not available: {e}")


def _unavailable_msg(operation: str) -> str:
    return f"Error: DAG {operation} is not available. The Airflow MCP backend could not be loaded."


async def handle_dag_list(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("list")
    return await _list_dags()


async def handle_dag_info(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("info")
    dag_id = params.get("dag_id")
    if not dag_id:
        return "Error: DAG ID is required. Try: 'dag info <dag_id>'"
    return await _get_dag_info(dag_id=dag_id)


async def handle_dag_trigger(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("trigger")
    dag_id = params.get("dag_id")
    if not dag_id:
        return "Error: DAG ID is required. Try: 'trigger dag <dag_id>'"
    return await _trigger_dag(dag_id=dag_id, conf=params.get("conf"))


register(IntentCategory.DAG_LIST, handle_dag_list)
register(IntentCategory.DAG_INFO, handle_dag_info)
register(IntentCategory.DAG_TRIGGER, handle_dag_trigger)
