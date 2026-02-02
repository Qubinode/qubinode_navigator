"""
Troubleshooting handlers.

Delegates to existing functions from airflow/scripts/mcp_server_fastmcp.py.
"""

import logging
from typing import Dict

from ..router import register
from ..models import IntentCategory

logger = logging.getLogger("intent-parser.handlers.troubleshoot")

_backend_available = False
try:
    import sys
    import os

    _scripts_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "airflow", "scripts"
    )
    _scripts_dir = os.path.normpath(_scripts_dir)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)

    from mcp_server_fastmcp import (
        diagnose_issue as _diagnose_issue,
        get_troubleshooting_history as _get_troubleshooting_history,
        log_troubleshooting_attempt as _log_troubleshooting_attempt,
    )

    _backend_available = True
    logger.info("Troubleshooting backend functions loaded")
except ImportError as e:
    logger.warning(f"Troubleshooting backend not available: {e}")


def _unavailable_msg(operation: str) -> str:
    return (
        f"Error: Troubleshooting {operation} is not available. "
        "The Airflow MCP backend could not be loaded."
    )


async def handle_diagnose(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("diagnose")
    symptom = params.get("symptom", params.get("query", "Unknown issue"))
    return await _diagnose_issue(
        symptom=symptom,
        component=params.get("component", "unknown"),
        error_message=params.get("error_message", ""),
        affected_resource=params.get("affected_resource", ""),
    )


async def handle_history(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("history")
    return await _get_troubleshooting_history(
        error_pattern=params.get("error_pattern"),
        component=params.get("component"),
        only_successful=params.get("only_successful", False),
        limit=params.get("limit", 10),
    )


async def handle_log(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("log")
    task = params.get("task")
    if not task:
        return "Error: Task description is required to log a troubleshooting attempt."
    solution = params.get("solution")
    if not solution:
        return "Error: Solution description is required."
    result = params.get("result")
    if result not in ("success", "failed", "partial"):
        return "Error: Result must be 'success', 'failed', or 'partial'."
    return await _log_troubleshooting_attempt(
        task=task,
        solution=solution,
        result=result,
        error_message=params.get("error_message"),
        component=params.get("component"),
        details=params.get("details"),
    )


register(IntentCategory.TROUBLESHOOT_DIAGNOSE, handle_diagnose)
register(IntentCategory.TROUBLESHOOT_HISTORY, handle_history)
register(IntentCategory.TROUBLESHOOT_LOG, handle_log)
