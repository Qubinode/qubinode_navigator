"""
Tests for the VM SSH pre-flight checks module (second-hop validation).

Uses mocked httpx responses to simulate MCP server replies.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from intent_parser.ssh_preflight import CheckStatus
from intent_parser.vm_ssh_preflight import (
    clear_cache,
    get_vm_for_dag,
    run_vm_ssh_preflight,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int = 200, json_data: dict = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


def _patch_httpx(response):
    """Patch httpx.AsyncClient to return a preset response on GET."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return patch(
        "intent_parser.vm_ssh_preflight.httpx.AsyncClient",
        return_value=mock_ctx,
    ), client


def _patch_httpx_error(exc):
    """Patch httpx.AsyncClient.get to raise an exception."""
    client = AsyncMock()
    client.get = AsyncMock(side_effect=exc)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return patch(
        "intent_parser.vm_ssh_preflight.httpx.AsyncClient",
        return_value=mock_ctx,
    ), client


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure cache is clean before and after each test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture(autouse=True)
def _env_defaults(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_URL", "http://mcp:8889")
    monkeypatch.setenv("VM_SSH_PREFLIGHT_CACHE_TTL", "120")


# ---------------------------------------------------------------------------
# get_vm_for_dag tests
# ---------------------------------------------------------------------------

class TestGetVmForDag:
    def test_known_dag(self):
        result = get_vm_for_dag("freeipa_deployment")
        assert result == ("freeipa", "cloud-user")

    def test_known_dag_vyos(self):
        result = get_vm_for_dag("vyos_router_deployment")
        assert result == ("vyos-router", "vyos")

    def test_unknown_dag(self):
        result = get_vm_for_dag("some_random_dag")
        assert result is None

    def test_conf_override_vm_name(self):
        result = get_vm_for_dag("freeipa_deployment", conf={"vm_name": "custom-vm"})
        assert result is not None
        vm_name, ssh_user = result
        assert vm_name == "custom-vm"
        assert ssh_user == "cloud-user"

    def test_conf_override_vm_and_user(self):
        result = get_vm_for_dag(
            "freeipa_deployment",
            conf={"vm_name": "custom-vm", "ssh_user": "admin"},
        )
        assert result == ("custom-vm", "admin")

    def test_conf_none(self):
        result = get_vm_for_dag("freeipa_deployment", conf=None)
        assert result == ("freeipa", "cloud-user")

    def test_conf_empty_vm_name(self):
        """Empty vm_name in conf should fall back to static map."""
        result = get_vm_for_dag("freeipa_deployment", conf={"vm_name": ""})
        assert result == ("freeipa", "cloud-user")


# ---------------------------------------------------------------------------
# run_vm_ssh_preflight tests
# ---------------------------------------------------------------------------

class TestRunVmSshPreflight:

    @pytest.mark.asyncio
    async def test_status_no_vm(self):
        resp = _mock_response(json_data={"status": "no_vm", "vm": "freeipa"})
        patcher, client = _patch_httpx(resp)
        with patcher:
            result = await run_vm_ssh_preflight("freeipa")

        assert len(result.checks) == 1
        assert result.checks[0].status == CheckStatus.OK
        assert "does not exist yet" in result.checks[0].message
        assert result.can_proceed is True

    @pytest.mark.asyncio
    async def test_status_ok(self):
        resp = _mock_response(json_data={
            "status": "ok", "vm": "freeipa", "ip": "192.168.122.10",
        })
        patcher, client = _patch_httpx(resp)
        with patcher:
            result = await run_vm_ssh_preflight("freeipa")

        assert len(result.checks) == 1
        assert result.checks[0].status == CheckStatus.OK
        assert "SSH OK" in result.checks[0].message

    @pytest.mark.asyncio
    async def test_status_no_ip(self):
        resp = _mock_response(json_data={"status": "no_ip", "vm": "freeipa"})
        patcher, client = _patch_httpx(resp)
        with patcher:
            result = await run_vm_ssh_preflight("freeipa")

        assert result.checks[0].status == CheckStatus.WARNING
        assert "no IP" in result.checks[0].message

    @pytest.mark.asyncio
    async def test_status_port_closed(self):
        resp = _mock_response(json_data={
            "status": "port_closed", "vm": "freeipa", "ip": "192.168.122.10",
        })
        patcher, client = _patch_httpx(resp)
        with patcher:
            result = await run_vm_ssh_preflight("freeipa")

        assert result.checks[0].status == CheckStatus.WARNING
        assert "port 22 is closed" in result.checks[0].message

    @pytest.mark.asyncio
    async def test_status_auth_failed(self):
        resp = _mock_response(json_data={
            "status": "auth_failed",
            "vm": "freeipa",
            "ip": "192.168.122.10",
            "error": "Permission denied (publickey)",
        })
        patcher, client = _patch_httpx(resp)
        with patcher:
            result = await run_vm_ssh_preflight("freeipa")

        assert result.checks[0].status == CheckStatus.WARNING
        assert "auth failed" in result.checks[0].message
        assert "Permission denied" in result.checks[0].message

    @pytest.mark.asyncio
    async def test_status_fixed(self):
        resp = _mock_response(json_data={
            "status": "fixed",
            "vm": "freeipa",
            "ip": "192.168.122.10",
            "fix": "injected host public key",
        })
        patcher, client = _patch_httpx(resp)
        with patcher:
            result = await run_vm_ssh_preflight("freeipa")

        assert result.checks[0].status == CheckStatus.FIXED
        assert result.checks[0].fix_applied == "injected host public key"

    @pytest.mark.asyncio
    async def test_mcp_unreachable(self):
        import httpx as httpx_mod

        patcher, client = _patch_httpx_error(
            httpx_mod.ConnectError("Connection refused")
        )
        with patcher:
            result = await run_vm_ssh_preflight("freeipa")

        assert len(result.checks) == 1
        assert result.checks[0].status == CheckStatus.WARNING
        assert "MCP server unreachable" in result.checks[0].message
        assert result.can_proceed is True

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        resp = _mock_response(json_data={
            "status": "ok", "vm": "freeipa", "ip": "192.168.122.10",
        })
        patcher, client = _patch_httpx(resp)
        with patcher:
            result1 = await run_vm_ssh_preflight("freeipa")
            result2 = await run_vm_ssh_preflight("freeipa")

        # Should only call MCP once
        assert client.get.call_count == 1
        assert result2.checks[0].status == CheckStatus.OK

    @pytest.mark.asyncio
    async def test_cache_expiry(self, monkeypatch):
        monkeypatch.setenv("VM_SSH_PREFLIGHT_CACHE_TTL", "1")

        resp = _mock_response(json_data={
            "status": "ok", "vm": "freeipa", "ip": "192.168.122.10",
        })
        patcher, client = _patch_httpx(resp)
        with patcher:
            await run_vm_ssh_preflight("freeipa")
            # Expire the cache
            time.sleep(1.1)
            await run_vm_ssh_preflight("freeipa")

        assert client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_force_bypasses_cache(self):
        resp = _mock_response(json_data={
            "status": "ok", "vm": "freeipa", "ip": "192.168.122.10",
        })
        patcher, client = _patch_httpx(resp)
        with patcher:
            await run_vm_ssh_preflight("freeipa")
            await run_vm_ssh_preflight("freeipa", force=True)

        assert client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_report_format_all_ok(self):
        resp = _mock_response(json_data={
            "status": "ok", "vm": "freeipa", "ip": "192.168.122.10",
        })
        patcher, _ = _patch_httpx(resp)
        with patcher:
            result = await run_vm_ssh_preflight("freeipa")

        report = result.format_report()
        assert "[VM SSH Pre-flight] All checks passed." == report

    @pytest.mark.asyncio
    async def test_report_format_fixed(self):
        resp = _mock_response(json_data={
            "status": "fixed",
            "vm": "freeipa",
            "ip": "192.168.122.10",
            "fix": "injected host public key",
        })
        patcher, _ = _patch_httpx(resp)
        with patcher:
            result = await run_vm_ssh_preflight("freeipa")

        report = result.format_report()
        assert "[VM SSH Pre-flight]" in report
        assert "Auto-fixed 1 issue(s)" in report
        assert "injected host public key" in report

    @pytest.mark.asyncio
    async def test_label(self):
        resp = _mock_response(json_data={"status": "ok", "vm": "freeipa", "ip": "1.2.3.4"})
        patcher, _ = _patch_httpx(resp)
        with patcher:
            result = await run_vm_ssh_preflight("freeipa")

        assert result.label == "VM SSH Pre-flight"

    @pytest.mark.asyncio
    async def test_unknown_status(self):
        resp = _mock_response(json_data={"status": "something_new"})
        patcher, _ = _patch_httpx(resp)
        with patcher:
            result = await run_vm_ssh_preflight("freeipa")

        assert result.checks[0].status == CheckStatus.WARNING
        assert "Unexpected" in result.checks[0].message
