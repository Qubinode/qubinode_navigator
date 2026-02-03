"""
Lineage query handlers.

Delegates to existing functions from airflow/scripts/mcp_server_fastmcp.py.
"""

import logging
from typing import Dict

from ..router import register
from ..models import IntentCategory

logger = logging.getLogger("intent-parser.handlers.lineage")

_backend_available = False
try:
    import sys
    import os

    _scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "airflow", "scripts")
    _scripts_dir = os.path.normpath(_scripts_dir)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)

    from mcp_server_fastmcp import (
        get_dag_lineage as _get_dag_lineage_tool,
        get_failure_blast_radius as _get_failure_blast_radius_tool,
    )

    def _unwrap(t):
        if callable(t):
            return t
        fn = getattr(t, "fn", None)
        if fn and callable(fn):
            return fn
        raise TypeError(f"Cannot unwrap {type(t)}")

    _get_dag_lineage = _unwrap(_get_dag_lineage_tool)
    _get_failure_blast_radius = _unwrap(_get_failure_blast_radius_tool)

    _backend_available = True
    logger.info("Lineage backend functions loaded")
except ImportError as e:
    logger.warning(f"Lineage backend not available: {e}")


def _unavailable_msg(operation: str) -> str:
    return f"Error: Lineage {operation} is not available. The Airflow MCP backend could not be loaded."


async def handle_lineage_dag(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("query")
    dag_id = params.get("dag_id")
    if not dag_id:
        return "Error: DAG ID is required. Try: 'lineage for dag <dag_id>'"
    return await _get_dag_lineage(
        dag_id=dag_id,
        depth=params.get("depth", 5),
    )


async def handle_blast_radius(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("blast radius")
    dag_id = params.get("dag_id")
    if not dag_id:
        return "Error: DAG ID is required. Try: 'blast radius for dag <dag_id>'"
    return await _get_failure_blast_radius(
        dag_id=dag_id,
        task_id=params.get("task_id"),
    )


register(IntentCategory.LINEAGE_DAG, handle_lineage_dag)
register(IntentCategory.LINEAGE_BLAST_RADIUS, handle_blast_radius)
