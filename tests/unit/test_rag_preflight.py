"""
Tests for the RAG pre-flight checks module.

Uses mocked httpx responses and filesystem to validate all 4 checks,
auto-fix logic, and caching.
"""

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from intent_parser.ssh_preflight import CheckStatus, PreflightCheck, PreflightResult
from intent_parser.rag_preflight import (
    clear_cache,
    run_rag_preflight,
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


def _health_json(document_count: int = 10, documents_loaded: bool = True):
    return {
        "status": "healthy",
        "services": {
            "rag": {
                "document_count": document_count,
                "documents_loaded": documents_loaded,
            }
        },
    }


def _reload_json(success: bool = True, adrs_loaded: bool = True, rag_documents: int = 15):
    return {
        "success": success,
        "status": {
            "adrs_loaded": adrs_loaded,
            "rag_documents": rag_documents,
        },
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
    return patch("intent_parser.rag_preflight.httpx.AsyncClient", return_value=mock_ctx)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure cache is clean before and after each test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture(autouse=True)
def _env_defaults(monkeypatch):
    """Set stable env defaults for tests."""
    monkeypatch.setenv("AI_ASSISTANT_URL", "http://ai:8080")
    monkeypatch.setenv("QUBINODE_ROOT", "/opt/qubinode_navigator")
    monkeypatch.setenv("RAG_DATA_DIR", "/app/data")
    monkeypatch.setenv("RAG_PREFLIGHT_CACHE_TTL", "300")


# ---------------------------------------------------------------------------
# Test 1: All checks pass
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_checks_pass(tmp_path):
    """ADRs exist, chunks exist, health shows docs loaded -> all OK."""
    # Set up filesystem
    adr_dir = tmp_path / "docs" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "adr-0001.md").write_text("# ADR 1")
    (adr_dir / "adr-0002.md").write_text("# ADR 2")

    chunks_dir = tmp_path / "data" / "rag-docs"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "document_chunks.json").write_text(json.dumps([{"id": 1}] * 50))

    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _health_json(10, True))),
    )

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        result = await run_rag_preflight(force=True)

    assert result.can_proceed is True
    assert len(result.checks) == 3  # No reload needed
    assert all(c.status == CheckStatus.OK for c in result.checks)
    assert "All checks passed" in result.format_report()
    assert "RAG Pre-flight" in result.format_report()


# ---------------------------------------------------------------------------
# Test 2: ADR directory missing -> WARNING
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adr_dir_missing_warning(tmp_path):
    """ADR directory not found -> WARNING."""
    chunks_dir = tmp_path / "data" / "rag-docs"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "document_chunks.json").write_text(json.dumps([{"id": 1}] * 50))

    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _health_json(10, True))),
    )

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        result = await run_rag_preflight(force=True)

    adr_check = [c for c in result.checks if c.name == "adr_source_files"][0]
    assert adr_check.status == CheckStatus.WARNING
    assert "not found" in adr_check.message
    assert result.can_proceed is True


# ---------------------------------------------------------------------------
# Test 3: ADR directory empty -> WARNING
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adr_dir_empty_warning(tmp_path):
    """ADR directory exists but no adr-*.md files -> WARNING."""
    adr_dir = tmp_path / "docs" / "adrs"
    adr_dir.mkdir(parents=True)
    # Create a non-matching file
    (adr_dir / "readme.md").write_text("Not an ADR")

    chunks_dir = tmp_path / "data" / "rag-docs"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "document_chunks.json").write_text(json.dumps([{"id": 1}] * 50))

    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _health_json(10, True))),
    )

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        result = await run_rag_preflight(force=True)

    adr_check = [c for c in result.checks if c.name == "adr_source_files"][0]
    assert adr_check.status == CheckStatus.WARNING
    assert "no adr-*.md" in adr_check.message


# ---------------------------------------------------------------------------
# Test 4: Chunks missing triggers reload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chunks_missing_triggers_reload(tmp_path):
    """No chunks file + 0 docs -> reload triggered -> FIXED."""
    adr_dir = tmp_path / "docs" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "adr-0001.md").write_text("# ADR 1")

    # No chunks file created

    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _health_json(0, False))),
        post=AsyncMock(return_value=_mock_response(200, _reload_json(True, True, 15))),
    )

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        result = await run_rag_preflight(force=True)

    assert result.can_proceed is True
    reload_check = [c for c in result.checks if c.name == "rag_reload"][0]
    assert reload_check.status == CheckStatus.FIXED
    assert "reload" in reload_check.fix_applied.lower()


# ---------------------------------------------------------------------------
# Test 5: Zero docs triggers reload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_zero_docs_triggers_reload(tmp_path):
    """Chunks exist but health shows 0 docs -> reload -> FIXED."""
    adr_dir = tmp_path / "docs" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "adr-0001.md").write_text("# ADR 1")

    chunks_dir = tmp_path / "data" / "rag-docs"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "document_chunks.json").write_text(json.dumps([{"id": 1}] * 50))

    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _health_json(0, False))),
        post=AsyncMock(return_value=_mock_response(200, _reload_json(True, True, 15))),
    )

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        result = await run_rag_preflight(force=True)

    assert result.can_proceed is True
    reload_check = [c for c in result.checks if c.name == "rag_reload"][0]
    assert reload_check.status == CheckStatus.FIXED


# ---------------------------------------------------------------------------
# Test 6: Reload fails gracefully
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reload_fails_gracefully(tmp_path):
    """Reload returns non-200 -> WARNING, can_proceed=True."""
    adr_dir = tmp_path / "docs" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "adr-0001.md").write_text("# ADR 1")

    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _health_json(0, False))),
        post=AsyncMock(return_value=_mock_response(500, {"error": "Internal server error"})),
    )

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        result = await run_rag_preflight(force=True)

    assert result.can_proceed is True
    reload_check = [c for c in result.checks if c.name == "rag_reload"][0]
    assert reload_check.status == CheckStatus.WARNING
    assert "500" in reload_check.message


# ---------------------------------------------------------------------------
# Test 7: Reload succeeds but still empty
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reload_succeeds_but_still_empty(tmp_path):
    """Reload 200 but adrs_loaded=False -> WARNING."""
    adr_dir = tmp_path / "docs" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "adr-0001.md").write_text("# ADR 1")

    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _health_json(0, False))),
        post=AsyncMock(return_value=_mock_response(200, _reload_json(True, False, 0))),
    )

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        result = await run_rag_preflight(force=True)

    assert result.can_proceed is True
    reload_check = [c for c in result.checks if c.name == "rag_reload"][0]
    assert reload_check.status == CheckStatus.WARNING
    assert "adrs_loaded=False" in reload_check.message


# ---------------------------------------------------------------------------
# Test 8: Cache hit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_hit(tmp_path):
    """Second call returns cached result, no HTTP."""
    adr_dir = tmp_path / "docs" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "adr-0001.md").write_text("# ADR 1")

    chunks_dir = tmp_path / "data" / "rag-docs"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "document_chunks.json").write_text(json.dumps([{"id": 1}] * 50))

    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _health_json(10, True))),
    )

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        result1 = await run_rag_preflight(force=True)

    client.get.reset_mock()

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        result2 = await run_rag_preflight()  # No force -> cache hit

    client.get.assert_not_called()
    assert len(result2.checks) == len(result1.checks)


# ---------------------------------------------------------------------------
# Test 9: Cache expired
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_expired(tmp_path, monkeypatch):
    """After TTL, checks run again."""
    monkeypatch.setenv("RAG_PREFLIGHT_CACHE_TTL", "1")

    adr_dir = tmp_path / "docs" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "adr-0001.md").write_text("# ADR 1")

    chunks_dir = tmp_path / "data" / "rag-docs"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "document_chunks.json").write_text(json.dumps([{"id": 1}] * 50))

    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _health_json(10, True))),
    )

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        await run_rag_preflight(force=True)

    time.sleep(1.1)

    client.get.reset_mock()

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        await run_rag_preflight()  # Cache expired, should re-run

    client.get.assert_called_once()


# ---------------------------------------------------------------------------
# Test 10: Cache bypass with force
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_bypass_with_force(tmp_path):
    """force=True ignores cache."""
    adr_dir = tmp_path / "docs" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "adr-0001.md").write_text("# ADR 1")

    chunks_dir = tmp_path / "data" / "rag-docs"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "document_chunks.json").write_text(json.dumps([{"id": 1}] * 50))

    client = _make_mock_client(
        get=AsyncMock(return_value=_mock_response(200, _health_json(10, True))),
    )

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        await run_rag_preflight(force=True)

    client.get.reset_mock()

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        await run_rag_preflight(force=True)  # Force bypasses cache

    client.get.assert_called_once()


# ---------------------------------------------------------------------------
# Test 11: format_report all OK
# ---------------------------------------------------------------------------

def test_format_report_all_ok():
    """Report for all-OK should use RAG Pre-flight label."""
    result = PreflightResult(
        checks=[
            PreflightCheck(name="a", status=CheckStatus.OK, message="Good"),
            PreflightCheck(name="b", status=CheckStatus.OK, message="Good"),
        ],
        label="RAG Pre-flight",
    )
    report = result.format_report()
    assert report == "[RAG Pre-flight] All checks passed."


# ---------------------------------------------------------------------------
# Test 12: format_report with fixes
# ---------------------------------------------------------------------------

def test_format_report_with_fixes():
    """Report should show auto-fix count and details with RAG label."""
    result = PreflightResult(
        checks=[
            PreflightCheck(
                name="reload", status=CheckStatus.FIXED, message="Reloaded",
                fix_applied="triggered /orchestrator/context/reload (15 docs loaded)",
            ),
            PreflightCheck(name="adr", status=CheckStatus.OK, message="OK"),
        ],
        label="RAG Pre-flight",
    )
    report = result.format_report()
    assert "[RAG Pre-flight]" in report
    assert "Auto-fixed 1 issue" in report
    assert "reload" in report


# ---------------------------------------------------------------------------
# Test 13: AI Assistant unreachable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_assistant_unreachable(tmp_path):
    """HTTP exception -> WARNING, can_proceed=True."""
    adr_dir = tmp_path / "docs" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "adr-0001.md").write_text("# ADR 1")

    chunks_dir = tmp_path / "data" / "rag-docs"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "document_chunks.json").write_text(json.dumps([{"id": 1}] * 50))

    client = _make_mock_client(
        get=AsyncMock(side_effect=Exception("Connection refused")),
        post=AsyncMock(side_effect=Exception("Connection refused")),
    )

    with _patch_httpx_client(client), \
         patch.dict("os.environ", {"QUBINODE_ROOT": str(tmp_path), "RAG_DATA_DIR": str(tmp_path / "data")}):
        result = await run_rag_preflight(force=True)

    assert result.can_proceed is True
    doc_check = [c for c in result.checks if c.name == "rag_document_count"][0]
    assert doc_check.status == CheckStatus.WARNING
    assert "Cannot reach" in doc_check.message
