"""
VM SSH pre-flight checks (second-hop validation) with auto-fix.

Validates that the host can SSH into target VMs before triggering DAGs
that execute commands on those VMs. The AI assistant container cannot
reach VMs directly, so all checks are proxied through the MCP server's
``/api/check-vm-ssh/{vm_name}`` endpoint (port 8889).

Results are cached to avoid repeated HTTP calls on consecutive triggers.
Never blocks — can_proceed=True always.
"""

import logging
import os
import time
from typing import Dict, Optional, Tuple

import httpx

from .ssh_preflight import CheckStatus, PreflightCheck, PreflightResult

logger = logging.getLogger("intent-parser.vm-ssh-preflight")


# ---------------------------------------------------------------------------
# DAG-to-VM registry
# ---------------------------------------------------------------------------

_DAG_VM_MAP: Dict[str, Tuple[str, str]] = {
    "freeipa_deployment": ("freeipa", "cloud-user"),
    "vyos_router_deployment": ("vyos-router", "vyos"),
    "harbor_deployment": ("harbor", "cloud-user"),
    "step_ca_deployment": ("step-ca", "cloud-user"),
    "jumpserver_deployment": ("jumpserver", "cloud-user"),
    "mirror_registry_deployment": ("mirror-registry", "cloud-user"),
}


def get_vm_for_dag(dag_id: str, conf: Optional[Dict] = None) -> Optional[Tuple[str, str]]:
    """Return ``(vm_name, ssh_user)`` for a DAG, or ``None`` to skip.

    Checks ``conf["vm_name"]`` first (user override), then the static map.
    """
    if conf and conf.get("vm_name"):
        vm_name = conf["vm_name"]
        ssh_user = conf.get("ssh_user", "cloud-user")
        return (vm_name, ssh_user)

    entry = _DAG_VM_MAP.get(dag_id)
    return entry  # None if not in map


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def _get_config() -> Dict[str, str]:
    mcp_url = os.getenv("MCP_SERVER_URL", "")
    if not mcp_url:
        # Fall back to QUBINODE_MCP_URL (may end with /sse); strip SSE path
        mcp_url = os.getenv("QUBINODE_MCP_URL", "http://localhost:8889")
        mcp_url = mcp_url.rstrip("/").removesuffix("/sse")
    return {
        "mcp_url": mcp_url,
        "cache_ttl": int(os.getenv("VM_SSH_PREFLIGHT_CACHE_TTL", "120")),
    }


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_cache: Dict[str, tuple] = {}  # {vm_name: (timestamp, PreflightResult)}


def clear_cache() -> None:
    """Clear the preflight cache (useful for testing)."""
    _cache.clear()


def _get_cached(vm_name: str, ttl: int) -> Optional[PreflightResult]:
    entry = _cache.get(vm_name)
    if entry is None:
        return None
    ts, result = entry
    if time.time() - ts > ttl:
        del _cache[vm_name]
        return None
    return result


def _set_cached(vm_name: str, result: PreflightResult) -> None:
    _cache[vm_name] = (time.time(), result)


# ---------------------------------------------------------------------------
# Status-to-check mapping
# ---------------------------------------------------------------------------

_STATUS_MAP = {
    "no_vm": lambda data: PreflightCheck(
        name="vm_exists",
        status=CheckStatus.OK,
        message=f"VM '{data.get('vm', '?')}' does not exist yet — will be created by DAG.",
    ),
    "no_ip": lambda data: PreflightCheck(
        name="vm_ip",
        status=CheckStatus.WARNING,
        message=f"VM '{data.get('vm', '?')}' has no IP assigned. " "It may still be booting — the DAG will retry.",
    ),
    "port_closed": lambda data: PreflightCheck(
        name="vm_ssh_port",
        status=CheckStatus.WARNING,
        message=f"VM '{data.get('vm', '?')}' ({data.get('ip', '?')}): SSH port 22 is closed. " "sshd may not be running yet.",
    ),
    "ok": lambda data: PreflightCheck(
        name="vm_ssh_auth",
        status=CheckStatus.OK,
        message=f"VM '{data.get('vm', '?')}' ({data.get('ip', '?')}): SSH OK.",
    ),
    "fixed": lambda data: PreflightCheck(
        name="vm_ssh_auth",
        status=CheckStatus.FIXED,
        message=f"VM '{data.get('vm', '?')}' ({data.get('ip', '?')}): SSH key was missing.",
        fix_applied=data.get("fix", "injected host public key"),
    ),
    "auth_failed": lambda data: PreflightCheck(
        name="vm_ssh_auth",
        status=CheckStatus.WARNING,
        message=f"VM '{data.get('vm', '?')}' ({data.get('ip', '?')}): SSH auth failed "
        f"after auto-fix attempt. {data.get('error', '')}. "
        "Check that the correct SSH key pair is in /root/.ssh/ on the host.",
    ),
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def run_vm_ssh_preflight(
    vm_name: str,
    ssh_user: str = "cloud-user",
    force: bool = False,
) -> PreflightResult:
    """Run VM SSH second-hop pre-flight via the MCP server endpoint.

    Results are cached for ``VM_SSH_PREFLIGHT_CACHE_TTL`` seconds (default 120).
    Pass ``force=True`` to bypass cache.
    """
    cfg = _get_config()

    if not force:
        cached = _get_cached(vm_name, cfg["cache_ttl"])
        if cached is not None:
            logger.debug("VM SSH preflight cache hit for %s", vm_name)
            return cached

    checks = []
    mcp_url = cfg["mcp_url"]

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{mcp_url}/api/check-vm-ssh/{vm_name}",
                params={"ssh_user": ssh_user},
            )
            data = resp.json()
    except Exception as exc:
        logger.warning("MCP server unreachable for VM SSH check: %s", exc)
        checks.append(
            PreflightCheck(
                name="mcp_reachable",
                status=CheckStatus.WARNING,
                message=f"MCP server unreachable ({exc}). Skipping VM SSH pre-flight.",
            )
        )
        result = PreflightResult(checks=checks, label="VM SSH Pre-flight")
        result.summary = result.format_report()
        return result

    status = data.get("status", "unknown")
    handler = _STATUS_MAP.get(status)
    if handler:
        checks.append(handler(data))
    else:
        checks.append(
            PreflightCheck(
                name="vm_ssh_unknown",
                status=CheckStatus.WARNING,
                message=f"Unexpected VM SSH check status: {status}",
            )
        )

    result = PreflightResult(checks=checks, label="VM SSH Pre-flight")
    result.summary = result.format_report()
    _set_cached(vm_name, result)
    return result
