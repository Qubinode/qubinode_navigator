"""
DAG operation handlers.

Delegates to existing functions from airflow/scripts/mcp_server_fastmcp.py.
Falls back to Airflow REST API when running outside the Airflow container.
"""

import json
import logging
import os
from typing import Dict, Optional

from ..router import register
from ..models import IntentCategory

logger = logging.getLogger("intent-parser.handlers.dag")

_backend_available = False
try:
    import sys

    _scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "airflow", "scripts")
    _scripts_dir = os.path.normpath(_scripts_dir)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)

    from mcp_server_fastmcp import (
        list_dags as _list_dags_tool,
        get_dag_info as _get_dag_info_tool,
        trigger_dag as _trigger_dag_tool,
    )

    # MCP tools may be wrapped by @mcp.tool() as FunctionTool objects.
    # Extract the underlying async function if so.
    def _unwrap(tool_or_fn):
        if callable(tool_or_fn):
            return tool_or_fn
        fn = getattr(tool_or_fn, "fn", None)
        if fn and callable(fn):
            return fn
        raise TypeError(f"Cannot unwrap {type(tool_or_fn)}")

    _list_dags = _unwrap(_list_dags_tool)
    _get_dag_info = _unwrap(_get_dag_info_tool)
    _trigger_dag = _unwrap(_trigger_dag_tool)

    _backend_available = True
    logger.info("DAG backend functions loaded")
except ImportError as e:
    logger.warning(f"DAG backend not available: {e}")


# --- Airflow REST API fallback ---
# Used when the MCP backend returns "Airflow is not available"
# (i.e., running outside the Airflow container but with HTTP access)

_AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://localhost:8888")
_AIRFLOW_USER = os.getenv("AIRFLOW_USER") or os.getenv("AIRFLOW_API_USER") or "admin"
_AIRFLOW_PASS = os.getenv("AIRFLOW_PASSWORD") or os.getenv("AIRFLOW_API_PASSWORD") or "admin"


async def _http_list_dags() -> str:
    """List DAGs via Airflow REST API."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{_AIRFLOW_API_URL}/api/v1/dags",
                params={"limit": 50},
                auth=(_AIRFLOW_USER, _AIRFLOW_PASS),
            )
            if resp.status_code != 200:
                return f"Error: Airflow API returned {resp.status_code}"
            data = resp.json()
            dags = data.get("dags", [])
            if not dags:
                return "No DAGs found."
            lines = ["Available DAGs:\n"]
            for dag in dags:
                paused = " (paused)" if dag.get("is_paused") else ""
                lines.append(f"  - {dag['dag_id']}: {dag.get('description', 'No description')}{paused}")
            return "\n".join(lines)
    except Exception as e:
        return f"Error listing DAGs via API: {e}"


async def _http_get_dag_info(dag_id: str) -> str:
    """Get DAG info via Airflow REST API."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{_AIRFLOW_API_URL}/api/v1/dags/{dag_id}",
                auth=(_AIRFLOW_USER, _AIRFLOW_PASS),
            )
            if resp.status_code == 404:
                return f"Error: DAG '{dag_id}' not found"
            if resp.status_code != 200:
                return f"Error: Airflow API returned {resp.status_code}"
            dag = resp.json()
            return (
                f"DAG: {dag['dag_id']}\n"
                f"Description: {dag.get('description', 'None')}\n"
                f"Is Paused: {dag.get('is_paused', 'unknown')}\n"
                f"Schedule: {dag.get('schedule_interval', 'None')}\n"
                f"Tags: {', '.join(t.get('name', '') for t in dag.get('tags', []))}"
            )
    except Exception as e:
        return f"Error getting DAG info via API: {e}"


async def _http_trigger_dag(dag_id: str, conf: Optional[dict] = None) -> str:
    """Trigger a DAG via Airflow REST API."""
    import httpx

    try:
        body = {"conf": conf or {}}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{_AIRFLOW_API_URL}/api/v1/dags/{dag_id}/dagRuns",
                json=body,
                auth=(_AIRFLOW_USER, _AIRFLOW_PASS),
            )
            if resp.status_code == 404:
                return f"Error: DAG '{dag_id}' not found"
            if resp.status_code not in (200, 201):
                return f"Error: Airflow API returned {resp.status_code}: {resp.text}"
            data = resp.json()
            run_id = data.get("dag_run_id", "unknown")
            return f"Successfully triggered DAG '{dag_id}'\nRun ID: {run_id}\nConf: {json.dumps(conf or {})}"
    except Exception as e:
        return f"Error triggering DAG via API: {e}"


def _unavailable_msg(operation: str) -> str:
    return f"Error: DAG {operation} is not available. The Airflow MCP backend could not be loaded."


async def _call_with_http_fallback(mcp_fn, http_fn, *args, **kwargs) -> str:
    """Call MCP backend function, fall back to HTTP API if Airflow unavailable."""
    if _backend_available:
        result = await mcp_fn(*args, **kwargs)
        if isinstance(result, str) and "Airflow is not available" in result:
            logger.info("Airflow Python API unavailable, falling back to REST API")
            return await http_fn(*args, **kwargs)
        return result
    return await http_fn(*args, **kwargs)


async def handle_dag_list(params: Dict) -> str:
    return await _call_with_http_fallback(_list_dags if _backend_available else (lambda: ""), _http_list_dags)


async def handle_dag_info(params: Dict) -> str:
    dag_id = params.get("dag_id")
    if not dag_id:
        return "Error: DAG ID is required. Try: 'dag info <dag_id>'"
    return await _call_with_http_fallback(
        (lambda dag_id: _get_dag_info(dag_id=dag_id)) if _backend_available else (lambda dag_id: ""),
        _http_get_dag_info,
        dag_id,
    )


async def handle_dag_trigger(params: Dict) -> str:
    dag_id = params.get("dag_id")
    if not dag_id:
        return "Error: DAG ID is required. Try: 'trigger dag <dag_id>'"

    # Run SSH pre-flight checks with auto-fix
    from ..ssh_preflight import run_ssh_preflight

    preflight = await run_ssh_preflight()
    preflight_report = preflight.format_report()

    # VM SSH pre-flight (second hop)
    from ..vm_ssh_preflight import get_vm_for_dag, run_vm_ssh_preflight

    conf = params.get("conf")
    vm_preflight_report = ""
    vm_info = get_vm_for_dag(dag_id, conf)
    if vm_info:
        vm_name, ssh_user = vm_info
        vm_preflight = await run_vm_ssh_preflight(vm_name, ssh_user)
        vm_preflight_report = vm_preflight.format_report()

    trigger_result = await _call_with_http_fallback(
        (lambda dag_id, conf: _trigger_dag(dag_id=dag_id, conf=conf)) if _backend_available else (lambda dag_id, conf: ""),
        _http_trigger_dag,
        dag_id,
        conf,
    )

    reports = [r for r in [preflight_report, vm_preflight_report] if r]
    if reports:
        return "\n\n".join(reports) + f"\n\n{trigger_result}"
    return trigger_result


register(IntentCategory.DAG_LIST, handle_dag_list)
register(IntentCategory.DAG_INFO, handle_dag_info)
register(IntentCategory.DAG_TRIGGER, handle_dag_trigger)
