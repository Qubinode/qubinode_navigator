"""
Tests for the SSH pre-flight checks module.

Uses mocked httpx responses to validate all 4 checks, auto-fix logic, and caching.
"""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from intent_parser.ssh_preflight import (
    CheckStatus,
    PreflightCheck,
    PreflightResult,
    clear_cache,
    run_ssh_preflight,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(status_code: int, json_data: dict = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = json.dumps(json_data or {})
    return resp


def _conn_json(login: str = "root", key_file: str = "/root/.ssh/id_rsa"):
    return {
        "connection_id": "localhost_ssh",
        "conn_type": "ssh",
        "host": "localhost",
        "login": login,
        "port": 22,
        "extra": json.dumps({"key_file": key_file}),
    }


def _make_mock_client(**overrides):
    """Create an AsyncMock httpx client with configurable methods."""
    client = AsyncMock()
    for method, mock_val in overrides.items():
        setattr(client, method, mock_val)
    return client


def _patch_httpx_client(client):
    """Return a patch context manager that injects a mock httpx.AsyncClient."""
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return patch("intent_parser.ssh_preflight.httpx.AsyncClient", return_value=mock_ctx)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure cache is clean before and after each test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture(autouse=True)
def _env_defaults(monkeypatch):
    """Set stable env defaults for tests."""
    monkeypatch.setenv("AIRFLOW_API_URL", "http://airflow:8888")
    monkeypatch.setenv("AIRFLOW_USER", "admin")
    monkeypatch.setenv("AIRFLOW_PASSWORD", "admin")
    monkeypatch.setenv("QUBINODE_SSH_USER", "root")
    monkeypatch.setenv("QUBINODE_SSH_CONN_ID", "localhost_ssh")
    monkeypatch.setenv("SSH_PREFLIGHT_CACHE_TTL", "300")


# ---------------------------------------------------------------------------
# Test: Connection exists and all checks pass
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connection_exists_ok():
    """All checks pass when connection exists with correct user and key."""
    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _conn_json())),
        post=AsyncMock(return_value=_mock_response(200, {"status": True})),
    )

    with _patch_httpx_client(client):
        result = await run_ssh_preflight(force=True)

    assert result.can_proceed is True
    assert len(result.checks) == 4
    assert all(c.status == CheckStatus.OK for c in result.checks)
    assert "All checks passed" in result.format_report()


# ---------------------------------------------------------------------------
# Test: Connection missing -> auto-create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connection_missing_auto_create():
    """When connection is missing (404), it should be auto-created."""
    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(404)),
        post=AsyncMock(
            side_effect=[
                _mock_response(201, _conn_json()),
                _mock_response(200, {"status": True}),
            ]
        ),
    )

    with _patch_httpx_client(client):
        result = await run_ssh_preflight(force=True)

    assert result.can_proceed is True
    conn_check = result.checks[0]
    assert conn_check.status == CheckStatus.FIXED
    assert "created" in conn_check.fix_applied.lower()


# ---------------------------------------------------------------------------
# Test: Wrong SSH user -> auto-fix
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wrong_ssh_user_auto_fix():
    """When SSH user doesn't match, it should be patched."""
    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _conn_json(login="wronguser"))),
        patch=AsyncMock(return_value=_mock_response(200, _conn_json(login="root"))),
        post=AsyncMock(return_value=_mock_response(200, {"status": True})),
    )

    with _patch_httpx_client(client):
        result = await run_ssh_preflight(force=True)

    assert result.can_proceed is True
    user_check = [c for c in result.checks if c.name == "ssh_user"][0]
    assert user_check.status == CheckStatus.FIXED
    assert "root" in user_check.fix_applied


# ---------------------------------------------------------------------------
# Test: sshd not reachable -> warning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sshd_not_reachable_warning():
    """When sshd can't be reached, should warn but still allow proceeding."""
    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _conn_json())),
        post=AsyncMock(side_effect=Exception("Connection refused")),
    )

    with _patch_httpx_client(client), patch("intent_parser.ssh_preflight.asyncio.wait_for", new_callable=AsyncMock, side_effect=Exception("Connection refused")):
        result = await run_ssh_preflight(force=True)

    assert result.can_proceed is True
    sshd_check = [c for c in result.checks if c.name == "sshd_reachable"][0]
    assert sshd_check.status == CheckStatus.WARNING
    assert "systemctl" in sshd_check.message


# ---------------------------------------------------------------------------
# Test: No SSH key configured -> warning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_ssh_key_warning():
    """When no SSH key file is configured, should produce a warning."""
    conn = _conn_json()
    conn["extra"] = json.dumps({})  # No key_file

    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, conn)),
        post=AsyncMock(return_value=_mock_response(200, {"status": True})),
    )

    with _patch_httpx_client(client):
        result = await run_ssh_preflight(force=True)

    key_check = [c for c in result.checks if c.name == "ssh_key"][0]
    assert key_check.status == CheckStatus.WARNING
    assert "No SSH key" in key_check.message


# ---------------------------------------------------------------------------
# Test: Cache hit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_hit():
    """Second call should return cached result without API calls."""
    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _conn_json())),
        post=AsyncMock(return_value=_mock_response(200, {"status": True})),
    )

    with _patch_httpx_client(client):
        result1 = await run_ssh_preflight(force=True)

    # Reset mocks
    client.get.reset_mock()
    client.post.reset_mock()

    with _patch_httpx_client(client):
        result2 = await run_ssh_preflight()  # No force -> cache hit

    client.get.assert_not_called()
    client.post.assert_not_called()
    assert len(result2.checks) == len(result1.checks)


# ---------------------------------------------------------------------------
# Test: Cache expired
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_expired(monkeypatch):
    """After TTL expires, checks should run again."""
    monkeypatch.setenv("SSH_PREFLIGHT_CACHE_TTL", "1")  # 1 second TTL

    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _conn_json())),
        post=AsyncMock(return_value=_mock_response(200, {"status": True})),
    )

    with _patch_httpx_client(client):
        await run_ssh_preflight(force=True)

    time.sleep(1.1)

    client.get.reset_mock()
    client.post.reset_mock()

    with _patch_httpx_client(client):
        await run_ssh_preflight()  # Cache expired, should re-run

    client.get.assert_called_once()


# ---------------------------------------------------------------------------
# Test: format_report output
# ---------------------------------------------------------------------------


def test_format_report_all_ok():
    """Report for all-OK should be a single line."""
    result = PreflightResult(
        checks=[
            PreflightCheck(name="a", status=CheckStatus.OK, message="Good"),
            PreflightCheck(name="b", status=CheckStatus.OK, message="Good"),
        ]
    )
    report = result.format_report()
    assert report == "[SSH Pre-flight] All checks passed."


def test_format_report_with_fixes():
    """Report should show auto-fixed count and details."""
    result = PreflightResult(
        checks=[
            PreflightCheck(name="conn", status=CheckStatus.FIXED, message="Created", fix_applied="created connection 'localhost_ssh'"),
            PreflightCheck(name="user", status=CheckStatus.OK, message="OK"),
        ]
    )
    report = result.format_report()
    assert "Auto-fixed 1 issue" in report
    assert "created connection" in report


def test_format_report_with_warnings():
    """Report should include warning messages."""
    result = PreflightResult(
        checks=[
            PreflightCheck(name="ok", status=CheckStatus.OK, message="Fine"),
            PreflightCheck(name="sshd", status=CheckStatus.WARNING, message="Cannot reach sshd"),
        ]
    )
    report = result.format_report()
    assert "WARNING" in report
    assert "Cannot reach sshd" in report


def test_format_report_empty():
    """Empty checks should produce empty report."""
    result = PreflightResult(checks=[])
    assert result.format_report() == ""
