"""
VM operation handlers.

Delegates to existing functions from airflow/scripts/mcp_server_fastmcp.py.
"""

import logging
from typing import Dict

from ..router import register
from ..models import IntentCategory

logger = logging.getLogger("intent-parser.handlers.vm")

# Try to import backend functions
_backend_available = False
try:
    import sys
    import os

    # Add airflow scripts to path if not already there
    _scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "airflow", "scripts")
    _scripts_dir = os.path.normpath(_scripts_dir)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)

    from mcp_server_fastmcp import (
        list_vms as _list_vms_tool,
        get_vm_info as _get_vm_info_tool,
        create_vm as _create_vm_tool,
        delete_vm as _delete_vm_tool,
        preflight_vm_creation as _preflight_vm_creation_tool,
    )

    def _unwrap(t):
        if callable(t):
            return t
        fn = getattr(t, "fn", None)
        if fn and callable(fn):
            return fn
        raise TypeError(f"Cannot unwrap {type(t)}")

    _list_vms = _unwrap(_list_vms_tool)
    _get_vm_info = _unwrap(_get_vm_info_tool)
    _create_vm = _unwrap(_create_vm_tool)
    _delete_vm = _unwrap(_delete_vm_tool)
    _preflight_vm_creation = _unwrap(_preflight_vm_creation_tool)

    _backend_available = True
    logger.info("VM backend functions loaded")
except ImportError as e:
    logger.warning(f"VM backend not available: {e}")


def _unavailable_msg(operation: str) -> str:
    return f"Error: VM {operation} is not available. The Airflow MCP backend could not be loaded."


async def handle_vm_list(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("list")
    return await _list_vms()


async def handle_vm_info(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("info")
    name = params.get("name")
    if not name:
        return "Error: VM name is required. Try: 'vm info <name>'"
    return await _get_vm_info(vm_name=name)


async def handle_vm_create(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("create")
    name = params.get("name")
    if not name:
        return "Error: VM name is required. Try: 'create vm named <name>'"
    return await _create_vm(
        name=name,
        image=params.get("image", "centos10stream"),
        memory=params.get("memory", 2048),
        cpus=params.get("cpus", 2),
        disk_size=params.get("disk_size", 10),
    )


async def handle_vm_delete(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("delete")
    name = params.get("name")
    if not name:
        return "Error: VM name is required. Try: 'delete vm <name>'"
    return await _delete_vm(name=name)


async def handle_vm_preflight(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("preflight")
    name = params.get("name", "check")
    return await _preflight_vm_creation(
        name=name,
        image=params.get("image", "centos10stream"),
        memory=params.get("memory", 2048),
        cpus=params.get("cpus", 2),
        disk_size=params.get("disk_size", 10),
    )


# Register handlers
register(IntentCategory.VM_LIST, handle_vm_list)
register(IntentCategory.VM_INFO, handle_vm_info)
register(IntentCategory.VM_CREATE, handle_vm_create)
register(IntentCategory.VM_DELETE, handle_vm_delete)
register(IntentCategory.VM_PREFLIGHT, handle_vm_preflight)
