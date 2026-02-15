"""
SSH pre-flight checks with auto-fix for DAG triggers.

Validates the Airflow SSH connection (localhost_ssh) before triggering DAGs
that rely on SSHOperator. Checks connection existence, SSH user, key config,
and sshd reachability. Auto-fixes what it can, warns about the rest.

Results are cached to avoid repeated API calls on consecutive triggers.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("intent-parser.ssh-preflight")


class CheckStatus(str, Enum):
    OK = "ok"
    FIXED = "fixed"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class PreflightCheck:
    name: str
    status: CheckStatus
    message: str
    fix_applied: Optional[str] = None


@dataclass
class PreflightResult:
    checks: List[PreflightCheck] = field(default_factory=list)
    can_proceed: bool = True  # Always True — warn but never block
    summary: str = ""
    label: str = "SSH Pre-flight"

    def format_report(self) -> str:
        """Format checks into a human-readable report for prepending to trigger output."""
        if not self.checks:
            return ""

        # If everything is OK, keep it brief
        if all(c.status == CheckStatus.OK for c in self.checks):
            return f"[{self.label}] All checks passed."

        fixed = [c for c in self.checks if c.status == CheckStatus.FIXED]
        warnings = [c for c in self.checks if c.status == CheckStatus.WARNING]
        errors = [c for c in self.checks if c.status == CheckStatus.ERROR]

        parts = [f"[{self.label}]"]

        if fixed:
            fixes = "; ".join(c.fix_applied or c.message for c in fixed)
            parts.append(f"  Auto-fixed {len(fixed)} issue(s): {fixes}")

        if warnings:
            for w in warnings:
                parts.append(f"  WARNING: {w.message}")

        if errors:
            for e in errors:
                parts.append(f"  ERROR: {e.message}")

        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _get_config() -> Dict[str, str]:
    ssh_user = os.getenv("QUBINODE_SSH_USER", os.getenv("USER", "root"))
    ssh_key = os.getenv("QUBINODE_SSH_KEY_PATH", f"/home/{ssh_user}/.ssh/id_rsa")
    return {
        "api_url": os.getenv("AIRFLOW_API_URL", "http://localhost:8888"),
        "user": os.getenv("AIRFLOW_USER") or os.getenv("AIRFLOW_API_USER") or "admin",
        "password": os.getenv("AIRFLOW_PASSWORD") or os.getenv("AIRFLOW_API_PASSWORD") or "admin",
        "ssh_user": ssh_user,
        "ssh_key": ssh_key,
        "conn_id": os.getenv("QUBINODE_SSH_CONN_ID", "localhost_ssh"),
        "cache_ttl": int(os.getenv("SSH_PREFLIGHT_CACHE_TTL", "300")),
    }


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_cache: Dict[str, tuple] = {}  # {conn_id: (timestamp, PreflightResult)}


def clear_cache() -> None:
    """Clear the preflight cache (useful for testing)."""
    _cache.clear()


def _get_cached(conn_id: str, ttl: int) -> Optional[PreflightResult]:
    entry = _cache.get(conn_id)
    if entry is None:
        return None
    ts, result = entry
    if time.time() - ts > ttl:
        del _cache[conn_id]
        return None
    return result


def _set_cached(conn_id: str, result: PreflightResult) -> None:
    _cache[conn_id] = (time.time(), result)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

async def _check_connection_exists(
    client: Any, api_url: str, auth: tuple, conn_id: str, ssh_user: str,
    ssh_key: str = "",
) -> tuple:
    """Check if the SSH connection exists; create it if missing.

    Returns (PreflightCheck, conn_data_or_None).
    """
    key_file = ssh_key or f"/home/{ssh_user}/.ssh/id_rsa"
    try:
        resp = await client.get(
            f"{api_url}/api/v1/connections/{conn_id}",
            auth=auth,
        )
    except Exception as exc:
        return PreflightCheck(
            name="connection_exists",
            status=CheckStatus.ERROR,
            message=f"Cannot reach Airflow API: {exc}",
        ), None

    if resp.status_code == 200:
        conn_data = resp.json()
        return PreflightCheck(
            name="connection_exists",
            status=CheckStatus.OK,
            message=f"Connection '{conn_id}' exists.",
        ), conn_data

    if resp.status_code == 404:
        # Auto-create the connection
        new_conn = {
            "connection_id": conn_id,
            "conn_type": "ssh",
            "host": "localhost",
            "login": ssh_user,
            "port": 22,
            "extra": json.dumps({"key_file": key_file}),
        }
        try:
            create_resp = await client.post(
                f"{api_url}/api/v1/connections",
                json=new_conn,
                auth=auth,
            )
            if create_resp.status_code in (200, 201):
                return PreflightCheck(
                    name="connection_exists",
                    status=CheckStatus.FIXED,
                    message=f"Created missing connection '{conn_id}'.",
                    fix_applied=f"created connection '{conn_id}'",
                ), new_conn
            else:
                return PreflightCheck(
                    name="connection_exists",
                    status=CheckStatus.ERROR,
                    message=f"Failed to create connection: HTTP {create_resp.status_code}",
                ), None
        except Exception as exc:
            return PreflightCheck(
                name="connection_exists",
                status=CheckStatus.ERROR,
                message=f"Failed to create connection: {exc}",
            ), None

    return PreflightCheck(
        name="connection_exists",
        status=CheckStatus.ERROR,
        message=f"Unexpected API response: HTTP {resp.status_code}",
    ), None


async def _check_ssh_user(
    client: Any, api_url: str, auth: tuple, conn_id: str, conn_data: Dict, ssh_user: str
) -> PreflightCheck:
    """Check that the connection login matches the expected SSH user; patch if wrong."""
    current_login = conn_data.get("login", "")
    if current_login == ssh_user:
        return PreflightCheck(
            name="ssh_user",
            status=CheckStatus.OK,
            message=f"SSH user is '{ssh_user}'.",
        )

    # Auto-fix: PATCH the connection
    try:
        patch_resp = await client.patch(
            f"{api_url}/api/v1/connections/{conn_id}",
            json={"login": ssh_user},
            auth=auth,
        )
        if patch_resp.status_code == 200:
            return PreflightCheck(
                name="ssh_user",
                status=CheckStatus.FIXED,
                message=f"Updated SSH user from '{current_login}' to '{ssh_user}'.",
                fix_applied=f"updated SSH user to '{ssh_user}'",
            )
        return PreflightCheck(
            name="ssh_user",
            status=CheckStatus.WARNING,
            message=f"SSH user is '{current_login}' but expected '{ssh_user}'. "
                    f"PATCH failed with HTTP {patch_resp.status_code}.",
        )
    except Exception as exc:
        return PreflightCheck(
            name="ssh_user",
            status=CheckStatus.WARNING,
            message=f"SSH user is '{current_login}' but expected '{ssh_user}'. "
                    f"Auto-fix failed: {exc}",
        )


def _check_ssh_key(conn_data: Dict, expected_key: str = "") -> PreflightCheck:
    """Check if the connection has the correct SSH key file configured."""
    extra_raw = conn_data.get("extra", "{}")
    if isinstance(extra_raw, str):
        try:
            extra = json.loads(extra_raw)
        except (json.JSONDecodeError, TypeError):
            extra = {}
    else:
        extra = extra_raw

    key_file = extra.get("key_file", "")
    if not key_file:
        return PreflightCheck(
            name="ssh_key",
            status=CheckStatus.WARNING,
            message="No SSH key file configured in connection extras. "
                    "SSHOperator may rely on ssh-agent or password auth.",
        )
    if expected_key and key_file != expected_key:
        return PreflightCheck(
            name="ssh_key",
            status=CheckStatus.WARNING,
            message=f"SSH key mismatch: connection uses '{key_file}' "
                    f"but QUBINODE_SSH_KEY_PATH is '{expected_key}'.",
        )
    return PreflightCheck(
        name="ssh_key",
        status=CheckStatus.OK,
        message=f"SSH key configured: {key_file}",
    )


async def _check_sshd_reachable(
    client: Any, api_url: str, auth: tuple, conn_id: str
) -> PreflightCheck:
    """Check if sshd is reachable via the Airflow connection test API or TCP fallback."""
    # Try Airflow's connection test endpoint first
    try:
        resp = await client.post(
            f"{api_url}/api/v1/connections/test",
            json={"connection_id": conn_id},
            auth=auth,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status", False):
                return PreflightCheck(
                    name="sshd_reachable",
                    status=CheckStatus.OK,
                    message="sshd is reachable on localhost:22.",
                )
    except Exception:
        pass  # Fall through to TCP check

    # TCP fallback: try connecting to port 22 directly

    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection("localhost", 22),
            timeout=3.0,
        )
        writer.close()
        await writer.wait_closed()
        return PreflightCheck(
            name="sshd_reachable",
            status=CheckStatus.OK,
            message="sshd is reachable on localhost:22 (TCP check).",
        )
    except Exception:
        return PreflightCheck(
            name="sshd_reachable",
            status=CheckStatus.WARNING,
            message="Cannot reach sshd on localhost:22. "
                    "Ensure sshd is running: 'sudo systemctl start sshd'",
        )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_ssh_preflight(force: bool = False) -> PreflightResult:
    """Run SSH pre-flight checks, returning a PreflightResult.

    Results are cached for `SSH_PREFLIGHT_CACHE_TTL` seconds (default 300).
    Pass force=True to bypass cache.
    """
    cfg = _get_config()
    conn_id = cfg["conn_id"]

    if not force:
        cached = _get_cached(conn_id, cfg["cache_ttl"])
        if cached is not None:
            logger.debug("SSH preflight cache hit for %s", conn_id)
            return cached

    checks: List[PreflightCheck] = []
    auth = (cfg["user"], cfg["password"])

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Check 1: Connection exists
        conn_check, conn_data = await _check_connection_exists(
            client, cfg["api_url"], auth, conn_id, cfg["ssh_user"],
            ssh_key=cfg["ssh_key"],
        )
        checks.append(conn_check)

        if conn_data is not None:
            # Check 2: SSH user
            user_check = await _check_ssh_user(
                client, cfg["api_url"], auth, conn_id, conn_data, cfg["ssh_user"]
            )
            checks.append(user_check)

            # Check 3: SSH key
            key_check = _check_ssh_key(conn_data, expected_key=cfg["ssh_key"])
            checks.append(key_check)

        # Check 4: sshd reachable
        sshd_check = await _check_sshd_reachable(
            client, cfg["api_url"], auth, conn_id
        )
        checks.append(sshd_check)

    result = PreflightResult(checks=checks)
    result.summary = result.format_report()
    _set_cached(conn_id, result)
    return result
