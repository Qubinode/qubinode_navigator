"""
Tests for the intent router.

Tests handler registration, routing, error handling, and read-only mode.
Uses mock handlers (no backend needed).
"""

import os
import pytest

from intent_parser.models import IntentCategory, IntentResult
from intent_parser.router import register, get_handler, route, _handlers


@pytest.fixture(autouse=True)
def clean_handlers():
    """Clear handler registry before each test."""
    _handlers.clear()
    yield
    _handlers.clear()


@pytest.fixture
def mock_handler():
    """Create a simple mock handler."""

    async def handler(params):
        return f"mock result: {params}"

    return handler


@pytest.fixture
def failing_handler():
    """Create a handler that raises an exception."""

    async def handler(params):
        raise RuntimeError("backend unavailable")

    return handler


class TestHandlerRegistration:
    """Test handler registration mechanics."""

    def test_register_handler(self, mock_handler):
        register(IntentCategory.VM_LIST, mock_handler)
        assert get_handler(IntentCategory.VM_LIST) is mock_handler

    def test_get_unregistered_handler(self):
        assert get_handler(IntentCategory.VM_LIST) is None

    def test_register_multiple(self, mock_handler):
        register(IntentCategory.VM_LIST, mock_handler)
        register(IntentCategory.DAG_LIST, mock_handler)
        assert get_handler(IntentCategory.VM_LIST) is mock_handler
        assert get_handler(IntentCategory.DAG_LIST) is mock_handler

    def test_override_handler(self, mock_handler):
        async def other_handler(params):
            return "other"

        register(IntentCategory.VM_LIST, mock_handler)
        register(IntentCategory.VM_LIST, other_handler)
        assert get_handler(IntentCategory.VM_LIST) is other_handler


class TestRouting:
    """Test the route() function."""

    @pytest.mark.asyncio
    async def test_route_to_handler(self, mock_handler):
        register(IntentCategory.VM_LIST, mock_handler)
        result = await route("list vms")
        assert result.success is True
        assert "mock result" in result.output

    @pytest.mark.asyncio
    async def test_route_unknown_input(self):
        result = await route("asdfghjkl nonsense")
        assert result.success is False
        assert len(result.suggestions) > 0

    @pytest.mark.asyncio
    async def test_route_empty_input(self):
        result = await route("")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_route_help(self):
        result = await route("help")
        assert result.success is True
        assert "VM Operations" in result.output

    @pytest.mark.asyncio
    async def test_route_no_handler(self):
        # Don't register any handlers - should get "no handler" error
        result = await route("list vms")
        assert result.success is False
        assert "No handler" in result.output

    @pytest.mark.asyncio
    async def test_route_handler_error(self, failing_handler):
        register(IntentCategory.VM_LIST, failing_handler)
        result = await route("list vms")
        assert result.success is False
        assert "backend unavailable" in result.output

    @pytest.mark.asyncio
    async def test_route_passes_params(self):
        received_params = {}

        async def capturing_handler(params):
            received_params.update(params)
            return "ok"

        register(IntentCategory.VM_INFO, capturing_handler)
        await route("vm info test-vm-01")
        assert received_params.get("name") == "test-vm-01"


class TestReadOnlyMode:
    """Test read-only mode blocking write operations."""

    @pytest.mark.asyncio
    async def test_write_blocked_in_readonly(self, mock_handler, monkeypatch):
        monkeypatch.setenv("AIRFLOW_MCP_TOOLS_READ_ONLY", "true")
        register(IntentCategory.VM_CREATE, mock_handler)
        result = await route("create a vm named test01")
        assert result.success is False
        assert "read-only" in result.output.lower()

    @pytest.mark.asyncio
    async def test_read_allowed_in_readonly(self, mock_handler, monkeypatch):
        monkeypatch.setenv("AIRFLOW_MCP_TOOLS_READ_ONLY", "true")
        register(IntentCategory.VM_LIST, mock_handler)
        result = await route("list vms")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_write_allowed_when_not_readonly(self, mock_handler, monkeypatch):
        monkeypatch.setenv("AIRFLOW_MCP_TOOLS_READ_ONLY", "false")
        register(IntentCategory.VM_CREATE, mock_handler)
        result = await route("create a vm named test01")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_delete_blocked_in_readonly(self, mock_handler, monkeypatch):
        monkeypatch.setenv("AIRFLOW_MCP_TOOLS_READ_ONLY", "true")
        register(IntentCategory.VM_DELETE, mock_handler)
        result = await route("delete vm test01")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_trigger_blocked_in_readonly(self, mock_handler, monkeypatch):
        monkeypatch.setenv("AIRFLOW_MCP_TOOLS_READ_ONLY", "true")
        register(IntentCategory.DAG_TRIGGER, mock_handler)
        result = await route("trigger dag freeipa_deploy")
        assert result.success is False


class TestIntentResult:
    """Test IntentResult model."""

    def test_success_result(self):
        result = IntentResult(success=True, output="done")
        assert result.success is True
        assert result.error is None
        assert result.suggestions == []

    def test_error_result(self):
        result = IntentResult(
            success=False,
            output="failed",
            error="something broke",
            suggestions=["try again"],
        )
        assert result.success is False
        assert result.error == "something broke"
        assert len(result.suggestions) == 1
